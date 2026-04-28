from __future__ import annotations

import argparse
import asyncio

from backend.app.services.realtime_embedding_worker import (
    REALTIME_MAX_SEGMENTS_PER_REQUEST,
    REALTIME_MAX_SINGLE_SEGMENT_TOKENS,
    REALTIME_MAX_TOKENS_PER_REQUEST,
    run_realtime_embedding_worker,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the realtime OpenAI embedding worker against missing or mismatched segment embeddings."
    )
    parser.add_argument("--content-field", choices=["normalized_content", "content", "content_gloss"])
    parser.add_argument("--tradition-id")
    parser.add_argument("--collection-id")
    parser.add_argument("--language-id")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--scan-batch-size", type=int, default=2000)
    parser.add_argument("--max-segments-per-request", type=int, default=REALTIME_MAX_SEGMENTS_PER_REQUEST)
    parser.add_argument("--max-tokens-per-request", type=int, default=REALTIME_MAX_TOKENS_PER_REQUEST)
    parser.add_argument("--max-single-segment-tokens", type=int, default=REALTIME_MAX_SINGLE_SEGMENT_TOKENS)
    parser.add_argument("--max-segments", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--min-text-length", type=int)
    parser.add_argument("--max-text-length", type=int)
    parser.add_argument("--min-routing-tokens", type=int)
    parser.add_argument("--max-routing-tokens", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = asyncio.run(
        run_realtime_embedding_worker(
            content_field=args.content_field,
            tradition_id=args.tradition_id,
            collection_id=args.collection_id,
            language_id=args.language_id,
            concurrency=args.concurrency,
            scan_batch_size=args.scan_batch_size,
            max_segments_per_request=args.max_segments_per_request,
            max_tokens_per_request=args.max_tokens_per_request,
            max_single_segment_tokens=args.max_single_segment_tokens,
            max_segments=args.max_segments,
            run_id=args.run_id,
            min_text_length=args.min_text_length,
            max_text_length=args.max_text_length,
            min_routing_tokens=args.min_routing_tokens,
            max_routing_tokens=args.max_routing_tokens,
        )
    )
    print(f"total_missing={stats['total_missing']}")
    print(f"processed={stats['processed']}")
    print(f"failed={stats['failed']}")
    print(f"tokens_used={stats['tokens_used']}")
    print(f"elapsed_time={stats['elapsed_time']:.2f}")
    print(f"segments_per_min={stats['segments_per_min']:.2f}")
    print(f"tokens_per_min={stats['tokens_per_min']:.2f}")
    print(f"resume_after_segment_id={stats.get('resume_after_segment_id') or ''}")
    print(f"completed_scan={bool(stats.get('completed_scan'))}")


if __name__ == "__main__":
    main()
