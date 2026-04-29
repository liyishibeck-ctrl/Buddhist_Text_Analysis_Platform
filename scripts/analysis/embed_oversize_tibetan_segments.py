from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from backend.app.db.session import SessionLocal
from backend.app.models import Segment
from backend.app.services.realtime_embedding_worker import (
    RealtimeEmbeddingResponse,
    ensure_realtime_embedding_tables,
    _persist_response_batch,
    _segment_record_payload,
    _token_encoder,
    estimate_segment_tokens,
    request_realtime_embeddings,
    segment_text_value,
)
from backend.app.services.vector_service import resolve_embedding_runtime, resolve_storage_embedding_model


DEFAULT_SEGMENT_IDS = [
    "seg-plain-toh-127-093",
    "seg-plain-toh-10-1622",
    "seg-plain-toh-201-840",
    "seg-plain-toh-9-4301",
    "seg-plain-toh-44-45-5393",
    "seg-plain-toh-44-45-443",
    "seg-plain-toh-44-45-003",
    "seg-plain-toh-44-45-5360",
    "seg-plain-toh-44-45-1298",
    "seg-plain-toh-44-45-7092",
    "seg-plain-toh-185-048",
    "seg-plain-toh-44-45-1181",
]


def _split_by_chars(text_value: str, *, max_chars: int) -> list[str]:
    return [
        text_value[start : start + max_chars]
        for start in range(0, len(text_value), max_chars)
        if text_value[start : start + max_chars]
    ]


def _chunk_text_by_tokens(
    text_value: str,
    *,
    max_tokens: int,
    max_chars: int,
) -> list[tuple[str, int]]:
    stripped = text_value.strip()
    try:
        encoder = _token_encoder()
    except ModuleNotFoundError:
        return [
            (stripped[start : start + max_chars], estimate_segment_tokens(stripped[start : start + max_chars]))
            for start in range(0, len(stripped), max_chars)
            if stripped[start : start + max_chars]
        ]

    token_ids = encoder.encode(stripped)
    chunks: list[tuple[str, int]] = []
    for start in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[start : start + max_tokens]
        if not chunk_ids:
            continue
        chunk_text = encoder.decode(chunk_ids)
        for char_chunk in _split_by_chars(chunk_text, max_chars=max_chars):
            chunks.append((char_chunk, estimate_segment_tokens(char_chunk)))
    return chunks


def _weighted_average(vectors: list[list[float]], weights: list[int]) -> list[float]:
    if not vectors:
        raise ValueError("Cannot average an empty vector set.")
    total_weight = float(sum(weights))
    averaged = [0.0] * len(vectors[0])
    for vector, weight in zip(vectors, weights):
        for index, value in enumerate(vector):
            averaged[index] += value * (weight / total_weight)
    norm = math.sqrt(sum(value * value for value in averaged))
    if norm > 0:
        averaged = [value / norm for value in averaged]
    return averaged


def _segment_record(session, segment_id: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    segment = session.get(Segment, segment_id)
    if segment is None:
        raise ValueError(f"Segment not found: {segment_id}")
    return _segment_record_payload(segment)


def _already_indexed(session, *, segment_id: str, content_field: str, tradition_id: str, model: str, dimension: int) -> bool:  # type: ignore[no-untyped-def]
    return bool(
        session.execute(
            text(
                """
                SELECT 1
                FROM embedding_index_metadata
                WHERE owner_type = 'segment'
                  AND owner_id = :segment_id
                  AND embedding_model = :model
                  AND dimension = :dimension
                  AND status = 'indexed'
                  AND COALESCE(metadata_json->>'content_field', 'normalized_content') = :content_field
                  AND metadata_json->>'tradition_id' = :tradition_id
                LIMIT 1
                """
            ),
            {
                "segment_id": segment_id,
                "model": model,
                "dimension": dimension,
                "content_field": content_field,
                "tradition_id": tradition_id,
            },
        ).scalar()
    )


def embed_oversize_segments(
    *,
    segment_ids: list[str],
    content_field: str,
    tradition_id: str,
    chunk_token_limit: int,
    chunk_char_limit: int,
    force: bool,
    dry_run: bool,
) -> dict[str, int]:
    runtime = resolve_embedding_runtime(tradition_id=tradition_id)
    runtime.timeout_seconds = min(float(runtime.timeout_seconds), 45.0)
    storage_model = resolve_storage_embedding_model(runtime.model, content_field=content_field)
    run_id = datetime.now(timezone.utc).strftime("oversize-%Y%m%d%H%M%S")
    summary = {"seen": 0, "indexed": 0, "skipped_existing": 0, "chunks": 0}

    if not dry_run:
        with SessionLocal() as session:
            ensure_realtime_embedding_tables(session.connection(), dimension=runtime.dimension)

    for segment_id in segment_ids:
        with SessionLocal() as session:
            record = _segment_record(session, segment_id)
            text_value = segment_text_value(record, content_field=content_field)
            token_count = estimate_segment_tokens(text_value)
            chunks = _chunk_text_by_tokens(
                text_value,
                max_tokens=chunk_token_limit,
                max_chars=chunk_char_limit,
            )
            summary["seen"] += 1
            summary["chunks"] += len(chunks)
            already_indexed = False
            if not force:
                already_indexed = _already_indexed(
                    session,
                    segment_id=segment_id,
                    content_field=content_field,
                    tradition_id=tradition_id,
                    model=storage_model,
                    dimension=runtime.dimension,
                )
            session.rollback()

            print(
                f"{segment_id} chars={len(text_value)} tokens={token_count} chunks={len(chunks)}",
                flush=True,
            )
        if dry_run:
            continue
        if already_indexed:
            summary["skipped_existing"] += 1
            continue

        chunk_payloads: list[dict[str, Any]] = []
        chunk_tokens_used = 0
        for index, (chunk_text, _) in enumerate(chunks):
            chunk_record = {
                **record,
                "id": f"{segment_id}::chunk-{index + 1:03d}",
                content_field: chunk_text,
            }
            print(
                f"chunk_request segment={segment_id} chunk={index + 1}/{len(chunks)} chars={len(chunk_text)}",
                flush=True,
            )
            response = request_realtime_embeddings(
                [chunk_record],
                runtime=runtime,
                content_field=content_field,
            )
            if response.skipped_records:
                raise RuntimeError(f"OpenAI still rejected chunk {index + 1} for {segment_id}.")
            chunk_payloads.extend(response.payloads)
            chunk_tokens_used += response.tokens_used

        vector = _weighted_average(
            [payload["embedding"] for payload in chunk_payloads],
            [weight for _, weight in chunks],
        )
        merged_response = RealtimeEmbeddingResponse(
            payloads=[{"record": record, "embedding": vector}],
            tokens_used=chunk_tokens_used,
        )
        _persist_response_batch(
            merged_response,
            run_id=run_id,
            runtime=runtime,
            content_field=content_field,
        )
        extra_metadata = (
            '{"oversize_strategy":"token_chunk_weighted_average",'
            f'"chunk_count":{len(chunks)},'
            f'"chunk_token_limit":{chunk_token_limit},'
            f'"chunk_char_limit":{chunk_char_limit},'
            f'"original_estimated_tokens":{token_count}'
            "}"
        )
        with SessionLocal() as session:
            session.execute(
                text(
                    """
                    UPDATE embedding_index_metadata
                    SET metadata_json = CAST(
                        COALESCE(CAST(metadata_json AS jsonb), '{}'::jsonb)
                        || CAST(:extra_metadata AS jsonb)
                        AS json
                    )
                    WHERE owner_type = 'segment'
                      AND owner_id = :segment_id
                      AND embedding_model = :model
                    """
                ),
                {
                    "segment_id": segment_id,
                    "model": storage_model,
                    "extra_metadata": extra_metadata,
                },
            )
            session.execute(
                text(
                    """
                    UPDATE segment_embeddings
                    SET metadata_json = COALESCE(metadata_json, '{}'::jsonb)
                        || CAST(:extra_metadata AS jsonb)
                    WHERE segment_id = :segment_id
                      AND embedding_model = :model
                    """
                ),
                {
                    "segment_id": segment_id,
                    "model": storage_model,
                    "extra_metadata": extra_metadata,
                },
            )
            session.commit()
        summary["indexed"] += 1
        print(f"indexed segment={segment_id} chunks={len(chunks)}", flush=True)

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed Tibetan segments that exceed OpenAI's per-input token limit.")
    parser.add_argument("--segment-id", action="append", dest="segment_ids")
    parser.add_argument("--content-field", default="normalized_content", choices=["normalized_content", "content", "content_gloss"])
    parser.add_argument("--tradition-id", default="trad-tibetan")
    parser.add_argument("--chunk-token-limit", type=int, default=3000)
    parser.add_argument("--chunk-char-limit", type=int, default=1000)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = embed_oversize_segments(
        segment_ids=args.segment_ids or DEFAULT_SEGMENT_IDS,
        content_field=args.content_field,
        tradition_id=args.tradition_id,
        chunk_token_limit=args.chunk_token_limit,
        chunk_char_limit=args.chunk_char_limit,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(
        "summary "
        f"seen={summary['seen']} "
        f"indexed={summary['indexed']} "
        f"skipped_existing={summary['skipped_existing']} "
        f"chunks={summary['chunks']}"
    )


if __name__ == "__main__":
    main()
