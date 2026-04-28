from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the realtime embedding supervisor in detached mode.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--tradition-id", required=True)
    parser.add_argument("--content-field", required=True)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-segments-per-request", type=int, default=64)
    parser.add_argument("--max-segments-per-run", type=int, default=1024)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--min-text-length", type=int)
    parser.add_argument("--max-text-length", type=int)
    parser.add_argument("--min-routing-tokens", type=int)
    parser.add_argument("--max-routing-tokens", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    log_dir = root / "data" / "processed" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int((time.time() % 1) * 1000):03d}"
    slug_parts = [args.tradition_id, args.content_field]
    if args.min_text_length is not None:
        slug_parts.append(f"minlen{args.min_text_length}")
    if args.max_text_length is not None:
        slug_parts.append(f"maxlen{args.max_text_length}")
    if args.min_routing_tokens is not None:
        slug_parts.append(f"minrt{args.min_routing_tokens}")
    if args.max_routing_tokens is not None:
        slug_parts.append(f"maxrt{args.max_routing_tokens}")
    slug = "-".join(slug_parts).replace("_", "-")
    out_path = log_dir / f"realtime-{slug}-supervisor-{timestamp}.out.log"
    err_path = log_dir / f"realtime-{slug}-supervisor-{timestamp}.err.log"
    state_path = (
        args.state_file.resolve()
        if args.state_file is not None
        else log_dir / f"latest_realtime_embedding_worker_{args.tradition_id.replace('-', '_')}.txt"
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    supervisor_state_path = state_path.with_suffix(".json")

    command = [
        sys.executable,
        "-u",
        str(root / "scripts" / "analysis" / "run_realtime_embedding_supervisor.py"),
        "--state-file",
        str(supervisor_state_path),
        "--tradition-id",
        args.tradition_id,
        "--content-field",
        args.content_field,
        "--concurrency",
        str(args.concurrency),
        "--max-segments-per-request",
        str(args.max_segments_per_request),
        "--max-segments-per-run",
        str(args.max_segments_per_run),
        "--pause-seconds",
        str(args.pause_seconds),
    ]
    if args.min_text_length is not None:
        command.extend(["--min-text-length", str(args.min_text_length)])
    if args.max_text_length is not None:
        command.extend(["--max-text-length", str(args.max_text_length)])
    if args.min_routing_tokens is not None:
        command.extend(["--min-routing-tokens", str(args.min_routing_tokens)])
    if args.max_routing_tokens is not None:
        command.extend(["--max-routing-tokens", str(args.max_routing_tokens)])

    popen_kwargs: dict[str, object] = {
        "cwd": str(root),
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
        "env": os.environ.copy(),
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    with out_path.open("ab") as stdout_file, err_path.open("ab") as stderr_file:
        process = subprocess.Popen(command, stdout=stdout_file, stderr=stderr_file, **popen_kwargs)

    state_lines = [
        f"PID={process.pid}",
        f"STDOUT={out_path}",
        f"STDERR={err_path}",
        f"STARTED_AT={time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())}Z",
        f"SUPERVISOR_STATE={supervisor_state_path}",
        f"TRADITION_ID={args.tradition_id}",
        f"CONTENT_FIELD={args.content_field}",
        "EMBEDDING_MODEL=text-embedding-3-large",
        "STORAGE_EMBEDDING_MODEL=text-embedding-3-large",
        "DIMENSION=2048",
    ]
    state_path.write_text("\n".join(state_lines) + "\n", encoding="utf-8")

    print(f"Started detached realtime supervisor pid={process.pid}")
    print(f"stdout log: {out_path}")
    print(f"stderr log: {err_path}")
    print(f"state file: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
