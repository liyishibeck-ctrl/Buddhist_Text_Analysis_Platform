from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.db.session import SessionLocal
from backend.app.services.openai_batch_embeddings import (
    OPENAI_BATCH_MAX_REQUESTS,
    apply_batch_output_file,
    collect_pending_segment_records,
    create_embedding_batch,
    download_jsonl_file_to_path,
    download_file_to_path,
    inspect_jsonl_file,
    preserve_bad_file,
    retrieve_batch,
    upload_batch_input_file,
    write_batch_request_file,
)
from backend.app.services.vector_service import (
    resolve_embedding_content_field,
    resolve_embedding_runtime,
    resolve_storage_embedding_model,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE_ROOT = ROOT_DIR / "data" / "processed" / "openai_batch_embeddings"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-") or "default"


def _default_workspace_dir(args: argparse.Namespace) -> Path:
    scope = _slug(args.tradition_id or "all")
    field = _slug(resolve_embedding_content_field(args.content_field))
    return DEFAULT_WORKSPACE_ROOT / f"{scope}-{field}"


def _workspace_dir(args: argparse.Namespace) -> Path:
    return (args.workspace_dir or _default_workspace_dir(args)).resolve()


def _workspace_paths(workspace_dir: Path) -> dict[str, Path]:
    return {
        "manifest": workspace_dir / "manifest.json",
        "jobs": workspace_dir / "jobs.json",
        "requests": workspace_dir / "requests",
        "responses": workspace_dir / "responses",
        "errors": workspace_dir / "errors",
    }


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_manifest(paths: dict[str, Path]) -> dict[str, Any]:
    manifest = _read_json(paths["manifest"], default={})
    if not manifest:
        raise FileNotFoundError(f"Batch manifest not found: {paths['manifest']}")
    return manifest


def _load_jobs(paths: dict[str, Path]) -> list[dict[str, Any]]:
    return _read_json(paths["jobs"], default=[])


def _save_jobs(paths: dict[str, Path], jobs: list[dict[str, Any]]) -> None:
    _write_json(paths["jobs"], jobs)


def _request_job_map(jobs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(job["request_file"]): job for job in jobs}


def _job_for_batch_id(jobs: list[dict[str, Any]], batch_id: str) -> dict[str, Any] | None:
    target = batch_id.strip()
    for job in jobs:
        if str(job.get("batch_id") or "").strip() == target:
            return job
        prior_batch_ids = [str(value).strip() for value in (job.get("prior_batch_ids") or [])]
        if target in prior_batch_ids:
            return job
    return None


def _job_request_file_path(workspace_dir: Path, job: dict[str, Any]) -> Path:
    return workspace_dir / str(job["request_file"])


def _job_missing_custom_ids_path(paths: dict[str, Path], job: dict[str, Any]) -> Path:
    request_stem = Path(str(job["request_file"])).stem
    return paths["responses"] / f"{request_stem}.missing_custom_ids.txt"


def _print_job_summary(jobs: list[dict[str, Any]]) -> None:
    total = len(jobs)
    completed = sum(1 for job in jobs if job.get("status") == "completed")
    applied = sum(1 for job in jobs if job.get("applied_at"))
    failed = sum(1 for job in jobs if job.get("status") in {"failed", "expired", "cancelled"})
    pending = total - completed - failed
    print(
        f"Jobs: total={total} pending={pending} completed={completed} failed={failed} applied={applied}"
    )


def _apply_completed_job(
    *,
    workspace_dir: Path,
    paths: dict[str, Path],
    manifest: dict[str, Any],
    job: dict[str, Any],
    runtime,
    chunk_size: int,
) -> None:
    request_file_path = _job_request_file_path(workspace_dir, job)
    missing_custom_ids_path = _job_missing_custom_ids_path(paths, job)
    output_path = workspace_dir / str(job["output_path"]) if job.get("output_path") else None
    output_bad_path = workspace_dir / str(job["output_bad_path"]) if job.get("output_bad_path") else None
    source_path = output_path if output_path and output_path.exists() else output_bad_path

    if source_path is None or not source_path.exists():
        job["apply_error"] = "No downloaded output file is available for apply."
        print(f"Skipped apply for {job['request_file']}: {job['apply_error']}")
        return

    with SessionLocal() as session:
        result = apply_batch_output_file(
            session,
            source_path,
            embedding_model=manifest.get("embedding_model"),
            content_field=manifest.get("content_field"),
            tradition_id=manifest.get("tradition_id"),
            request_file_path=request_file_path,
            missing_custom_ids_path=missing_custom_ids_path,
            chunk_size=chunk_size,
        )

    job["inserted_count"] = result.inserted_count
    job["success_count"] = result.success_count
    job["error_count"] = result.error_count
    job["ok_lines"] = result.ok_lines
    job["bad_line"] = result.bad_line
    job["bad_offset"] = result.bad_offset
    job["last_custom_id"] = result.last_custom_id
    job["output_custom_ids_count"] = result.output_custom_ids_count
    job["missing_custom_ids_count"] = result.missing_custom_ids_count
    if result.missing_custom_ids_path:
        job["missing_custom_ids_path"] = result.missing_custom_ids_path
    elif job.get("missing_custom_ids_path"):
        job.pop("missing_custom_ids_path", None)

    if result.bad_line is None and result.missing_custom_ids_count == 0:
        job["applied_at"] = _utc_now()
        job.pop("partial_applied_at", None)
        job.pop("apply_error", None)
    else:
        if output_path and source_path == output_path and output_path.exists():
            bad_path = preserve_bad_file(output_path)
            job["output_bad_path"] = str(bad_path.relative_to(workspace_dir))
            job.pop("output_path", None)
        job["partial_applied_at"] = _utc_now()
        job["apply_error"] = (
            f"partial apply; bad_line={result.bad_line} bad_offset={result.bad_offset} "
            f"missing_custom_ids={result.missing_custom_ids_count}"
        )

    print(
        f"Applied {job['request_file']}: inserted={result.inserted_count} "
        f"success={result.success_count} error={result.error_count} "
        f"ok_lines={result.ok_lines} bad_line={result.bad_line} "
        f"missing={result.missing_custom_ids_count}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage OpenAI Batch embedding jobs for segment content or gloss.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_args(target: argparse.ArgumentParser) -> None:
        target.add_argument("--embedding-model")
        target.add_argument("--content-field", choices=["normalized_content", "content", "content_gloss"])
        target.add_argument("--tradition-id")
        target.add_argument("--collection-id")
        target.add_argument("--language-id")
        target.add_argument("--workspace-dir", type=Path)

    build_parser = subparsers.add_parser("build", help="Build batch request files from pending segments.")
    add_common_args(build_parser)
    build_parser.add_argument("--max-requests-per-file", type=int, default=OPENAI_BATCH_MAX_REQUESTS)
    build_parser.add_argument("--max-files", type=int)
    build_parser.add_argument("--start-after-segment-id")

    submit_parser = subparsers.add_parser("submit", help="Upload request files and create OpenAI Batch jobs.")
    add_common_args(submit_parser)
    submit_parser.add_argument("--retry-failed", action="store_true")

    sync_parser = subparsers.add_parser("sync", help="Refresh remote job status, download outputs, and optionally apply.")
    add_common_args(sync_parser)
    sync_parser.add_argument("--apply", action="store_true")
    sync_parser.add_argument("--chunk-size", type=int, default=250)

    watch_parser = subparsers.add_parser("watch", help="Poll batch status until all submitted jobs settle.")
    add_common_args(watch_parser)
    watch_parser.add_argument("--apply", action="store_true")
    watch_parser.add_argument("--chunk-size", type=int, default=250)
    watch_parser.add_argument("--interval-seconds", type=int, default=60)

    diagnose_parser = subparsers.add_parser(
        "diagnose-output",
        help="Fetch batch metadata, download an output JSONL to a .part file, and validate it without writing to the database.",
    )
    add_common_args(diagnose_parser)
    diagnose_parser.add_argument("--batch-id")
    diagnose_parser.add_argument("--output-file-id")
    diagnose_parser.add_argument("--request-file", type=Path)
    diagnose_parser.add_argument("--destination-path", type=Path)

    return parser.parse_args()


def build_workspace(args: argparse.Namespace) -> None:
    workspace_dir = _workspace_dir(args)
    paths = _workspace_paths(workspace_dir)
    if paths["manifest"].exists() or any(path.exists() for path in paths.values() if path.name != "jobs.json"):
        raise FileExistsError(f"Workspace already exists: {workspace_dir}")

    runtime = resolve_embedding_runtime(embedding_model=args.embedding_model, tradition_id=args.tradition_id)
    resolved_field = resolve_embedding_content_field(args.content_field)
    storage_embedding_model = resolve_storage_embedding_model(runtime.model, content_field=resolved_field)

    created_files: list[dict[str, Any]] = []
    next_cursor = args.start_after_segment_id
    file_index = 1
    manifest = {
        "created_at": _utc_now(),
        "workspace_dir": str(workspace_dir),
        "embedding_model": runtime.model,
        "storage_embedding_model": storage_embedding_model,
        "content_field": resolved_field,
        "tradition_id": args.tradition_id,
        "collection_id": args.collection_id,
        "language_id": args.language_id,
        "request_files": created_files,
        "next_start_after_segment_id": next_cursor,
    }
    _write_json(paths["manifest"], manifest)
    _save_jobs(paths, [])

    with SessionLocal() as session:
        while True:
            if args.max_files is not None and file_index > args.max_files:
                break
            records = collect_pending_segment_records(
                session,
                embedding_model=runtime.model,
                content_field=resolved_field,
                tradition_id=args.tradition_id,
                collection_id=args.collection_id,
                language_id=args.language_id,
                start_after_segment_id=next_cursor,
                limit=args.max_requests_per_file,
            )
            if not records:
                break
            request_path = paths["requests"] / f"batch-{file_index:04d}.jsonl"
            request_count = write_batch_request_file(
                request_path,
                records=records,
                runtime=runtime,
                content_field=resolved_field,
            )
            created_files.append(
                {
                    "request_file": str(request_path.relative_to(workspace_dir)),
                    "record_count": request_count,
                    "first_segment_id": records[0]["id"],
                    "last_segment_id": records[-1]["id"],
                }
            )
            next_cursor = records[-1]["id"]
            manifest["next_start_after_segment_id"] = next_cursor
            _write_json(paths["manifest"], manifest)
            print(f"Built {request_path.name}: {request_count} requests through {next_cursor}", flush=True)
            file_index += 1

    _write_json(paths["manifest"], manifest)
    print(f"Workspace: {workspace_dir}")
    print(f"Request files: {len(created_files)}")
    print(f"Storage embedding model: {storage_embedding_model}")


def submit_workspace(args: argparse.Namespace) -> None:
    workspace_dir = _workspace_dir(args)
    paths = _workspace_paths(workspace_dir)
    manifest = _load_manifest(paths)
    jobs = _load_jobs(paths)
    job_by_request_file = _request_job_map(jobs)
    runtime = resolve_embedding_runtime(
        embedding_model=manifest.get("embedding_model"),
        tradition_id=manifest.get("tradition_id"),
    )

    for item in manifest.get("request_files", []):
        request_key = str(item["request_file"])
        existing_job = job_by_request_file.get(request_key)
        if existing_job and not (args.retry_failed and existing_job.get("status") == "failed"):
            continue
        request_path = workspace_dir / request_key
        if existing_job and existing_job.get("input_file_id"):
            input_file_id = str(existing_job["input_file_id"])
        else:
            upload_payload = upload_batch_input_file(runtime, request_path)
            input_file_id = str(upload_payload["id"])
        batch_payload = create_embedding_batch(
            runtime,
            input_file_id=input_file_id,
            metadata={
                "content_field": str(manifest.get("content_field") or ""),
                "tradition_id": str(manifest.get("tradition_id") or ""),
                "request_file": request_key,
            },
        )
        if existing_job:
            prior_batch_ids = list(existing_job.get("prior_batch_ids") or [])
            if existing_job.get("batch_id"):
                prior_batch_ids.append(str(existing_job["batch_id"]))
            existing_job["prior_batch_ids"] = prior_batch_ids
            existing_job["batch_id"] = batch_payload["id"]
            existing_job["input_file_id"] = input_file_id
            existing_job["status"] = batch_payload.get("status")
            existing_job["submitted_at"] = _utc_now()
            existing_job["last_synced_at"] = None
            existing_job["output_file_id"] = None
            existing_job["error_file_id"] = None
            existing_job["request_counts"] = None
            existing_job.pop("output_path", None)
            existing_job.pop("error_path", None)
            existing_job.pop("applied_at", None)
            existing_job.pop("inserted_count", None)
            existing_job.pop("success_count", None)
            existing_job.pop("error_count", None)
            print(f"Resubmitted {request_key} -> {batch_payload['id']}")
        else:
            jobs.append(
                {
                    "request_file": request_key,
                    "record_count": item["record_count"],
                    "batch_id": batch_payload["id"],
                    "input_file_id": input_file_id,
                    "status": batch_payload.get("status"),
                    "submitted_at": _utc_now(),
                }
            )
            print(f"Submitted {request_key} -> {batch_payload['id']}")

    _save_jobs(paths, jobs)
    _print_job_summary(jobs)


def diagnose_output(args: argparse.Namespace) -> None:
    manifest: dict[str, Any] = {}
    jobs: list[dict[str, Any]] = []
    workspace_dir: Path | None = None
    if args.workspace_dir:
        workspace_dir = args.workspace_dir.resolve()
        paths = _workspace_paths(workspace_dir)
        manifest = _load_manifest(paths)
        jobs = _load_jobs(paths)

    embedding_model = args.embedding_model or manifest.get("embedding_model")
    tradition_id = args.tradition_id or manifest.get("tradition_id")
    runtime = resolve_embedding_runtime(
        embedding_model=embedding_model,
        tradition_id=tradition_id,
    )

    batch_payload: dict[str, Any] | None = None
    job: dict[str, Any] | None = None
    if args.batch_id:
        batch_payload = retrieve_batch(runtime, str(args.batch_id))
        if jobs:
            job = _job_for_batch_id(jobs, str(args.batch_id))
    output_file_id = args.output_file_id or (batch_payload or {}).get("output_file_id")
    if not output_file_id:
        raise ValueError("No output file id available. Provide --output-file-id or a --batch-id whose batch has output_file_id.")

    error_file_id = (batch_payload or {}).get("error_file_id")
    request_counts = (batch_payload or {}).get("request_counts")

    if args.destination_path:
        destination_path = args.destination_path.resolve()
    elif workspace_dir is not None:
        destination_path = (workspace_dir / "diagnostics" / f"{str(output_file_id)}.output.jsonl").resolve()
    else:
        destination_path = (DEFAULT_WORKSPACE_ROOT / "diagnostics" / f"{str(output_file_id)}.output.jsonl").resolve()

    request_file_path: Path | None = None
    if args.request_file:
        request_file_path = args.request_file.resolve()
    elif workspace_dir is not None and job is not None:
        request_file_path = _job_request_file_path(workspace_dir, job)

    missing_custom_ids_path = destination_path.with_name(f"{destination_path.stem}.missing_custom_ids.txt")
    download_result = download_jsonl_file_to_path(
        runtime,
        str(output_file_id),
        destination_path,
        request_file_path=request_file_path,
        missing_custom_ids_path=missing_custom_ids_path,
        promote_on_success=False,
    )
    inspected_path = download_result.bad_path or download_result.temp_path
    if inspected_path != download_result.temp_path:
        inspection = inspect_jsonl_file(
            inspected_path,
            request_file_path=request_file_path,
            missing_custom_ids_path=missing_custom_ids_path,
        )
    else:
        inspection = download_result.inspection

    print(f"BATCH_ID={args.batch_id or (job or {}).get('batch_id') or ''}")
    print(f"BATCH_STATUS={(batch_payload or {}).get('status') or ''}")
    print(f"OUTPUT_FILE_ID={output_file_id}")
    print(f"ERROR_FILE_ID={error_file_id or ''}")
    print(f"REQUEST_COUNTS={json.dumps(request_counts or {}, ensure_ascii=False)}")
    print(f"LOCAL_PATH={inspected_path}")
    print(f"LOCAL_SIZE={download_result.byte_count}")
    print(f"HEADERS={json.dumps(download_result.headers, ensure_ascii=False)}")
    print(f"OK_LINES={inspection.ok_lines}")
    print(f"BAD_LINE={inspection.bad_line if inspection.bad_line is not None else ''}")
    print(f"BAD_OFFSET={inspection.bad_offset if inspection.bad_offset is not None else ''}")
    print(f"LAST_CUSTOM_ID={inspection.last_custom_id or ''}")
    print(f"OUTPUT_CUSTOM_IDS={inspection.output_custom_ids_count}")
    print(f"MISSING_CUSTOM_IDS={inspection.missing_custom_ids_count}")
    print(f"MISSING_CUSTOM_IDS_PATH={inspection.missing_custom_ids_path or ''}")
    print(f"BAD_PATH={download_result.bad_path or ''}")


def sync_workspace(args: argparse.Namespace) -> bool:
    workspace_dir = _workspace_dir(args)
    paths = _workspace_paths(workspace_dir)
    manifest = _load_manifest(paths)
    jobs = _load_jobs(paths)
    runtime = resolve_embedding_runtime(
        embedding_model=manifest.get("embedding_model"),
        tradition_id=manifest.get("tradition_id"),
    )

    changed = False
    for job in jobs:
        batch_id = job.get("batch_id")
        if not batch_id:
            continue
        batch_payload = retrieve_batch(runtime, str(batch_id))
        job["status"] = batch_payload.get("status")
        job["last_synced_at"] = _utc_now()
        job["output_file_id"] = batch_payload.get("output_file_id")
        job["error_file_id"] = batch_payload.get("error_file_id")
        job["request_counts"] = batch_payload.get("request_counts")
        job["errors"] = batch_payload.get("errors")
        changed = True

        request_path = Path(str(job["request_file"]))
        request_stem = request_path.stem
        output_file_id = job.get("output_file_id")
        if output_file_id:
            output_path = paths["responses"] / f"{request_stem}.output.jsonl"
            missing_custom_ids_path = _job_missing_custom_ids_path(paths, job)
            if not output_path.exists():
                download_result = download_jsonl_file_to_path(
                    runtime,
                    str(output_file_id),
                    output_path,
                    request_file_path=workspace_dir / str(job["request_file"]),
                    missing_custom_ids_path=missing_custom_ids_path,
                )
                job["output_headers"] = download_result.headers
                job["output_file_size"] = download_result.byte_count
                job["ok_lines"] = download_result.inspection.ok_lines
                job["bad_line"] = download_result.inspection.bad_line
                job["bad_offset"] = download_result.inspection.bad_offset
                job["last_custom_id"] = download_result.inspection.last_custom_id
                job["output_custom_ids_count"] = download_result.inspection.output_custom_ids_count
                job["missing_custom_ids_count"] = download_result.inspection.missing_custom_ids_count
                if download_result.inspection.missing_custom_ids_path:
                    job["missing_custom_ids_path"] = download_result.inspection.missing_custom_ids_path
                if download_result.destination_path:
                    job["output_path"] = str(download_result.destination_path.relative_to(workspace_dir))
                    job.pop("output_bad_path", None)
                if download_result.bad_path:
                    job["output_bad_path"] = str(download_result.bad_path.relative_to(workspace_dir))
                    job.pop("output_path", None)
            elif "output_path" not in job:
                job["output_path"] = str(output_path.relative_to(workspace_dir))

        error_file_id = job.get("error_file_id")
        if error_file_id:
            error_path = paths["errors"] / f"{request_stem}.error.jsonl"
            if not error_path.exists():
                download_file_to_path(runtime, str(error_file_id), error_path)
            job["error_path"] = str(error_path.relative_to(workspace_dir))

        if (
            args.apply
            and job.get("status") == "completed"
            and (job.get("output_path") or job.get("output_bad_path"))
            and not job.get("applied_at")
        ):
            _apply_completed_job(
                workspace_dir=workspace_dir,
                paths=paths,
                manifest=manifest,
                job=job,
                runtime=runtime,
                chunk_size=args.chunk_size,
            )

    if changed:
        _save_jobs(paths, jobs)
    _print_job_summary(jobs)
    return all(job.get("status") in {"completed", "failed", "expired", "cancelled"} for job in jobs)


def watch_workspace(args: argparse.Namespace) -> None:
    while True:
        settled = sync_workspace(args)
        if settled:
            return
        time.sleep(max(5, args.interval_seconds))


def main() -> None:
    args = parse_args()
    if args.command == "build":
        build_workspace(args)
        return
    if args.command == "submit":
        submit_workspace(args)
        return
    if args.command == "sync":
        sync_workspace(args)
        return
    if args.command == "watch":
        watch_workspace(args)
        return
    if args.command == "diagnose-output":
        diagnose_output(args)
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
