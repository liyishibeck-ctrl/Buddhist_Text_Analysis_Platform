from __future__ import annotations

import argparse

from backend.app.db.session import SessionLocal
from backend.app.services.concept_analysis_service import backfill_core_concepts, ensure_core_concept_tags


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill core concept tags across the current corpus.")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--tradition-id")
    parser.add_argument("--collection-id")
    parser.add_argument("--language-id")
    args = parser.parse_args()

    with SessionLocal() as session:
        created = ensure_core_concept_tags(session)
        inserted = backfill_core_concepts(
            session,
            batch_size=args.batch_size,
            tradition_id=args.tradition_id,
            collection_id=args.collection_id,
            language_id=args.language_id,
        )

    print(f"Ensured concept tags: {created}")
    print(f"Inserted concept links: {inserted}")


if __name__ == "__main__":
    main()
