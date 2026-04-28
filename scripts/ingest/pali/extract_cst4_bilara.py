"""
Extract plain text Pali from SuttaCentral sc-data bilara-data JSON distribution.

This script reads the JSON files from the cloned sc-data repo bilara-data directory
and extracts the Pali text into individual .txt files ready for import.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional


def extract_pali_from_json(json_path: Path) -> Optional[str]:
    """Extract Pali text from bilara JSON file.

    Each segment in JSON is output on its own line for proper paragraph/segment breaks.
    This makes it easier to read with proper spacing between segments.
    """
    with json_path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    # All values are Pali text segments
    # Output each segment on its own line for proper segmentation
    pali_lines = []
    for segment_text in data.values():
        cleaned = segment_text.strip()
        if cleaned:
            pali_lines.append(cleaned)

    # Join with newlines - each segment becomes a paragraph for import segmentation
    pali_text = '\n'.join(pali_lines)
    return pali_text if pali_text else None


def extract_sutta_info(json_path: Path) -> tuple[str, int, str]:
    """Extract nikaya code and sutta number from bilara path.

    Bilara path structure: root/pli/ms/sutta/dn/dn1_root-pli-ms.json
    So we can get nikaya from directory: dn, mn, sn, an, kn
    and sutta number from filename: dn1 -> dn 1
    """
    filename = json_path.name

    # Split path into components
    parts = list(json_path.parts)

    found = []
    for part in parts:
        part_lower = part.lower()
        for nikaya in ('dn', 'mn', 'sn', 'an', 'kn'):
            if part_lower == nikaya:
                # Found the nikaya directory
                # Now look for the file which starts with nikaya
                found.append((nikaya, None))
                break

    if found:
        # The last found is the one we want
        nikaya, _ = found[-1]
        # Extract number from filename - handle formats like:
        # dn1_, an1.1-10_, sn12.3_
        m = __import__('re').match(rf'^{nikaya}(\d+)', filename.lower())
        if m:
            number = int(m.group(1))
            return nikaya, number, f"{nikaya}{number:03d}_{filename.split('_')[0]}.txt"

    # If not found in directories, search filename directly
    m = __import__('re').match(r'^([dmksa][nrel])(\d+)', filename.lower())
    if m:
        nikaya = m.group(1)
        number = int(m.group(2))
        if nikaya in ('dn', 'mn', 'sn', 'an', 'kn'):
            return nikaya, number, f"{nikaya}{number:03d}_{filename.split('_')[0]}.txt"

    # Give up
    raise ValueError(f"Cannot extract sutta info from {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Pali text from CST4 bilara JSON.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/tmp/sc-data/sc_bilara_data/root/pli/ms/sutta"),
        help="Directory containing the CST4 bilara sutta JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/pali/cst4-full"),
        help="Output directory for extracted .txt files.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(args.source_dir.rglob('*.json'))
    print(f"Found {len(json_files)} JSON files")

    extracted = 0
    skipped = 0

    for json_path in json_files:
        # Skip anything that's not actually the main root text
        if not json_path.name.endswith('_root-pli-ms.json'):
            continue

        try:
            nikaya_code, number, out_name = extract_sutta_info(json_path)
        except ValueError as e:
            print(f"WARNING: Skipping {json_path}: {e}")
            skipped += 1
            continue

        pali_text = extract_pali_from_json(json_path)
        if not pali_text:
            print(f"WARNING: No Pali text extracted from {json_path}")
            skipped += 1
            continue

        out_path = args.output_dir / out_name
        with out_path.open('w', encoding='utf-8') as f:
            f.write(pali_text)
        extracted += 1

        if extracted % 100 == 0:
            print(f"  Extracted {extracted} files...")

    print(f"\nDone. Extracted {extracted} files to {args.output_dir}, skipped {skipped}")


if __name__ == "__main__":
    main()
