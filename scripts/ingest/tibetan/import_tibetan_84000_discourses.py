from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.core.config import ROOT_DIR
from backend.app.db.session import SessionLocal
from backend.app.models import TextVersion
from backend.app.services.plain_text_loader import seed_plain_text_works
from backend.app.services.tibetan_84000_discourses import (
    DEFAULT_MANIFEST_PATH,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_TEI_ROOT,
    DEFAULT_TMX_ROOT,
    SOURCE_ID,
    build_manifest_payload,
    ensure_tibetan_84000_prerequisites,
    write_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import 84000 Tibetan Discourses (Toh 8–359) into the Buddha MVP.")
    parser.add_argument("--force", action="store_true", help="Re-import the 84000 Tibetan Discourses source.")
    parser.add_argument("--resume", action="store_true", help="Continue an interrupted import by skipping already imported text versions.")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on how many texts to build and import.")
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_PATH, help="Path to the generated manifest.")
    parser.add_argument("--output-text-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Directory for generated Tibetan plain-text files.")
    parser.add_argument("--tmx-root", type=Path, default=DEFAULT_TMX_ROOT, help="Directory containing 84000 TMX files.")
    parser.add_argument("--tei-root", type=Path, default=DEFAULT_TEI_ROOT, help="Directory containing 84000 published TEI translations.")
    args = parser.parse_args()

    with SessionLocal() as session:
        ensure_tibetan_84000_prerequisites(session)

    payload, stats = build_manifest_payload(
        tei_root=args.tei_root,
        tmx_root=args.tmx_root,
        output_root=args.output_text_root,
        limit=None if args.resume else args.limit,
    )

    if args.resume:
        with SessionLocal() as session:
            existing_text_version_ids = {
                row[0]
                for row in session.query(TextVersion.id)
                .filter(TextVersion.source_id == SOURCE_ID)
                .all()
            }
        payload["texts"] = [
            text_item
            for text_item in payload["texts"]
            if text_item["text_version"]["id"] not in existing_text_version_ids
        ]
        payload["texts"].sort(
            key=lambda text_item: (
                (ROOT_DIR / text_item["text_path"]).stat().st_size
                if not Path(text_item["text_path"]).is_absolute()
                else Path(text_item["text_path"]).stat().st_size
            )
        )
        if args.limit is not None:
            payload["texts"] = payload["texts"][: args.limit]
        stats["resume_existing_text_versions"] = len(existing_text_version_ids)
        stats["resume_remaining_texts"] = len(payload["texts"])

    manifest_path = write_manifest(payload, args.manifest_output)

    print(f"Manifest written to: {manifest_path}")
    for key in sorted(stats):
        print(f"{key}: {stats[key]}")

    with SessionLocal() as session:
        seeded = seed_plain_text_works(
            session,
            tradition_id="trad-tibetan",
            force=args.force,
            resume=args.resume,
            manifest_path=manifest_path,
        )

    print("84000 Tibetan Discourses import completed." if seeded else "84000 Tibetan Discourses source already present.")


if __name__ == "__main__":
    main()
