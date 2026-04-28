from __future__ import annotations

import argparse
import http.client
import json
import threading
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from backend.app.db.session import SessionLocal
from backend.app.models import EmbeddingIndexMetadata, Segment, TextVersion, Work
from backend.app.services import vector_service


STEP_LOCATIONS = {
    "STEP 1": "backend/app/services/vector_service.py:794-820",
    "STEP 2": "backend/app/services/vector_service.py:823-831",
    "STEP 3": "backend/app/services/vector_service.py:193-305",
    "STEP 4": "backend/app/services/vector_service.py:372-453",
}


@dataclass(slots=True)
class DebugContext:
    start_after_segment_id: str
    max_segments: int
    select_timeout_seconds: int
    filter_timeout_seconds: int
    embedding_timeout_seconds: int
    write_timeout_seconds: int


@dataclass(slots=True)
class StepResult:
    records: list[dict[str, Any]]
    raw_segments: list[dict[str, Any]]
    runtime: Optional[vector_service.EmbeddingRuntime] = None
    embeddings: Optional[list[list[float]]] = None


LAST_LOG_LINE: str = ""


def log(message: str) -> None:
    global LAST_LOG_LINE
    LAST_LOG_LINE = message
    print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug a single frontier embedding worker batch.")
    parser.add_argument("--start-after-segment-id", default="seg-cbeta-t0001-2355")
    parser.add_argument("--max-segments", type=int, default=10)
    parser.add_argument("--select-timeout-seconds", type=int, default=30)
    parser.add_argument("--filter-timeout-seconds", type=int, default=30)
    parser.add_argument("--embedding-timeout-seconds", type=int, default=180)
    parser.add_argument("--write-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def run_with_timeout(
    *,
    step_name: str,
    timeout_seconds: int,
    fn: Callable[[], Any],
) -> Any:
    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def target() -> None:
        try:
            result_box["value"] = fn()
        except BaseException as exc:  # pragma: no cover - debug helper
            error_box["error"] = exc
            error_box["traceback"] = traceback.format_exc()

    started = time.monotonic()
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        log(f"{step_name}: HARD TIMEOUT after {timeout_seconds}s")
        log(f"{step_name}: LAST LOG BEFORE TIMEOUT -> {LAST_LOG_LINE}")
        log(f"{step_name}: CODE LOCATION -> {STEP_LOCATIONS[step_name]}")
        raise TimeoutError(f"{step_name} exceeded {timeout_seconds}s")

    elapsed = time.monotonic() - started
    if "error" in error_box:
        log(f"{step_name}: EXCEPTION after {elapsed:.3f}s")
        log(str(error_box["error"]))
        log(str(error_box["traceback"]))
        log(f"{step_name}: LAST LOG BEFORE FAILURE -> {LAST_LOG_LINE}")
        log(f"{step_name}: CODE LOCATION -> {STEP_LOCATIONS[step_name]}")
        raise error_box["error"]

    return result_box.get("value"), elapsed


def _segment_to_record(segment: Segment) -> dict[str, Any]:
    return {
        "id": segment.id,
        "content": segment.content,
        "normalized_content": segment.normalized_content or segment.content,
        "work_id": segment.text_version.work.id,
        "text_version_id": segment.text_version.id,
        "tradition_id": segment.text_version.work.tradition.id,
        "collection_id": segment.text_version.work.collection.id,
        "language_id": segment.text_version.language.id,
    }


def step_1_select_segments(context: DebugContext) -> StepResult:
    log("STEP 1: select segments start")
    with SessionLocal() as session:
        stmt = (
            select(Segment)
            .options(
                selectinload(Segment.text_version).selectinload(TextVersion.language),
                selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
                selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
            )
            .join(Segment.text_version)
            .join(TextVersion.work)
            .where(Segment.id > context.start_after_segment_id)
            .order_by(Segment.id)
            .limit(context.max_segments)
        )
        segments = session.scalars(stmt).unique().all()

    records = [_segment_to_record(segment) for segment in segments]
    log(
        "STEP 1: select segments end "
        f"count={len(records)} first_id={(records[0]['id'] if records else None)} "
        f"last_id={(records[-1]['id'] if records else None)}"
    )
    return StepResult(records=records, raw_segments=records)


def step_2_filter_completed(step_1: StepResult) -> StepResult:
    log("STEP 2: filter/check completed start")
    ids = [record["id"] for record in step_1.records]
    with SessionLocal() as session:
        completed_ids = set(
            session.scalars(
                select(EmbeddingIndexMetadata.owner_id).where(
                    EmbeddingIndexMetadata.owner_type == "segment",
                    EmbeddingIndexMetadata.owner_id.in_(ids),
                    EmbeddingIndexMetadata.embedding_model == vector_service.settings.embedding_model,
                )
            ).all()
        )

    filtered = [record for record in step_1.records if record["id"] not in completed_ids]
    log(
        "STEP 2: filter/check completed end "
        f"input={len(step_1.records)} completed={len(completed_ids)} remaining={len(filtered)} "
        f"first_remaining={(filtered[0]['id'] if filtered else None)}"
    )
    return StepResult(records=filtered, raw_segments=step_1.raw_segments)


def _debug_embed_batch(
    text_values: list[str],
    *,
    runtime: vector_service.EmbeddingRuntime,
    batch_label: str,
    depth: int = 0,
) -> list[list[float]]:
    indent = "  " * depth
    headers = {"Content-Type": "application/json"}
    if vector_service.settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {vector_service.settings.embedding_api_key}"

    request_body = {
        "model": runtime.model,
        "input": text_values,
        "dimensions": runtime.dimension,
    }
    request_payload = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        vector_service.settings.embedding_api_url,
        data=request_payload,
        headers=headers,
        method="POST",
    )

    retry_delay = vector_service.OPENAI_COMPATIBLE_RETRY_DELAY_SECONDS
    for attempt in range(vector_service.OPENAI_COMPATIBLE_MAX_RETRIES + 1):
        attempt_started = time.monotonic()
        log(
            f"STEP 3: {indent}batch={batch_label} attempt={attempt + 1} request start "
            f"count={len(text_values)}"
        )
        try:
            with urllib.request.urlopen(request, timeout=vector_service.settings.embedding_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            rows = payload.get("data")
            if not isinstance(rows, list) or len(rows) != len(text_values):
                raise ValueError("Embedding provider returned an unexpected number of embeddings.")
            ordered_rows = sorted(rows, key=lambda item: int(item.get("index", 0)))
            embeddings: list[list[float]] = []
            for row in ordered_rows:
                embedding = row.get("embedding")
                if not isinstance(embedding, list):
                    raise ValueError("Embedding provider returned a malformed embedding payload.")
                vector = [float(value) for value in embedding]
                embeddings.append(vector)
            elapsed = time.monotonic() - attempt_started
            dimension = len(embeddings[0]) if embeddings else 0
            log(
                f"STEP 3: {indent}batch={batch_label} attempt={attempt + 1} request end "
                f"elapsed={elapsed:.3f}s returned={len(embeddings)} dimension={dimension}"
            )
            return embeddings
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            elapsed = time.monotonic() - attempt_started
            log(
                f"STEP 3: {indent}batch={batch_label} attempt={attempt + 1} HTTPError "
                f"code={exc.code} elapsed={elapsed:.3f}s body={error_body}"
            )
            if exc.code == 429 and attempt < vector_service.OPENAI_COMPATIBLE_MAX_RETRIES:
                log(f"STEP 3: {indent}batch={batch_label} retry sleep={retry_delay}s reason=429")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            if exc.code >= 500:
                if len(text_values) > 1:
                    midpoint = max(1, len(text_values) // 2)
                    log(
                        f"STEP 3: {indent}batch={batch_label} split on 5xx "
                        f"left={midpoint} right={len(text_values) - midpoint}"
                    )
                    return _debug_embed_batch(
                        text_values[:midpoint],
                        runtime=runtime,
                        batch_label=f"{batch_label}.L",
                        depth=depth + 1,
                    ) + _debug_embed_batch(
                        text_values[midpoint:],
                        runtime=runtime,
                        batch_label=f"{batch_label}.R",
                        depth=depth + 1,
                    )
                if attempt < vector_service.OPENAI_COMPATIBLE_MAX_RETRIES:
                    log(f"STEP 3: {indent}batch={batch_label} retry sleep={retry_delay}s reason=5xx-single")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            raise
        except urllib.error.URLError as exc:
            elapsed = time.monotonic() - attempt_started
            log(
                f"STEP 3: {indent}batch={batch_label} attempt={attempt + 1} URLError "
                f"elapsed={elapsed:.3f}s reason={exc.reason}"
            )
            if attempt < vector_service.OPENAI_COMPATIBLE_MAX_RETRIES:
                log(f"STEP 3: {indent}batch={batch_label} retry sleep={retry_delay}s reason=urlerror")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise
        except http.client.IncompleteRead as exc:
            elapsed = time.monotonic() - attempt_started
            log(
                f"STEP 3: {indent}batch={batch_label} attempt={attempt + 1} IncompleteRead "
                f"elapsed={elapsed:.3f}s partial={len(exc.partial)} expected_more={exc.expected}"
            )
            if attempt < vector_service.OPENAI_COMPATIBLE_MAX_RETRIES:
                log(f"STEP 3: {indent}batch={batch_label} retry sleep={retry_delay}s reason=incomplete-read")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise

    raise RuntimeError("STEP 3 exhausted retries")


def step_3_request_embeddings(step_2: StepResult) -> StepResult:
    log("STEP 3: request embeddings start")
    runtime = vector_service.resolve_embedding_runtime()
    texts = [record.get("normalized_content") or record.get("content") or "" for record in step_2.records]
    embeddings = _debug_embed_batch(texts, runtime=runtime, batch_label="frontier")
    dimension = len(embeddings[0]) if embeddings else 0
    log(
        "STEP 3: request embeddings end "
        f"returned={len(embeddings)} dimension={dimension}"
    )
    return StepResult(records=step_2.records, raw_segments=step_2.raw_segments, runtime=runtime, embeddings=embeddings)


def step_4_write_pgvector(step_3: StepResult) -> int:
    if step_3.runtime is None or step_3.embeddings is None:
        raise ValueError("STEP 4 requires runtime and embeddings.")

    log("STEP 4: write pgvector start")
    log("STEP 4: session open start")
    with SessionLocal() as session:
        log("STEP 4: session open end")
        log("STEP 4: session.connection start")
        connection = session.connection()
        log("STEP 4: session.connection end")
        log("STEP 4: ensure_postgres_vector_objects start")
        vector_service.ensure_postgres_vector_objects(connection, dimension=step_3.runtime.dimension)
        log("STEP 4: ensure_postgres_vector_objects end")
        log("STEP 4: advisory lock start")
        session.execute(text("SELECT pg_advisory_xact_lock(334455)"))
        log("STEP 4: advisory lock end")

        payloads: list[dict[str, Any]] = []
        metadata_rows: list[EmbeddingIndexMetadata] = []
        for record, embedding in zip(step_3.records, step_3.embeddings):
            content_hash = vector_service._segment_content_hash(record)
            metadata_json = vector_service._embedding_index_metadata(
                record,
                runtime=step_3.runtime,
                content_hash=content_hash,
            )
            payloads.append(
                {
                    "segment_id": record["id"],
                    "embedding_model": step_3.runtime.model,
                    "embedding": vector_service._vector_literal(embedding),
                    "content_hash": content_hash,
                    "metadata_json": json.dumps(metadata_json, ensure_ascii=False),
                }
            )
            metadata_rows.append(
                EmbeddingIndexMetadata(
                    id=vector_service._embedding_metadata_id(
                        owner_type="segment",
                        owner_id=record["id"],
                        embedding_model=step_3.runtime.model,
                    ),
                    owner_type="segment",
                    owner_id=record["id"],
                    chunk_scope="segment",
                    embedding_model=step_3.runtime.model,
                    vector_backend="pgvector",
                    dimension=step_3.runtime.dimension,
                    status="indexed",
                    indexed_at=vector_service.datetime.utcnow(),
                    metadata_json=metadata_json,
                )
            )

        log("STEP 4: pgvector insert start")
        session.execute(
            text(
                """
                INSERT INTO segment_embeddings (
                    segment_id,
                    embedding_model,
                    embedding,
                    content_hash,
                    indexed_at,
                    metadata_json
                )
                VALUES (
                    :segment_id,
                    :embedding_model,
                    CAST(:embedding AS vector),
                    :content_hash,
                    NOW(),
                    CAST(:metadata_json AS jsonb)
                )
                ON CONFLICT (segment_id, embedding_model)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    content_hash = EXCLUDED.content_hash,
                    indexed_at = NOW(),
                    metadata_json = EXCLUDED.metadata_json
                """
            ),
            payloads,
        )
        log(f"STEP 4: pgvector insert end rows={len(payloads)}")

        log("STEP 4: metadata refresh start")
        session.query(EmbeddingIndexMetadata).filter(
            EmbeddingIndexMetadata.owner_type == "segment",
            EmbeddingIndexMetadata.owner_id.in_([record["id"] for record in step_3.records]),
            EmbeddingIndexMetadata.embedding_model == step_3.runtime.model,
        ).delete(synchronize_session=False)
        session.add_all(metadata_rows)
        log("STEP 4: metadata refresh end")

        log("STEP 4: commit start")
        session.commit()
        log("STEP 4: commit end")

    log("STEP 4: write pgvector end")
    return len(payloads)


def main() -> None:
    args = parse_args()
    context = DebugContext(
        start_after_segment_id=args.start_after_segment_id,
        max_segments=args.max_segments,
        select_timeout_seconds=args.select_timeout_seconds,
        filter_timeout_seconds=args.filter_timeout_seconds,
        embedding_timeout_seconds=args.embedding_timeout_seconds,
        write_timeout_seconds=args.write_timeout_seconds,
    )

    step_1_result, step_1_elapsed = run_with_timeout(
        step_name="STEP 1",
        timeout_seconds=context.select_timeout_seconds,
        fn=lambda: step_1_select_segments(context),
    )
    log(f"STEP 1: elapsed={step_1_elapsed:.3f}s")

    step_2_result, step_2_elapsed = run_with_timeout(
        step_name="STEP 2",
        timeout_seconds=context.filter_timeout_seconds,
        fn=lambda: step_2_filter_completed(step_1_result),
    )
    log(f"STEP 2: elapsed={step_2_elapsed:.3f}s")

    step_3_result, step_3_elapsed = run_with_timeout(
        step_name="STEP 3",
        timeout_seconds=context.embedding_timeout_seconds,
        fn=lambda: step_3_request_embeddings(step_2_result),
    )
    log(f"STEP 3: elapsed={step_3_elapsed:.3f}s")

    written_count, step_4_elapsed = run_with_timeout(
        step_name="STEP 4",
        timeout_seconds=context.write_timeout_seconds,
        fn=lambda: step_4_write_pgvector(step_3_result),
    )
    log(f"STEP 4: elapsed={step_4_elapsed:.3f}s written={written_count}")


if __name__ == "__main__":
    main()
