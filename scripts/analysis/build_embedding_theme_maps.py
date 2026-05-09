from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.services.embedding_theme_map_service import (
    EMBEDDING_THEME_MAP_SNAPSHOT_PATH,
    TRADITION_CONFIGS,
    build_embedding_theme_maps_snapshot,
    save_embedding_theme_maps_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build embedding-based theme maps for Han, Pali, and Tibetan text.")
    parser.add_argument("--tradition-id", action="append", choices=sorted(TRADITION_CONFIGS), help="Limit to one or more traditions.")
    parser.add_argument("--output", type=Path, default=EMBEDDING_THEME_MAP_SNAPSHOT_PATH)
    parser.add_argument("--sample-limit", type=int, default=None, help="Override per-tradition embedding sample size.")
    parser.add_argument("--cluster-count", type=int, default=None, help="Override per-tradition cluster count.")
    parser.add_argument("--max-examples-per-theme", type=int, default=4)
    parser.add_argument("--max-top-works", type=int, default=5)
    parser.add_argument("--max-edges", type=int, default=28)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as session:
        snapshot = build_embedding_theme_maps_snapshot(
            session,
            tradition_ids=args.tradition_id,
            sample_limit=args.sample_limit,
            cluster_count=args.cluster_count,
            max_examples_per_theme=args.max_examples_per_theme,
            max_top_works=args.max_top_works,
            max_edges=args.max_edges,
        )

    output_path = save_embedding_theme_maps_snapshot(snapshot, path=args.output)
    print(f"Output: {output_path}")
    print(f"Maps emitted: {snapshot['map_count']}")
    for item in snapshot["maps"]:
        print(
            f"- {item['tradition_id']}: "
            f"model={item['embedding_model']} "
            f"indexed={item['indexed_segment_count']} "
            f"sampled={item['sampled_segment_count']} "
            f"clusters={item['cluster_count']} "
            f"edges={len(item['edges'])}"
        )


if __name__ == "__main__":
    main()
