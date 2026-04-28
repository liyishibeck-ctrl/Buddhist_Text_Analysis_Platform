from __future__ import annotations

import asyncio
import base64
import json
import math
import random
import socket
import sys
import time
import urllib.error
import urllib.request
from array import array
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models import EmbeddingIndexMetadata, Segment, TextVersion, Work
from backend.app.services.vector_service import (
    DEFAULT_EMBEDDING_CONTENT_FIELD,
    EmbeddingRuntime,
    OPENAI_COMPATIBLE_EMBEDDING_PROVIDER,
    _embedding_index_metadata,
    _embedding_metadata_id,
    _qualified_segment_embeddings_table,
    _segment_content_hash,
    ensure_postgres_vector_objects,
    resolve_embedding_content_field,
    resolve_embedding_runtime,
    resolve_storage_embedding_model,
    segment_text_value,
)


REALTIME_EMBEDDING_MODEL = "text-embedding-3-large"
REALTIME_EMBEDDING_DIMENSION = 2048
REALTIME_MAX_SEGMENTS_PER_REQUEST = 512
REALTIME_MAX_TOKENS_PER_REQUEST = 100_000
REALTIME_MAX_SINGLE_SEGMENT_TOKENS = 8_192
REALTIME_MAX_REQUEST_TIMEOUT_SECONDS = 120.0
REALTIME_MAX_RETRIES = 8
REALTIME_INITIAL_BACKOFF_SECONDS = 2.0
REALTIME_STAGING_TABLE_NAME = "segment_embedding_staging"
REALTIME_DB_WRITE_MAX_RETRIES = 3
REALTIME_DB_WRITE_INITIAL_BACKOFF_SECONDS = 2.0
TIBETAN_CONSERVATIVE_TOKEN_MULTIPLIER = 1.8


@dataclass(slots=True)
class RealtimeEmbeddingCandidate:
    record: dict[str, Any]
    token_count: int
    text_length: int
    routing_token_count: int


@dataclass(slots=True)
class RealtimeEmbeddingBatch:
    records: list[dict[str, Any]]
    token_count: int


@dataclass(slots=True)
class RealtimeEmbeddingResponse:
    payloads: list[dict[str, Any]]
    tokens_used: int
    skipped_records: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class RealtimeEmbeddingStats:
    started_at_monotonic: float = field(default_factory=time.monotonic)
    started_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_missing: int = 0
    processed: int = 0
    failed: int = 0
    skipped_oversize: int = 0
    tokens_used: int = 0
    resume_after_segment_id: Optional[str] = None
    completed_scan: bool = False

    def snapshot(self) -> dict[str, Any]:
        elapsed_seconds = max(0.001, time.monotonic() - self.started_at_monotonic)
        elapsed_minutes = elapsed_seconds / 60.0
        return {
            "total_missing": self.total_missing,
            "processed": self.processed,
            "failed": self.failed,
            "tokens_used": self.tokens_used,
            "elapsed_time": elapsed_seconds,
            "segments_per_min": self.processed / elapsed_minutes,
            "tokens_per_min": self.tokens_used / elapsed_minutes,
            "started_at": self.started_at_utc,
            "resume_after_segment_id": self.resume_after_segment_id,
            "completed_scan": self.completed_scan,
        }


def _realtime_staging_table() -> str:
    schema_name = settings.pgvector_schema_hint or "public"
    return f"{schema_name}.{REALTIME_STAGING_TABLE_NAME}"


def validate_realtime_runtime(runtime: EmbeddingRuntime) -> None:
    if runtime.provider != OPENAI_COMPATIBLE_EMBEDDING_PROVIDER:
        raise ValueError("Realtime embedding worker requires EMBEDDING_PROVIDER=openai-compatible.")
    if runtime.model != REALTIME_EMBEDDING_MODEL:
        raise ValueError(
            f"Realtime embedding worker requires EMBEDDING_MODEL={REALTIME_EMBEDDING_MODEL}, "
            f"but resolved {runtime.model!r}."
        )
    if runtime.dimension != REALTIME_EMBEDDING_DIMENSION:
        raise ValueError(
            f"Realtime embedding worker requires EMBEDDING_DIMENSION={REALTIME_EMBEDDING_DIMENSION}, "
            f"but resolved {runtime.dimension}."
        )


def _advisory_lock_sql() -> Any:
    return text("SELECT pg_advisory_xact_lock(334455)")


def _acquire_embedding_write_lock(session: Session) -> None:
    session.execute(_advisory_lock_sql())


def ensure_realtime_embedding_tables(connection, *, dimension: int) -> None:  # type: ignore[no-untyped-def]
    ensure_postgres_vector_objects(connection, dimension=dimension)
    qualified_staging_table = _realtime_staging_table()
    existing_table = connection.execute(
        text("SELECT to_regclass(:qualified_name)"),
        {"qualified_name": qualified_staging_table},
    ).scalar()
    if not existing_table:
        connection.exec_driver_sql(
            f"""
            CREATE TABLE {qualified_staging_table} (
                stage_id BIGSERIAL PRIMARY KEY,
                run_id VARCHAR(64) NOT NULL,
                metadata_id VARCHAR(64) NOT NULL,
                segment_id VARCHAR(64) NOT NULL,
                embedding_model VARCHAR(128) NOT NULL,
                dimension INTEGER NOT NULL,
                field_name VARCHAR(64) NOT NULL,
                tradition_id VARCHAR(64),
                content_hash VARCHAR(64) NOT NULL,
                metadata_json JSONB NOT NULL,
                embedding vector({dimension}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    connection.exec_driver_sql(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{REALTIME_STAGING_TABLE_NAME}_run_created
        ON {qualified_staging_table} (run_id, created_at)
        """
    )
    connection.exec_driver_sql(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{REALTIME_STAGING_TABLE_NAME}_segment_model
        ON {qualified_staging_table} (segment_id, embedding_model)
        """
    )


@lru_cache(maxsize=1)
def _token_encoder():  # type: ignore[no-untyped-def]
    import tiktoken  # type: ignore[import-not-found]

    try:
        return tiktoken.encoding_for_model(REALTIME_EMBEDDING_MODEL)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def estimate_segment_tokens(text_value: str) -> int:
    stripped = (text_value or "").strip()
    if not stripped:
        return 0
    try:
        encoder = _token_encoder()
        return len(encoder.encode(stripped))
    except Exception:
        return max(1, len(stripped.encode("utf-8")) // 4)


def estimate_routing_tokens(
    record: dict[str, Any],
    *,
    text_value: str,
    token_count: int,
) -> int:
    text_length = len(text_value)
    if record.get("tradition_id") == "trad-tibetan":
        conservative_by_length = math.ceil(text_length * TIBETAN_CONSERVATIVE_TOKEN_MULTIPLIER)
        return max(token_count, conservative_by_length)
    return token_count


def decode_base64_embedding(encoded_value: str, *, dimension: int) -> list[float]:
    decoded = base64.b64decode(encoded_value)
    values = array("f")
    values.frombytes(decoded)
    if sys.byteorder != "little":
        values.byteswap()
    if len(values) != dimension:
        raise ValueError(f"Embedding returned {len(values)} dimensions; expected {dimension}.")
    return [float(value) for value in values]


def _embed_request(runtime: EmbeddingRuntime, text_values: list[str]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if runtime.api_key:
        headers["Authorization"] = f"Bearer {runtime.api_key}"
    request_body = {
        "model": runtime.model,
        "input": text_values,
        "dimensions": runtime.dimension,
        "encoding_format": "base64",
    }
    request_payload = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        runtime.api_url,
        data=request_payload,
        headers=headers,
        method="POST",
    )
    request_timeout_seconds = min(float(runtime.timeout_seconds), REALTIME_MAX_REQUEST_TIMEOUT_SECONDS)
    with urllib.request.urlopen(request, timeout=request_timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def request_realtime_embeddings(
    records: list[dict[str, Any]],
    *,
    runtime: EmbeddingRuntime,
    content_field: str,
) -> RealtimeEmbeddingResponse:
    if not records:
        return RealtimeEmbeddingResponse(payloads=[], tokens_used=0, skipped_records=[])
    text_values = [segment_text_value(record, content_field=content_field) for record in records]
    backoff_seconds = REALTIME_INITIAL_BACKOFF_SECONDS
    last_error: str | None = None

    for attempt in range(REALTIME_MAX_RETRIES + 1):
        try:
            payload = _embed_request(runtime, text_values)
            break
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            retry_after_header = exc.headers.get("Retry-After") if exc.headers else None
            retry_after = float(retry_after_header) if retry_after_header and retry_after_header.isdigit() else 0.0
            last_error = f"HTTP {exc.code}: {error_body}"
            if exc.code == 400 and "maximum input length is 8192 tokens" in error_body:
                if len(records) == 1:
                    return RealtimeEmbeddingResponse(payloads=[], tokens_used=0, skipped_records=[records[0]])
                midpoint = max(1, len(records) // 2)
                left = request_realtime_embeddings(
                    records[:midpoint],
                    runtime=runtime,
                    content_field=content_field,
                )
                right = request_realtime_embeddings(
                    records[midpoint:],
                    runtime=runtime,
                    content_field=content_field,
                )
                return RealtimeEmbeddingResponse(
                    payloads=left.payloads + right.payloads,
                    tokens_used=left.tokens_used + right.tokens_used,
                    skipped_records=left.skipped_records + right.skipped_records,
                )
            if exc.code == 429 or exc.code >= 500:
                if attempt < REALTIME_MAX_RETRIES:
                    time.sleep(max(backoff_seconds, retry_after))
                    backoff_seconds *= 2
                    continue
            raise RuntimeError(last_error) from exc
        except urllib.error.URLError as exc:
            last_error = f"URL error: {exc.reason}"
            if attempt < REALTIME_MAX_RETRIES:
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
                continue
            raise RuntimeError(last_error) from exc
        except (TimeoutError, socket.timeout) as exc:
            last_error = f"Timeout: {exc}"
            if attempt < REALTIME_MAX_RETRIES:
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
                continue
            raise RuntimeError(last_error) from exc
    else:
        raise RuntimeError(last_error or "Embedding request exhausted retries.")

    response_rows = payload.get("data")
    if not isinstance(response_rows, list):
        raise ValueError("Embedding response did not include a data array.")

    row_by_index: dict[int, dict[str, Any]] = {}
    for row in response_rows:
        index = int(row.get("index", -1))
        row_by_index[index] = row

    staged_payloads: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        row = row_by_index.get(index)
        if row is None:
            raise ValueError(f"Embedding response omitted input index {index}.")
        embedding_payload = row.get("embedding")
        if isinstance(embedding_payload, str):
            embedding = decode_base64_embedding(embedding_payload, dimension=runtime.dimension)
        elif isinstance(embedding_payload, list):
            embedding = [float(value) for value in embedding_payload]
        else:
            raise ValueError(f"Embedding payload at index {index} is malformed.")
        if len(embedding) != runtime.dimension:
            raise ValueError(
                f"Embedding response for index {index} returned {len(embedding)} dimensions; "
                f"expected {runtime.dimension}."
            )
        staged_payloads.append(
            {
                "record": record,
                "embedding": embedding,
            }
        )

    usage = payload.get("usage") or {}
    tokens_used = int(usage.get("total_tokens") or usage.get("prompt_tokens") or 0)
    return RealtimeEmbeddingResponse(payloads=staged_payloads, tokens_used=tokens_used)


def _segment_record_payload(segment: Segment) -> dict[str, Any]:
    return {
        "id": segment.id,
        "content": segment.content,
        "normalized_content": segment.normalized_content or segment.content,
        "content_gloss": segment.content_gloss,
        "segment_key": segment.segment_key,
        "work_id": segment.text_version.work.id,
        "text_version_id": segment.text_version.id,
        "tradition_id": segment.text_version.work.tradition.id,
        "collection_id": segment.text_version.work.collection.id,
        "language_id": segment.text_version.language.id,
    }


def _needs_realtime_embedding(
    record: dict[str, Any],
    metadata: EmbeddingIndexMetadata | None,
    *,
    runtime: EmbeddingRuntime,
    content_field: str,
) -> bool:
    if metadata is None:
        return True
    if metadata.embedding_model != resolve_storage_embedding_model(runtime.model, content_field=content_field):
        return True
    if metadata.dimension != runtime.dimension:
        return True
    if metadata.status != "indexed":
        return True
    metadata_json = metadata.metadata_json or {}
    if str(metadata_json.get("content_field") or DEFAULT_EMBEDDING_CONTENT_FIELD) != content_field:
        return True
    if str(metadata_json.get("tradition_id") or "") != str(record["tradition_id"]):
        return True
    return False


def fetch_pending_realtime_candidates(
    session: Session,
    *,
    runtime: EmbeddingRuntime,
    content_field: str,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    start_after_segment_id: Optional[str],
    scan_limit: int,
    min_text_length: Optional[int],
    max_text_length: Optional[int],
    min_routing_tokens: Optional[int],
    max_routing_tokens: Optional[int],
) -> tuple[list[RealtimeEmbeddingCandidate], Optional[str], bool]:
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=content_field)
    stmt = (
        select(Segment)
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
        )
        .join(Segment.text_version)
        .join(TextVersion.work)
        .order_by(Segment.id)
        .limit(scan_limit)
    )
    if start_after_segment_id:
        stmt = stmt.where(Segment.id > start_after_segment_id)
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    if collection_id:
        stmt = stmt.where(Work.collection_id == collection_id)
    if language_id:
        stmt = stmt.where(TextVersion.language_id == language_id)

    segments = session.scalars(stmt).unique().all()
    if not segments:
        return [], start_after_segment_id, True

    segment_ids = [segment.id for segment in segments]
    indexed_rows = session.scalars(
        select(EmbeddingIndexMetadata).where(
            EmbeddingIndexMetadata.owner_type == "segment",
            EmbeddingIndexMetadata.owner_id.in_(segment_ids),
            EmbeddingIndexMetadata.embedding_model == storage_embedding_model,
        )
    ).all()
    indexed_by_id = {row.owner_id: row for row in indexed_rows}

    candidates: list[RealtimeEmbeddingCandidate] = []
    for segment in segments:
        record = _segment_record_payload(segment)
        text_value = segment_text_value(record, content_field=content_field).strip()
        if not text_value:
            continue
        metadata = indexed_by_id.get(segment.id)
        if not _needs_realtime_embedding(record, metadata, runtime=runtime, content_field=content_field):
            continue
        text_length = len(text_value)
        if min_text_length is not None and text_length < min_text_length:
            continue
        if max_text_length is not None and text_length > max_text_length:
            continue
        token_count = estimate_segment_tokens(text_value)
        routing_token_count = estimate_routing_tokens(record, text_value=text_value, token_count=token_count)
        if min_routing_tokens is not None and routing_token_count < min_routing_tokens:
            continue
        if max_routing_tokens is not None and routing_token_count > max_routing_tokens:
            continue
        candidates.append(
            RealtimeEmbeddingCandidate(
                record=record,
                token_count=token_count,
                text_length=text_length,
                routing_token_count=routing_token_count,
            )
        )

    return candidates, segments[-1].id, False


def scan_pending_realtime_candidates(
    *,
    runtime: EmbeddingRuntime,
    content_field: str,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    start_after_segment_id: Optional[str],
    scan_limit: int,
    min_text_length: Optional[int],
    max_text_length: Optional[int],
    min_routing_tokens: Optional[int],
    max_routing_tokens: Optional[int],
) -> tuple[list[RealtimeEmbeddingCandidate], Optional[str], bool]:
    with SessionLocal() as session:
        return fetch_pending_realtime_candidates(
            session,
            runtime=runtime,
            content_field=content_field,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
            start_after_segment_id=start_after_segment_id,
            scan_limit=scan_limit,
            min_text_length=min_text_length,
            max_text_length=max_text_length,
            min_routing_tokens=min_routing_tokens,
            max_routing_tokens=max_routing_tokens,
        )


def pack_realtime_batches(
    candidates: Iterable[RealtimeEmbeddingCandidate],
    *,
    max_segments_per_request: int,
    max_tokens_per_request: int,
    max_single_segment_tokens: int,
) -> tuple[list[RealtimeEmbeddingBatch], list[RealtimeEmbeddingCandidate]]:
    batches: list[RealtimeEmbeddingBatch] = []
    oversize: list[RealtimeEmbeddingCandidate] = []
    current_records: list[dict[str, Any]] = []
    current_tokens = 0

    for candidate in candidates:
        if candidate.token_count <= 0:
            continue
        if candidate.token_count > max_single_segment_tokens or candidate.token_count > max_tokens_per_request:
            oversize.append(candidate)
            continue
        if current_records and (
            len(current_records) >= max_segments_per_request
            or current_tokens + candidate.token_count > max_tokens_per_request
        ):
            batches.append(RealtimeEmbeddingBatch(records=current_records, token_count=current_tokens))
            current_records = []
            current_tokens = 0
        current_records.append(candidate.record)
        current_tokens += candidate.token_count

    if current_records:
        batches.append(RealtimeEmbeddingBatch(records=current_records, token_count=current_tokens))
    return batches, oversize


def _stage_rows_payload(
    response: RealtimeEmbeddingResponse,
    *,
    runtime: EmbeddingRuntime,
    content_field: str,
    run_id: str,
) -> list[dict[str, Any]]:
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=content_field)
    payloads: list[dict[str, Any]] = []
    for item in response.payloads:
        record = item["record"]
        embedding = item["embedding"]
        content_hash = _segment_content_hash(record, content_field=content_field)
        metadata_json = _embedding_index_metadata(
            record,
            runtime=runtime,
            content_hash=content_hash,
            content_field=content_field,
            storage_embedding_model=storage_embedding_model,
        )
        payloads.append(
            {
                "run_id": run_id,
                "metadata_id": _embedding_metadata_id(
                    owner_type="segment",
                    owner_id=record["id"],
                    embedding_model=storage_embedding_model,
                ),
                "segment_id": record["id"],
                "embedding_model": storage_embedding_model,
                "dimension": runtime.dimension,
                "field_name": content_field,
                "tradition_id": record.get("tradition_id"),
                "content_hash": content_hash,
                "metadata_json": json.dumps(metadata_json, ensure_ascii=False),
                "embedding": "[" + ",".join(f"{value:.8f}" for value in embedding) + "]",
            }
        )
    return payloads


def stage_embedding_payloads(
    session: Session,
    payloads: list[dict[str, Any]],
) -> None:
    if not payloads:
        return
    session.execute(
        text(
            f"""
            INSERT INTO {_realtime_staging_table()} (
                run_id,
                metadata_id,
                segment_id,
                embedding_model,
                dimension,
                field_name,
                tradition_id,
                content_hash,
                metadata_json,
                embedding,
                created_at
            )
            VALUES (
                :run_id,
                :metadata_id,
                :segment_id,
                :embedding_model,
                :dimension,
                :field_name,
                :tradition_id,
                :content_hash,
                CAST(:metadata_json AS jsonb),
                CAST(:embedding AS vector),
                NOW()
            )
            """
        ),
        payloads,
    )


def promote_staged_segment_ids(
    session: Session,
    *,
    run_id: Optional[str],
    segment_ids: list[str],
    runtime: EmbeddingRuntime,
    content_field: str,
) -> int:
    if not segment_ids:
        return 0

    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=content_field)
    params: dict[str, Any] = {
        "segment_ids": segment_ids,
        "embedding_model": storage_embedding_model,
        "field_name": content_field,
        "default_field": DEFAULT_EMBEDDING_CONTENT_FIELD,
    }
    if run_id is not None:
        params["run_id"] = run_id

    session.execute(
        text(
            """
            DELETE FROM segment_embeddings se
            USING embedding_index_metadata eim
            WHERE eim.owner_type = 'segment'
              AND eim.owner_id = se.segment_id
              AND eim.owner_id = ANY(:segment_ids)
              AND COALESCE(eim.metadata_json->>'content_field', :default_field) = :field_name
              AND se.embedding_model = eim.embedding_model
              AND se.embedding_model <> :embedding_model
            """
        ),
        params,
    )
    session.execute(
        text(
            """
            DELETE FROM embedding_index_metadata
            WHERE owner_type = 'segment'
              AND owner_id = ANY(:segment_ids)
              AND COALESCE(metadata_json->>'content_field', :default_field) = :field_name
              AND embedding_model <> :embedding_model
            """
        ),
        params,
    )

    stage_where = "segment_id = ANY(:segment_ids) AND embedding_model = :embedding_model AND field_name = :field_name"
    if run_id is not None:
        stage_where += " AND run_id = :run_id"

    session.execute(
        text(
            f"""
            INSERT INTO {_qualified_segment_embeddings_table()} (
                segment_id,
                embedding_model,
                embedding,
                content_hash,
                indexed_at,
                metadata_json
            )
            SELECT
                segment_id,
                embedding_model,
                embedding,
                content_hash,
                NOW(),
                metadata_json
            FROM {_realtime_staging_table()}
            WHERE {stage_where}
            ON CONFLICT (segment_id, embedding_model)
            DO UPDATE SET
                embedding = EXCLUDED.embedding,
                content_hash = EXCLUDED.content_hash,
                indexed_at = NOW(),
                metadata_json = EXCLUDED.metadata_json
            """
        ),
        params,
    )

    session.execute(
        text(
            """
            DELETE FROM embedding_index_metadata
            WHERE owner_type = 'segment'
              AND owner_id = ANY(:segment_ids)
              AND embedding_model = :embedding_model
            """
        ),
        params,
    )
    session.execute(
        text(
            f"""
            INSERT INTO embedding_index_metadata (
                id,
                owner_type,
                owner_id,
                chunk_scope,
                embedding_model,
                vector_backend,
                dimension,
                status,
                indexed_at,
                metadata_json
            )
            SELECT
                metadata_id,
                'segment',
                segment_id,
                'segment',
                embedding_model,
                'pgvector',
                dimension,
                'indexed',
                NOW(),
                metadata_json
            FROM {_realtime_staging_table()}
            WHERE {stage_where}
            ON CONFLICT (id)
            DO UPDATE SET
                owner_id = EXCLUDED.owner_id,
                embedding_model = EXCLUDED.embedding_model,
                vector_backend = EXCLUDED.vector_backend,
                dimension = EXCLUDED.dimension,
                status = EXCLUDED.status,
                indexed_at = EXCLUDED.indexed_at,
                metadata_json = EXCLUDED.metadata_json
            """
        ),
        params,
    )
    session.execute(
        text(
            f"""
            DELETE FROM {_realtime_staging_table()}
            WHERE {stage_where}
            """
        ),
        params,
    )
    return len(segment_ids)


def _is_retryable_db_error(exc: BaseException) -> bool:
    original = getattr(exc, "orig", exc)
    module_name = getattr(type(original), "__module__", "")
    class_name = type(original).__name__
    if module_name.startswith("psycopg.errors") and class_name in {
        "DeadlockDetected",
        "SerializationFailure",
        "LockNotAvailable",
    }:
        return True
    return False


def _run_db_write_with_retry(operation, *, description: str):  # type: ignore[no-untyped-def]
    backoff_seconds = REALTIME_DB_WRITE_INITIAL_BACKOFF_SECONDS
    last_exc: BaseException | None = None
    for attempt in range(REALTIME_DB_WRITE_MAX_RETRIES):
        try:
            return operation()
        except DBAPIError as exc:
            if not _is_retryable_db_error(exc):
                raise
            last_exc = exc
            if attempt >= REALTIME_DB_WRITE_MAX_RETRIES - 1:
                raise
            time.sleep(backoff_seconds + random.uniform(0.0, 0.5))
            backoff_seconds *= 2
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{description} failed without an exception.")


def flush_staging_backlog(
    *,
    runtime: EmbeddingRuntime,
    content_field: str,
    tradition_id: Optional[str],
    limit: int = 1_000,
) -> int:
    flushed = 0
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=content_field)
    while True:
        def _flush_once() -> int:
            with SessionLocal() as session:
                _acquire_embedding_write_lock(session)
                sql = f"""
                    SELECT DISTINCT segment_id
                    FROM {_realtime_staging_table()}
                    WHERE embedding_model = :embedding_model
                      AND field_name = :field_name
                """
                params: dict[str, Any] = {
                    "embedding_model": storage_embedding_model,
                    "field_name": content_field,
                    "limit": limit,
                }
                if tradition_id is not None:
                    sql += " AND tradition_id = :tradition_id"
                    params["tradition_id"] = tradition_id
                sql += "\n ORDER BY segment_id\n LIMIT :limit"
                pending_segment_ids = list(session.execute(text(sql), params).scalars())
                if not pending_segment_ids:
                    session.commit()
                    return 0
                inserted = promote_staged_segment_ids(
                    session,
                    run_id=None,
                    segment_ids=pending_segment_ids,
                    runtime=runtime,
                    content_field=content_field,
                )
                session.commit()
                return inserted

        inserted = _run_db_write_with_retry(_flush_once, description="flush_staging_backlog")
        if inserted <= 0:
            return flushed
        flushed += inserted


def _persist_response_batch(
    response: RealtimeEmbeddingResponse,
    *,
    run_id: str,
    runtime: EmbeddingRuntime,
    content_field: str,
) -> int:
    payloads = _stage_rows_payload(
        response,
        runtime=runtime,
        content_field=content_field,
        run_id=run_id,
    )
    segment_ids = [payload["segment_id"] for payload in payloads]

    def _write_once() -> int:
        with SessionLocal() as session:
            _acquire_embedding_write_lock(session)
            stage_embedding_payloads(session, payloads)
            promote_staged_segment_ids(
                session,
                run_id=run_id,
                segment_ids=segment_ids,
                runtime=runtime,
                content_field=content_field,
            )
            session.commit()
            return len(segment_ids)

    return _run_db_write_with_retry(_write_once, description="_persist_response_batch")


async def run_realtime_embedding_worker(
    *,
    content_field: Optional[str] = None,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    start_after_segment_id: Optional[str] = None,
    concurrency: int = 4,
    scan_batch_size: int = 2_000,
    max_segments_per_request: int = REALTIME_MAX_SEGMENTS_PER_REQUEST,
    max_tokens_per_request: int = REALTIME_MAX_TOKENS_PER_REQUEST,
    max_single_segment_tokens: int = REALTIME_MAX_SINGLE_SEGMENT_TOKENS,
    max_segments: Optional[int] = None,
    run_id: Optional[str] = None,
    min_text_length: Optional[int] = None,
    max_text_length: Optional[int] = None,
    min_routing_tokens: Optional[int] = None,
    max_routing_tokens: Optional[int] = None,
) -> dict[str, Any]:
    if not settings.uses_postgres:
        raise ValueError("Realtime embedding worker requires PostgreSQL.")

    resolved_field = resolve_embedding_content_field(content_field)
    runtime = resolve_embedding_runtime(tradition_id=tradition_id)
    validate_realtime_runtime(runtime)
    run_id = run_id or datetime.now(timezone.utc).strftime("rt-%Y%m%d%H%M%S")

    with SessionLocal() as session:
        ensure_realtime_embedding_tables(session.connection(), dimension=runtime.dimension)

    flush_staging_backlog(runtime=runtime, content_field=resolved_field, tradition_id=tradition_id)

    queue: asyncio.Queue[RealtimeEmbeddingBatch | None] = asyncio.Queue(maxsize=max(1, concurrency * 2))
    stats = RealtimeEmbeddingStats()
    stats_lock = asyncio.Lock()
    db_write_semaphore = asyncio.Semaphore(1)

    async def producer() -> None:
        last_segment_id = start_after_segment_id
        queued_missing = 0
        while True:
            candidates, scanned_cursor, completed = await asyncio.to_thread(
                scan_pending_realtime_candidates,
                runtime=runtime,
                content_field=resolved_field,
                tradition_id=tradition_id,
                collection_id=collection_id,
                language_id=language_id,
                start_after_segment_id=last_segment_id,
                scan_limit=scan_batch_size,
                min_text_length=min_text_length,
                max_text_length=max_text_length,
                min_routing_tokens=min_routing_tokens,
                max_routing_tokens=max_routing_tokens,
            )
            if not candidates and completed:
                async with stats_lock:
                    stats.resume_after_segment_id = scanned_cursor or last_segment_id
                    stats.completed_scan = True
                break
            if max_segments is not None and queued_missing >= max_segments:
                break
            original_candidate_count = len(candidates)
            truncated = False
            if max_segments is not None:
                remaining = max_segments - queued_missing
                if remaining <= 0:
                    break
                if original_candidate_count > remaining:
                    candidates = candidates[:remaining]
                    truncated = True
            batches, oversize = pack_realtime_batches(
                candidates,
                max_segments_per_request=max_segments_per_request,
                max_tokens_per_request=max_tokens_per_request,
                max_single_segment_tokens=max_single_segment_tokens,
            )
            async with stats_lock:
                stats.total_missing += len(candidates)
                stats.failed += len(oversize)
                stats.skipped_oversize += len(oversize)
            queued_missing += len(candidates)
            if candidates:
                if truncated:
                    last_segment_id = candidates[-1].record["id"]
                else:
                    last_segment_id = scanned_cursor
            else:
                last_segment_id = scanned_cursor
            async with stats_lock:
                stats.resume_after_segment_id = last_segment_id
                if completed and not truncated:
                    stats.completed_scan = True
            for batch in batches:
                await queue.put(batch)
            if completed and not truncated:
                break

        for _ in range(max(1, concurrency)):
            await queue.put(None)

    async def worker() -> None:
        while True:
            batch = await queue.get()
            try:
                if batch is None:
                    return
                response = await asyncio.to_thread(
                    request_realtime_embeddings,
                    batch.records,
                    runtime=runtime,
                    content_field=resolved_field,
                )
                async with db_write_semaphore:
                    processed_count = await asyncio.to_thread(
                        _persist_response_batch,
                        response,
                        run_id=run_id,
                        runtime=runtime,
                        content_field=resolved_field,
                    )
                async with stats_lock:
                    stats.processed += processed_count
                    stats.tokens_used += response.tokens_used
                    stats.failed += len(response.skipped_records)
                    stats.skipped_oversize += len(response.skipped_records)
            except Exception:
                async with stats_lock:
                    stats.failed += len(batch.records)
                raise
            finally:
                queue.task_done()

    producer_task = asyncio.create_task(producer())
    worker_tasks = [asyncio.create_task(worker()) for _ in range(max(1, concurrency))]
    await producer_task
    await queue.join()
    for task in worker_tasks:
        await task
    return stats.snapshot()
