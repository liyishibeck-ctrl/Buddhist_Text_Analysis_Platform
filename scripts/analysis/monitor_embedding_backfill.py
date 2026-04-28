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
class BackfillRunInfo:
    pid: Optional[int]
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    batch_size: Optional[int]
    started_at: datetime


@dataclass(slots=True)
class BackfillSnapshot:
    total_segments: int
    embedded_segments: int
    embedded_since_start: int
    earliest_indexed_at: Optional[datetime]
    latest_indexed_at: Optional[datetime]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor the current embedding backfill progress.")
    parser.add_argument("--watch", action="store_true", help="Refresh continuously until interrupted.")
    parser.add_argument("--interval", type=int, default=30, help="Refresh interval in seconds when --watch is set.")
    parser.add_argument("--embedding-model", default=settings.embedding_model, help="Embedding model to monitor.")
    parser.add_argument("--tail-lines", type=int, default=20, help="How many stderr lines to show.")
    parser.add_argument("--latest-file", type=Path, default=LATEST_BACKFILL_PATH, help="Path to latest backfill state file.")
    return parser.parse_args()


def read_run_info(latest_file: Path) -> BackfillRunInfo:
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
    batch_size = int(values["BATCH_SIZE"]) if values.get("BATCH_SIZE") else None
    return BackfillRunInfo(
        pid=pid,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        batch_size=batch_size,
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


def fetch_snapshot(*, embedding_model: str, started_at: datetime) -> BackfillSnapshot:
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
        embedded_since_start = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM public.segment_embeddings
                WHERE embedding_model = :embedding_model
                  AND indexed_at >= :started_at
                """
            ),
            {"embedding_model": embedding_model, "started_at": started_at},
        ).scalar_one()
        earliest_indexed_at, latest_indexed_at = session.execute(
            text(
                """
                SELECT MIN(indexed_at), MAX(indexed_at)
                FROM public.segment_embeddings
                WHERE embedding_model = :embedding_model
                """
            ),
            {"embedding_model": embedding_model},
        ).one()

    return BackfillSnapshot(
        total_segments=total_segments,
        embedded_segments=embedded_segments,
        embedded_since_start=embedded_since_start,
        earliest_indexed_at=earliest_indexed_at,
        latest_indexed_at=latest_indexed_at,
    )


def format_duration(duration: timedelta) -> str:
    total_seconds = max(0, int(duration.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_eta(remaining_count: int, embedded_since_start: int, elapsed: timedelta) -> str:
    if embedded_since_start <= 0 or elapsed.total_seconds() <= 0:
        return "unknown"

    rate_per_second = embedded_since_start / elapsed.total_seconds()
    if rate_per_second <= 0:
        return "unknown"

    eta = timedelta(seconds=remaining_count / rate_per_second)
    return format_duration(eta)


def read_stderr_tail(stderr_path: Optional[Path], *, tail_lines: int) -> list[str]:
    if stderr_path is None or not stderr_path.exists() or stderr_path.stat().st_size == 0:
        return []

    lines = stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-tail_lines:]


def print_snapshot(
    *,
    embedding_model: str,
    run_info: BackfillRunInfo,
    snapshot: BackfillSnapshot,
    stderr_tail: list[str],
) -> None:
    now_local = datetime.now().astimezone()
    started_at_local = run_info.started_at.astimezone()
    elapsed = now_local - started_at_local
    remaining_count = max(0, snapshot.total_segments - snapshot.embedded_segments)
    alive = is_process_alive(run_info.pid)
    percent = (snapshot.embedded_segments / snapshot.total_segments * 100) if snapshot.total_segments else 0.0
    rate_per_hour = (
        snapshot.embedded_since_start / elapsed.total_seconds() * 3600
        if snapshot.embedded_since_start > 0 and elapsed.total_seconds() > 0
        else 0.0
    )

    print("=" * 72)
    print(f"Checked at: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Embedding model: {embedding_model}")
    print(f"Backfill PID: {run_info.pid or 'unknown'} ({'alive' if alive else 'not running'})")
    print(f"Batch size: {run_info.batch_size or 'unknown'}")
    print(f"Started at: {started_at_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Progress: {snapshot.embedded_segments:,} / {snapshot.total_segments:,} ({percent:.2f}%)")
    print(f"Embedded since start: {snapshot.embedded_since_start:,}")
    print(f"Estimated rate: {rate_per_hour:,.0f} rows/hour")
    print(f"Estimated time remaining: {format_eta(remaining_count, snapshot.embedded_since_start, elapsed)}")
    print(f"Elapsed: {format_duration(elapsed)}")
    print(f"Latest indexed_at: {snapshot.latest_indexed_at or 'none'}")
    if run_info.stdout_path:
        print(f"Stdout log: {run_info.stdout_path}")
    if run_info.stderr_path:
        print(f"Stderr log: {run_info.stderr_path}")

    if stderr_tail:
        print("-" * 72)
        print("Recent stderr tail:")
        for line in stderr_tail:
            print(line)


def run_once(args: argparse.Namespace) -> None:
    run_info = read_run_info(args.latest_file)
    snapshot = fetch_snapshot(embedding_model=args.embedding_model, started_at=run_info.started_at)
    stderr_tail = read_stderr_tail(run_info.stderr_path, tail_lines=args.tail_lines)
    print_snapshot(
        embedding_model=args.embedding_model,
        run_info=run_info,
        snapshot=snapshot,
        stderr_tail=stderr_tail,
    )


def main() -> None:
    args = parse_args()

    if not args.watch:
        run_once(args)
        return

    try:
        while True:
            run_once(args)
            time.sleep(max(1, args.interval))
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


if __name__ == "__main__":
    main()
