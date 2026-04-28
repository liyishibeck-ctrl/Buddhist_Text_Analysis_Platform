from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from backend.app.core.config import ROOT_DIR
from backend.app.db.session import SessionLocal
from backend.app.services.realtime_embedding_worker import (
    REALTIME_EMBEDDING_DIMENSION,
    REALTIME_EMBEDDING_MODEL,
    _realtime_staging_table,
)
from backend.app.services.vector_service import (
    DEFAULT_EMBEDDING_CONTENT_FIELD,
    resolve_embedding_content_field,
    resolve_storage_embedding_model,
)


LOG_DIR = ROOT_DIR / "data" / "processed" / "logs"
LATEST_REALTIME_WORKER_PATH = LOG_DIR / "latest_realtime_embedding_worker.txt"


@dataclass(slots=True)
class RealtimeWorkerInfo:
    pid: Optional[int]
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    supervisor_state_path: Optional[Path]
    tradition_id: Optional[str]
    collection_id: Optional[str]
    language_id: Optional[str]
    content_field: str
    embedding_model: str
    storage_embedding_model: str
    dimension: int
    started_at: datetime


@dataclass(slots=True)
class RealtimeSnapshot:
    total_target_segments: int
    indexed_segments: int
    indexed_since_started_at: int
    staging_backlog: int
    latest_indexed_at: Optional[datetime]


@dataclass(slots=True)
class RealtimeSample:
    observed_at: datetime
    snapshot: RealtimeSnapshot


def read_supervisor_state(path: Optional[Path]) -> Optional[dict]:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch a realtime embedding worker for progress and stalls.")
    parser.add_argument("--state-file", type=Path, default=LATEST_REALTIME_WORKER_PATH)
    parser.add_argument("--interval", type=int, default=30, help="Refresh interval in seconds.")
    parser.add_argument("--stall-seconds", type=int, default=180, help="Alert if no progress for this many seconds.")
    parser.add_argument("--tail-lines", type=int, default=20, help="How many stderr lines to show on alerts.")
    parser.add_argument("--once", action="store_true", help="Print one snapshot and exit.")
    return parser.parse_args()


def read_worker_info(state_file: Path) -> RealtimeWorkerInfo:
    if not state_file.exists():
        raise FileNotFoundError(f"Realtime worker state file not found: {state_file}")

    values: dict[str, str] = {}
    for line in state_file.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    started_at_raw = values.get("STARTED_AT")
    if started_at_raw:
        started_at = datetime.fromisoformat(started_at_raw)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
    else:
        started_at = datetime.fromtimestamp(state_file.stat().st_mtime, tz=timezone.utc)

    content_field = resolve_embedding_content_field(values.get("CONTENT_FIELD") or DEFAULT_EMBEDDING_CONTENT_FIELD)
    embedding_model = values.get("EMBEDDING_MODEL") or REALTIME_EMBEDDING_MODEL
    storage_embedding_model = values.get("STORAGE_EMBEDDING_MODEL") or resolve_storage_embedding_model(
        embedding_model,
        content_field=content_field,
    )
    return RealtimeWorkerInfo(
        pid=int(values["PID"]) if values.get("PID") else None,
        stdout_path=Path(values["STDOUT"]) if values.get("STDOUT") else None,
        stderr_path=Path(values["STDERR"]) if values.get("STDERR") else None,
        supervisor_state_path=Path(values["SUPERVISOR_STATE"]) if values.get("SUPERVISOR_STATE") else None,
        tradition_id=values.get("TRADITION_ID") or None,
        collection_id=values.get("COLLECTION_ID") or None,
        language_id=values.get("LANGUAGE_ID") or None,
        content_field=content_field,
        embedding_model=embedding_model,
        storage_embedding_model=storage_embedding_model,
        dimension=int(values.get("DIMENSION") or REALTIME_EMBEDDING_DIMENSION),
        started_at=started_at,
    )


def is_process_alive(pid: Optional[int]) -> bool:
    if pid is None:
        return False
    if os.name == "nt":
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; if ($p) {{ 'alive' }}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() == "alive"
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _content_presence_clause(content_field: str) -> str:
    if content_field == DEFAULT_EMBEDDING_CONTENT_FIELD:
        return "COALESCE(NULLIF(BTRIM(s.normalized_content), ''), NULLIF(BTRIM(s.content), '')) IS NOT NULL"
    return f"NULLIF(BTRIM(s.{content_field}), '') IS NOT NULL"


def fetch_snapshot(worker_info: RealtimeWorkerInfo) -> RealtimeSnapshot:
    content_presence_clause = _content_presence_clause(worker_info.content_field)
    segment_filters = [content_presence_clause]
    indexed_filters = [
        "eim.owner_type = 'segment'",
        "eim.embedding_model = :embedding_model",
        "eim.dimension = :dimension",
        "eim.status = 'indexed'",
        "COALESCE(eim.metadata_json->>'content_field', :default_field) = :content_field",
    ]
    staging_filters = [
        "embedding_model = :embedding_model",
        "dimension = :dimension",
        "field_name = :content_field",
    ]
    params = {
        "embedding_model": worker_info.storage_embedding_model,
        "dimension": worker_info.dimension,
        "default_field": DEFAULT_EMBEDDING_CONTENT_FIELD,
        "content_field": worker_info.content_field,
    }
    if worker_info.tradition_id is not None:
        segment_filters.append("w.tradition_id = :tradition_id")
        indexed_filters.append("w.tradition_id = :tradition_id")
        staging_filters.append("tradition_id = :tradition_id")
        params["tradition_id"] = worker_info.tradition_id
    if worker_info.collection_id is not None:
        segment_filters.append("w.collection_id = :collection_id")
        indexed_filters.append("w.collection_id = :collection_id")
        params["collection_id"] = worker_info.collection_id
    if worker_info.language_id is not None:
        segment_filters.append("tv.language_id = :language_id")
        indexed_filters.append("tv.language_id = :language_id")
        params["language_id"] = worker_info.language_id

    total_sql = f"""
        SELECT COUNT(*)
        FROM segments s
        JOIN text_versions tv ON tv.id = s.text_version_id
        JOIN works w ON w.id = tv.work_id
        WHERE {" AND ".join(segment_filters)}
    """
    indexed_sql = f"""
        SELECT COUNT(*)
        FROM embedding_index_metadata eim
        JOIN segments s ON s.id = eim.owner_id
        JOIN text_versions tv ON tv.id = s.text_version_id
        JOIN works w ON w.id = tv.work_id
        WHERE {" AND ".join(indexed_filters)}
    """
    staging_sql = f"""
        SELECT COUNT(*)
        FROM {_realtime_staging_table()}
        WHERE {" AND ".join(staging_filters)}
    """
    indexed_since_started_at_sql = f"""
        SELECT COUNT(*)
        FROM embedding_index_metadata eim
        JOIN segments s ON s.id = eim.owner_id
        JOIN text_versions tv ON tv.id = s.text_version_id
        JOIN works w ON w.id = tv.work_id
        WHERE {" AND ".join(indexed_filters)}
          AND eim.indexed_at >= :started_at
    """
    latest_indexed_sql = f"""
        SELECT MAX(eim.indexed_at)
        FROM embedding_index_metadata eim
        JOIN segments s ON s.id = eim.owner_id
        JOIN text_versions tv ON tv.id = s.text_version_id
        JOIN works w ON w.id = tv.work_id
        WHERE {" AND ".join(indexed_filters)}
    """
    with SessionLocal() as session:
        total_target_segments = int(session.execute(text(total_sql), params).scalar_one())
        indexed_segments = int(session.execute(text(indexed_sql), params).scalar_one())
        indexed_since_started_at = int(
            session.execute(
                text(indexed_since_started_at_sql),
                {**params, "started_at": worker_info.started_at},
            ).scalar_one()
        )
        staging_exists = session.execute(
            text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": _realtime_staging_table()},
        ).scalar()
        staging_backlog = int(session.execute(text(staging_sql), params).scalar_one()) if staging_exists else 0
        latest_indexed_at = session.execute(text(latest_indexed_sql), params).scalar_one()
    return RealtimeSnapshot(
        total_target_segments=total_target_segments,
        indexed_segments=indexed_segments,
        indexed_since_started_at=indexed_since_started_at,
        staging_backlog=staging_backlog,
        latest_indexed_at=latest_indexed_at,
    )


def read_stderr_tail(stderr_path: Optional[Path], *, tail_lines: int) -> list[str]:
    if stderr_path is None or not stderr_path.exists() or stderr_path.stat().st_size == 0:
        return []
    return stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()[-tail_lines:]


def format_duration(duration: timedelta) -> str:
    total_seconds = max(0, int(duration.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def collect_sample(worker_info: RealtimeWorkerInfo) -> RealtimeSample:
    return RealtimeSample(
        observed_at=datetime.now(timezone.utc),
        snapshot=fetch_snapshot(worker_info),
    )


def has_progress(previous: RealtimeSample, current: RealtimeSample) -> bool:
    return (
        current.snapshot.indexed_segments > previous.snapshot.indexed_segments
        or current.snapshot.staging_backlog != previous.snapshot.staging_backlog
        or current.snapshot.latest_indexed_at != previous.snapshot.latest_indexed_at
    )


def print_status(
    worker_info: RealtimeWorkerInfo,
    sample: RealtimeSample,
    baseline: RealtimeSample,
    *,
    status: str,
    reason: Optional[str] = None,
) -> None:
    supervisor_state = read_supervisor_state(worker_info.supervisor_state_path)
    now_local = sample.observed_at.astimezone()
    started_at_local = worker_info.started_at.astimezone()
    elapsed = now_local - started_at_local
    remaining = max(0, sample.snapshot.total_target_segments - sample.snapshot.indexed_segments)
    processed_since_start = sample.snapshot.indexed_since_started_at
    elapsed_minutes = max(0.001, elapsed.total_seconds() / 60.0)
    segments_per_min = processed_since_start / elapsed_minutes
    eta = "unknown"
    if segments_per_min > 0 and remaining > 0:
        eta = format_duration(timedelta(minutes=remaining / segments_per_min))
    elif remaining == 0 and sample.snapshot.staging_backlog == 0:
        eta = "done"
    percent = (
        sample.snapshot.indexed_segments / sample.snapshot.total_target_segments * 100
        if sample.snapshot.total_target_segments
        else 0.0
    )
    print("=" * 88)
    print(f"[{status}] {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    if reason:
        print(f"Reason: {reason}")
    print(
        f"Scope: tradition={worker_info.tradition_id or 'all'} "
        f"field={worker_info.content_field} "
        f"model={worker_info.storage_embedding_model} "
        f"dim={worker_info.dimension}"
    )
    print(f"PID: {worker_info.pid or 'unknown'} ({'alive' if is_process_alive(worker_info.pid) else 'not running'})")
    print(f"Started: {started_at_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Elapsed: {format_duration(elapsed)}")
    print(
        f"Progress: {sample.snapshot.indexed_segments:,} / {sample.snapshot.total_target_segments:,} "
        f"({percent:.2f}%)"
    )
    print(f"Processed since worker start: {processed_since_start:,}")
    print(f"Remaining: {remaining:,}")
    print(f"Speed: {segments_per_min:,.2f} segments/min")
    print(f"ETA: {eta}")
    print(f"Staging backlog: {sample.snapshot.staging_backlog:,}")
    print(f"Latest indexed_at: {sample.snapshot.latest_indexed_at or 'none'}")
    if supervisor_state:
        print(
            "Supervisor: "
            f"status={supervisor_state.get('status', 'unknown')} "
            f"wave={supervisor_state.get('current_wave', supervisor_state.get('runs_completed', 0))} "
            f"total_processed={supervisor_state.get('total_processed', 0)} "
            f"total_failed={supervisor_state.get('total_failed', 0)}"
        )
        last_wave = supervisor_state.get("last_wave") or {}
        last_stats = last_wave.get("stats") or {}
        if last_stats:
            print(
                "Last wave: "
                f"processed={last_stats.get('processed', 0)} "
                f"failed={last_stats.get('failed', 0)} "
                f"tokens={last_stats.get('tokens_used', 0)} "
                f"elapsed={last_stats.get('elapsed_time', 0):.2f}s"
            )
        if worker_info.supervisor_state_path:
            print(f"Supervisor state: {worker_info.supervisor_state_path}")
    if worker_info.stdout_path:
        print(f"Stdout log: {worker_info.stdout_path}")
    if worker_info.stderr_path:
        print(f"Stderr log: {worker_info.stderr_path}")


def main() -> None:
    args = parse_args()
    worker_info = read_worker_info(args.state_file)
    baseline = collect_sample(worker_info)
    last_progress_sample = baseline
    print_status(worker_info, baseline, baseline, status="INFO")

    if args.once:
        return

    while True:
        time.sleep(max(1, args.interval))
        worker_info = read_worker_info(args.state_file)
        current = collect_sample(worker_info)
        if has_progress(last_progress_sample, current):
            last_progress_sample = current
            print_status(worker_info, current, baseline, status="INFO", reason="progress")
            continue

        no_progress_anchor = last_progress_sample.observed_at
        if current.snapshot.latest_indexed_at is not None:
            no_progress_anchor = _as_aware_utc(current.snapshot.latest_indexed_at)
        no_progress_for = current.observed_at - no_progress_anchor
        process_alive = is_process_alive(worker_info.pid)
        if not process_alive:
            done = (
                current.snapshot.indexed_segments >= current.snapshot.total_target_segments
                and current.snapshot.staging_backlog == 0
            )
            print_status(
                worker_info,
                current,
                baseline,
                status="DONE" if done else "ALERT",
                reason="worker exited cleanly" if done else "worker process is not running",
            )
            stderr_tail = read_stderr_tail(worker_info.stderr_path, tail_lines=args.tail_lines)
            if stderr_tail:
                print("-" * 88)
                print("Recent stderr tail:")
                for line in stderr_tail:
                    print(line)
            return

        if no_progress_for.total_seconds() >= args.stall_seconds:
            print_status(
                worker_info,
                current,
                baseline,
                status="ALERT",
                reason=f"no progress for {format_duration(no_progress_for)}",
            )
            stderr_tail = read_stderr_tail(worker_info.stderr_path, tail_lines=args.tail_lines)
            if stderr_tail:
                print("-" * 88)
                print("Recent stderr tail:")
                for line in stderr_tail:
                    print(line)
            return

        print_status(
            worker_info,
            current,
            baseline,
            status="INFO",
            reason=f"no progress yet ({format_duration(no_progress_for)})",
        )


if __name__ == "__main__":
    main()
