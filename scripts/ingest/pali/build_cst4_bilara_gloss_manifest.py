from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.pali_bilara_gloss import (  # noqa: E402
    build_bilingual_manifest_payload,
    build_root_index,
    build_translation_index,
    write_manifest,
)
from backend.app.services.plain_text_loader import load_plain_text_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a CST4 Pali manifest with aligned Bilara gloss lines.")
    parser.add_argument(
        "--base-manifest",
        type=Path,
        default=Path("data/raw/pali/cst4_sutta_pitaka_manifest.json"),
        help="Base CST4 manifest to enrich with Bilara gloss.",
    )
    parser.add_argument(
        "--root-base",
        type=Path,
        default=Path("data/raw/sc-data/sc_bilara_data/root/pli/ms/sutta"),
        help="Bilara root Pali JSON directory.",
    )
    parser.add_argument(
        "--translation-lang",
        type=str,
        default="en",
        help="Bilara translation language code, e.g. en or zh.",
    )
    parser.add_argument(
        "--translation-base",
        type=Path,
        default=Path("data/raw/sc-data/sc_bilara_data/translation"),
        help="Bilara translation root directory containing per-language folders.",
    )
    parser.add_argument(
        "--output-text-root",
        type=Path,
        default=Path("data/processed/pali/cst4-bilara-en"),
        help="Output directory for generated bilingual text files.",
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        default=Path("data/processed/pali/cst4_sutta_pitaka_manifest_en_gloss.json"),
        help="Output path for the generated manifest.",
    )
    args = parser.parse_args()

    base_manifest = load_plain_text_manifest("pali", args.base_manifest)
    root_index = build_root_index((ROOT_DIR / args.root_base).resolve())
    translation_lang_base = (ROOT_DIR / args.translation_base / args.translation_lang).resolve()
    translation_index = build_translation_index(
        translation_lang_base,
        language_code=args.translation_lang,
    )
    payload, stats = build_bilingual_manifest_payload(
        base_manifest=base_manifest,
        root_index=root_index,
        translation_index=translation_index,
        output_root=args.output_text_root,
        language_code=args.translation_lang,
        translation_lang_base=translation_lang_base,
    )
    manifest_path = write_manifest(payload, (ROOT_DIR / args.output_manifest).resolve())

    print(f"Manifest written to: {manifest_path}")
    print(f"Texts processed: {stats['texts_total']}")
    print(f"Texts with translation file: {stats['texts_with_translation_file']}")
    print(f"Segments generated: {stats['segments_total']}")
    print(f"Segments with gloss: {stats['segments_with_gloss']}")


if __name__ == "__main__":
    main()
