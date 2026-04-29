from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.services.realtime_embedding_worker import run_realtime_embedding_worker


ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "data" / "processed" / "logs"
DEFAULT_STATE_FILE = LOG_DIR / "realtime_embedding_supervisor_state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repeatedly run bounded realtime embedding chunks to avoid long-lived worker stalls."
    )
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--tradition-id")
    parser.add_argument("--content-field", required=True)
    parser.add_argument("--dry-run-scan-only", action="store_true")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-segments-per-request", type=int, default=64)
    parser.add_argument("--max-segments-per-run", type=int, default=256)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--max-runs", type=int)
    parser.add_argument("--min-text-length", type=int)
    parser.add_argument("--max-text-length", type=int)
    parser.add_argument("--min-routing-tokens", type=int)
    parser.add_argument("--max-routing-tokens", type=int)
    return parser.parse_args()


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _worker_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-u",
        str(ROOT_DIR / "scripts" / "analysis" / "run_realtime_segment_embeddings.py"),
        "--content-field",
        args.content_field,
        "--concurrency",
        str(args.concurrency),
        "--max-segments-per-request",
        str(args.max_segments_per_request),
        "--max-segments",
        str(args.max_segments_per_run),
    ]
    if args.tradition_id:
        command.extend(["--tradition-id", args.tradition_id])
    if args.dry_run_scan_only:
        command.append("--dry-run-scan-only")
    if args.min_text_length is not None:
        command.extend(["--min-text-length", str(args.min_text_length)])
    if args.max_text_length is not None:
        command.extend(["--max-text-length", str(args.max_text_length)])
    if args.min_routing_tokens is not None:
        command.extend(["--min-routing-tokens", str(args.min_routing_tokens)])
    if args.max_routing_tokens is not None:
        command.extend(["--max-routing-tokens", str(args.max_routing_tokens)])
    return command


def main() -> None:
    args = parse_args()
    supervisor_started_at = datetime.now(timezone.utc)
    total_processed = 0
    total_failed = 0
    run_count = 0
    prior_state = _load_state(args.state_file)
    resume_after_segment_id = prior_state.get("next_start_after_segment_id")
    if isinstance(prior_state.get("total_processed"), int):
        total_processed = int(prior_state["total_processed"])
    if isinstance(prior_state.get("total_failed"), int):
        total_failed = int(prior_state["total_failed"])

    try:
        while True:
            run_count += 1
            if args.max_runs is not None and run_count > args.max_runs:
                _write_state(
                    args.state_file,
                    {
                        "status": "paused",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "max_runs_reached",
                        "supervisor_started_at": supervisor_started_at.isoformat(),
                        "runs_completed": run_count - 1,
                        "total_processed": total_processed,
                        "total_failed": total_failed,
                        "next_start_after_segment_id": resume_after_segment_id,
                    },
                )
                break

            command = _worker_command(args)
            wave_started_at = datetime.now(timezone.utc)
            _write_state(
                args.state_file,
                {
                    "status": "running",
                    "updated_at": wave_started_at.isoformat(),
                    "supervisor_started_at": supervisor_started_at.isoformat(),
                    "current_wave": run_count,
                    "runs_completed": run_count - 1,
                    "total_processed": total_processed,
                    "total_failed": total_failed,
                    "next_start_after_segment_id": resume_after_segment_id,
                    "worker_command": command,
                    "filters": {
                        "tradition_id": args.tradition_id,
                        "content_field": args.content_field,
                        "dry_run_scan_only": args.dry_run_scan_only,
                        "concurrency": args.concurrency,
                        "max_segments_per_request": args.max_segments_per_request,
                        "max_segments_per_run": args.max_segments_per_run,
                        "min_text_length": args.min_text_length,
                        "max_text_length": args.max_text_length,
                        "min_routing_tokens": args.min_routing_tokens,
                        "max_routing_tokens": args.max_routing_tokens,
                    },
                },
            )

            print(f"=== supervisor_run={run_count} ===", flush=True)
            print("command=" + " ".join(command), flush=True)
            stats = asyncio.run(
                run_realtime_embedding_worker(
                    content_field=args.content_field,
                    tradition_id=args.tradition_id,
                    start_after_segment_id=resume_after_segment_id,
                    dry_run_scan_only=args.dry_run_scan_only,
                    concurrency=args.concurrency,
                    max_segments_per_request=args.max_segments_per_request,
                    max_segments=args.max_segments_per_run,
                    min_text_length=args.min_text_length,
                    max_text_length=args.max_text_length,
                    min_routing_tokens=args.min_routing_tokens,
                    max_routing_tokens=args.max_routing_tokens,
                )
            )
            print(f"total_missing={stats['total_missing']}", flush=True)
            print(f"processed={stats['processed']}", flush=True)
            print(f"failed={stats['failed']}", flush=True)
            print(f"tokens_used={stats['tokens_used']}", flush=True)
            print(f"elapsed_time={stats['elapsed_time']:.2f}", flush=True)
            print(f"segments_per_min={stats['segments_per_min']:.2f}", flush=True)
            print(f"tokens_per_min={stats['tokens_per_min']:.2f}", flush=True)
            print(f"input_resume_after_segment_id={stats.get('input_resume_after_segment_id') or ''}", flush=True)
            print(f"scan_started_after_segment_id={stats.get('scan_started_after_segment_id') or ''}", flush=True)
            print(f"scan_last_seen_segment_id={stats.get('scan_last_seen_segment_id') or ''}", flush=True)
            print(f"scan_candidate_hits={stats.get('scan_candidate_hits', 0)}", flush=True)
            print(f"scan_selected_count={stats.get('scan_selected_count', 0)}", flush=True)
            print(f"planned_embedding_segments={stats.get('planned_embedding_segments', 0)}", flush=True)
            print(f"scan_elapsed_time={stats.get('scan_elapsed_time', 0.0):.2f}", flush=True)
            print(f"api_elapsed_time={stats.get('api_elapsed_time', 0.0):.2f}", flush=True)
            print(f"db_write_elapsed_time={stats.get('db_write_elapsed_time', 0.0):.2f}", flush=True)
            print(f"resume_after_segment_id={stats.get('resume_after_segment_id') or ''}", flush=True)
            print(f"completed_scan={bool(stats.get('completed_scan'))}", flush=True)
            for batch in stats.get("batch_metrics", []):
                print(
                    "batch_metric="
                    f"index:{batch.get('batch_index')} "
                    f"size:{batch.get('batch_size')} "
                    f"tokens:{batch.get('batch_tokens')} "
                    f"request_elapsed:{batch.get('request_elapsed_time', 0.0):.2f} "
                    f"db_write_elapsed:{batch.get('db_write_elapsed_time', 0.0):.2f} "
                    f"dry_run:{batch.get('dry_run', False)}",
                    flush=True,
                )
            processed = int(stats.get("processed", 0) or 0)
            failed = int(stats.get("failed", 0) or 0)
            resume_after_segment_id = stats.get("resume_after_segment_id") or resume_after_segment_id
            total_processed += processed
            total_failed += failed
            print(
                f"supervisor_totals processed={total_processed} failed={total_failed} runs={run_count}",
                flush=True,
            )
            _write_state(
                args.state_file,
                {
                    "status": "running",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "supervisor_started_at": supervisor_started_at.isoformat(),
                    "current_wave": run_count,
                    "runs_completed": run_count,
                    "total_processed": total_processed,
                    "total_failed": total_failed,
                    "next_start_after_segment_id": resume_after_segment_id,
                    "last_wave": {
                        "started_at": wave_started_at.isoformat(),
                        "ended_at": datetime.now(timezone.utc).isoformat(),
                        "stats": stats,
                    },
                    "worker_command": command,
                },
            )

            no_progress = processed <= 0 and not args.dry_run_scan_only
            if no_progress or bool(stats.get("completed_scan")):
                _write_state(
                    args.state_file,
                    {
                        "status": "completed",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "supervisor_started_at": supervisor_started_at.isoformat(),
                        "runs_completed": run_count,
                        "total_processed": total_processed,
                        "total_failed": total_failed,
                        "next_start_after_segment_id": resume_after_segment_id,
                        "last_wave": {
                            "started_at": wave_started_at.isoformat(),
                            "ended_at": datetime.now(timezone.utc).isoformat(),
                            "stats": stats,
                        },
                    },
                )
                break

            if args.pause_seconds > 0:
                time.sleep(args.pause_seconds)
    except BaseException as exc:
        _write_state(
            args.state_file,
            {
                "status": "crashed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "supervisor_started_at": supervisor_started_at.isoformat(),
                "runs_completed": max(0, run_count - 1),
                "total_processed": total_processed,
                "total_failed": total_failed,
                "next_start_after_segment_id": resume_after_segment_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise


if __name__ == "__main__":
    main()
