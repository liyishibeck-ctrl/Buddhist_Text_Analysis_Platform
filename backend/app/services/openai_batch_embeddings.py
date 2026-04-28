from __future__ import annotations

import json
import uuid
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import EmbeddingIndexMetadata, Segment, TextVersion, Work
from backend.app.services.vector_service import (
    EmbeddingRuntime,
    resolve_embedding_content_field,
    resolve_embedding_runtime,
    resolve_storage_embedding_model,
    segment_text_value,
    upsert_segment_embeddings,
)


OPENAI_BATCH_MAX_REQUESTS = 50_000
OPENAI_BATCH_COMPLETION_WINDOW = "24h"


@dataclass(slots=True)
class BatchApplyResult:
    inserted_count: int
    success_count: int
    error_count: int
    ok_lines: int = 0
    bad_line: int | None = None
    bad_offset: int | None = None
    last_custom_id: str | None = None
    output_custom_ids_count: int = 0
    missing_custom_ids_count: int = 0
    missing_custom_ids_path: str | None = None


@dataclass(slots=True)
class DownloadedFileResult:
    path: Path
    byte_count: int
    headers: dict[str, str]


@dataclass(slots=True)
class JsonlInspectionResult:
    ok_lines: int
    bad_line: int | None
    bad_offset: int | None
    last_custom_id: str | None
    output_custom_ids_count: int
    missing_custom_ids_count: int = 0
    missing_custom_ids_path: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.bad_line is None


@dataclass(slots=True)
class DownloadedJsonlResult:
    temp_path: Path
    byte_count: int
    headers: dict[str, str]
    inspection: JsonlInspectionResult
    destination_path: Path | None = None
    bad_path: Path | None = None


def derive_batch_api_base_url(api_url: str) -> str:
    parsed = urllib.parse.urlsplit(api_url)
    normalized_path = parsed.path.rstrip("/")
    if not normalized_path.endswith("/embeddings"):
        raise ValueError("EMBEDDING_API_URL must point to an embeddings endpoint to derive the Batch API base URL.")
    base_path = normalized_path[: -len("/embeddings")]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))


def _authorized_request(
    *,
    runtime: EmbeddingRuntime,
    path: str,
    method: str,
    body: bytes | None = None,
    content_type: str | None = None,
    extra_headers: Optional[dict[str, str]] = None,
) -> urllib.request.Request:
    base_url = derive_batch_api_base_url(runtime.api_url).rstrip("/")
    headers = {"Authorization": f"Bearer {runtime.api_key}"}
    if content_type:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
    return urllib.request.Request(f"{base_url}{path}", data=body, headers=headers, method=method)


def _json_request(
    *,
    runtime: EmbeddingRuntime,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = _authorized_request(
        runtime=runtime,
        path=path,
        method=method,
        body=body,
        content_type="application/json",
    )
    with urllib.request.urlopen(request, timeout=runtime.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _multipart_body(*, purpose: str, file_path: Path) -> tuple[str, bytes]:
    boundary = f"----CodexBoundary{uuid.uuid4().hex}"
    payload = bytearray()
    payload.extend(
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="purpose"\r\n\r\n'
            f"{purpose}\r\n"
        ).encode("utf-8")
    )
    payload.extend(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            "Content-Type: application/jsonl\r\n\r\n"
        ).encode("utf-8")
    )
    payload.extend(file_path.read_bytes())
    payload.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return f"multipart/form-data; boundary={boundary}", bytes(payload)


def upload_batch_input_file(runtime: EmbeddingRuntime, file_path: Path) -> dict[str, Any]:
    content_type, body = _multipart_body(purpose="batch", file_path=file_path)
    request = _authorized_request(
        runtime=runtime,
        path="/files",
        method="POST",
        body=body,
        content_type=content_type,
    )
    with urllib.request.urlopen(request, timeout=runtime.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def create_embedding_batch(
    runtime: EmbeddingRuntime,
    *,
    input_file_id: str,
    metadata: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "input_file_id": input_file_id,
        "endpoint": "/v1/embeddings",
        "completion_window": OPENAI_BATCH_COMPLETION_WINDOW,
    }
    if metadata:
        payload["metadata"] = metadata
    return _json_request(runtime=runtime, path="/batches", method="POST", payload=payload)


def retrieve_batch(runtime: EmbeddingRuntime, batch_id: str) -> dict[str, Any]:
    return _json_request(runtime=runtime, path=f"/batches/{batch_id}")


def _download_response_to_temp(runtime: EmbeddingRuntime, file_id: str, temp_path: Path) -> DownloadedFileResult:
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    if temp_path.exists():
        temp_path.unlink()
    request = _authorized_request(
        runtime=runtime,
        path=f"/files/{file_id}/content",
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=runtime.timeout_seconds) as response:
        headers = {key: value for key, value in response.headers.items()}
        byte_count = 0
        with temp_path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                byte_count += len(chunk)
    return DownloadedFileResult(path=temp_path, byte_count=byte_count, headers=headers)


def _bad_evidence_path(path: Path) -> Path:
    while True:
        candidate = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.bad")
        if not candidate.exists():
            return candidate


def preserve_bad_file(path: Path) -> Path:
    bad_path = _bad_evidence_path(path)
    path.replace(bad_path)
    return bad_path


def _read_request_custom_ids(request_file_path: Path) -> list[str]:
    custom_ids: list[str] = []
    with request_file_path.open("rb") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            payload = json.loads(raw_line.decode("utf-8"))
            custom_id = str(payload.get("custom_id") or "").strip()
            if custom_id:
                custom_ids.append(custom_id)
    return custom_ids


def inspect_jsonl_file(
    path: Path,
    *,
    request_file_path: Path | None = None,
    missing_custom_ids_path: Path | None = None,
) -> JsonlInspectionResult:
    ok_lines = 0
    bad_line: int | None = None
    bad_offset: int | None = None
    last_custom_id: str | None = None
    output_custom_ids: list[str] = []
    output_custom_id_set: set[str] = set()
    byte_offset = 0

    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line_start_offset = byte_offset
            byte_offset += len(raw_line)
            if not raw_line.strip():
                continue
            try:
                decoded = raw_line.decode("utf-8")
            except UnicodeDecodeError as exc:
                bad_line = line_number
                bad_offset = line_start_offset + exc.start
                break
            stripped = decoded.strip()
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                bad_line = line_number
                bad_offset = line_start_offset + exc.pos
                break

            ok_lines += 1
            custom_id = str(payload.get("custom_id") or "").strip()
            if custom_id:
                last_custom_id = custom_id
                if custom_id not in output_custom_id_set:
                    output_custom_id_set.add(custom_id)
                    output_custom_ids.append(custom_id)

    missing_custom_ids_count = 0
    missing_custom_ids_path_str: str | None = None
    if request_file_path and missing_custom_ids_path:
        request_custom_ids = _read_request_custom_ids(request_file_path)
        missing_custom_ids = [custom_id for custom_id in request_custom_ids if custom_id not in output_custom_id_set]
        if missing_custom_ids:
            missing_custom_ids_path.parent.mkdir(parents=True, exist_ok=True)
            missing_custom_ids_path.write_text("\n".join(missing_custom_ids) + "\n", encoding="utf-8")
            missing_custom_ids_count = len(missing_custom_ids)
            missing_custom_ids_path_str = str(missing_custom_ids_path)
        elif missing_custom_ids_path.exists():
            missing_custom_ids_path.unlink()

    return JsonlInspectionResult(
        ok_lines=ok_lines,
        bad_line=bad_line,
        bad_offset=bad_offset,
        last_custom_id=last_custom_id,
        output_custom_ids_count=len(output_custom_ids),
        missing_custom_ids_count=missing_custom_ids_count,
        missing_custom_ids_path=missing_custom_ids_path_str,
    )


def download_file_to_path(runtime: EmbeddingRuntime, file_id: str, destination_path: Path) -> Path:
    temp_path = destination_path.with_suffix(destination_path.suffix + ".part")
    _download_response_to_temp(runtime, file_id, temp_path)
    temp_path.replace(destination_path)
    return destination_path


def download_jsonl_file_to_path(
    runtime: EmbeddingRuntime,
    file_id: str,
    destination_path: Path,
    *,
    request_file_path: Path | None = None,
    missing_custom_ids_path: Path | None = None,
    promote_on_success: bool = True,
) -> DownloadedJsonlResult:
    temp_path = destination_path.with_suffix(destination_path.suffix + ".part")
    download_result = _download_response_to_temp(runtime, file_id, temp_path)
    inspection = inspect_jsonl_file(
        temp_path,
        request_file_path=request_file_path,
        missing_custom_ids_path=missing_custom_ids_path,
    )

    if inspection.is_valid:
        if promote_on_success:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.replace(destination_path)
            return DownloadedJsonlResult(
                temp_path=temp_path,
                byte_count=download_result.byte_count,
                headers=download_result.headers,
                inspection=inspection,
                destination_path=destination_path,
            )
        return DownloadedJsonlResult(
            temp_path=temp_path,
            byte_count=download_result.byte_count,
            headers=download_result.headers,
            inspection=inspection,
        )

    bad_path = _bad_evidence_path(destination_path)
    temp_path.replace(bad_path)
    return DownloadedJsonlResult(
        temp_path=temp_path,
        byte_count=download_result.byte_count,
        headers=download_result.headers,
        inspection=inspection,
        bad_path=bad_path,
    )


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


def collect_pending_segment_records(
    session: Session,
    *,
    embedding_model: Optional[str] = None,
    content_field: Optional[str] = None,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    start_after_segment_id: Optional[str] = None,
    limit: int = OPENAI_BATCH_MAX_REQUESTS,
) -> list[dict[str, Any]]:
    resolved_field = resolve_embedding_content_field(content_field)
    runtime = resolve_embedding_runtime(embedding_model=embedding_model, tradition_id=tradition_id)
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=resolved_field)

    stmt = (
        select(Segment)
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
        )
        .join(Segment.text_version)
        .join(TextVersion.work)
        .outerjoin(
            EmbeddingIndexMetadata,
            and_(
                EmbeddingIndexMetadata.owner_type == "segment",
                EmbeddingIndexMetadata.owner_id == Segment.id,
                EmbeddingIndexMetadata.embedding_model == storage_embedding_model,
            ),
        )
        .where(EmbeddingIndexMetadata.id.is_(None))
        .order_by(Segment.id)
        .limit(limit)
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
    records: list[dict[str, Any]] = []
    for segment in segments:
        record = _segment_record_payload(segment)
        if not segment_text_value(record, content_field=resolved_field).strip():
            continue
        records.append(record)
    return records


def hydrate_segment_records(session: Session, segment_ids: list[str]) -> list[dict[str, Any]]:
    if not segment_ids:
        return []

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
    return [_segment_record_payload(segment) for segment in segments]


def build_batch_request_lines(
    records: list[dict[str, Any]],
    *,
    runtime: EmbeddingRuntime,
    content_field: Optional[str] = None,
) -> list[str]:
    resolved_field = resolve_embedding_content_field(content_field)
    lines: list[str] = []
    for record in records:
        text_value = segment_text_value(record, content_field=resolved_field)
        if not text_value.strip():
            continue
        payload = {
            "custom_id": record["id"],
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {
                "model": runtime.model,
                "input": text_value,
                "dimensions": runtime.dimension,
            },
        }
        lines.append(json.dumps(payload, ensure_ascii=False))
    return lines


def write_batch_request_file(
    destination_path: Path,
    *,
    records: list[dict[str, Any]],
    runtime: EmbeddingRuntime,
    content_field: Optional[str] = None,
) -> int:
    lines = build_batch_request_lines(records, runtime=runtime, content_field=content_field)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(lines)
    if payload:
        payload += "\n"
    destination_path.write_text(payload, encoding="utf-8")
    return len(lines)


def apply_batch_output_file(
    session: Session,
    output_path: Path,
    *,
    embedding_model: Optional[str] = None,
    content_field: Optional[str] = None,
    tradition_id: Optional[str] = None,
    request_file_path: Path | None = None,
    missing_custom_ids_path: Path | None = None,
    chunk_size: int = 250,
) -> BatchApplyResult:
    resolved_field = resolve_embedding_content_field(content_field)
    runtime = resolve_embedding_runtime(embedding_model=embedding_model, tradition_id=tradition_id)
    pending_segment_ids: list[str] = []
    embedding_by_segment_id: dict[str, list[float]] = {}
    inserted_count = 0
    success_count = 0
    error_count = 0
    ok_lines = 0
    bad_line: int | None = None
    bad_offset: int | None = None
    last_custom_id: str | None = None
    output_custom_id_set: set[str] = set()

    def flush_pending() -> None:
        nonlocal inserted_count
        if not pending_segment_ids:
            return
        records = hydrate_segment_records(session, pending_segment_ids)
        record_by_id = {record["id"]: record for record in records}
        ordered_records: list[dict[str, Any]] = []
        ordered_embeddings: list[list[float]] = []
        for segment_id in pending_segment_ids:
            record = record_by_id.get(segment_id)
            embedding = embedding_by_segment_id.get(segment_id)
            if record is None or embedding is None:
                continue
            if not segment_text_value(record, content_field=resolved_field).strip():
                continue
            ordered_records.append(record)
            ordered_embeddings.append(embedding)
        if ordered_records:
            inserted_count += upsert_segment_embeddings(
                session,
                ordered_records,
                ordered_embeddings,
                runtime=runtime,
                content_field=resolved_field,
            )
        pending_segment_ids.clear()
        embedding_by_segment_id.clear()

    byte_offset = 0
    with output_path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line_start_offset = byte_offset
            byte_offset += len(raw_line)
            if not raw_line.strip():
                continue
            try:
                decoded = raw_line.decode("utf-8")
            except UnicodeDecodeError as exc:
                bad_line = line_number
                bad_offset = line_start_offset + exc.start
                break
            stripped = decoded.strip()
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                bad_line = line_number
                bad_offset = line_start_offset + exc.pos
                break

            ok_lines += 1
            custom_id = str(payload.get("custom_id") or "").strip()
            if custom_id:
                last_custom_id = custom_id
                output_custom_id_set.add(custom_id)
            response = payload.get("response") or {}
            body = response.get("body") or {}
            data = body.get("data") or []
            if response.get("status_code") != 200 or not custom_id or not data:
                error_count += 1
                continue
            embedding = data[0].get("embedding")
            if not isinstance(embedding, list):
                error_count += 1
                continue
            embedding_by_segment_id[custom_id] = [float(value) for value in embedding]
            pending_segment_ids.append(custom_id)
            success_count += 1
            if len(pending_segment_ids) >= chunk_size:
                flush_pending()

    flush_pending()

    missing_custom_ids_count = 0
    missing_custom_ids_path_str: str | None = None
    if request_file_path and missing_custom_ids_path:
        request_custom_ids = _read_request_custom_ids(request_file_path)
        missing_custom_ids = [custom_id for custom_id in request_custom_ids if custom_id not in output_custom_id_set]
        if missing_custom_ids:
            missing_custom_ids_path.parent.mkdir(parents=True, exist_ok=True)
            missing_custom_ids_path.write_text("\n".join(missing_custom_ids) + "\n", encoding="utf-8")
            missing_custom_ids_count = len(missing_custom_ids)
            missing_custom_ids_path_str = str(missing_custom_ids_path)
        elif missing_custom_ids_path.exists():
            missing_custom_ids_path.unlink()

    return BatchApplyResult(
        inserted_count=inserted_count,
        success_count=success_count,
        error_count=error_count,
        ok_lines=ok_lines,
        bad_line=bad_line,
        bad_offset=bad_offset,
        last_custom_id=last_custom_id,
        output_custom_ids_count=len(output_custom_id_set),
        missing_custom_ids_count=missing_custom_ids_count,
        missing_custom_ids_path=missing_custom_ids_path_str,
    )
