from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import ROOT_DIR
from backend.app.db.session import SessionLocal
from sqlalchemy import text


LOG_DIR = ROOT_DIR / "data" / "processed" / "logs"
DEFAULT_STATE_DIR = LOG_DIR / "embedding_pool_states"
LATEST_POOL_PATH = LOG_DIR / "latest_embedding_pool.json"
WORKER_SCRIPT = ROOT_DIR / "scripts" / "analysis" / "backfill_segment_embeddings.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded multi-process embedding backfill pool.")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-segments-per-worker", type=int, default=2000)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--log-dir", type=Path, default=LOG_DIR)
    parser.add_argument("--embedding-model")
    parser.add_argument("--tradition-id")
    parser.add_argument("--collection-id")
    parser.add_argument("--language-id")
    parser.add_argument("--stagger-seconds", type=int, default=5)
    return parser.parse_args()


def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def compute_shard_ranges(worker_count: int) -> list[tuple[str | None, str | None]]:
    if worker_count <= 0:
        raise ValueError("workers must be greater than zero.")
    if worker_count == 1:
        return [(None, None)]

    with SessionLocal() as session:
        total_segments = session.execute(text("SELECT COUNT(*) FROM segments")).scalar_one()
        boundaries: list[str] = []
        for shard_index in range(1, worker_count):
            offset = int(total_segments * shard_index / worker_count)
            boundary = session.execute(
                text("SELECT id FROM segments ORDER BY id OFFSET :offset LIMIT 1"),
                {"offset": offset},
            ).scalar_one()
            boundaries.append(boundary)

    ranges: list[tuple[str | None, str | None]] = []
    lower_bound: str | None = None
    for boundary in boundaries:
        ranges.append((lower_bound, boundary))
        lower_bound = boundary
    ranges.append((lower_bound, None))
    return ranges


def build_worker_command(
    args: argparse.Namespace,
    *,
    shard_index: int,
    state_file: Path,
    lower_bound: str | None,
    upper_bound: str | None,
) -> list[str]:
    command = [
        sys.executable,
        str(WORKER_SCRIPT),
        "--batch-size",
        str(args.batch_size),
        "--max-segments",
        str(args.max_segments_per_worker),
        "--state-file",
        str(state_file),
    ]
    if lower_bound is not None:
        command.extend(["--start-after-segment-id", lower_bound])
    if upper_bound is not None:
        command.extend(["--end-at-segment-id", upper_bound])
    if args.embedding_model:
        command.extend(["--embedding-model", args.embedding_model])
    if args.tradition_id:
        command.extend(["--tradition-id", args.tradition_id])
    if args.collection_id:
        command.extend(["--collection-id", args.collection_id])
    if args.language_id:
        command.extend(["--language-id", args.language_id])
    return command


def main() -> None:
    args = parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    worker_runs: list[dict] = []
    processes: list[tuple[subprocess.Popen, object, object, dict]] = []
    shard_ranges = compute_shard_ranges(args.workers)

    for shard_index, (lower_bound, upper_bound) in enumerate(shard_ranges):
        state_file = args.state_dir / f"embedding_shard_{shard_index}_of_{args.workers}.json"
        state = load_state(state_file)
        if state.get("completed"):
            worker_runs.append(
                {
                    "shard_index": shard_index,
                    "state_file": str(state_file),
                    "skipped": True,
                    "reason": "completed",
                }
            )
            continue

        stdout_path = args.log_dir / f"embedding_pool_{timestamp}_shard{shard_index}.out.log"
        stderr_path = args.log_dir / f"embedding_pool_{timestamp}_shard{shard_index}.err.log"
        command = build_worker_command(
            args,
            shard_index=shard_index,
            state_file=state_file,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        stdout_handle = open(stdout_path, "w", encoding="utf-8")
        stderr_handle = open(stderr_path, "w", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            stdout=stdout_handle,
            stderr=stderr_handle,
        )
        worker_info = {
            "shard_index": shard_index,
            "pid": process.pid,
            "state_file": str(state_file),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "command": command,
        }
        worker_runs.append(worker_info)
        processes.append((process, stdout_handle, stderr_handle, worker_info))
        if args.stagger_seconds > 0 and shard_index < args.workers - 1:
            time.sleep(args.stagger_seconds)

    latest_payload = {
        "started_at": started_at.isoformat(),
        "workers": args.workers,
        "batch_size": args.batch_size,
        "max_segments_per_worker": args.max_segments_per_worker,
        "state_dir": str(args.state_dir),
        "worker_runs": worker_runs,
    }
    LATEST_POOL_PATH.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if not processes:
        print("No shard workers were started. All tracked shards are already marked completed.")
        return

    exit_codes: list[dict[str, int]] = []
    for process, stdout_handle, stderr_handle, worker_info in processes:
        return_code = process.wait()
        stdout_handle.close()
        stderr_handle.close()
        exit_codes.append({"shard_index": worker_info["shard_index"], "return_code": return_code})

    print(json.dumps({"started_workers": len(processes), "exit_codes": exit_codes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
