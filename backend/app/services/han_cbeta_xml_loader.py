from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR, settings
from backend.app.models import (
    CitationLink,
    EmbeddingIndexMetadata,
    ParallelLink,
    Person,
    Segment,
    Source,
    StructuralUnit,
    TextVersion,
    TextVersionPersonRole,
    Work,
)
from backend.app.services.seed_utils import load_json_payload


HAN_CBETA_SOURCE_ID = "source-han-cbeta-xml-p5"
TEI_NS = "http://www.tei-c.org/ns/1.0"
CB_NS = "http://www.cbeta.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"tei": TEI_NS, "cb": CB_NS}
TEI_BODY_TAG = f"{{{TEI_NS}}}body"
TEI_P_TAG = f"{{{TEI_NS}}}p"
TEI_L_TAG = f"{{{TEI_NS}}}l"
CB_DIV_TAG = f"{{{CB_NS}}}div"
CB_JUAN_TAG = f"{{{CB_NS}}}juan"
CB_JHEAD_TAG = f"{{{CB_NS}}}jhead"
CB_MILESTONE_TAG = f"{{{CB_NS}}}milestone"
IGNORED_TAGS = {
    f"{{{TEI_NS}}}note",
    f"{{{TEI_NS}}}app",
    f"{{{TEI_NS}}}lem",
    f"{{{TEI_NS}}}rdg",
}
EXCLUDED_DIVISION_TYPES = {
    "xu",
    "w",
    "apparatus",
    "tt",
    "cbeta-notes",
    "taisho-notes",
    "add-notes",
    "rest-notes",
}


def load_han_cbeta_manifest(path: Path | None = None) -> dict[str, Any]:
    payload_path = Path(path or settings.han_cbeta_manifest_path)
    return load_json_payload(payload_path)


def _upsert_person(session: Session, person_record: dict[str, Any]) -> None:
    existing = session.get(Person, person_record["id"])
    if existing:
        for key, value in person_record.items():
            setattr(existing, key, value)
        return
    session.add(Person(**person_record))


def _resolve_data_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (ROOT_DIR / candidate).resolve()


def _relative_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_xml_paths(text_item: dict[str, Any]) -> list[Path]:
    raw_paths = text_item.get("xml_paths")
    if raw_paths is None:
        raw_path = text_item.get("xml_path")
        if raw_path is None:
            raise ValueError(f"Manifest item is missing xml_path/xml_paths for {text_item['work_id']}")
        raw_paths = [raw_path]

    resolved_paths = [_resolve_data_path(str(path_value)) for path_value in raw_paths]
    if not resolved_paths:
        raise ValueError(f"Manifest item has no XML sources for {text_item['work_id']}")
    return resolved_paths


def _resolve_display_urls(text_item: dict[str, Any], expected_count: int) -> list[str | None]:
    raw_urls = text_item.get("display_urls")
    if raw_urls is None:
        raw_url = text_item.get("display_url")
        raw_urls = [raw_url] if raw_url else []

    display_urls = [str(url_value) if url_value else None for url_value in raw_urls]
    if not display_urls:
        return [None] * expected_count
    if len(display_urls) == 1 and expected_count > 1:
        return display_urls * expected_count
    if len(display_urls) != expected_count:
        raise ValueError(
            f"Manifest display URL count does not match XML path count for {text_item['work_id']}: "
            f"{len(display_urls)} != {expected_count}"
        )
    return display_urls


def _stable_segment_id(canonical_code: str, position: int) -> str:
    return f"seg-cbeta-{canonical_code.lower()}-{position:03d}"


def _segment_key(canonical_code: str, position: int) -> str:
    return f"{canonical_code}-CBETA-{position:03d}"


def _build_char_normalization_map(root: ET.Element) -> dict[str, str]:
    char_map: dict[str, str] = {}
    for char in root.findall(".//tei:charDecl/tei:char", NS):
        char_id = char.attrib.get(f"{{{XML_NS}}}id")
        if not char_id:
            continue
        normalized_value: str | None = None
        for char_prop in char.findall("tei:charProp", NS):
            local_name = char_prop.findtext("tei:localName", default="", namespaces=NS).strip().lower()
            if local_name == "normalized form":
                normalized_value = char_prop.findtext("tei:value", default="", namespaces=NS).strip() or None
                break
        if normalized_value:
            char_map[f"#{char_id}"] = normalized_value
    return char_map


def _collect_text(node: ET.Element, char_map: dict[str, str]) -> str:
    parts: list[str] = []
    if node.tag not in IGNORED_TAGS and node.text:
        parts.append(node.text)

    for child in list(node):
        if child.tag in IGNORED_TAGS:
            if child.tail:
                parts.append(child.tail)
            continue

        if child.tag == f"{{{TEI_NS}}}g":
            ref = child.attrib.get("ref")
            glyph_text = (child.text or "").strip()
            if glyph_text:
                parts.append(glyph_text)
            elif ref and ref in char_map:
                parts.append(char_map[ref])
        else:
            parts.append(_collect_text(child, char_map))

        if child.tail:
            parts.append(child.tail)

    return "".join(parts)


def _clean_text(text: str) -> str:
    cleaned = text.replace("\r", "").replace("\n", "").replace("\t", "")
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    return cleaned.strip()


def _normalized_search_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _normalize_juan_number(raw_number: str | None, fallback: int) -> tuple[int, str]:
    match = re.search(r"\d+", raw_number or "")
    if match:
        number = int(match.group())
    else:
        number = fallback
    return number, f"{number:03d}"


def _normalize_pin_title(raw_title: str | None) -> str | None:
    if not raw_title:
        return None
    cleaned = re.sub(r"^\d+\s*", "", raw_title).strip()
    return cleaned or raw_title.strip() or None


def _extract_pin_heading(node: ET.Element, char_map: dict[str, str]) -> tuple[str | None, str | None]:
    mulu = node.find("cb:mulu", NS)
    if mulu is not None:
        raw_title = _clean_text(_collect_text(mulu, char_map))
        return mulu.attrib.get("n"), _normalize_pin_title(raw_title)

    head = node.find("tei:head", NS)
    if head is not None:
        return None, _normalize_pin_title(_clean_text(_collect_text(head, char_map)))

    return None, None


def _active_division_type(div_stack: list[str]) -> str | None:
    if not div_stack or any(item in EXCLUDED_DIVISION_TYPES for item in div_stack):
        return None
    for item in reversed(div_stack):
        if item:
            return item
    return "body"


def _parse_cbeta_xml(xml_path: Path) -> dict[str, Any]:
    # Use defusedxml for secure XML parsing with XXE protection
    tree = ET.parse(xml_path)
    root = tree.getroot()
    char_map = _build_char_normalization_map(root)
    body = root.find(".//tei:body", NS)
    if body is None:
        raise ValueError(f"No TEI body found in {xml_path}")

    juan_units: dict[str, dict[str, Any]] = {}
    pin_units: dict[str, dict[str, Any]] = {}
    paragraphs: list[dict[str, Any]] = []
    div_stack: list[str] = []
    current_juan_key: str | None = None
    current_pin_key: str | None = None
    pending_juan_number: str | None = None
    juan_pin_counts: dict[str, int] = {}

    def ensure_juan(raw_number: str | None = None, *, title: str | None = None) -> str:
        nonlocal current_pin_key, pending_juan_number
        number, key = _normalize_juan_number(raw_number or pending_juan_number, len(juan_units) + 1)
        juan_record = juan_units.get(key)
        if juan_record is None:
            juan_record = {
                "key": key,
                "number": number,
                "label": f"卷{number}",
                "title": title or f"卷{number}",
                "position": len(juan_units) + 1,
            }
            juan_units[key] = juan_record
        elif title and juan_record.get("title") == juan_record.get("label"):
            juan_record["title"] = title
        current_pin_key = None
        pending_juan_number = None
        return key

    def start_pin(raw_title: str | None = None, *, raw_number: str | None = None) -> str:
        nonlocal current_juan_key, current_pin_key
        if current_juan_key is None:
            current_juan_key = ensure_juan("1")

        pin_title = _normalize_pin_title(raw_title)
        existing_pin = pin_units.get(current_pin_key) if current_pin_key else None
        if existing_pin and existing_pin["juan_key"] == current_juan_key:
            existing_title = existing_pin.get("title")
            if pin_title is None or pin_title == existing_title:
                return existing_pin["key"]

        next_position = juan_pin_counts.get(current_juan_key, 0) + 1
        juan_pin_counts[current_juan_key] = next_position
        pin_key = f"{current_juan_key}-{next_position:03d}"
        pin_units[pin_key] = {
            "key": pin_key,
            "juan_key": current_juan_key,
            "number": raw_number,
            "label": f"品{raw_number}" if raw_number else f"品{next_position}",
            "title": pin_title or f"品{next_position}",
            "position": next_position,
        }
        current_pin_key = pin_key
        return pin_key

    def walk(node: ET.Element) -> None:
        nonlocal current_juan_key, current_pin_key, pending_juan_number

        if node.tag == CB_MILESTONE_TAG and node.attrib.get("unit") == "juan":
            pending_juan_number = node.attrib.get("n")

        if node.tag == CB_JUAN_TAG and node.attrib.get("fun") == "open":
            jhead = node.find("cb:jhead", NS)
            juan_title = _clean_text(_collect_text(jhead if jhead is not None else node, char_map)) or None
            current_juan_key = ensure_juan(node.attrib.get("n"), title=juan_title)

        if node.tag == CB_JHEAD_TAG and node.attrib.get("type") == "pin":
            pin_title = _clean_text(_collect_text(node, char_map)) or None
            current_pin_key = start_pin(pin_title)
            return

        if node.tag == CB_DIV_TAG:
            div_type = (node.attrib.get("type") or "").strip()
            div_stack.append(div_type)
            previous_pin_key = current_pin_key
            if div_type == "pin":
                pin_number, pin_title = _extract_pin_heading(node, char_map)
                current_pin_key = start_pin(pin_title, raw_number=pin_number)
            for child in list(node):
                walk(child)
            div_stack.pop()
            if div_type == "pin":
                current_pin_key = previous_pin_key
            return

        if node.tag in {TEI_P_TAG, TEI_L_TAG}:
            division_type = _active_division_type(div_stack)
            if division_type:
                if current_juan_key is None:
                    current_juan_key = ensure_juan("1")

                content = _clean_text(_collect_text(node, char_map))
                if content:
                    preview = content[:20].strip()
                    xml_id = node.attrib.get(f"{{{XML_NS}}}id")
                    cbeta_place = node.attrib.get(f"{{{CB_NS}}}place")
                    juan_record = juan_units[current_juan_key]
                    segment_kind = "paragraph" if node.tag == TEI_P_TAG else "verse_line"
                    paragraphs.append(
                        {
                            "position": len(paragraphs) + 1,
                            "title": f"{preview}..." if len(content) > 20 else preview,
                            "content": content,
                            "normalized_content": _normalized_search_text(content),
                            "juan_key": current_juan_key,
                            "metadata_json": {
                                "xml_id": xml_id,
                                "cbeta_place": cbeta_place,
                                "xml_path": _relative_display_path(xml_path),
                                "source_scope": "official_xml",
                                "division_type": division_type,
                                "juan_number": juan_record["number"],
                                "juan_label": juan_record["label"],
                                "segment_kind": segment_kind,
                            },
                        }
                    )
                    if current_pin_key:
                        pin_record = pin_units[current_pin_key]
                        paragraphs[-1]["pin_key"] = current_pin_key
                        paragraphs[-1]["metadata_json"]["pin_label"] = pin_record["label"]
                        paragraphs[-1]["metadata_json"]["pin_title"] = pin_record["title"]
            return

        for child in list(node):
            walk(child)

    walk(body)
    if not paragraphs:
        raise ValueError(f"No main-body paragraphs found in {xml_path}")

    return {
        "juan_units": sorted(juan_units.values(), key=lambda item: item["position"]),
        "pin_units": sorted(
            pin_units.values(),
            key=lambda item: (item["juan_key"], item["position"], item["label"]),
        ),
        "paragraphs": paragraphs,
    }


def _merge_parsed_cbeta_xml_documents(xml_paths: list[Path]) -> dict[str, Any]:
    merged_juan_units: dict[str, dict[str, Any]] = {}
    merged_pin_units: list[dict[str, Any]] = []
    merged_paragraphs: list[dict[str, Any]] = []

    for xml_path in xml_paths:
        parsed_text = _parse_cbeta_xml(xml_path)
        for juan_record in parsed_text["juan_units"]:
            juan_key = juan_record["key"]
            existing = merged_juan_units.get(juan_key)
            if existing is None:
                merged_juan_units[juan_key] = dict(juan_record)
            elif existing.get("title") == existing.get("label") and juan_record.get("title"):
                existing["title"] = juan_record["title"]

        merged_pin_units.extend(dict(pin_record) for pin_record in parsed_text["pin_units"])

        for paragraph in parsed_text["paragraphs"]:
            merged_paragraphs.append(
                {
                    **paragraph,
                    "position": len(merged_paragraphs) + 1,
                }
            )

    if not merged_paragraphs:
        raise ValueError("No main-body paragraphs found across the configured CBETA XML sources")

    ordered_juan_units = sorted(
        merged_juan_units.values(),
        key=lambda item: (item["number"], item["position"]),
    )
    for index, juan_record in enumerate(ordered_juan_units, start=1):
        juan_record["position"] = index

    ordered_pin_units: list[dict[str, Any]] = []
    for juan_record in ordered_juan_units:
        juan_pins = sorted(
            (item for item in merged_pin_units if item["juan_key"] == juan_record["key"]),
            key=lambda item: (item["position"], item["label"]),
        )
        for index, pin_record in enumerate(juan_pins, start=1):
            ordered_pin_units.append(
                {
                    **pin_record,
                    "position": index,
                }
            )

    return {
        "juan_units": ordered_juan_units,
        "pin_units": ordered_pin_units,
        "paragraphs": merged_paragraphs,
    }


def clear_han_cbeta_xml_data(session: Session, *, source_id: str = HAN_CBETA_SOURCE_ID) -> None:
    text_versions = session.scalars(select(TextVersion).where(TextVersion.source_id == source_id)).all()
    if not text_versions:
        session.query(Source).filter(Source.id == source_id).delete(synchronize_session=False)
        return

    text_version_ids = [item.id for item in text_versions]
    work_ids = sorted({item.work_id for item in text_versions})
    structural_unit_ids = session.scalars(
        select(StructuralUnit.id).where(StructuralUnit.text_version_id.in_(text_version_ids))
    ).all()
    segment_ids = session.scalars(select(Segment.id).where(Segment.text_version_id.in_(text_version_ids))).all()

    if segment_ids:
        session.query(EmbeddingIndexMetadata).filter(
            EmbeddingIndexMetadata.owner_type == "segment",
            EmbeddingIndexMetadata.owner_id.in_(segment_ids),
        ).delete(synchronize_session=False)
        session.query(ParallelLink).filter(
            or_(ParallelLink.source_segment_id.in_(segment_ids), ParallelLink.target_segment_id.in_(segment_ids))
        ).delete(synchronize_session=False)
        session.query(CitationLink).filter(
            or_(CitationLink.source_segment_id.in_(segment_ids), CitationLink.target_segment_id.in_(segment_ids))
        ).delete(synchronize_session=False)
        session.query(Segment).filter(Segment.id.in_(segment_ids)).delete(synchronize_session=False)

    if structural_unit_ids:
        session.query(StructuralUnit).filter(StructuralUnit.id.in_(structural_unit_ids)).delete(
            synchronize_session=False
        )

    session.query(TextVersionPersonRole).filter(
        TextVersionPersonRole.text_version_id.in_(text_version_ids)
    ).delete(synchronize_session=False)
    session.query(TextVersion).filter(TextVersion.id.in_(text_version_ids)).delete(synchronize_session=False)
    session.query(Source).filter(Source.id == source_id).delete(synchronize_session=False)

    if work_ids:
        remaining_fulltext_work_ids = set(
            session.scalars(
                select(TextVersion.work_id).where(
                    TextVersion.work_id.in_(work_ids),
                    TextVersion.is_catalog_only.is_(False),
                )
            ).all()
        )
        for work_id in work_ids:
            work = session.get(Work, work_id)
            if work and work_id not in remaining_fulltext_work_ids:
                work.is_catalog_only = True
                work.is_sample = True


def seed_han_cbeta_xml_texts(
    session: Session,
    *,
    force: bool = False,
    manifest_path: Path | None = None,
) -> bool:
    payload_path = Path(manifest_path or settings.han_cbeta_manifest_path)
    if not payload_path.exists():
        return False

    payload = load_han_cbeta_manifest(payload_path)
    source_record = payload["source"]
    source_id = source_record["id"]

    existing = session.scalar(select(Source.id).where(Source.id == source_id))
    if existing and not force:
        return False
    if force:
        clear_han_cbeta_xml_data(session, source_id=source_id)

    source = session.get(Source, source_id)
    if source:
        for key, value in source_record.items():
            setattr(source, key, value)
    else:
        session.add(Source(**source_record))

    for text_item in payload.get("texts", []):
        work = session.get(Work, text_item["work_id"])
        if not work:
            raise ValueError(f"Unknown work_id in Han CBETA manifest: {text_item['work_id']}")

        xml_paths = _resolve_xml_paths(text_item)
        display_urls = _resolve_display_urls(text_item, len(xml_paths))
        display_url_map = {
            _relative_display_path(xml_path): display_url
            for xml_path, display_url in zip(xml_paths, display_urls)
        }
        for xml_path in xml_paths:
            if not xml_path.exists():
                raise FileNotFoundError(f"Missing CBETA XML file: {xml_path}")

        work.is_catalog_only = False
        work.is_sample = False
        note_suffix = "已接入官方 CBETA XML 正文版本。"
        existing_note = (work.catalog_note or "").strip()
        if note_suffix not in existing_note:
            work.catalog_note = f"{existing_note} {note_suffix}".strip()

        text_version_record = dict(text_item["text_version"])
        text_version_record["work_id"] = work.id
        text_version_record["language_id"] = text_version_record.get("language_id") or "lang-lzh"
        text_version_record["source_id"] = source_id
        text_version_record["is_sample"] = False
        text_version_record["is_catalog_only"] = False
        text_version_record["sample_note"] = None
        session.add(TextVersion(**text_version_record))

        text_version_id = text_version_record["id"]
        for role_record in text_item.get("person_roles", []):
            person_id = role_record["person_id"]
            if not session.get(Person, person_id):
                _upsert_person(
                    session,
                    {
                        "id": person_id,
                        "slug": person_id.replace("person-", ""),
                        "display_name": role_record.get("display_name") or person_id,
                        "native_name": role_record.get("native_name"),
                        "tradition_affiliation": "汉传",
                        "role_summary": role_record.get("role", "translator"),
                        "note": "Created from Han CBETA XML manifest role assignment.",
                    },
                )
            session.add(
                TextVersionPersonRole(
                    text_version_id=text_version_id,
                    person_id=person_id,
                    role=role_record["role"],
                    note=role_record.get("note"),
                )
            )

        parsed_text = _merge_parsed_cbeta_xml_documents(xml_paths)

        root_unit_id = f"su-{text_version_id}-root"
        session.add(
            StructuralUnit(
                id=root_unit_id,
                text_version_id=text_version_id,
                parent_id=None,
                unit_type="text",
                label="全文",
                title=text_version_record["title"],
                position=1,
                depth=0,
                path="text",
            )
        )

        juan_unit_ids: dict[str, str] = {}
        for juan_record in parsed_text["juan_units"]:
            juan_unit_id = f"su-{text_version_id}-juan-{juan_record['key']}"
            juan_unit_ids[juan_record["key"]] = juan_unit_id
            session.add(
                StructuralUnit(
                    id=juan_unit_id,
                    text_version_id=text_version_id,
                    parent_id=root_unit_id,
                    unit_type="juan",
                    label=juan_record["label"],
                    title=juan_record["title"],
                    position=juan_record["position"],
                    depth=1,
                    path=f"text/juan-{juan_record['key']}",
                )
            )

        pin_unit_ids: dict[str, str] = {}
        for pin_record in parsed_text["pin_units"]:
            pin_unit_id = f"su-{text_version_id}-pin-{pin_record['key']}"
            pin_unit_ids[pin_record["key"]] = pin_unit_id
            session.add(
                StructuralUnit(
                    id=pin_unit_id,
                    text_version_id=text_version_id,
                    parent_id=juan_unit_ids[pin_record["juan_key"]],
                    unit_type="pin",
                    label=pin_record["label"],
                    title=pin_record["title"],
                    position=pin_record["position"],
                    depth=2,
                    path=f"text/juan-{pin_record['juan_key']}/pin-{pin_record['position']:03d}",
                )
            )

        for paragraph in parsed_text["paragraphs"]:
            position = paragraph["position"]
            content = paragraph["content"]
            metadata_json = dict(paragraph["metadata_json"])
            metadata_json["display_url"] = display_url_map.get(metadata_json["xml_path"])
            if len(display_urls) > 1:
                metadata_json["display_urls"] = [url for url in display_urls if url]
            metadata_json["canonical_code"] = text_item["canonical_code"]
            structural_unit_id = juan_unit_ids[paragraph["juan_key"]]
            if paragraph.get("pin_key"):
                structural_unit_id = pin_unit_ids[paragraph["pin_key"]]

            session.add(
                Segment(
                    id=_stable_segment_id(text_item["canonical_code"], position),
                    text_version_id=text_version_id,
                    structural_unit_id=structural_unit_id,
                    segment_key=_segment_key(text_item["canonical_code"], position),
                    title=paragraph["title"],
                    content=content,
                    normalized_content=paragraph["normalized_content"],
                    note="Imported from the official CBETA XML P5 main scripture division.",
                    position=position,
                    char_count=len(content),
                    metadata_json=metadata_json,
                )
            )

    session.commit()
    return True
