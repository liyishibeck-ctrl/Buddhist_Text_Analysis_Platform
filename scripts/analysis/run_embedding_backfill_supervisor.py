from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import ROOT_DIR


LOG_DIR = ROOT_DIR / "data" / "processed" / "logs"
DEFAULT_STATE_FILE = LOG_DIR / "embedding_supervisor_state.json"
LATEST_SUPERVISOR_PATH = LOG_DIR / "latest_embedding_supervisor.json"
WORKER_SCRIPT = ROOT_DIR / "scripts" / "analysis" / "backfill_segment_embeddings.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supervise bounded embedding backfill waves with restart support.")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-segments-per-wave", type=int, default=1000)
    parser.add_argument("--wave-timeout-seconds", type=int, default=1800)
    parser.add_argument("--pause-seconds", type=int, default=15)
    parser.add_argument("--max-waves", type=int)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--embedding-model")
    parser.add_argument("--tradition-id")
    parser.add_argument("--collection-id")
    parser.add_argument("--language-id")
    return parser.parse_args()


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def build_worker_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(WORKER_SCRIPT),
        "--batch-size",
        str(args.batch_size),
        "--max-segments",
        str(args.max_segments_per_wave),
        "--state-file",
        str(args.state_file),
    ]
    if args.embedding_model:
        command.extend(["--embedding-model", args.embedding_model])
    if args.tradition_id:
        command.extend(["--tradition-id", args.tradition_id])
    if args.collection_id:
        command.extend(["--collection-id", args.collection_id])
    if args.language_id:
        command.extend(["--language-id", args.language_id])
    return command


def write_supervisor_state(payload: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_SUPERVISOR_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.state_file.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    supervisor_started_at = datetime.now(timezone.utc)
    worker_command = build_worker_command(args)
    wave_index = 0

    while True:
        current_state = load_state(args.state_file)
        if current_state.get("completed"):
            summary = {
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "state_file": str(args.state_file),
                "waves_run": wave_index,
                "last_state": current_state,
            }
            write_supervisor_state(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return

        if args.max_waves is not None and wave_index >= args.max_waves:
            summary = {
                "status": "paused",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "reason": "max_waves_reached",
                "state_file": str(args.state_file),
                "waves_run": wave_index,
                "last_state": current_state,
            }
            write_supervisor_state(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return

        wave_started_at = datetime.now(timezone.utc)
        timestamp = wave_started_at.strftime("%Y%m%d_%H%M%S")
        stdout_path = LOG_DIR / f"embedding_supervisor_wave_{timestamp}.out.log"
        stderr_path = LOG_DIR / f"embedding_supervisor_wave_{timestamp}.err.log"
        stdout_handle = open(stdout_path, "w", encoding="utf-8")
        stderr_handle = open(stderr_path, "w", encoding="utf-8")
        process = subprocess.Popen(
            worker_command,
            cwd=ROOT_DIR,
            stdout=stdout_handle,
            stderr=stderr_handle,
        )
        wave_index += 1

        last_seen_state = current_state
        timed_out = False
        while True:
            return_code = process.poll()
            if return_code is not None:
                break

            elapsed = (datetime.now(timezone.utc) - wave_started_at).total_seconds()
            if elapsed >= args.wave_timeout_seconds:
                timed_out = True
                process.kill()
                process.wait()
                return_code = process.returncode
                break

            time.sleep(5)
            last_seen_state = load_state(args.state_file)
            if last_seen_state.get("completed"):
                process.wait()
                return_code = process.returncode
                break

        stdout_handle.close()
        stderr_handle.close()

        last_seen_state = load_state(args.state_file)
        supervisor_payload = {
            "status": "running",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "supervisor_started_at": supervisor_started_at.isoformat(),
            "state_file": str(args.state_file),
            "current_wave": wave_index,
            "wave_timeout_seconds": args.wave_timeout_seconds,
            "max_segments_per_wave": args.max_segments_per_wave,
            "batch_size": args.batch_size,
            "worker_command": worker_command,
            "last_wave": {
                "started_at": wave_started_at.isoformat(),
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "return_code": return_code,
                "timed_out": timed_out,
            },
            "last_state": last_seen_state,
        }
        write_supervisor_state(supervisor_payload)

        if last_seen_state.get("completed"):
            supervisor_payload["status"] = "completed"
            write_supervisor_state(supervisor_payload)
            print(json.dumps(supervisor_payload, ensure_ascii=False, indent=2))
            return

        if args.pause_seconds > 0:
            time.sleep(args.pause_seconds)


if __name__ == "__main__":
    main()
