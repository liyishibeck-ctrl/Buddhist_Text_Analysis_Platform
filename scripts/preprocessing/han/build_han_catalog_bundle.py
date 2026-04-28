from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.core.config import settings
from backend.app.services.han_catalog_pipeline import build_han_catalog_payload, write_han_catalog_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a processed JSON bundle from the Han catalog CSV seed.")
    parser.add_argument("--source", type=Path, default=settings.han_catalog_source_path)
    parser.add_argument("--output", type=Path, default=settings.han_catalog_bundle_path)
    args = parser.parse_args()

    payload = build_han_catalog_payload(args.source)
    bundle_path = write_han_catalog_bundle(payload, args.output)

    print(f"Bundle written to: {bundle_path}")
    print(f"Works: {len(payload.get('works', []))}")
    print(f"Text versions: {len(payload.get('text_versions', []))}")
    print(f"Catalog nodes: {len(payload.get('catalog_nodes', []))}")


if __name__ == "__main__":
    main()
