from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import re
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from sqlalchemy import BigInteger, cast, func, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models import EmbeddingIndexMetadata, Segment, TextVersion, Work
from backend.app.services import search_service


LOCAL_EMBEDDING_PROVIDER = "local-hash"
OPENAI_COMPATIBLE_EMBEDDING_PROVIDER = "openai-compatible"
LOCAL_EMBEDDING_MODEL = "local-hash-v1"
LOCAL_EMBEDDING_DIMENSION = 64
DEFAULT_EMBEDDING_MODEL = settings.embedding_model or LOCAL_EMBEDDING_MODEL
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
VECTOR_DIMENSION_PATTERN = re.compile(r"vector\((\d+)\)")
OPENAI_COMPATIBLE_MAX_RETRIES = 6
OPENAI_COMPATIBLE_RETRY_DELAY_SECONDS = 2.0
DEFAULT_EMBEDDING_CONTENT_FIELD = "normalized_content"
SUPPORTED_EMBEDDING_CONTENT_FIELDS = frozenset({"normalized_content", "content", "content_gloss"})


@dataclass(slots=True)
class EmbeddingRuntime:
    provider: str
    model: str
    dimension: int
    api_url: str = ""
    api_key: str = ""
    batch_size: int = 32
    timeout_seconds: float = 30.0


@dataclass(slots=True)
class BackfillResult:
    inserted_count: int
    last_segment_id: Optional[str]
    completed: bool


def resolve_embedding_content_field(content_field: Optional[str] = None) -> str:
    resolved = (content_field or DEFAULT_EMBEDDING_CONTENT_FIELD).strip().lower()
    if resolved not in SUPPORTED_EMBEDDING_CONTENT_FIELDS:
        supported = ", ".join(sorted(SUPPORTED_EMBEDDING_CONTENT_FIELDS))
        raise ValueError(f"Unsupported embedding content field '{resolved}'. Expected one of: {supported}.")
    return resolved


def resolve_storage_embedding_model(embedding_model: str, *, content_field: Optional[str] = None) -> str:
    resolved_field = resolve_embedding_content_field(content_field)
    if resolved_field == DEFAULT_EMBEDDING_CONTENT_FIELD:
        return embedding_model
    return f"{embedding_model}::{resolved_field}"


def segment_text_value(segment_record: dict[str, Any], *, content_field: Optional[str] = None) -> str:
    resolved_field = resolve_embedding_content_field(content_field)
    if resolved_field == DEFAULT_EMBEDDING_CONTENT_FIELD:
        return segment_record.get("normalized_content") or segment_record.get("content") or ""
    return segment_record.get(resolved_field) or ""


def _tradition_env_name(base_name: str, tradition_id: Optional[str]) -> Optional[str]:
    if not tradition_id:
        return None
    suffix = tradition_id.strip().upper().replace("-", "_")
    if not suffix:
        return None
    return f"{base_name}_{suffix}"


def _tradition_string_override(base_name: str, tradition_id: Optional[str]) -> Optional[str]:
    env_name = _tradition_env_name(base_name, tradition_id)
    if not env_name:
        return None
    value = os.getenv(env_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _tradition_int_override(base_name: str, tradition_id: Optional[str]) -> Optional[int]:
    value = _tradition_string_override(base_name, tradition_id)
    if value is None:
        return None
    return int(value)


def _tradition_float_override(base_name: str, tradition_id: Optional[str]) -> Optional[float]:
    value = _tradition_string_override(base_name, tradition_id)
    if value is None:
        return None
    return float(value)


def resolve_embedding_runtime(
    *,
    embedding_model: Optional[str] = None,
    tradition_id: Optional[str] = None,
) -> EmbeddingRuntime:
    provider = (
        _tradition_string_override("EMBEDDING_PROVIDER", tradition_id)
        or settings.embedding_provider
        or LOCAL_EMBEDDING_PROVIDER
    ).strip().lower()
    resolved_model = (
        embedding_model
        or _tradition_string_override("EMBEDDING_MODEL", tradition_id)
        or settings.embedding_model
        or ""
    ).strip()

    if provider == LOCAL_EMBEDDING_PROVIDER:
        return EmbeddingRuntime(
            provider=provider,
            model=resolved_model or LOCAL_EMBEDDING_MODEL,
            dimension=LOCAL_EMBEDDING_DIMENSION,
            batch_size=max(1, settings.embedding_batch_size),
            timeout_seconds=settings.embedding_timeout_seconds,
        )

    if provider == OPENAI_COMPATIBLE_EMBEDDING_PROVIDER:
        api_url = _tradition_string_override("EMBEDDING_API_URL", tradition_id) or settings.embedding_api_url
        api_key = _tradition_string_override("EMBEDDING_API_KEY", tradition_id) or settings.embedding_api_key
        dimension = _tradition_int_override("EMBEDDING_DIMENSION", tradition_id) or settings.embedding_dimension
        batch_size = _tradition_int_override("EMBEDDING_BATCH_SIZE", tradition_id) or settings.embedding_batch_size
        timeout_seconds = (
            _tradition_float_override("EMBEDDING_TIMEOUT_SECONDS", tradition_id)
            or settings.embedding_timeout_seconds
        )
        if not api_url:
            raise ValueError("EMBEDDING_API_URL must be set when EMBEDDING_PROVIDER=openai-compatible.")
        if not resolved_model:
            raise ValueError("EMBEDDING_MODEL must be set when EMBEDDING_PROVIDER=openai-compatible.")
        if dimension <= 0:
            raise ValueError(
                "EMBEDDING_DIMENSION must be set to the provider vector size when "
                "EMBEDDING_PROVIDER=openai-compatible."
            )
        return EmbeddingRuntime(
            provider=provider,
            model=resolved_model,
            dimension=dimension,
            api_url=api_url,
            api_key=api_key,
            batch_size=max(1, batch_size),
            timeout_seconds=timeout_seconds,
        )

    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER '{provider}'. "
        f"Expected '{LOCAL_EMBEDDING_PROVIDER}' or '{OPENAI_COMPATIBLE_EMBEDDING_PROVIDER}'."
    )


def _qualified_segment_embeddings_table() -> str:
    schema_name = settings.pgvector_schema_hint or "public"
    return f"{schema_name}.segment_embeddings"


def _existing_vector_dimension(connection: Connection) -> Optional[int]:
    vector_type = connection.execute(
        text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :schema_name
              AND c.relname = 'segment_embeddings'
              AND a.attname = 'embedding'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        ),
        {"schema_name": settings.pgvector_schema_hint or "public"},
    ).scalar()
    if not vector_type:
        return None

    match = VECTOR_DIMENSION_PATTERN.search(str(vector_type))
    if not match:
        return None
    return int(match.group(1))


def ensure_postgres_vector_objects(connection: Connection, *, dimension: int) -> None:
    if connection.dialect.name != "postgresql":
        return

    qualified_table_name = _qualified_segment_embeddings_table()
    existing_table = connection.execute(
        text("SELECT to_regclass(:qualified_name)"),
        {"qualified_name": qualified_table_name},
    ).scalar()
    if not existing_table:
        connection.exec_driver_sql(
            f"""
            CREATE TABLE {qualified_table_name} (
                segment_id VARCHAR(64) NOT NULL,
                embedding_model VARCHAR(128) NOT NULL,
                embedding vector({dimension}) NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata_json JSONB,
                PRIMARY KEY (segment_id, embedding_model),
                CONSTRAINT fk_segment_embeddings_segment_id_segments
                    FOREIGN KEY (segment_id) REFERENCES segments (id) ON DELETE CASCADE
            )
            """
        )
    else:
        existing_dimension = _existing_vector_dimension(connection)
        if existing_dimension is not None and existing_dimension != dimension:
            raise ValueError(
                f"segment_embeddings.embedding uses vector({existing_dimension}) but the configured embedding "
                f"runtime expects vector({dimension}). Recreate the table or point the app at a fresh database."
            )

    connection.exec_driver_sql(
        f"""
        CREATE INDEX IF NOT EXISTS ix_segment_embeddings_model
        ON {qualified_table_name} (embedding_model)
        """
    )
    connection.exec_driver_sql(
        f"""
        CREATE INDEX IF NOT EXISTS ix_segment_embeddings_indexed_at
        ON {qualified_table_name} (indexed_at DESC)
        """
    )


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in TOKEN_PATTERN.findall(text.lower()):
        if not raw_token:
            continue
        tokens.append(raw_token)
        if len(raw_token) > 1:
            tokens.extend(raw_token[index : index + 2] for index in range(len(raw_token) - 1))
    return tokens


def build_local_embedding(text_value: str, *, dimension: int = LOCAL_EMBEDDING_DIMENSION) -> list[float]:
    vector = [0.0] * dimension
    tokens = _tokenize(text_value)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        primary = int.from_bytes(digest[:4], "big") % dimension
        secondary = int.from_bytes(digest[4:8], "big") % dimension
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        token_weight = 1.0 + min(len(token), 4) * 0.15
        vector[primary] += sign * token_weight
        vector[secondary] += (sign * -0.5) * token_weight

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


def _embed_with_openai_compatible_provider(
    text_values: list[str],
    *,
    runtime: EmbeddingRuntime,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    batch_size = max(1, runtime.batch_size)

    for start in range(0, len(text_values), batch_size):
        batch = text_values[start : start + batch_size]
        embeddings.extend(_embed_openai_compatible_batch(batch, runtime=runtime))

    return embeddings


def _embed_openai_compatible_batch(
    text_values: list[str],
    *,
    runtime: EmbeddingRuntime,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    headers = {"Content-Type": "application/json"}
    if runtime.api_key:
        headers["Authorization"] = f"Bearer {runtime.api_key}"

    request_body = {
        "model": runtime.model,
        "input": text_values,
        "dimensions": runtime.dimension,
    }
    request_payload = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        runtime.api_url,
        data=request_payload,
        headers=headers,
        method="POST",
    )
    retry_delay = OPENAI_COMPATIBLE_RETRY_DELAY_SECONDS
    for attempt in range(OPENAI_COMPATIBLE_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=runtime.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt < OPENAI_COMPATIBLE_MAX_RETRIES:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            if exc.code >= 500:
                if len(text_values) > 1:
                    midpoint = max(1, len(text_values) // 2)
                    return _embed_openai_compatible_batch(
                        text_values[:midpoint],
                        runtime=runtime,
                    ) + _embed_openai_compatible_batch(
                        text_values[midpoint:],
                        runtime=runtime,
                    )
                if attempt < OPENAI_COMPATIBLE_MAX_RETRIES:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            raise ValueError(f"Embedding provider request failed with HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            if attempt < OPENAI_COMPATIBLE_MAX_RETRIES:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise ValueError(f"Embedding provider request failed: {exc.reason}") from exc
        except http.client.IncompleteRead as exc:
            if attempt < OPENAI_COMPATIBLE_MAX_RETRIES:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise ValueError(f"Embedding provider response was truncated: {exc}") from exc
        except (TimeoutError, socket.timeout) as exc:
            if attempt < OPENAI_COMPATIBLE_MAX_RETRIES:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise ValueError(f"Embedding provider response timed out: {exc}") from exc
    else:
        raise ValueError("Embedding provider request exhausted retries without a response.")

    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) != len(text_values):
        raise ValueError("Embedding provider returned an unexpected number of embeddings.")

    ordered_rows = sorted(rows, key=lambda item: int(item.get("index", 0)))
    for row in ordered_rows:
        embedding = row.get("embedding")
        if not isinstance(embedding, list):
            raise ValueError("Embedding provider returned a malformed embedding payload.")
        vector = [float(value) for value in embedding]
        if len(vector) != runtime.dimension:
            raise ValueError(
                f"Embedding provider returned {len(vector)} dimensions for model '{runtime.model}', "
                f"but EMBEDDING_DIMENSION is set to {runtime.dimension}."
            )
        embeddings.append(vector)

    return embeddings


def embed_text_values(
    text_values: Iterable[str],
    *,
    embedding_model: Optional[str] = None,
    tradition_id: Optional[str] = None,
) -> tuple[EmbeddingRuntime, list[list[float]]]:
    runtime = resolve_embedding_runtime(embedding_model=embedding_model, tradition_id=tradition_id)
    materialized = [(text_value or "") for text_value in text_values]
    if not materialized:
        return runtime, []

    if runtime.provider == LOCAL_EMBEDDING_PROVIDER:
        return runtime, [build_local_embedding(text_value, dimension=runtime.dimension) for text_value in materialized]

    return runtime, _embed_with_openai_compatible_provider(materialized, runtime=runtime)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(left_item * right_item for left_item, right_item in zip(left, right))


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _segment_content_hash(segment_record: dict[str, Any], *, content_field: Optional[str] = None) -> str:
    base = segment_text_value(segment_record, content_field=content_field)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _embedding_metadata(segment_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_id": segment_record.get("work_id"),
        "text_version_id": segment_record.get("text_version_id"),
        "tradition_id": segment_record.get("tradition_id"),
        "collection_id": segment_record.get("collection_id"),
        "language_id": segment_record.get("language_id"),
    }


def _embedding_metadata_id(*, owner_type: str, owner_id: str, embedding_model: str) -> str:
    digest = hashlib.sha1(f"{owner_type}:{owner_id}:{embedding_model}".encode("utf-8")).hexdigest()[:24]
    return f"embmeta-{digest}"


def _embedding_index_metadata(
    segment_record: dict[str, Any],
    *,
    runtime: EmbeddingRuntime,
    content_hash: str,
    content_field: Optional[str] = None,
    storage_embedding_model: Optional[str] = None,
) -> dict[str, Any]:
    metadata = _embedding_metadata(segment_record)
    resolved_field = resolve_embedding_content_field(content_field)
    metadata.update(
        {
            "embedding_provider": runtime.provider,
            "embedding_source_model": runtime.model,
            "storage_embedding_model": storage_embedding_model or runtime.model,
            "content_field": resolved_field,
            "content_hash": content_hash,
        }
    )
    return metadata


def indexed_owner_count(
    session: Session,
    *,
    embedding_model: Optional[str] = None,
    tradition_id: Optional[str] = None,
    content_field: Optional[str] = None,
) -> int:
    if not settings.uses_postgres:
        return 0

    runtime = resolve_embedding_runtime(embedding_model=embedding_model, tradition_id=tradition_id)
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=content_field)
    ensure_postgres_vector_objects(session.connection(), dimension=runtime.dimension)
    return int(
        session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM segment_embeddings
                WHERE embedding_model = :embedding_model
                """
            ),
            {"embedding_model": storage_embedding_model},
        ).scalar_one()
    )


def upsert_segment_embeddings(
    session: Session,
    records: Iterable[dict[str, Any]],
    embeddings: Iterable[list[float]],
    *,
    runtime: EmbeddingRuntime,
    content_field: Optional[str] = None,
    ensure_vector_objects: bool = True,
) -> int:
    materialized_records = list(records)
    materialized_embeddings = list(embeddings)
    if not materialized_records or not settings.uses_postgres:
        return 0
    if len(materialized_records) != len(materialized_embeddings):
        raise ValueError("records and embeddings must have the same length.")

    resolved_field = resolve_embedding_content_field(content_field)
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=resolved_field)
    if ensure_vector_objects:
        ensure_postgres_vector_objects(session.connection(), dimension=runtime.dimension)
    session.execute(text("SELECT pg_advisory_xact_lock(334455)"))

    segment_ids = [record["id"] for record in materialized_records]
    payloads: list[dict[str, Any]] = []
    metadata_rows: list[EmbeddingIndexMetadata] = []
    for record, embedding in zip(materialized_records, materialized_embeddings):
        content_hash = _segment_content_hash(record, content_field=resolved_field)
        metadata_json = _embedding_index_metadata(
            record,
            runtime=runtime,
            content_hash=content_hash,
            content_field=resolved_field,
            storage_embedding_model=storage_embedding_model,
        )
        payloads.append(
            {
                "segment_id": record["id"],
                "embedding_model": storage_embedding_model,
                "embedding": _vector_literal(embedding),
                "content_hash": content_hash,
                "metadata_json": json.dumps(metadata_json, ensure_ascii=False),
            }
        )
        metadata_rows.append(
            EmbeddingIndexMetadata(
                id=_embedding_metadata_id(
                    owner_type="segment",
                    owner_id=record["id"],
                    embedding_model=storage_embedding_model,
                ),
                owner_type="segment",
                owner_id=record["id"],
                chunk_scope="segment",
                embedding_model=storage_embedding_model,
                vector_backend="pgvector",
                dimension=runtime.dimension,
                status="indexed",
                indexed_at=datetime.utcnow(),
                metadata_json=metadata_json,
            )
        )

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

    session.query(EmbeddingIndexMetadata).filter(
        EmbeddingIndexMetadata.owner_type == "segment",
        EmbeddingIndexMetadata.owner_id.in_(segment_ids),
        EmbeddingIndexMetadata.embedding_model == storage_embedding_model,
    ).delete(synchronize_session=False)
    session.add_all(metadata_rows)
    session.commit()
    return len(payloads)


def index_segment_records(
    session: Session,
    records: Iterable[dict[str, Any]],
    *,
    embedding_model: Optional[str] = None,
    tradition_id: Optional[str] = None,
    content_field: Optional[str] = None,
    ensure_vector_objects: bool = True,
) -> int:
    materialized = list(records)
    if not materialized or not settings.uses_postgres:
        return 0

    resolved_field = resolve_embedding_content_field(content_field)
    if tradition_id is None:
        record_traditions = {record.get("tradition_id") for record in materialized if record.get("tradition_id")}
        if len(record_traditions) == 1:
            tradition_id = next(iter(record_traditions))

    prepared_records = [
        record for record in materialized if segment_text_value(record, content_field=resolved_field).strip()
    ]
    if not prepared_records:
        return 0

    runtime, embeddings = embed_text_values(
        [segment_text_value(record, content_field=resolved_field) for record in prepared_records],
        embedding_model=embedding_model,
        tradition_id=tradition_id,
    )
    return upsert_segment_embeddings(
        session,
        prepared_records,
        embeddings,
        runtime=runtime,
        content_field=resolved_field,
        ensure_vector_objects=ensure_vector_objects,
    )


def _candidate_records(
    session: Session,
    *,
    query_text: str,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    work_id: Optional[str] = None,
    text_version_id: Optional[str] = None,
    limit: int,
) -> list[dict[str, Any]]:
    matches = search_service.retrieve_segment_matches(
        session,
        q=query_text,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
        text_version_id=text_version_id,
        limit=limit,
        include_content=True,
    )
    if matches:
        return matches

    stmt = (
        select(Segment)
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
        )
        .join(Segment.text_version)
        .join(TextVersion.work)
        .limit(limit)
    )
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    if collection_id:
        stmt = stmt.where(Work.collection_id == collection_id)
    if language_id:
        stmt = stmt.where(TextVersion.language_id == language_id)
    if work_id:
        stmt = stmt.where(Work.id == work_id)
    if text_version_id:
        stmt = stmt.where(TextVersion.id == text_version_id)

    segments = session.scalars(stmt).unique().all()
    return [
        {
            "id": segment.id,
            "segment_key": segment.segment_key,
            "title": segment.title,
            "position": segment.position,
            "work_title": segment.text_version.work.title,
            "text_version_title": segment.text_version.title,
            "tradition_name": segment.text_version.work.tradition.name,
            "language_name": segment.text_version.language.name,
            "content_preview": segment.content[:120],
            "content": segment.content,
            "normalized_content": segment.normalized_content or segment.content,
            "content_gloss": segment.content_gloss,
            "is_sample": segment.text_version.work.is_sample,
            "work_id": segment.text_version.work.id,
            "text_version_id": segment.text_version.id,
            "collection_id": segment.text_version.work.collection.id,
            "tradition_id": segment.text_version.work.tradition.id,
            "language_id": segment.text_version.language.id,
            "match_reason": "vector-seed",
            "match_score": None,
            "concept_labels": [],
        }
        for segment in segments
    ]


def _load_segment_payloads(session: Session, segment_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not segment_ids:
        return {}

    stmt = (
        select(Segment)
        .where(Segment.id.in_(segment_ids))
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
        )
    )
    segments = session.scalars(stmt).unique().all()
    payload: dict[str, dict[str, Any]] = {}
    for segment in segments:
        payload[segment.id] = {
            "id": segment.id,
            "segment_key": segment.segment_key,
            "title": segment.title,
            "position": segment.position,
            "work_title": segment.text_version.work.title,
            "text_version_title": segment.text_version.title,
            "tradition_name": segment.text_version.work.tradition.name,
            "language_name": segment.text_version.language.name,
            "content_preview": segment.content[:120],
            "content": segment.content,
            "normalized_content": segment.normalized_content or segment.content,
            "is_sample": segment.text_version.work.is_sample,
            "work_id": segment.text_version.work.id,
            "text_version_id": segment.text_version.id,
            "collection_id": segment.text_version.work.collection.id,
            "tradition_id": segment.text_version.work.tradition.id,
            "language_id": segment.text_version.language.id,
            "concept_labels": [],
        }
    return payload


def _postgres_vector_search(
    session: Session,
    *,
    query_text: str,
    top_k: int,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    embedding_model: Optional[str],
) -> dict[str, Any]:
    runtime, query_embeddings = embed_text_values(
        [query_text],
        embedding_model=embedding_model,
        tradition_id=tradition_id,
    )
    ensure_postgres_vector_objects(session.connection(), dimension=runtime.dimension)
    existing_count = indexed_owner_count(session, embedding_model=runtime.model)
    if existing_count == 0:
        candidates = _candidate_records(
            session,
            query_text=query_text,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
            limit=max(top_k * 50, 600),
        )
        if candidates:
            index_segment_records(
                session,
                candidates,
                embedding_model=runtime.model,
                tradition_id=tradition_id,
            )
        existing_count = indexed_owner_count(session, embedding_model=runtime.model)

    query_embedding = _vector_literal(query_embeddings[0])
    where_clauses = ["se.embedding_model = :embedding_model"]
    params = {
        "query_embedding": query_embedding,
        "embedding_model": runtime.model,
        "top_k": top_k,
    }
    if tradition_id:
        where_clauses.append("w.tradition_id = :tradition_id")
        params["tradition_id"] = tradition_id
    if collection_id:
        where_clauses.append("w.collection_id = :collection_id")
        params["collection_id"] = collection_id
    if language_id:
        where_clauses.append("tv.language_id = :language_id")
        params["language_id"] = language_id

    rows = session.execute(
        text(
            f"""
            SELECT
                se.segment_id,
                1 - (se.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM segment_embeddings se
            JOIN segments s ON s.id = se.segment_id
            JOIN text_versions tv ON tv.id = s.text_version_id
            JOIN works w ON w.id = tv.work_id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY se.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
            """
        ),
        params,
    ).all()

    score_by_id = {row.segment_id: float(row.similarity) for row in rows}
    payload_by_id = _load_segment_payloads(session, [row.segment_id for row in rows])
    results: list[dict[str, Any]] = []
    for segment_id, similarity in sorted(score_by_id.items(), key=lambda item: item[1], reverse=True):
        payload = payload_by_id.get(segment_id)
        if not payload:
            continue
        payload["match_score"] = round(similarity, 6)
        payload["match_reason"] = "vector"
        results.append(payload)

    return {
        "status": "ready",
        "message": f"pgvector-backed {runtime.provider} embeddings are available for retrieval.",
        "configured_backend": "pgvector",
        "embedding_model": runtime.model,
        "indexed_owners": existing_count,
        "results": results,
        "pgvector_hint": "Backfill more rows with the embedding script for broader recall.",
    }


def _python_vector_search(
    session: Session,
    *,
    query_text: str,
    top_k: int,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    embedding_model: Optional[str],
) -> dict[str, Any]:
    candidates = _candidate_records(
        session,
        query_text=query_text,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        limit=max(top_k * 50, 300),
    )
    runtime, embeddings = embed_text_values(
        [query_text] + [record.get("normalized_content") or record.get("content") or "" for record in candidates],
        embedding_model=embedding_model,
        tradition_id=tradition_id,
    )
    query_embedding = embeddings[0]
    ranked: list[tuple[float, dict[str, Any]]] = []
    for record, candidate_embedding in zip(candidates, embeddings[1:]):
        similarity = _cosine_similarity(query_embedding, candidate_embedding)
        record["match_score"] = round(similarity, 6)
        record["match_reason"] = "vector"
        ranked.append((similarity, record))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return {
        "status": "ready",
        "message": f"Python fallback retrieval is using the {runtime.provider} embedding provider.",
        "configured_backend": "python-fallback",
        "embedding_model": runtime.model,
        "indexed_owners": 0,
        "results": [item[1] for item in ranked[:top_k]],
        "pgvector_hint": "Switch to PostgreSQL to persist vectors and use pgvector similarity queries.",
    }


def _misconfigured_vector_payload(*, embedding_model: Optional[str], message: str) -> dict[str, Any]:
    resolved_model = (embedding_model or settings.embedding_model or "unconfigured").strip() or "unconfigured"
    return {
        "status": "misconfigured",
        "message": message,
        "configured_backend": "pgvector" if settings.uses_postgres else "python-fallback",
        "embedding_model": resolved_model,
        "indexed_owners": 0,
        "results": [],
        "pgvector_hint": (
            "Use EMBEDDING_PROVIDER=local-hash for the built-in baseline, or configure "
            "EMBEDDING_API_URL, EMBEDDING_MODEL, and EMBEDDING_DIMENSION for an external worker."
        ),
    }


def vector_search(
    session: Session,
    *,
    query_text: str,
    top_k: int = 5,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> dict[str, Any]:
    try:
        if settings.uses_postgres:
            return _postgres_vector_search(
                session,
                query_text=query_text,
                top_k=top_k,
                tradition_id=tradition_id,
                collection_id=collection_id,
                language_id=language_id,
                embedding_model=embedding_model,
            )
        return _python_vector_search(
            session,
            query_text=query_text,
            top_k=top_k,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
            embedding_model=embedding_model,
        )
    except ValueError as exc:
        return _misconfigured_vector_payload(embedding_model=embedding_model, message=str(exc))


def find_similar_segments(
    session: Session,
    *,
    segment_id: str,
    top_k: int = 5,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> dict[str, Any]:
    stmt = (
        select(Segment)
        .where(Segment.id == segment_id)
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
        )
    )
    source_segment = session.scalars(stmt).unique().first()
    if not source_segment:
        raise LookupError(f"Segment '{segment_id}' not found.")

    query_text = source_segment.normalized_content or source_segment.content or ""
    source_payload = {
        "id": source_segment.id,
        "segment_key": source_segment.segment_key,
        "title": source_segment.title,
        "position": source_segment.position,
        "work_title": source_segment.text_version.work.title,
        "text_version_title": source_segment.text_version.title,
        "tradition_name": source_segment.text_version.work.tradition.name,
        "language_name": source_segment.text_version.language.name,
        "content_preview": source_segment.content[:120],
        "match_score": None,
        "match_reason": "source",
        "concept_labels": [],
    }

    vector_payload = vector_search(
        session,
        query_text=query_text,
        top_k=max(top_k + 1, 8),
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        embedding_model=embedding_model,
    )

    filtered_results = [
        item
        for item in vector_payload["results"]
        if item.get("id") != segment_id
    ][:top_k]

    return {
        "status": vector_payload["status"],
        "message": (
            f"Retrieved vector neighbors for segment {source_segment.segment_key}."
            if vector_payload["status"] == "ready"
            else vector_payload["message"]
        ),
        "configured_backend": vector_payload["configured_backend"],
        "embedding_model": vector_payload["embedding_model"],
        "indexed_owners": vector_payload["indexed_owners"],
        "source_segment": source_payload,
        "results": filtered_results,
        "pgvector_hint": vector_payload["pgvector_hint"],
    }


def _segment_shard_filter(*, shard_count: Optional[int], shard_index: Optional[int]):  # type: ignore[no-untyped-def]
    if shard_count is None and shard_index is None:
        return None
    if shard_count is None or shard_index is None:
        raise ValueError("shard_count and shard_index must be set together.")
    if shard_count == 1:
        return None
    if shard_count <= 0:
        raise ValueError("shard_count must be greater than zero.")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be within the shard_count range.")

    return func.mod(func.abs(cast(func.hashtext(Segment.id), BigInteger)), shard_count) == shard_index


def backfill_segment_embeddings(
    session: Session,
    *,
    batch_size: int = 500,
    embedding_model: Optional[str] = None,
    content_field: Optional[str] = None,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    max_segments: Optional[int] = None,
    shard_count: Optional[int] = None,
    shard_index: Optional[int] = None,
    start_after_segment_id: Optional[str] = None,
    end_at_segment_id: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> BackfillResult:
    if not settings.uses_postgres:
        return BackfillResult(inserted_count=0, last_segment_id=start_after_segment_id, completed=True)

    resolved_field = resolve_embedding_content_field(content_field)
    runtime = resolve_embedding_runtime(embedding_model=embedding_model, tradition_id=tradition_id)
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=resolved_field)
    ensure_postgres_vector_objects(session.connection(), dimension=runtime.dimension)
    total_indexed = 0
    last_segment_id = start_after_segment_id
    shard_filter = _segment_shard_filter(shard_count=shard_count, shard_index=shard_index)

    while True:
        remaining_segments = None if max_segments is None else max_segments - total_indexed
        if remaining_segments is not None and remaining_segments <= 0:
            return BackfillResult(inserted_count=total_indexed, last_segment_id=last_segment_id, completed=False)

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
            .limit(batch_size)
        )
        if last_segment_id:
            stmt = stmt.where(Segment.id > last_segment_id)
        if end_at_segment_id:
            stmt = stmt.where(Segment.id <= end_at_segment_id)
        if tradition_id:
            stmt = stmt.where(Work.tradition_id == tradition_id)
        if collection_id:
            stmt = stmt.where(Work.collection_id == collection_id)
        if language_id:
            stmt = stmt.where(TextVersion.language_id == language_id)
        if shard_filter is not None:
            stmt = stmt.where(shard_filter)

        segments = session.scalars(stmt).unique().all()
        if not segments:
            return BackfillResult(inserted_count=total_indexed, last_segment_id=last_segment_id, completed=True)

        indexed_segment_ids = set(
            session.scalars(
                select(EmbeddingIndexMetadata.owner_id).where(
                    EmbeddingIndexMetadata.owner_type == "segment",
                    EmbeddingIndexMetadata.owner_id.in_([segment.id for segment in segments]),
                    EmbeddingIndexMetadata.embedding_model == storage_embedding_model,
                )
            ).all()
        )

        records = []
        for segment in segments:
            if segment.id in indexed_segment_ids:
                continue
            records.append(
                {
                    "id": segment.id,
                    "content": segment.content,
                    "normalized_content": segment.normalized_content or segment.content,
                    "content_gloss": segment.content_gloss,
                    "work_id": segment.text_version.work.id,
                    "text_version_id": segment.text_version.id,
                    "tradition_id": segment.text_version.work.tradition.id,
                    "collection_id": segment.text_version.work.collection.id,
                    "language_id": segment.text_version.language.id,
                }
            )
        last_segment_id = segments[-1].id
        if remaining_segments is not None:
            records = records[:remaining_segments]
        if records:
            total_indexed += index_segment_records(
                session,
                records,
                embedding_model=runtime.model,
                content_field=resolved_field,
                ensure_vector_objects=False,
            )
        if progress_callback is not None and last_segment_id is not None:
            progress_callback(last_segment_id, total_indexed)
