from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.services.han_cbeta_xml_loader import seed_han_cbeta_xml_texts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import official CBETA XML P5 Han texts into the Buddha MVP.")
    parser.add_argument("--force", action="store_true", help="Re-import the official CBETA XML versions.")
    parser.add_argument("--manifest", type=Path, default=None, help="Optional override path to the CBETA XML manifest.")
    args = parser.parse_args()

    with SessionLocal() as session:
        seeded = seed_han_cbeta_xml_texts(session, force=args.force, manifest_path=args.manifest)

    print("CBETA XML import completed." if seeded else "CBETA XML source already present.")


if __name__ == "__main__":
    main()
