from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.services.unit_theme_map_service import (
    UNIT_THEME_MAP_SNAPSHOT_PATH,
    UNIT_TRADITION_CONFIGS,
    build_unit_theme_maps_snapshot,
    save_unit_theme_core_report,
    save_unit_theme_maps_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unit-level embedding maps over fascicles/works.")
    parser.add_argument("--tradition-id", action="append", choices=sorted(UNIT_TRADITION_CONFIGS))
    parser.add_argument("--output", type=Path, default=UNIT_THEME_MAP_SNAPSHOT_PATH)
    parser.add_argument("--core-units-per-cluster", type=int, default=10)
    parser.add_argument("--skip-report", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as session:
        snapshot = build_unit_theme_maps_snapshot(
            session,
            tradition_ids=args.tradition_id,
            core_units_per_cluster=args.core_units_per_cluster,
        )
    output_path = save_unit_theme_maps_snapshot(snapshot, path=args.output)
    print(f"Output: {output_path}")
    print(f"Maps emitted: {snapshot['map_count']}")
    for item in snapshot["maps"]:
        print(
            f"- {item['tradition_id']}: "
            f"model={item['embedding_model']} "
            f"units={item['unit_count']} "
            f"clusters={item['cluster_count']} "
            f"points={len(item['points'])}"
        )
    if not args.skip_report:
        report_path = save_unit_theme_core_report(snapshot)
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
