from __future__ import annotations

import argparse

from backend.app.db.init_db import initialize_database
from backend.app.db.session import SessionLocal
from backend.app.services.catalog_service import get_overview
from backend.app.services.han_catalog_loader import seed_han_catalog_snapshot
from backend.app.services.han_cbeta_xml_loader import seed_han_cbeta_xml_texts
from backend.app.services.han_core_text_loader import seed_han_core_texts
from backend.app.services.sample_loader import seed_sample_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Create tables and seed the Buddha MVP sample corpus.")
    parser.add_argument("--force", action="store_true", help="Re-seed even if data already exists.")
    args = parser.parse_args()

    initialize_database(reset_schema=args.force)
    with SessionLocal() as session:
        if args.force:
            seeded = seed_sample_corpus(session, force=True)
            seeded = seed_han_catalog_snapshot(session, force=True) or seeded
            seeded = seed_han_core_texts(session, force=True) or seeded
            seeded = seed_han_cbeta_xml_texts(session, force=True) or seeded
        else:
            seeded = False
            seeded = seed_han_catalog_snapshot(session) or seeded
            seeded = seed_han_core_texts(session) or seeded
            seeded = seed_han_cbeta_xml_texts(session) or seeded
        overview = get_overview(session)

    print("Seed completed." if seeded else "Database ready.")
    print(f"Collections: {overview['total_collections']}")
    print(f"Works: {overview['total_works']}")
    print(f"Text versions: {overview['total_text_versions']}")
    print(f"Segments: {overview['total_segments']}")
    print(f"Parallel links: {overview['total_parallel_links']}")


if __name__ == "__main__":
    main()
