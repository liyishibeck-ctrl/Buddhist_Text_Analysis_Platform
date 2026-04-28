from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.init_db import initialize_database
from backend.app.db.session import SessionLocal
from backend.app.services.catalog_service import get_han_catalog_overview
from backend.app.services.han_catalog_loader import seed_han_catalog_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the Han catalog CSV seed into the application database.")
    parser.add_argument("--force", action="store_true", help="Replace previously imported Han catalog rows.")
    parser.add_argument("--source", type=Path, default=None, help="Optional CSV path override.")
    parser.add_argument(
        "--write-bundle",
        action="store_true",
        help="Also emit a processed JSON bundle under data/processed/han/.",
    )
    args = parser.parse_args()

    initialize_database()
    with SessionLocal() as session:
        seeded = seed_han_catalog_snapshot(
            session,
            force=args.force,
            source_path=args.source,
            write_bundle=args.write_bundle,
        )
        overview = get_han_catalog_overview(session)

    print("Han catalog imported." if seeded else "Han catalog already present.")
    if overview:
        print(f"Works: {overview['work_count']}")
        print(f"Catalog nodes: {overview['catalog_node_count']}")


if __name__ == "__main__":
    main()
