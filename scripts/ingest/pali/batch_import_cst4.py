"""
Batch import entire CST4 Pali Sutta Pitaka into the platform.

This script scans a directory containing CST4 plain text files and generates
the manifest needed for import, then runs the import.

Expected file naming format (common in CST4 distributions):
  dn001_name.txt - Dīgha Nikāya, sutta 1
  mn001_name.txt - Majjhima Nikāya, sutta 1
  sn001_name.txt - Saṁyutta Nikāya, sutta 1
  an001_name.txt - Aṅguttara Nikāya, sutta 1
  kn001_name.txt - Khuddaka Nikāya, text 1

Each file can contain lines in format:
  pali_text ||| chinese_translation
or just plain pali_text (if no translation available).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend.app.core.config import ROOT_DIR


NIKAYA_MAP = {
    'dn': {
        'nikaya': 'dn',
        'name_cn': '长部',
        'name_en': 'Dīgha Nikāya',
        'collection_slug': 'pali-dn',
        'collection_title': '长部 / Dīgha Nikāya',
    },
    'mn': {
        'nikaya': 'mn',
        'name_cn': '中部',
        'name_en': 'Majjhima Nikāya',
        'collection_slug': 'pali-mn',
        'collection_title': '中部 / Majjhima Nikāya',
    },
    'sn': {
        'nikaya': 'sn',
        'name_cn': '相应部',
        'name_en': 'Saṁyutta Nikāya',
        'collection_slug': 'pali-sn',
        'collection_title': '相应部 / Saṁyutta Nikāya',
    },
    'an': {
        'nikaya': 'an',
        'name_cn': '增支部',
        'name_en': 'Aṅguttara Nikāya',
        'collection_slug': 'pali-an',
        'collection_title': '增支部 / Aṅguttara Nikāya',
    },
    'kn': {
        'nikaya': 'kn',
        'name_cn': '小部',
        'name_en': 'Khuddaka Nikāya',
        'collection_slug': 'pali-kn',
        'collection_title': '小部 / Khuddaka Nikāya',
    },
}

FILENAME_PATTERN = re.compile(r"^(?P<nikaya>dn|mn|sn|an|kn)(?P<group>\d+)_(?P<reference>.+)\.txt$", re.IGNORECASE)
TOP_LINE_SCAN_LIMIT = 8
KN_FALLBACKS = (
    {
        "canonical_ref": "Dhp",
        "title_pali": "Dhammapada",
        "text_path": "data/raw/pali/texts/dhammapada.txt",
    },
)


def _normalize_reference(reference: str) -> str:
    """Normalize dotted/ranged numeric references by stripping zero padding."""

    def _normalize_match(match: re.Match[str]) -> str:
        return str(int(match.group(0)))

    return re.sub(r"\d+", _normalize_match, reference)


def _reference_slug(reference: str) -> str:
    """Convert canonical reference into a readable slug."""
    slug = re.sub(r"[^0-9a-z]+", "-", reference.lower()).strip("-")
    return slug or "unknown"


def _extract_title_pali(file_path: Path) -> str | None:
    """Extract a likely sutta title from the opening lines."""
    with file_path.open('r', encoding='utf-8') as f:
        for _ in range(TOP_LINE_SCAN_LIMIT):
            raw_line = f.readline()
            if not raw_line:
                break
            candidate = raw_line.split('|||', 1)[0].strip().strip('*').strip()
            if not candidate:
                continue
            candidate_lower = candidate.casefold()
            if "nikāya" in candidate_lower:
                continue
            if re.match(r"^\d+(?:\.\d+(?:-\d+)?)?$", candidate):
                continue
            if re.match(r"^\d+\.\s+", candidate):
                continue
            if candidate_lower.startswith("evaṁ me sutaṁ"):
                continue
            if candidate_lower.endswith(("sutta", "suttanta")):
                if len(candidate) > 80:
                    return candidate[:77] + '...'
                return candidate
    return None


def parse_filename(filename: str) -> dict | None:
    """Parse filename like dn001_name.txt into components.

    For CST4 files we expect: {nikaya}{group:03d}_{nikaya}{reference}.txt.
    Examples:
      dn001_dn1.txt -> DN 1
      sn047_sn47.45.txt -> SN 47.45
      an001_an1.1-10.txt -> AN 1.1-10
    """
    m = FILENAME_PATTERN.match(filename.lower())
    if not m:
        return None
    nikaya_code = m.group("nikaya")
    raw_reference = m.group("reference")
    reference_match = re.match(fr"^{nikaya_code}(?P<reference>[0-9][0-9.\-]*)$", raw_reference)
    if not reference_match:
        return None
    canonical_ref = _normalize_reference(reference_match.group("reference"))
    return {
        'nikaya_code': nikaya_code,
        'canonical_ref': canonical_ref,
        'reference_slug': _reference_slug(canonical_ref),
    }


def generate_work_metadata(
    nikaya_info: dict,
    canonical_ref: str,
    title_pali: str | None,
) -> dict:
    """Generate work metadata."""
    reference_slug = _reference_slug(canonical_ref)
    work_id = f"work-pi-{nikaya_info['nikaya']}-{reference_slug}"
    collection_id = f"coll-pali-{nikaya_info['nikaya']}"
    canonical_code = f"{nikaya_info['nikaya'].upper()} {canonical_ref}"
    title = f"{nikaya_info['name_en']} {canonical_ref}"
    if title_pali:
        title = f"{title_pali} ({canonical_code})"
    return {
        'id': work_id,
        'slug': work_id,
        'title': title,
        'title_english': f"{nikaya_info['name_en']} {canonical_ref}",
        'genre': 'sutta',
        'pitaka_division': 'sutra',
        'canonical_code': canonical_code,
        'tradition_id': 'trad-pali',
        'collection_id': collection_id,
        'is_catalog_only': False,
        'is_sample': False,
    }


def generate_manifest_entry(
    file_path: Path,
    nikaya_code: str,
    canonical_ref: str,
    title_pali: str | None,
    language_id: str = 'lang-pi',
) -> dict:
    """Generate a manifest text entry."""
    nikaya_info = NIKAYA_MAP[nikaya_code]
    work_metadata = generate_work_metadata(nikaya_info, canonical_ref, title_pali)
    work_id = work_metadata['id']
    reference_slug = _reference_slug(canonical_ref)
    tv_id = f"tv-{nikaya_code}-{reference_slug}-cst4"
    slug = f"{nikaya_code}-{reference_slug}-cst4"

    # Get relative path for storage
    file_path_abs = file_path.resolve()
    rel_path = file_path_abs.relative_to(ROOT_DIR).as_posix()

    canonical_code = work_metadata['canonical_code']
    return {
        'work_id': work_id,
        'work_metadata': work_metadata,
        'canonical_code': canonical_code,
        'language_id': language_id,
        'text_path': rel_path,
        'segment_by': 'line',
        'is_sample': False,
        'text_version': {
            'id': tv_id,
            'slug': slug,
            'title': f"{title_pali} ({canonical_code})" if title_pali else canonical_code,
            'version_label': 'CST4 Pali',
            'summary': f"{nikaya_info['name_en']} text {canonical_ref} from CST4 edition.",
            'sample_note': None,
            'is_sample': False,
        },
        'person_roles': [
            {
                'person_id': 'person-buddha',
                'role': 'attributed_speaker',
                'note': f"Attributed to the Buddha in {nikaya_info['name_en']}.",
            }
        ],
    }


def _append_kn_fallback_if_needed(
    texts: list[dict],
    stats: dict,
    language_id: str,
) -> None:
    """Add a KN fallback text when the CST4 dump has no KN files."""
    if stats['by_nikaya'].get('kn'):
        return

    for fallback in KN_FALLBACKS:
        raw_path = Path(fallback["text_path"])
        fallback_path = raw_path if raw_path.is_absolute() else (ROOT_DIR / raw_path)
        if not fallback_path.exists():
            continue
        entry = generate_manifest_entry(
            fallback_path,
            'kn',
            fallback["canonical_ref"],
            fallback["title_pali"],
            language_id=language_id,
        )
        texts.append(entry)
        stats['total_valid'] += 1
        stats['by_nikaya']['kn'] = stats['by_nikaya'].get('kn', 0) + 1
        stats['kn_fallback_added'] = stats.get('kn_fallback_added', 0) + 1
        break


def scan_directory(
    input_dir: Path,
    language_id: str = 'lang-pi',
) -> dict:
    """Scan directory of CST4 text files and generate manifest."""
    source = {
        'id': 'source-pali-cst4-complete',
        'slug': 'pali-cst4-complete',
        'title': 'Pali Tipitaka CST4 complete edition',
        'source_type': 'canon',
        'citation': 'Chaṭṭha Saṅgāyana Tipiṭaka 4th edition (CST4) from SuttaCentral.',
        'url': 'https://suttacentral.net/',
        'access_note': 'Complete Sutta Pitaka from the open access CST4 corpus.',
        'is_sample': False,
    }

    texts: list[dict] = []
    stats = {
        'total_files': 0,
        'total_valid': 0,
        'by_nikaya': {},
    }

    for txt_file in sorted(input_dir.glob('*.txt')):
        stats['total_files'] += 1
        parsed = parse_filename(txt_file.name)
        if not parsed:
            print(f"WARNING: Skipping {txt_file.name} (does not match pattern)")
            continue

        nikaya_code = parsed['nikaya_code']
        canonical_ref = parsed['canonical_ref']

        if nikaya_code not in NIKAYA_MAP:
            print(f"WARNING: Unknown nikaya code {nikaya_code} in {txt_file.name}")
            continue

        title_pali = _extract_title_pali(txt_file)

        entry = generate_manifest_entry(
            txt_file,
            nikaya_code,
            canonical_ref,
            title_pali,
            language_id=language_id,
        )
        texts.append(entry)
        stats['total_valid'] += 1
        stats['by_nikaya'][nikaya_code] = stats['by_nikaya'].get(nikaya_code, 0) + 1

    _append_kn_fallback_if_needed(texts, stats, language_id)

    return {
        'source': source,
        'texts': texts,
        'stats': stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch scan and generate manifest for CST4 Pali texts."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing CST4 .txt files (one per sutta)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output manifest file path. Default: data/raw/pali/cst4_sutta_pitaka_manifest.json"
    )
    parser.add_argument(
        "--language-id",
        type=str,
        default="lang-pi",
        help="Language ID to use. Default: lang-pi (Romanized), use lang-pi-sinh for Sinhala script."
    )
    args = parser.parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    result = scan_directory(args.input_dir, args.language_id)

    output_path = args.output or ROOT_DIR / "data" / "raw" / "pali" / "cst4_sutta_pitaka_manifest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', encoding='utf-8') as f:
        # We need the specific structure that seed_plain_text_works expects
        full_output = {
            "source": result['source'],
            "texts": result['texts'],
        }
        json.dump(full_output, f, ensure_ascii=False, indent=2)

    print(f"\nManifest generated: {output_path}")
    print(f"Statistics:")
    print(f"   Total files scanned: {result['stats']['total_files']}")
    print(f"   Valid suttas: {result['stats']['total_valid']}")
    for nikaya, count in result['stats']['by_nikaya'].items():
        print(f"   {NIKAYA_MAP[nikaya]['name_cn']} ({nikaya}): {count}")

    print(f"\nNext step:")
    print(f"   python -m scripts.ingest.pali.import_pali_plain_text --force --manifest {output_path}")


if __name__ == "__main__":
    main()
