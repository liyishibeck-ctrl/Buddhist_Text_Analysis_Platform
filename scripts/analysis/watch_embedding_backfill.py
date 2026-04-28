from __future__ import annotations

import argparse
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from backend.app.core.config import ROOT_DIR, settings
from backend.app.db.session import SessionLocal


LOG_DIR = ROOT_DIR / "data" / "processed" / "logs"
LATEST_BACKFILL_PATH = LOG_DIR / "latest_embedding_backfill.txt"


@dataclass(slots=True)
class RunInfo:
    pid: Optional[int]
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    state_file: Optional[Path]
    batch_size: Optional[int]
    start_after: Optional[str]
    started_at: datetime


@dataclass(slots=True)
class Snapshot:
    total_segments: int
    embedded_segments: int
    frontier: Optional[str]
    latest_indexed_at: Optional[datetime]


@dataclass(slots=True)
class Sample:
    observed_at: datetime
    snapshot: Snapshot
    stderr_size: int
    state_mtime: Optional[datetime]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch the active embedding backfill and alert on stalls.")
    parser.add_argument("--interval", type=int, default=20, help="Refresh interval in seconds.")
    parser.add_argument("--stall-seconds", type=int, default=180, help="Alert if no progress for this many seconds.")
    parser.add_argument("--tail-lines", type=int, default=20, help="How many stderr lines to show on alert.")
    parser.add_argument("--embedding-model", default=settings.embedding_model, help="Embedding model to monitor.")
    parser.add_argument("--latest-file", type=Path, default=LATEST_BACKFILL_PATH, help="Path to latest backfill state file.")
    parser.add_argument("--once", action="store_true", help="Print one snapshot and exit.")
    return parser.parse_args()


def read_run_info(latest_file: Path) -> RunInfo:
    if not latest_file.exists():
        raise FileNotFoundError(f"Backfill state file not found: {latest_file}")

    values: dict[str, str] = {}
    for line in latest_file.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    started_at = datetime.fromtimestamp(latest_file.stat().st_mtime, tz=timezone.utc)
    pid = int(values["PID"]) if values.get("PID") else None
    stdout_path = Path(values["STDOUT"]) if values.get("STDOUT") else None
    stderr_path = Path(values["STDERR"]) if values.get("STDERR") else None
    state_file = Path(values["STATE_FILE"]) if values.get("STATE_FILE") else None
    batch_size = int(values["BATCH_SIZE"]) if values.get("BATCH_SIZE") else None
    start_after = values.get("START_AFTER") or None
    return RunInfo(
        pid=pid,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        state_file=state_file,
        batch_size=batch_size,
        start_after=start_after,
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


def fetch_snapshot(*, embedding_model: str) -> Snapshot:
    with SessionLocal() as session:
        total_segments = session.execute(text("SELECT COUNT(*) FROM segments")).scalar_one()
        embedded_segments = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM public.segment_embeddings
                WHERE embedding_model = :embedding_model
                """
            ),
            {"embedding_model": embedding_model},
        ).scalar_one()
        frontier = session.execute(
            text(
                """
                SELECT MAX(owner_id)
                FROM embedding_index_metadata
                WHERE owner_type = 'segment'
                  AND embedding_model = :embedding_model
                """
            ),
            {"embedding_model": embedding_model},
        ).scalar_one()
        latest_indexed_at = session.execute(
            text(
                """
                SELECT MAX(indexed_at)
                FROM public.segment_embeddings
                WHERE embedding_model = :embedding_model
                """
            ),
            {"embedding_model": embedding_model},
        ).scalar_one()
    return Snapshot(
        total_segments=total_segments,
        embedded_segments=embedded_segments,
        frontier=frontier,
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


def collect_sample(run_info: RunInfo, embedding_model: str) -> Sample:
    now = datetime.now(timezone.utc)
    snapshot = fetch_snapshot(embedding_model=embedding_model)
    stderr_size = 0
    if run_info.stderr_path and run_info.stderr_path.exists():
        stderr_size = run_info.stderr_path.stat().st_size
    state_mtime = None
    if run_info.state_file and run_info.state_file.exists():
        state_mtime = datetime.fromtimestamp(run_info.state_file.stat().st_mtime, tz=timezone.utc)
    return Sample(
        observed_at=now,
        snapshot=snapshot,
        stderr_size=stderr_size,
        state_mtime=state_mtime,
    )


def has_progress(previous: Sample, current: Sample) -> bool:
    return (
        current.snapshot.embedded_segments > previous.snapshot.embedded_segments
        or current.snapshot.frontier != previous.snapshot.frontier
        or (current.state_mtime is not None and previous.state_mtime != current.state_mtime)
    )


def print_status(run_info: RunInfo, sample: Sample, *, status: str, reason: Optional[str] = None) -> None:
    now_local = sample.observed_at.astimezone()
    started_at_local = run_info.started_at.astimezone()
    elapsed = now_local - started_at_local
    percent = (
        sample.snapshot.embedded_segments / sample.snapshot.total_segments * 100
        if sample.snapshot.total_segments
        else 0.0
    )
    print("=" * 80)
    print(f"[{status}] {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    if reason:
        print(f"Reason: {reason}")
    print(f"PID: {run_info.pid or 'unknown'} ({'alive' if is_process_alive(run_info.pid) else 'not running'})")
    print(f"Batch size: {run_info.batch_size or 'unknown'}")
    if run_info.start_after:
        print(f"Start after: {run_info.start_after}")
    print(f"Elapsed: {format_duration(elapsed)}")
    print(
        f"Progress: {sample.snapshot.embedded_segments:,} / {sample.snapshot.total_segments:,} "
        f"({percent:.2f}%)"
    )
    print(f"Frontier: {sample.snapshot.frontier or 'none'}")
    print(f"Latest indexed_at: {sample.snapshot.latest_indexed_at or 'none'}")
    if run_info.state_file:
        print(f"State file: {run_info.state_file}")
    if run_info.stderr_path:
        print(f"Stderr log: {run_info.stderr_path}")


def main() -> None:
    args = parse_args()
    run_info = read_run_info(args.latest_file)
    baseline = collect_sample(run_info, args.embedding_model)
    last_progress_sample = baseline
    print_status(run_info, baseline, status="INFO")

    if args.once:
        return

    while True:
        time.sleep(max(1, args.interval))
        run_info = read_run_info(args.latest_file)
        current = collect_sample(run_info, args.embedding_model)
        if has_progress(last_progress_sample, current):
            last_progress_sample = current
            print_status(run_info, current, status="INFO", reason="progress")
            continue

        no_progress_for = current.observed_at - last_progress_sample.observed_at
        if not is_process_alive(run_info.pid):
            print_status(run_info, current, status="ALERT", reason="backfill process is not running")
            stderr_tail = read_stderr_tail(run_info.stderr_path, tail_lines=args.tail_lines)
            if stderr_tail:
                print("-" * 80)
                print("Recent stderr tail:")
                for line in stderr_tail:
                    print(line)
            return

        if no_progress_for.total_seconds() >= args.stall_seconds:
            reason = f"no progress for {format_duration(no_progress_for)}"
            print_status(run_info, current, status="ALERT", reason=reason)
            stderr_tail = read_stderr_tail(run_info.stderr_path, tail_lines=args.tail_lines)
            if stderr_tail:
                print("-" * 80)
                print("Recent stderr tail:")
                for line in stderr_tail:
                    print(line)
            return

        print_status(
            run_info,
            current,
            status="INFO",
            reason=f"no progress yet ({format_duration(no_progress_for)})",
        )


if __name__ == "__main__":
    main()
