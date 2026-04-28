from __future__ import annotations

import csv
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from backend.app.core.config import ROOT_DIR, settings
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.services.han_catalog_loader import seed_han_catalog_snapshot
from backend.app.services.han_cbeta_xml_loader import seed_han_cbeta_xml_texts
from backend.app.services.han_core_text_loader import seed_han_core_texts
from backend.app.services.sample_loader import seed_sample_corpus


CBETA_WORKS_URL = "https://cbdata.dila.edu.tw/stable/works?canon=T&work_start=1&work_end=847"
CBETA_REFERER = "https://cbdata.dila.edu.tw/stable"
GITHUB_CONTENTS_TEMPLATE = "https://api.github.com/repos/cbeta-org/xml-p5/contents/T/{volume}"
GITHUB_RAW_TEMPLATE = "https://raw.githubusercontent.com/cbeta-org/xml-p5/master/T/{volume}/{stem}.xml"
GITHUB_DISPLAY_TEMPLATE = "https://github.com/cbeta-org/xml-p5/blob/master/T/{volume}/{stem}.xml"

BASE_CATALOG_PATH = ROOT_DIR / "data" / "raw" / "han" / "han_canon_catalog_seed.csv"
BASE_MANIFEST_PATH = ROOT_DIR / "data" / "raw" / "han" / "han_cbeta_xml_manifest.json"
GENERATED_CATALOG_PATH = ROOT_DIR / "data" / "processed" / "han" / "han_canon_catalog_seed_full_taisho_sutra.csv"
GENERATED_MANIFEST_PATH = ROOT_DIR / "data" / "processed" / "han" / "han_cbeta_xml_manifest_full_taisho_sutra.json"

SECTION_MAP = {
    "阿含部": ("agamas", "阿含部", "阿含部"),
    "本緣部": ("avadana", "本緣部", "本緣部"),
    "般若部": ("prajna", "般若部", "般若部"),
    "法華部": ("lotus", "法華部", "法華部"),
    "華嚴部": ("huayan", "華嚴部", "華嚴部"),
    "寶積部": ("ratnakuta", "寶積部", "寶積部"),
    "涅槃部": ("nirvana", "涅槃部", "涅槃部"),
    "大集部": ("mahasamnipata", "大集部", "大集部"),
    "經集部": ("sutra_misc", "經集部", "經集部"),
}


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Referer": CBETA_REFERER,
            "User-Agent": "BuddhaMVP/taisho-sutra-rebuild",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_volume_spec(volume_spec: str) -> list[str]:
    if ".." not in volume_spec:
        return [volume_spec]

    start, end = volume_spec.split("..", 1)
    prefix = start[:1]
    start_no = int(re.search(r"\d+", start).group())
    end_no = int(re.search(r"\d+", end).group())
    return [f"{prefix}{number:02d}" for number in range(start_no, end_no + 1)]


def _extract_numeric_order(canonical_code: str) -> int:
    match = re.search(r"\d+", canonical_code)
    return int(match.group()) if match else 0


def _load_existing_work_mappings(
    catalog_rows: list[dict[str, str]],
    manifest_payload: dict[str, Any],
) -> tuple[dict[str, str], set[str]]:
    catalog_code_to_slug = {
        row["canonical_code"].strip(): row["work_slug"].strip()
        for row in catalog_rows
        if row.get("canonical_code")
    }
    manifest_code_to_slug = {
        item["canonical_code"].strip(): item["work_id"].removeprefix("work-")
        for item in manifest_payload.get("texts", [])
        if item.get("canonical_code") and item.get("work_id")
    }
    combined = dict(catalog_code_to_slug)
    combined.update(manifest_code_to_slug)
    return combined, set(manifest_code_to_slug)


def _build_volume_file_index(works: list[dict[str, Any]]) -> dict[str, list[str]]:
    volumes = sorted(
        {
            volume
            for work in works
            for volume in _parse_volume_spec(work["vol"])
        }
    )
    index: dict[str, list[str]] = {}
    for volume in volumes:
        payload = _fetch_json(GITHUB_CONTENTS_TEMPLATE.format(volume=volume))
        index[volume] = sorted(item["name"] for item in payload if item["name"].endswith(".xml"))
    return index


def _resolve_file_stems(work: dict[str, Any], volume_index: dict[str, list[str]]) -> list[str]:
    work_token = work["work"][1:].lower()
    stems: list[str] = []
    for volume in _parse_volume_spec(work["vol"]):
        prefix = f"{volume.lower()}n{work_token}"
        for filename in volume_index.get(volume, []):
            if filename.lower().startswith(prefix) and filename.lower().endswith(".xml"):
                stems.append(filename[:-4])

    if stems:
        return sorted(set(stems))

    return [work["file"]]


def _build_generated_catalog_rows(
    works: list[dict[str, Any]],
    existing_work_slugs: dict[str, str],
    existing_catalog_codes: set[str],
) -> list[dict[str, str]]:
    category_positions: dict[str, int] = {}
    generated_rows: list[dict[str, str]] = []

    for work in sorted(works, key=lambda item: (_extract_numeric_order(item["work"]), item["work"])):
        canonical_code = work["work"]
        if canonical_code in existing_catalog_codes:
            continue

        orig_category = work["orig_category"]
        if orig_category not in SECTION_MAP:
            continue

        section_key, section_label, section_title = SECTION_MAP[orig_category]
        category_positions[orig_category] = category_positions.get(orig_category, 0) + 1
        work_slug = existing_work_slugs.get(canonical_code, canonical_code.lower())
        byline = (work.get("byline") or "").strip()
        note = "CBETA API 自动生成目录条目，等待正式 XML 导入。"
        if byline:
            note = f"{note} 署名：{byline}。"

        generated_rows.append(
            {
                "catalog_order": str(1000 + category_positions[orig_category]),
                "canonical_code": canonical_code,
                "work_slug": work_slug,
                "title": work["title"],
                "title_english": "",
                "title_transliterated": "",
                "genre": "sutra",
                "pitaka_division": "sutra",
                "section_key": section_key,
                "section_label": section_label,
                "section_title": section_title,
                "fascicle_count": str(work["juan"]),
                "volume_ref": work["vol"],
                "translator_slug": "",
                "translator_name": "",
                "translator_native_name": "",
                "translator_role": "",
                "notes": note,
            }
        )

    return generated_rows


def _build_generated_manifest(
    base_manifest: dict[str, Any],
    works: list[dict[str, Any]],
    existing_work_slugs: dict[str, str],
    existing_manifest_codes: set[str],
    volume_index: dict[str, list[str]],
) -> dict[str, Any]:
    payload = json.loads(json.dumps(base_manifest))
    payload["metadata"]["dataset_name"] = "Han CBETA XML Imports (Expanded Taisho Sutra Batch)"
    payload["metadata"]["version"] = "0.2.0"
    payload["metadata"]["notes"] = (
        "Combined official CBETA XML P5 import manifest including the expanded Taisho non-esoteric sutra batch."
    )

    for work in sorted(works, key=lambda item: (_extract_numeric_order(item["work"]), item["work"])):
        canonical_code = work["work"]
        if canonical_code in existing_manifest_codes:
            continue

        work_slug = existing_work_slugs.get(canonical_code, canonical_code.lower())
        stems = _resolve_file_stems(work, volume_index)
        xml_paths = [f"data/raw/han/cbeta_xml/{stem}.xml" for stem in stems]
        display_urls = [
            GITHUB_DISPLAY_TEMPLATE.format(volume=stem[:3], stem=stem)
            for stem in stems
        ]
        text_item: dict[str, Any] = {
            "work_id": f"work-{work_slug}",
            "canonical_code": canonical_code,
            "text_version": {
                "id": f"tv-{work_slug}-cbeta",
                "slug": f"{work_slug}-cbeta",
                "title": work["title"],
                "version_label": "CBETA XML P5 正式导入版",
                "script_note": "繁体汉文 / TEI P5",
                "date_note": None,
                "summary": (
                    f"Official CBETA XML P5 import for {work['title']}, segmented from the main body "
                    f"across {work['juan']} juan."
                ),
                "catalog_note": f"来源于 CBETA XML P5 官方仓库，保留目录编号 {canonical_code}。",
            },
            "person_roles": [],
        }

        if len(xml_paths) == 1:
            text_item["xml_path"] = xml_paths[0]
            text_item["display_url"] = display_urls[0]
        else:
            text_item["xml_paths"] = xml_paths
            text_item["display_urls"] = display_urls
            text_item["text_version"]["summary"] = (
                f"Official CBETA XML P5 import for {work['title']}, merged from {len(xml_paths)} XML source files "
                f"across {work['juan']} juan."
            )

        payload["texts"].append(text_item)

    return payload


def _download_manifest_xmls(manifest_payload: dict[str, Any]) -> None:
    for text_item in manifest_payload.get("texts", []):
        raw_paths = text_item.get("xml_paths") or [text_item["xml_path"]]
        for raw_path in raw_paths:
            output_path = ROOT_DIR / raw_path
            if output_path.exists():
                continue

            stem = output_path.stem
            volume = stem[:3]
            url = GITHUB_RAW_TEMPLATE.format(volume=volume, stem=stem)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, output_path)


def _write_catalog_csv(base_rows: list[dict[str, str]], generated_rows: list[dict[str, str]], output_path: Path) -> None:
    fieldnames = list(base_rows[0].keys())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(base_rows)
        writer.writerows(generated_rows)


def _write_manifest(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rebuild_database(catalog_source_path: Path, manifest_path: Path) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_sample_corpus(session)
        seed_han_catalog_snapshot(session, force=True, source_path=catalog_source_path, write_bundle=False)
        if settings.han_core_text_source_path.exists():
            seed_han_core_texts(session)
        seed_han_cbeta_xml_texts(session, manifest_path=manifest_path)


def main() -> None:
    base_catalog_rows = _read_csv_rows(BASE_CATALOG_PATH)
    base_manifest = _read_manifest(BASE_MANIFEST_PATH)
    existing_work_slugs, existing_manifest_codes = _load_existing_work_mappings(base_catalog_rows, base_manifest)
    existing_catalog_codes = {row["canonical_code"].strip() for row in base_catalog_rows if row.get("canonical_code")}

    works = _fetch_json(CBETA_WORKS_URL)["results"]
    works = [work for work in works if work.get("orig_category") in SECTION_MAP]
    volume_index = _build_volume_file_index(works)

    generated_rows = _build_generated_catalog_rows(works, existing_work_slugs, existing_catalog_codes)
    combined_manifest = _build_generated_manifest(
        base_manifest,
        works,
        existing_work_slugs,
        existing_manifest_codes,
        volume_index,
    )

    _write_catalog_csv(base_catalog_rows, generated_rows, GENERATED_CATALOG_PATH)
    _write_manifest(combined_manifest, GENERATED_MANIFEST_PATH)
    _download_manifest_xmls(combined_manifest)
    _rebuild_database(GENERATED_CATALOG_PATH, GENERATED_MANIFEST_PATH)

    print(f"Generated catalog CSV: {GENERATED_CATALOG_PATH}")
    print(f"Generated manifest JSON: {GENERATED_MANIFEST_PATH}")
    print(f"Added catalog rows: {len(generated_rows)}")
    print(f"Combined official XML texts: {len(combined_manifest.get('texts', []))}")


if __name__ == "__main__":
    main()
