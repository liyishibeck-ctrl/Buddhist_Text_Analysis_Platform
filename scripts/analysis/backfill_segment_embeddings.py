from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.db.session import SessionLocal
from backend.app.services.vector_service import backfill_segment_embeddings, indexed_owner_count, resolve_embedding_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill configured segment embeddings into the pgvector store.")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--embedding-model")
    parser.add_argument("--content-field", choices=["normalized_content", "content", "content_gloss"])
    parser.add_argument("--tradition-id")
    parser.add_argument("--collection-id")
    parser.add_argument("--language-id")
    parser.add_argument("--max-segments", type=int)
    parser.add_argument("--shard-count", type=int)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--start-after-segment-id")
    parser.add_argument("--end-at-segment-id")
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--reset-state", action="store_true")
    return parser.parse_args()


def load_state(state_file: Path | None, *, reset_state: bool) -> dict[str, Any]:
    if state_file is None or reset_state or not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def write_state(
    state_file: Path | None,
    *,
    last_segment_id: str | None,
    inserted_count: int,
    completed: bool,
    args: argparse.Namespace,
    runtime_model: str,
) -> None:
    if state_file is None:
        return

    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_segment_id": last_segment_id,
        "inserted_count": inserted_count,
        "completed": completed,
        "embedding_model": runtime_model,
        "content_field": args.content_field,
        "batch_size": args.batch_size,
        "max_segments": args.max_segments,
        "shard_count": args.shard_count,
        "shard_index": args.shard_index,
        "start_after_segment_id": args.start_after_segment_id,
        "end_at_segment_id": args.end_at_segment_id,
        "tradition_id": args.tradition_id,
        "collection_id": args.collection_id,
        "language_id": args.language_id,
    }
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    runtime = resolve_embedding_runtime(embedding_model=args.embedding_model, tradition_id=args.tradition_id)
    state = load_state(args.state_file, reset_state=args.reset_state)
    start_after_segment_id = state.get("last_segment_id") or args.start_after_segment_id

    def progress_callback(last_segment_id: str, inserted_count: int) -> None:
        write_state(
            args.state_file,
            last_segment_id=last_segment_id,
            inserted_count=inserted_count,
            completed=False,
            args=args,
            runtime_model=runtime.model,
        )

    with SessionLocal() as session:
        result = backfill_segment_embeddings(
            session,
            batch_size=args.batch_size,
            embedding_model=runtime.model,
            content_field=args.content_field,
            tradition_id=args.tradition_id,
            collection_id=args.collection_id,
            language_id=args.language_id,
            max_segments=args.max_segments,
            shard_count=args.shard_count,
            shard_index=args.shard_index,
            start_after_segment_id=start_after_segment_id,
            end_at_segment_id=args.end_at_segment_id,
            progress_callback=progress_callback,
        )
        indexed = indexed_owner_count(
            session,
            embedding_model=runtime.model,
            tradition_id=args.tradition_id,
            content_field=args.content_field,
        )

    write_state(
        args.state_file,
        last_segment_id=result.last_segment_id,
        inserted_count=result.inserted_count,
        completed=result.completed,
        args=args,
        runtime_model=runtime.model,
    )
    print(f"Embedding provider: {runtime.provider}")
    print(f"Embedding model: {runtime.model}")
    print(f"Embedding dimension: {runtime.dimension}")
    print(f"Segments indexed in this run: {result.inserted_count}")
    print(f"Indexed owners now present: {indexed}")
    print(f"Last segment id: {result.last_segment_id}")
    print(f"Completed shard scan: {result.completed}")


if __name__ == "__main__":
    main()
