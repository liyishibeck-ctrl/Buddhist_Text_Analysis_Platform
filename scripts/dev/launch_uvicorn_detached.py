from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the local Uvicorn app in detached mode.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--startup-timeout", type=int, default=45)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    return parser.parse_args()


def is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def wait_for_http(url: str, *, timeout_seconds: int, process: subprocess.Popen[bytes]) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if 200 <= response.status < 500:
                    return True
        except urllib.error.URLError:
            pass
        time.sleep(1.0)
    return False


def tail_text(path: Path, line_count: int = 20) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:])


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    processed_dir = root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    out_path = processed_dir / f"uvicorn-main-{args.port}.out.log"
    err_path = processed_dir / f"uvicorn-main-{args.port}.err.log"
    pid_path = processed_dir / f"uvicorn-main-{args.port}.pid"
    url = f"http://{args.host}:{args.port}/"

    if is_port_open(args.host, args.port):
        print(f"App already listening at {url}")
        return 0

    out_path.write_text("", encoding="utf-8")
    err_path.write_text("", encoding="utf-8")

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]

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

    pid_path.write_text(str(process.pid), encoding="utf-8")

    if not wait_for_http(url, timeout_seconds=args.startup_timeout, process=process):
        print(f"Uvicorn did not become ready in time. pid={process.pid} returncode={process.poll()}")
        err_tail = tail_text(err_path)
        if err_tail:
            print("--- uvicorn stderr tail ---")
            print(err_tail)
        return 1

    print(f"Started app at {url} (pid={process.pid})")
    print(f"stdout log: {out_path}")
    print(f"stderr log: {err_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
