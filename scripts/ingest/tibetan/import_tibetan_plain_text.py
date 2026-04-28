from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.services.plain_text_loader import seed_plain_text_works


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Tibetan plain texts (Wylie) into the Buddha MVP.")
    parser.add_argument("--force", action="store_true", help="Re-import the Tibetan plain text versions.")
    parser.add_argument("--manifest", type=Path, default=None, help="Optional override path to the Tibetan manifest.")
    args = parser.parse_args()

    with SessionLocal() as session:
        seeded = seed_plain_text_works(
            session,
            tradition_id="trad-tibetan",
            force=args.force,
            manifest_path=args.manifest,
        )

    print("Tibetan plain text import completed." if seeded else "Tibetan plain text source already present.")


if __name__ == "__main__":
    main()
