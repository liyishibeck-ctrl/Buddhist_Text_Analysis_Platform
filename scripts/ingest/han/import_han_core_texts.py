from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.init_db import initialize_database
from backend.app.db.session import SessionLocal
from backend.app.services.catalog_service import get_han_catalog_overview
from backend.app.services.han_core_text_loader import seed_han_core_texts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the Han core-text pilot into the application database.")
    parser.add_argument("--force", action="store_true", help="Replace previously imported Han core-text pilot rows.")
    parser.add_argument("--source", type=Path, default=None, help="Optional pilot JSON override.")
    args = parser.parse_args()

    initialize_database()
    with SessionLocal() as session:
        seeded = seed_han_core_texts(session, force=args.force, source_path=args.source)
        overview = get_han_catalog_overview(session)

    print("Han core-text pilot imported." if seeded else "Han core-text pilot already present.")
    if overview:
        print(f"Ingested works: {overview['ingested_work_count']}")
        print(f"Ingested segments: {overview['ingested_segment_count']}")


if __name__ == "__main__":
    main()
