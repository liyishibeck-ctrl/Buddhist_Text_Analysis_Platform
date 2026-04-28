from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR
from backend.app.models import Collection, Language


TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
TMX_NS = {
    "tmx": "http://www.lisa.org/tmx14",
    "tei": "http://www.tei-c.org/ns/1.0",
}
XML_LANG_ATTR = "{http://www.w3.org/XML/1998/namespace}lang"

SOURCE_ID = "source-tibetan-84000-discourses"
COLLECTION_ID = "coll-kangyur-84000-discourses"
LANGUAGE_ID = "lang-bo-tibt"
DEFAULT_MANIFEST_PATH = ROOT_DIR / "data" / "processed" / "tibetan" / "tibetan_84000_discourses_manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT_DIR / "data" / "processed" / "tibetan" / "84000-discourses"
DEFAULT_TMX_ROOT = ROOT_DIR / "data" / "raw" / "tibetan" / "84000" / "data-translation-memory-master"
DEFAULT_TEI_ROOT = (
    ROOT_DIR / "data" / "raw" / "tibetan" / "84000" / "data-tei-master" / "translations" / "kangyur" / "translations"
)

TOH_FILE_RE = re.compile(r"toh(?P<key>[0-9]+[a-z]?(?:-[0-9]+)?)", flags=re.IGNORECASE)
TMX_FILE_RE = re.compile(r"^(?P<key>toh[0-9]+[a-z]?(?:-[0-9]+)?)-v(?P<version>[0-9]+)\.tmx$", flags=re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Collapse repeated whitespace while preserving Tibetan syllable spaces."""
    return WHITESPACE_RE.sub(" ", value).strip()


def parse_primary_toh_key(name: str) -> str | None:
    """Extract the primary Toh key from a filename such as 'toh19,554' or 'toh44-31'."""
    match = TOH_FILE_RE.search(name)
    if not match:
        return None
    return f"toh{match.group('key').lower()}"


def parse_primary_toh_number(toh_key: str) -> int | None:
    """Return the first integer from a Toh key for range filtering."""
    match = re.search(r"toh(?P<number>[0-9]+)", toh_key, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group("number"))


def canonical_code_for_toh_key(toh_key: str) -> str:
    body = toh_key[3:].upper()
    return f"Toh {body}"


def build_tmx_index(tmx_root: Path) -> dict[str, Path]:
    """Choose the highest-version TMX for each Toh key."""
    latest_versions: dict[str, tuple[int, Path]] = {}
    for path in sorted(tmx_root.glob("toh*-v*.tmx")):
        match = TMX_FILE_RE.match(path.name)
        if not match:
            continue
        toh_key = match.group("key").lower()
        version = int(match.group("version"))
        current = latest_versions.get(toh_key)
        if current is None or version > current[0]:
            latest_versions[toh_key] = (version, path)
    return {key: value[1] for key, value in latest_versions.items()}


def _tei_title(root: ET.Element, *, title_type: str, language: str) -> str | None:
    for node in root.findall(".//tei:titleStmt/tei:title", TEI_NS):
        if node.get("type") != title_type:
            continue
        if node.attrib.get(XML_LANG_ATTR) != language:
            continue
        value = normalize_text("".join(node.itertext()))
        if value:
            return value
    return None


def _tei_summary(root: ET.Element) -> str | None:
    node = root.find(".//tei:front/tei:div[@type='summary']//tei:p", TEI_NS)
    if node is None:
        return None
    value = normalize_text("".join(node.itertext()))
    return value or None


def _relative_processed_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def iter_published_discourse_entries(tei_root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Collect one published TEI metadata entry per Discourses Toh key."""
    entries_by_key: dict[str, dict[str, Any]] = {}
    duplicate_count = 0

    for path in sorted(tei_root.glob("*.xml")):
        toh_key = parse_primary_toh_key(path.name)
        if not toh_key:
            continue
        toh_number = parse_primary_toh_number(toh_key)
        if toh_number is None or not (8 <= toh_number <= 359):
            continue

        root = ET.parse(path).getroot()
        entry = {
            "toh_key": toh_key,
            "canonical_code": canonical_code_for_toh_key(toh_key),
            "tei_path": path,
            "title_bo": _tei_title(root, title_type="mainTitle", language="bo"),
            "title_bo_ltn": _tei_title(root, title_type="mainTitle", language="Bo-Ltn"),
            "title_en": _tei_title(root, title_type="mainTitle", language="en"),
            "summary_en": _tei_summary(root),
        }

        existing = entries_by_key.get(toh_key)
        if existing is None:
            entries_by_key[toh_key] = entry
            continue

        duplicate_count += 1
        existing_name = existing["tei_path"].name
        if len(path.name) < len(existing_name) or (len(path.name) == len(existing_name) and path.name < existing_name):
            entries_by_key[toh_key] = entry

    stats = {
        "published_discourse_tei_files": len(entries_by_key),
        "duplicate_tei_matches": duplicate_count,
    }
    return [entries_by_key[key] for key in sorted(entries_by_key)], stats


def parse_tmx_segments(tmx_path: Path) -> tuple[list[str], int, int]:
    """Render TMX translation units into plain text lines with optional English glosses."""
    root = ET.parse(tmx_path).getroot()
    lines: list[str] = []
    total_segments = 0
    gloss_segments = 0

    for unit in root.findall(".//tmx:body/tmx:tu", TMX_NS):
        bo_node = None
        en_node = None
        for tuv in unit.findall("tmx:tuv", TMX_NS):
            lang = tuv.attrib.get(XML_LANG_ATTR)
            seg_node = tuv.find("tmx:seg", TMX_NS)
            if lang == "bo":
                bo_node = seg_node
            elif lang == "en":
                en_node = seg_node
        if bo_node is None:
            continue

        bo_text = normalize_text("".join(bo_node.itertext()))
        if not bo_text:
            continue

        en_text = ""
        if en_node is not None:
            en_text = normalize_text("".join(en_node.itertext()))

        if en_text:
            lines.append(f"{bo_text} ||| {en_text}")
            gloss_segments += 1
        else:
            lines.append(bo_text)
        total_segments += 1

    return lines, total_segments, gloss_segments


def ensure_tibetan_84000_prerequisites(session: Session) -> None:
    """Ensure the target Tibetan language and collection exist in the database."""
    language = session.get(Language, LANGUAGE_ID)
    if language is None:
        session.add(
            Language(
                id=LANGUAGE_ID,
                code="bo-Tibt",
                name="Tibetan (Ucen script)",
                script="Tibetan",
                direction="ltr",
                description="Tibetan in the native Tibetan Uchen script (Unicode).",
            )
        )

    collection = session.get(Collection, COLLECTION_ID)
    if collection is None:
        session.add(
            Collection(
                id=COLLECTION_ID,
                slug="kangyur-84000-discourses",
                title="84000 藏文经部",
                tradition_id="trad-tibetan",
                description="Published Kangyur Discourses (Toh 8–359) from the 84000 corpus, imported as Tibetan text with aligned English glosses.",
                coverage_note="Built from 84000 TEI translations and translation-memory files.",
                is_sample=False,
            )
        )
    session.commit()


def build_manifest_payload(
    *,
    tei_root: Path = DEFAULT_TEI_ROOT,
    tmx_root: Path = DEFAULT_TMX_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    limit: int | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Create a Tibetan plain-text manifest for published 84000 Discourses."""
    discourse_entries, tei_stats = iter_published_discourse_entries(tei_root)
    tmx_index = build_tmx_index(tmx_root)

    output_root.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "source": {
            "id": SOURCE_ID,
            "slug": "tibetan-84000-discourses",
            "title": "84000 Tibetan Discourses (Kangyur)",
            "source_type": "canon",
            "citation": "84000: Translating the Words of the Buddha, published Discourses section (Toh 8–359), Tibetan text aligned with English translation memory.",
            "url": "https://84000.co/canon-sections/discourses",
            "access_note": "Imported for non-commercial academic research from 84000 TEI and translation-memory files under CC BY-NC-ND terms.",
            "is_sample": False,
        },
        "texts": [],
    }

    stats = {
        **tei_stats,
        "tmx_candidates": len(tmx_index),
        "texts_built": 0,
        "missing_tmx": 0,
        "segments_generated": 0,
        "segments_with_gloss": 0,
    }

    for entry in discourse_entries[: limit or len(discourse_entries)]:
        toh_key = entry["toh_key"]
        tmx_path = tmx_index.get(toh_key)
        if tmx_path is None:
            stats["missing_tmx"] += 1
            continue

        lines, total_segments, gloss_segments = parse_tmx_segments(tmx_path)
        if not lines:
            stats["missing_tmx"] += 1
            continue

        text_output_path = output_root / f"{toh_key}.txt"
        text_output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        title_en = entry["title_en"] or canonical_code_for_toh_key(toh_key)
        title_bo_ltn = entry["title_bo_ltn"] or title_en
        work_id = f"work-{toh_key}"
        text_version_id = f"tv-{toh_key}-84000"

        payload["texts"].append(
            {
                "work_id": work_id,
                "canonical_code": canonical_code_for_toh_key(toh_key),
                "language_id": LANGUAGE_ID,
                "text_path": _relative_processed_path(text_output_path),
                "segment_by": "line",
                "is_sample": False,
                "work_metadata": {
                    "id": work_id,
                    "slug": toh_key,
                    "tradition_id": "trad-tibetan",
                    "collection_id": COLLECTION_ID,
                    "title": title_bo_ltn,
                    "title_english": title_en,
                    "title_transliterated": entry["title_bo_ltn"],
                    "genre": "sutra",
                    "summary": entry["summary_en"],
                    "pitaka_division": "sutra",
                    "canonical_code": canonical_code_for_toh_key(toh_key),
                    "catalog_note": f"84000 published Discourses import. Tibetan title: {entry['title_bo'] or 'N/A'}",
                    "is_catalog_only": False,
                    "is_sample": False,
                },
                "text_version": {
                    "id": text_version_id,
                    "slug": f"{toh_key}-84000",
                    "title": f"{title_en} ({canonical_code_for_toh_key(toh_key)})",
                    "version_label": "84000 Tibetan with aligned English gloss",
                    "script_note": "Unicode Tibetan with aligned English gloss",
                    "summary": entry["summary_en"],
                    "sample_note": None,
                    "catalog_note": f"Imported from {tmx_path.name} and {entry['tei_path'].name}.",
                    "is_sample": False,
                },
                "person_roles": [],
            }
        )
        stats["texts_built"] += 1
        stats["segments_generated"] += total_segments
        stats["segments_with_gloss"] += gloss_segments

    return payload, stats


def write_manifest(payload: dict[str, Any], path: Path = DEFAULT_MANIFEST_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
