from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.core.config import settings


HAN_TRADITION_ID = "trad-han"
HAN_LANGUAGE_ID = "lang-lzh"
HAN_COLLECTION_ID = "coll-han-canon-catalog"
HAN_SOURCE_ID = "source-han-catalog-snapshot"

DIVISION_META: dict[str, dict[str, Any]] = {
    "sutra": {"label": "经藏", "title": "汉传经藏目录", "position": 1},
    "vinaya": {"label": "律藏", "title": "汉传律藏目录", "position": 2},
    "abhidharma": {"label": "论藏", "title": "汉传论藏目录", "position": 3},
}

REQUIRED_COLUMNS = {
    "catalog_order",
    "canonical_code",
    "work_slug",
    "title",
    "title_english",
    "title_transliterated",
    "genre",
    "pitaka_division",
    "section_key",
    "section_label",
    "section_title",
    "fascicle_count",
    "volume_ref",
    "translator_slug",
    "translator_name",
    "translator_native_name",
    "translator_role",
    "notes",
}


def _optional_str(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return int(value)


def load_han_catalog_seed_frame(path: Path | None = None) -> pd.DataFrame:
    source_path = Path(path or settings.han_catalog_source_path)
    frame = pd.read_csv(source_path, dtype=str, keep_default_na=False)
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Han catalog seed is missing required columns: {missing_str}")

    frame["catalog_order"] = pd.to_numeric(frame["catalog_order"], errors="raise").astype(int)
    frame["fascicle_count"] = pd.to_numeric(frame["fascicle_count"], errors="coerce").astype("Int64")
    frame = frame.sort_values(["pitaka_division", "section_key", "catalog_order", "canonical_code"]).reset_index(drop=True)
    return frame


def build_han_catalog_payload(path: Path | None = None) -> dict[str, Any]:
    source_path = Path(path or settings.han_catalog_source_path)
    frame = load_han_catalog_seed_frame(source_path)

    payload: dict[str, Any] = {
        "metadata": {
            "generated_from": str(source_path),
            "record_count": int(len(frame.index)),
            "note": (
                "Catalog-only Han canon seed used to validate directory ingestion. "
                "These rows are not a full-text corpus."
            ),
        },
        "sources": [
            {
                "id": HAN_SOURCE_ID,
                "slug": "han-catalog-snapshot",
                "title": "汉传三藏目录快照（CSV seed）",
                "source_type": "catalog_snapshot",
                "citation": "Curated Han canon directory snapshot for MVP catalog ingestion.",
                "url": None,
                "access_note": "Catalog-only dataset. Full text, fascicle structure, and segments are not yet imported.",
                "is_sample": False,
            }
        ],
        "collections": [
            {
                "id": HAN_COLLECTION_ID,
                "slug": "han-canon-catalog",
                "title": "汉传三藏目录快照",
                "tradition_id": HAN_TRADITION_ID,
                "description": "Curated directory-level snapshot used to validate Han canon catalog import, browsing, and later full-text mapping.",
                "coverage_note": "Catalog-only. This snapshot preserves work-level identifiers, pitaka divisions, and section hierarchy.",
                "is_sample": False,
            }
        ],
        "persons": [],
        "works": [],
        "text_versions": [],
        "text_version_person_roles": [],
        "catalog_nodes": [],
    }

    payload["catalog_nodes"].append(
        {
            "id": "cat-han-root",
            "collection_id": HAN_COLLECTION_ID,
            "tradition_id": HAN_TRADITION_ID,
            "parent_id": None,
            "work_id": None,
            "node_type": "root",
            "node_key": "han-root",
            "label": "汉传三藏",
            "title": "汉传三藏目录树",
            "pitaka_division": None,
            "section_key": None,
            "depth": 0,
            "position": 1,
            "path": "han-root",
            "note": "MVP catalog tree root for Han canon ingestion.",
            "is_terminal": False,
        }
    )

    for division, meta in DIVISION_META.items():
        if frame.loc[frame["pitaka_division"] == division].empty:
            continue
        payload["catalog_nodes"].append(
            {
                "id": f"cat-han-{division}",
                "collection_id": HAN_COLLECTION_ID,
                "tradition_id": HAN_TRADITION_ID,
                "parent_id": "cat-han-root",
                "work_id": None,
                "node_type": "division",
                "node_key": division,
                "label": meta["label"],
                "title": meta["title"],
                "pitaka_division": division,
                "section_key": None,
                "depth": 1,
                "position": meta["position"],
                "path": f"han-root/{division}",
                "note": f"{meta['label']}目录节点",
                "is_terminal": False,
            }
        )

    persons: dict[str, dict[str, Any]] = {}
    section_positions: dict[tuple[str, str], int] = {}

    for row in frame.to_dict(orient="records"):
        division = str(row["pitaka_division"]).strip()
        section_key = str(row["section_key"]).strip()
        section_label = _optional_str(row["section_label"]) or section_key
        section_title = _optional_str(row["section_title"]) or section_label
        catalog_order = int(row["catalog_order"])
        work_slug = str(row["work_slug"]).strip()
        work_id = f"work-{work_slug}"
        text_version_id = f"tv-{work_slug}-catalog"
        fascicle_count = _optional_int(row["fascicle_count"])
        volume_ref = _optional_str(row["volume_ref"])
        note = _optional_str(row["notes"]) or "目录快照条目，正文尚未导入。"
        catalog_note = note if not volume_ref else f"{note}；卷次参考：{volume_ref}"

        section_token = (division, section_key)
        if section_token not in section_positions:
            section_positions[section_token] = len(section_positions) + 1
            payload["catalog_nodes"].append(
                {
                    "id": f"cat-han-{division}-{section_key}",
                    "collection_id": HAN_COLLECTION_ID,
                    "tradition_id": HAN_TRADITION_ID,
                    "parent_id": f"cat-han-{division}",
                    "work_id": None,
                    "node_type": "section",
                    "node_key": section_key,
                    "label": section_label,
                    "title": section_title,
                    "pitaka_division": division,
                    "section_key": section_key,
                    "depth": 2,
                    "position": section_positions[section_token],
                    "path": f"han-root/{division}/{section_key}",
                    "note": f"{section_title}目录节点",
                    "is_terminal": False,
                }
            )

        payload["works"].append(
            {
                "id": work_id,
                "slug": work_slug,
                "tradition_id": HAN_TRADITION_ID,
                "collection_id": HAN_COLLECTION_ID,
                "title": _optional_str(row["title"]) or work_slug,
                "title_english": _optional_str(row["title_english"]),
                "title_transliterated": _optional_str(row["title_transliterated"]),
                "genre": _optional_str(row["genre"]) or "catalog_entry",
                "summary": f"{section_title}目录项，已接入作品级元数据，后续可映射正文导入与段落切分。",
                "authenticity_note": None,
                "pitaka_division": division,
                "canonical_code": _optional_str(row["canonical_code"]),
                "fascicle_count": fascicle_count,
                "catalog_order": catalog_order,
                "catalog_note": catalog_note,
                "is_catalog_only": True,
                "is_sample": False,
            }
        )
        payload["text_versions"].append(
            {
                "id": text_version_id,
                "slug": f"{work_slug}-catalog",
                "work_id": work_id,
                "language_id": HAN_LANGUAGE_ID,
                "source_id": HAN_SOURCE_ID,
                "title": _optional_str(row["title"]) or work_slug,
                "version_label": "目录占位版本 / Catalog placeholder",
                "script_note": "文言汉文",
                "date_note": None,
                "summary": "Catalog-only placeholder version reserved for later full-text ingestion and structural anchoring.",
                "sample_note": None,
                "catalog_note": catalog_note,
                "is_catalog_only": True,
                "is_sample": False,
            }
        )
        payload["catalog_nodes"].append(
            {
                "id": f"cat-work-{work_slug}",
                "collection_id": HAN_COLLECTION_ID,
                "tradition_id": HAN_TRADITION_ID,
                "parent_id": f"cat-han-{division}-{section_key}",
                "work_id": work_id,
                "node_type": "work",
                "node_key": _optional_str(row["canonical_code"]) or work_slug,
                "label": _optional_str(row["canonical_code"]) or work_slug,
                "title": _optional_str(row["title"]),
                "pitaka_division": division,
                "section_key": section_key,
                "depth": 3,
                "position": catalog_order,
                "path": f"han-root/{division}/{section_key}/{work_slug}",
                "note": catalog_note,
                "is_terminal": True,
            }
        )

        translator_slug = _optional_str(row["translator_slug"])
        translator_name = _optional_str(row["translator_name"])
        translator_native_name = _optional_str(row["translator_native_name"])
        translator_role = _optional_str(row["translator_role"]) or "translator"
        if translator_slug and (translator_name or translator_native_name):
            person_id = f"person-han-{translator_slug}"
            if person_id not in persons:
                persons[person_id] = {
                    "id": person_id,
                    "slug": f"han-{translator_slug}",
                    "display_name": translator_name or translator_native_name,
                    "native_name": translator_native_name,
                    "tradition_affiliation": "汉传",
                    "role_summary": "目录层译者元数据",
                    "note": "Imported from Han catalog seed to preserve later full-text mapping and version provenance.",
                }
            payload["text_version_person_roles"].append(
                {
                    "text_version_id": text_version_id,
                    "person_id": person_id,
                    "role": translator_role,
                    "note": "Catalog-level translator assignment.",
                }
            )

    payload["persons"] = list(persons.values())
    return payload


def write_han_catalog_bundle(payload: dict[str, Any], output_path: Path | None = None) -> Path:
    bundle_path = Path(output_path or settings.han_catalog_bundle_path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle_path
