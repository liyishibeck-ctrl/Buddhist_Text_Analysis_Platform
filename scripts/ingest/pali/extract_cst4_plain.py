"""
Extract plain text Pali from SuttaCentral CST4 HTML distribution.

This script reads the HTML files from the cloned sc-data repo and extracts
the Pali text into individual .txt files ready for import.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Optional


def extract_pali_from_html(html_path: Path) -> Optional[str]:
    """Extract Pali text from HTML file."""
    with html_path.open('r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Find all the Pali text spans with class "pli"
    pali_spans = soup.find_all('span', class_='pli')
    if not pali_spans:
        # Try another approach - look for any text in the main content
        pali_text = soup.get_text()
        # Clean up
        pali_text = re.sub(r'\s+', ' ', pali_text).strip()
        return pali_text if pali_text else None

    # Join all Pali text
    pali_text = ' '.join(span.get_text().strip() for span in pali_spans)
    pali_text = re.sub(r'\s+', ' ', pali_text).strip()
    return pali_text if pali_text else None


def extract_sutta_info(html_path: Path) -> tuple[str, int, str]:
    """Extract nikaya code and sutta number from path.

    Returns: (nikaya_code, number, output_filename)
    """
    full_path = str(html_path).lower()
    filename = html_path.name

    # Split path into components and search from end backwards
    # We want the nikaya code that actually identifies this sutta, which is
    # in the directory structure: .../nikaya/nikayaNum/nikayaNum.xx.html
    # So the nikaya code appears multiple times, we want the one with the number that identifies this sutta
    parts = list(html_path.parts)
    parts.reverse()  # search from end backwards

    found = []
    for part in parts:
        part_lower = part.lower()
        for nikaya in ('dn', 'mn', 'sn', 'an', 'kn'):
            if part_lower.startswith(nikaya) and len(part_lower) >= len(nikaya) + 1:
                # Check if there are digits after nikaya
                digits = []
                for c in part_lower[len(nikaya):]:
                    if c.isdigit():
                        digits.append(c)
                    elif c == '.':
                        break
                    elif not c.isalnum():
                        break
                if digits:
                    # Found it - this is the nikaya + number we want
                    number = int(''.join(digits))
                    return nikaya, number, f"{nikaya}{number:03d}_{html_path.stem}.txt"

    # If not found in directories, search filename
    stem = html_path.stem  # filename without extension
    for nikaya in ('dn', 'mn', 'sn', 'an', 'kn'):
        if stem.startswith(nikaya) and len(stem) >= len(nikaya) + 1:
            digits = []
            for c in stem[len(nikaya):]:
                if c.isdigit():
                    digits.append(c)
                elif c == '.':
                    break
                else:
                    break
            if digits:
                number = int(''.join(digits))
                return nikaya, number, f"{nikaya}{number:03d}_{html_path.stem}.txt"

    # Give up
    raise ValueError(f"Cannot extract sutta info from {html_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Pali text from CST4 HTML.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/tmp/sc-data/html_text/en/pli/sutta"),
        help="Directory containing the CST4 sutta HTML files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/pali/cst4-full"),
        help="Output directory for extracted .txt files."
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(args.source_dir.rglob('*.html'))
    print(f"Found {len(html_files)} HTML files")

    extracted = 0
    skipped = 0

    for html_path in html_files:
        try:
            nikaya_code, number, out_name = extract_sutta_info(html_path)
        except ValueError as e:
            print(f"WARNING: Skipping {html_path}: {e}")
            skipped += 1
            continue

        pali_text = extract_pali_from_html(html_path)
        if not pali_text:
            print(f"WARNING: No Pali text extracted from {html_path}")
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
