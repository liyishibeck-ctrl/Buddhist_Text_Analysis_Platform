from __future__ import annotations

import argparse
import csv
import json
from itertools import combinations
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_PATH = ROOT_DIR / "data" / "raw" / "han" / "han_core_texts_pilot.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "han" / "han_core_texts_pilot_bundle.json"
DEFAULT_CATALOG_PATH = ROOT_DIR / "data" / "raw" / "han" / "han_canon_catalog_seed.csv"

ANCHOR_TAGS = {
    "bodhisattva",
    "buddhahood",
    "dependent-origination",
    "emptiness",
    "non-attachment",
    "one-vehicle",
    "practice-path",
    "prajna",
    "skillful-means",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_catalog_lookup(path: Path) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            canonical_code = (row.get("canonical_code") or "").strip()
            work_slug = (row.get("work_slug") or "").strip()
            if not canonical_code or not work_slug:
                continue
            lookup[canonical_code] = {
                "work_slug": work_slug,
                "work_id": f"work-{work_slug}",
                "title": (row.get("title") or "").strip(),
                "pitaka_division": (row.get("pitaka_division") or "").strip(),
                "section_key": (row.get("section_key") or "").strip(),
            }
    return lookup


def validate_raw(raw: dict[str, Any], catalog_lookup: dict[str, dict[str, str]]) -> None:
    if not isinstance(raw, dict):
        raise ValueError("Raw pilot file must be a JSON object.")

    texts = raw.get("texts")
    if not isinstance(texts, list):
        raise ValueError("Raw pilot file must contain a texts array.")
    if not 4 <= len(texts) <= 6:
        raise ValueError(f"Expected 4-6 core texts, found {len(texts)}.")

    seen_segments: set[str] = set()
    for text in texts:
        if not isinstance(text, dict):
            raise ValueError("Each texts[] item must be an object.")

        work_id = (text.get("work_id") or "").strip()
        canonical_code = (text.get("canonical_code") or "").strip()
        import_scope = (text.get("import_scope") or "").strip()
        text_version = text.get("text_version")
        segments = text.get("segments")
        person_roles = text.get("person_roles")
        structural_units = text.get("structural_units")

        if not work_id or not canonical_code:
            raise ValueError("Each text must include work_id and canonical_code.")
        if import_scope not in {"excerpt", "full"}:
            raise ValueError(f"{work_id}: import_scope must be excerpt or full.")
        if not isinstance(text_version, dict):
            raise ValueError(f"{work_id}: text_version must be an object.")
        if not isinstance(person_roles, list):
            raise ValueError(f"{work_id}: person_roles must be a list.")
        if not isinstance(structural_units, list):
            raise ValueError(f"{work_id}: structural_units must be a list.")
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"{work_id}: segments must be a non-empty list.")

        catalog_row = catalog_lookup.get(canonical_code)
        if not catalog_row:
            raise ValueError(f"{work_id}: canonical code {canonical_code} is not present in the Han catalog CSV.")
        if catalog_row["work_id"] != work_id:
            raise ValueError(
                f"{work_id}: catalog CSV maps {canonical_code} to {catalog_row['work_id']}, not the provided work_id."
            )

        text_version_id = (text_version.get("id") or "").strip()
        text_version_slug = (text_version.get("slug") or "").strip()
        if not text_version_id or not text_version_slug:
            raise ValueError(f"{work_id}: text_version must include id and slug.")

        segment_keys: set[str] = set()
        for segment in segments:
            if not isinstance(segment, dict):
                raise ValueError(f"{work_id}: each segment must be an object.")
            segment_key = (segment.get("segment_key") or "").strip()
            content = (segment.get("content") or "").strip()
            if not segment_key or not content:
                raise ValueError(f"{work_id}: every segment needs segment_key and content.")
            if segment_key in segment_keys:
                raise ValueError(f"{work_id}: duplicate segment_key {segment_key}.")
            segment_keys.add(segment_key)
            seen_segments.add(f"{work_id}:{segment_key}")

    if len(seen_segments) < len(texts) * 2:
        raise ValueError("Expected at least two segments per selected text.")


def normalize_bundle(raw: dict[str, Any], catalog_lookup: dict[str, dict[str, str]]) -> dict[str, Any]:
    normalized_texts: list[dict[str, Any]] = []
    flat_segments: list[dict[str, Any]] = []
    flat_concept_tags: list[dict[str, Any]] = []

    for text in raw["texts"]:
        canonical_code = text["canonical_code"]
        catalog_row = catalog_lookup[canonical_code]
        text_version = text["text_version"]
        text_id = text["work_id"]
        text_version_id = text_version["id"]

        normalized_text = {
            "work_id": text_id,
            "work_slug": catalog_row["work_slug"],
            "canonical_code": canonical_code,
            "import_scope": text["import_scope"],
            "catalog_reference": {
                "work_id": catalog_row["work_id"],
                "work_slug": catalog_row["work_slug"],
                "title": catalog_row["title"],
                "pitaka_division": catalog_row["pitaka_division"],
                "section_key": catalog_row["section_key"],
            },
            "text_version": text_version,
            "person_roles": text.get("person_roles", []),
            "structural_units": text.get("structural_units", []),
            "segments": text.get("segments", []),
            "segment_concept_tags": text.get("segment_concept_tags", []),
        }
        normalized_text["segment_count"] = len(normalized_text["segments"])
        normalized_text["person_role_count"] = len(normalized_text["person_roles"])
        normalized_text["structural_unit_count"] = len(normalized_text["structural_units"])

        normalized_texts.append(normalized_text)

        for segment in normalized_text["segments"]:
            segment_id = f"{text_version_id}-{segment['segment_key'].lower()}"
            flat_segments.append(
                {
                    "id": segment_id,
                    "work_id": text_id,
                    "work_slug": catalog_row["work_slug"],
                    "canonical_code": canonical_code,
                    "text_version_id": text_version_id,
                    "segment_key": segment["segment_key"],
                    "position": segment["position"],
                    "title": segment.get("title"),
                    "structural_unit_id": segment.get("structural_unit_id"),
                    "content": segment["content"],
                    "content_gloss": segment.get("content_gloss"),
                    "note": segment.get("note"),
                    "char_count": len(segment["content"]),
                }
            )

        for tag in normalized_text["segment_concept_tags"]:
            flat_concept_tags.append(
                {
                    "work_id": text_id,
                    "text_version_id": text_version_id,
                    "segment_key": tag["segment_key"],
                    "segment_concept_tag_slug": tag["concept_tag_slug"],
                    "segment_concept_tag_label": tag["concept_tag_label"],
                    "confidence": tag.get("confidence", 1.0),
                    "note": tag.get("note"),
                }
            )

    segment_tags: dict[str, set[str]] = {}
    for tag in flat_concept_tags:
        segment_id = f"{tag['text_version_id']}-{tag['segment_key'].lower()}"
        segment_tags.setdefault(segment_id, set()).add(tag["segment_concept_tag_slug"])

    parallel_candidates: list[dict[str, Any]] = []
    for left, right in combinations(flat_segments, 2):
        if left["work_id"] == right["work_id"]:
            continue
        left_tags = segment_tags.get(left["id"], set())
        right_tags = segment_tags.get(right["id"], set())
        shared = sorted(left_tags.intersection(right_tags))
        if not shared:
            continue
        if not any(tag in ANCHOR_TAGS for tag in shared):
            continue
        parallel_candidates.append(
            {
                "id": f"parallel-{left['id']}-{right['id']}",
                "source_segment_id": left["id"],
                "target_segment_id": right["id"],
                "source_work_id": left["work_id"],
                "target_work_id": right["work_id"],
                "shared_concepts": shared,
                "shared_count": len(shared),
                "relation_type": "conceptual_parallel",
                "note": "Derived from overlapping curated concept tags in the pilot asset.",
            }
        )

    parallel_candidates.sort(key=lambda item: (-item["shared_count"], item["id"]))

    concept_index: dict[str, dict[str, Any]] = {}
    for tag in flat_concept_tags:
        slug = tag["segment_concept_tag_slug"]
        entry = concept_index.setdefault(
            slug,
            {
                "slug": slug,
                "label": tag["segment_concept_tag_label"],
                "segment_count": 0,
                "works": set(),
            },
        )
        entry["segment_count"] += 1
        entry["works"].add(tag["work_id"])

    concept_index_rows = [
        {**entry, "works": sorted(entry["works"])}
        for entry in sorted(concept_index.values(), key=lambda item: item["slug"])
    ]

    return {
        "metadata": raw["metadata"],
        "source": raw["source"],
        "catalog_alignment": {
            "catalog_source": str(DEFAULT_CATALOG_PATH),
            "selected_text_count": len(normalized_texts),
            "selected_work_ids": [item["work_id"] for item in normalized_texts],
        },
        "texts": normalized_texts,
        "segments": flat_segments,
        "segment_concept_tags": flat_concept_tags,
        "concept_index": concept_index_rows,
        "parallel_candidates": parallel_candidates,
        "statistics": {
            "text_count": len(normalized_texts),
            "segment_count": len(flat_segments),
            "concept_tag_rows": len(flat_concept_tags),
            "parallel_candidate_count": len(parallel_candidates),
        },
    }


def write_bundle(bundle: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a processed bundle from the Han core texts pilot JSON.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    args = parser.parse_args()

    raw = load_json(args.source)
    catalog_lookup = load_catalog_lookup(args.catalog)
    validate_raw(raw, catalog_lookup)
    bundle = normalize_bundle(raw, catalog_lookup)
    bundle_path = write_bundle(bundle, args.output)

    print(f"Bundle written to: {bundle_path}")
    print(f"Texts: {len(bundle['texts'])}")
    print(f"Segments: {len(bundle['segments'])}")
    print(f"Concept tag rows: {len(bundle['segment_concept_tags'])}")
    print(f"Parallel candidates: {len(bundle['parallel_candidates'])}")


if __name__ == "__main__":
    main()
