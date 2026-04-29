from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.services.pali_theme_map_service import (
    PALI_THEME_MAP_SNAPSHOT_PATH,
    build_pali_theme_map_snapshot,
    save_pali_theme_map_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a processed Pali theme map snapshot from gloss segments.")
    parser.add_argument("--output", type=Path, default=PALI_THEME_MAP_SNAPSHOT_PATH)
    parser.add_argument("--max-examples-per-theme", type=int, default=4)
    parser.add_argument("--max-top-works", type=int, default=5)
    parser.add_argument("--max-edges", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as session:
        snapshot = build_pali_theme_map_snapshot(
            session,
            max_examples_per_theme=args.max_examples_per_theme,
            max_top_works=args.max_top_works,
            max_edges=args.max_edges,
        )
    output_path = save_pali_theme_map_snapshot(snapshot, path=args.output)
    print(f"Output: {output_path}")
    print(f"Gloss segments scanned: {snapshot['gloss_segment_count']}")
    print(f"Matched segments: {snapshot['matched_segment_count']}")
    print(f"Themes emitted: {snapshot['theme_count']}")
    print(f"Edges emitted: {len(snapshot['edges'])}")


if __name__ == "__main__":
    main()
