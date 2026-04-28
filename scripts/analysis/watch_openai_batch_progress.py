from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.services.openai_batch_embeddings import retrieve_batch
from backend.app.services.vector_service import resolve_embedding_runtime


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE_ROOT = ROOT_DIR / "data" / "processed" / "openai_batch_embeddings"
TERMINAL_BATCH_STATUSES = {"completed", "failed", "expired", "cancelled"}
DEFAULT_WORKSPACE_NAMES = (
    "trad-pali-normalized_content",
    "trad-pali-normalized_content-part2",
    "trad-pali-content_gloss",
    "trad-tibetan-normalized_content",
    "trad-tibetan-content_gloss",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch OpenAI Batch embedding progress across one or more workspaces.")
    parser.add_argument(
        "--workspace-dir",
        action="append",
        type=Path,
        help="Specific workspace to inspect. Repeat to watch multiple workspaces. Defaults to the main embedding workspaces.",
    )
    parser.add_argument(
        "--all-workspaces",
        action="store_true",
        help="Include every workspace directory under the root, including temporary debug splits.",
    )
    parser.add_argument("--sync", action="store_true", help="Refresh remote batch status before printing the summary.")
    parser.add_argument("--interval-seconds", type=int, default=0, help="Repeat every N seconds. Zero prints once.")
    return parser.parse_args()


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _workspace_paths(workspace_dir: Path) -> dict[str, Path]:
    return {
        "manifest": workspace_dir / "manifest.json",
        "jobs": workspace_dir / "jobs.json",
    }


def _discover_workspaces(workspace_dirs: list[Path] | None, *, all_workspaces: bool) -> list[Path]:
    if workspace_dirs:
        return [path.resolve() for path in workspace_dirs]
    discovered = sorted(path.resolve() for path in DEFAULT_WORKSPACE_ROOT.iterdir() if path.is_dir())
    if all_workspaces:
        return discovered
    preferred = {name: DEFAULT_WORKSPACE_ROOT / name for name in DEFAULT_WORKSPACE_NAMES}
    canonical = [path.resolve() for name, path in preferred.items() if path.exists()]
    return canonical or discovered


def _load_workspace(workspace_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = _workspace_paths(workspace_dir)
    manifest = _read_json(paths["manifest"], default={})
    jobs = _read_json(paths["jobs"], default=[])
    if not manifest:
        raise FileNotFoundError(f"Manifest not found: {paths['manifest']}")
    return manifest, jobs


def _sync_workspace(workspace_dir: Path, manifest: dict[str, Any], jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runtime = resolve_embedding_runtime(
        embedding_model=manifest.get("embedding_model"),
        tradition_id=manifest.get("tradition_id"),
    )
    for job in jobs:
        batch_id = job.get("batch_id")
        if not batch_id:
            continue
        payload = retrieve_batch(runtime, str(batch_id))
        job["status"] = payload.get("status")
        job["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        job["request_counts"] = payload.get("request_counts")
        job["errors"] = payload.get("errors")
        job["output_file_id"] = payload.get("output_file_id")
        job["error_file_id"] = payload.get("error_file_id")
    _write_json(_workspace_paths(workspace_dir)["jobs"], jobs)
    return jobs


def _request_totals(jobs: list[dict[str, Any]]) -> dict[str, int]:
    total_requests = sum(int(job.get("record_count") or 0) for job in jobs)
    total_completed = 0
    total_failed = 0
    for job in jobs:
        counts = job.get("request_counts") or {}
        total_completed += int(counts.get("completed") or 0)
        total_failed += int(counts.get("failed") or 0)
    return {
        "total_requests": total_requests,
        "completed_requests": total_completed,
        "failed_requests": total_failed,
    }


def _error_summary(jobs: list[dict[str, Any]]) -> str:
    codes: Counter[str] = Counter()
    for job in jobs:
        errors = job.get("errors") or {}
        for item in errors.get("data") or []:
            code = str(item.get("code") or "unknown")
            codes[code] += 1
    if not codes:
        return ""
    return ", ".join(f"{code} x{count}" for code, count in sorted(codes.items()))


def _workspace_summary(workspace_dir: Path, manifest: dict[str, Any], jobs: list[dict[str, Any]]) -> list[str]:
    status_counts = Counter(str(job.get("status") or "unknown") for job in jobs)
    request_totals = _request_totals(jobs)
    settled_jobs = sum(status_counts.get(status, 0) for status in TERMINAL_BATCH_STATUSES)
    pending_jobs = len(jobs) - settled_jobs
    error_summary = _error_summary(jobs)
    total_requests = request_totals["total_requests"]
    completion_pct = (request_totals["completed_requests"] / total_requests * 100) if total_requests else 0.0
    lines = [
        f"[{workspace_dir.name}]",
        (
            f"  jobs={len(jobs)} pending={pending_jobs} "
            f"completed={status_counts.get('completed', 0)} "
            f"in_progress={status_counts.get('in_progress', 0)} "
            f"validating={status_counts.get('validating', 0)} "
            f"failed={status_counts.get('failed', 0)}"
        ),
        (
            f"  requests={request_totals['completed_requests']}/{request_totals['total_requests']} "
            f"({completion_pct:.1f}%) "
            f"failed={request_totals['failed_requests']} "
            f"model={manifest.get('storage_embedding_model') or manifest.get('embedding_model')}"
        ),
    ]
    if error_summary:
        lines.append(f"  errors={error_summary}")
    return lines


def _overall_summary(workspace_summaries: list[tuple[dict[str, Any], list[dict[str, Any]]]]) -> list[str]:
    status_counts: Counter[str] = Counter()
    total_requests = 0
    completed_requests = 0
    failed_requests = 0
    for _manifest, jobs in workspace_summaries:
        status_counts.update(str(job.get("status") or "unknown") for job in jobs)
        request_totals = _request_totals(jobs)
        total_requests += request_totals["total_requests"]
        completed_requests += request_totals["completed_requests"]
        failed_requests += request_totals["failed_requests"]
    completion_pct = (completed_requests / total_requests * 100) if total_requests else 0.0
    return [
        "[overall]",
        (
            f"  jobs={sum(status_counts.values())} completed={status_counts.get('completed', 0)} "
            f"in_progress={status_counts.get('in_progress', 0)} "
            f"validating={status_counts.get('validating', 0)} "
            f"failed={status_counts.get('failed', 0)}"
        ),
        (
            f"  requests={completed_requests}/{total_requests} "
            f"({completion_pct:.1f}%) failed={failed_requests}"
        ),
    ]


def print_snapshot(workspace_dirs: list[Path], *, sync: bool) -> None:
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"OpenAI Batch progress @ {timestamp}")
    workspace_summaries: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for workspace_dir in workspace_dirs:
        try:
            manifest, jobs = _load_workspace(workspace_dir)
            if sync:
                jobs = _sync_workspace(workspace_dir, manifest, jobs)
            workspace_summaries.append((manifest, jobs))
            lines = _workspace_summary(workspace_dir, manifest, jobs)
        except FileNotFoundError as exc:
            lines = [f"[{workspace_dir.name}]", f"  missing={exc}"]
        for line in lines:
            print(line)
    if workspace_summaries:
        for line in _overall_summary(workspace_summaries):
            print(line)
    print("", flush=True)


def main() -> None:
    args = parse_args()
    workspace_dirs = _discover_workspaces(args.workspace_dir, all_workspaces=args.all_workspaces)
    if not workspace_dirs:
        raise FileNotFoundError(f"No workspaces found under {DEFAULT_WORKSPACE_ROOT}")

    if args.interval_seconds <= 0:
        print_snapshot(workspace_dirs, sync=args.sync)
        return

    while True:
        print_snapshot(workspace_dirs, sync=args.sync)
        time.sleep(max(5, args.interval_seconds))


if __name__ == "__main__":
    main()
