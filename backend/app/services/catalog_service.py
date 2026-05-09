from __future__ import annotations

from collections import defaultdict
import html
import re
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models import (
    CatalogNode,
    CitationLink,
    Collection,
    ConceptTag,
    EmbeddingIndexMetadata,
    ParallelLink,
    Segment,
    SegmentConceptTag,
    StructuralUnit,
    TextUnitSummary,
    TextVersion,
    TextVersionPersonRole,
    Tradition,
    Work,
    WorkPersonRole,
)
from backend.app.services import concept_analysis_service, vector_service
from backend.app.services.han_catalog_pipeline import DIVISION_META, HAN_COLLECTION_ID


def build_preview(content: str, limit: int = 100) -> str:
    compact = " ".join(content.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}..."


def render_summary_markdown_html(summary: Optional[str]) -> str:
    if not summary:
        return ""

    def inline_markup(value: str) -> str:
        escaped = html.escape(value, quote=False)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
        return escaped

    blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_tag: Optional[str] = None

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            blocks.append("<p>" + "<br>".join(inline_markup(line) for line in paragraph_lines) + "</p>")
            paragraph_lines = []

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            blocks.append(f"</{list_tag}>")
            list_tag = None

    for raw_line in summary.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            close_list()
            continue
        if line.startswith("### "):
            flush_paragraph()
            close_list()
            blocks.append(f"<h4>{inline_markup(line[4:])}</h4>")
            continue
        if line.startswith("## "):
            flush_paragraph()
            close_list()
            blocks.append(f"<h3>{inline_markup(line[3:])}</h3>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            if list_tag != "ul":
                close_list()
                blocks.append("<ul>")
                list_tag = "ul"
            blocks.append(f"<li>{inline_markup(line[2:])}</li>")
            continue
        if re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            if list_tag != "ol":
                close_list()
                blocks.append("<ol>")
                list_tag = "ol"
            item_text = re.sub(r"^\d+\.\s+", "", line)
            blocks.append(f"<li>{inline_markup(item_text)}</li>")
            continue
        close_list()
        paragraph_lines.append(line)

    flush_paragraph()
    close_list()
    return "\n".join(blocks)


def serialize_person_roles(role_rows: list[WorkPersonRole | TextVersionPersonRole]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for role_row in role_rows:
        items.append(
            {
                "person_id": role_row.person.id,
                "display_name": role_row.person.display_name,
                "native_name": role_row.person.native_name,
                "role": role_row.role,
                "note": role_row.note,
            }
        )
    return items


def serialize_work_summary(work: Work) -> dict[str, Any]:
    has_full_text = any(not version.is_catalog_only for version in work.text_versions)
    full_text_versions = sorted(
        [version for version in work.text_versions if not version.is_catalog_only],
        key=lambda item: (item.is_sample, item.title),
    )
    primary_text_version = full_text_versions[0] if full_text_versions else None
    return {
        "id": work.id,
        "slug": work.slug,
        "title": work.title,
        "title_english": work.title_english,
        "genre": work.genre,
        "tradition_id": work.tradition.id,
        "tradition_name": work.tradition.name,
        "collection_id": work.collection.id,
        "collection_title": work.collection.title,
        "is_sample": work.is_sample,
        "text_version_count": len(work.text_versions),
        "pitaka_division": work.pitaka_division,
        "canonical_code": work.canonical_code,
        "fascicle_count": work.fascicle_count,
        "catalog_order": work.catalog_order,
        "is_catalog_only": work.is_catalog_only,
        "has_full_text": has_full_text,
        "full_text_version_count": len(full_text_versions),
        "primary_text_version_id": primary_text_version.id if primary_text_version else None,
        "primary_text_version_title": primary_text_version.title if primary_text_version else None,
    }


def serialize_text_version_summary(text_version: TextVersion) -> dict[str, Any]:
    return {
        "id": text_version.id,
        "slug": text_version.slug,
        "title": text_version.title,
        "version_label": text_version.version_label,
        "language_id": text_version.language.id,
        "language_name": text_version.language.name,
        "source_id": text_version.source.id if text_version.source else None,
        "source_title": text_version.source.title if text_version.source else None,
        "is_sample": text_version.is_sample,
        "sample_note": text_version.sample_note,
        "is_catalog_only": text_version.is_catalog_only,
        "catalog_note": text_version.catalog_note,
    }


def serialize_segment_summary(segment: Segment) -> dict[str, Any]:
    return {
        "id": segment.id,
        "segment_key": segment.segment_key,
        "title": segment.title,
        "position": segment.position,
        "is_sample": segment.text_version.work.is_sample,
        "work_title": segment.text_version.work.title,
        "text_version_title": segment.text_version.title,
        "tradition_name": segment.text_version.work.tradition.name,
        "language_name": segment.text_version.language.name,
        "content_preview": build_preview(segment.content),
    }


def serialize_text_unit_summary(summary_row: TextUnitSummary) -> dict[str, Any]:
    metadata = summary_row.metadata_json or {}
    return {
        "id": summary_row.id,
        "owner_type": summary_row.owner_type,
        "owner_id": summary_row.owner_id,
        "summary_kind": summary_row.summary_kind,
        "model": summary_row.model,
        "summary": summary_row.summary,
        "summary_html": render_summary_markdown_html(summary_row.summary),
        "summary_preview": build_preview(summary_row.summary, 260),
        "source_segment_count": summary_row.source_segment_count,
        "metadata": metadata,
        "title": metadata.get("title"),
        "created_at": summary_row.created_at.isoformat() if summary_row.created_at else None,
        "updated_at": summary_row.updated_at.isoformat() if summary_row.updated_at else None,
    }


def _latest_summary_map(
    session: Session,
    *,
    owner_type: str,
    owner_ids: list[str],
    summary_kind: str = "rag_context",
) -> dict[str, dict[str, Any]]:
    if not owner_ids:
        return {}

    rows = session.scalars(
        select(TextUnitSummary)
        .where(
            TextUnitSummary.owner_type == owner_type,
            TextUnitSummary.summary_kind == summary_kind,
            TextUnitSummary.owner_id.in_(owner_ids),
        )
        .order_by(TextUnitSummary.owner_id, TextUnitSummary.updated_at.desc(), TextUnitSummary.id.desc())
    ).all()

    summary_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.owner_id in summary_map:
            continue
        summary_map[row.owner_id] = serialize_text_unit_summary(row)
    return summary_map


def list_collections(session: Session, tradition_id: Optional[str] = None) -> list[dict[str, Any]]:
    stmt = select(Collection).options(selectinload(Collection.tradition)).order_by(Collection.title)
    if tradition_id:
        stmt = stmt.where(Collection.tradition_id == tradition_id)
    collections = session.scalars(stmt).all()
    return [
        {
            "id": collection.id,
            "slug": collection.slug,
            "title": collection.title,
            "tradition_id": collection.tradition.id,
            "tradition_name": collection.tradition.name,
            "is_sample": collection.is_sample,
            "description": collection.description,
        }
        for collection in collections
    ]


def list_works(
    session: Session,
    *,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    pitaka_division: Optional[str] = None,
    q: Optional[str] = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(Work)
        .options(
            selectinload(Work.tradition),
            selectinload(Work.collection),
            selectinload(Work.text_versions),
        )
        .order_by(Work.is_sample.asc(), Work.is_catalog_only.asc(), Work.title)
    )
    if language_id:
        stmt = stmt.join(Work.text_versions).where(TextVersion.language_id == language_id)
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    if collection_id:
        stmt = stmt.where(Work.collection_id == collection_id)
    if pitaka_division:
        stmt = stmt.where(Work.pitaka_division == pitaka_division)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Work.title.ilike(pattern),
                Work.title_english.ilike(pattern),
                Work.summary.ilike(pattern),
                Work.canonical_code.ilike(pattern),
            )
        )
    works = session.scalars(stmt).unique().all()
    return [serialize_work_summary(work) for work in works]


def get_work_detail(session: Session, work_id: str) -> Optional[dict[str, Any]]:
    stmt = (
        select(Work)
        .where(Work.id == work_id)
        .options(
            selectinload(Work.tradition),
            selectinload(Work.collection),
            selectinload(Work.person_roles).selectinload(WorkPersonRole.person),
            selectinload(Work.text_versions).selectinload(TextVersion.language),
            selectinload(Work.text_versions).selectinload(TextVersion.source),
        )
    )
    work = session.scalars(stmt).first()
    if not work:
        return None
    payload = serialize_work_summary(work)
    sorted_versions = sorted(
        work.text_versions,
        key=lambda item: (item.is_catalog_only, item.is_sample, item.title),
    )
    payload.update(
        {
            "title_transliterated": work.title_transliterated,
            "summary": work.summary,
            "authenticity_note": work.authenticity_note,
            "catalog_note": work.catalog_note,
            "person_roles": serialize_person_roles(work.person_roles),
            "text_versions": [serialize_text_version_summary(version) for version in sorted_versions],
        }
    )
    return payload


def _build_structure_tree(text_version: TextVersion) -> list[dict[str, Any]]:
    ordered_units = sorted(text_version.structural_units, key=lambda item: (item.depth, item.position, item.path))
    segment_map: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for segment in sorted(text_version.segments, key=lambda item: item.position):
        segment_map[segment.structural_unit_id].append(
            {
                "id": segment.id,
                "segment_key": segment.segment_key,
                "title": segment.title,
                "position": segment.position,
                "preview": build_preview(segment.content, 80),
            }
        )

    node_map: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for unit in ordered_units:
        node_map[unit.id] = {
            "id": unit.id,
            "unit_type": unit.unit_type,
            "label": unit.label,
            "title": unit.title,
            "path": unit.path,
            "depth": unit.depth,
            "position": unit.position,
            "child_units": [],
            "segments": segment_map.get(unit.id, []),
        }

    for unit in ordered_units:
        node = node_map[unit.id]
        if unit.parent_id and unit.parent_id in node_map:
            node_map[unit.parent_id]["child_units"].append(node)
        else:
            roots.append(node)

    return roots


def _build_structure_outline(structural_units: list[StructuralUnit]) -> list[dict[str, Any]]:
    ordered_units = sorted(structural_units, key=lambda item: (item.depth, item.position, item.path))
    node_map: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for unit in ordered_units:
        node_map[unit.id] = {
            "id": unit.id,
            "unit_type": unit.unit_type,
            "label": unit.label,
            "title": unit.title,
            "path": unit.path,
            "depth": unit.depth,
            "position": unit.position,
            "child_units": [],
        }

    for unit in ordered_units:
        node = node_map[unit.id]
        if unit.parent_id and unit.parent_id in node_map:
            node_map[unit.parent_id]["child_units"].append(node)
        else:
            roots.append(node)

    return roots


def _build_catalog_tree(nodes: list[CatalogNode]) -> list[dict[str, Any]]:
    ordered_nodes = sorted(nodes, key=lambda item: (item.depth, item.position, item.path))
    node_map: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for node in ordered_nodes:
        full_text_versions = []
        if node.work:
            full_text_versions = [item for item in node.work.text_versions if not item.is_catalog_only]
        node_map[node.id] = {
            "id": node.id,
            "node_type": node.node_type,
            "node_key": node.node_key,
            "label": node.label,
            "title": node.title,
            "pitaka_division": node.pitaka_division,
            "section_key": node.section_key,
            "path": node.path,
            "depth": node.depth,
            "position": node.position,
            "note": node.note,
            "is_terminal": node.is_terminal,
            "work_id": node.work.id if node.work else None,
            "work_title": node.work.title if node.work else None,
            "canonical_code": node.work.canonical_code if node.work else None,
            "fascicle_count": node.work.fascicle_count if node.work else None,
            "has_full_text": bool(full_text_versions),
            "full_text_version_id": full_text_versions[0].id if full_text_versions else None,
            "child_nodes": [],
        }

    for node in ordered_nodes:
        payload_node = node_map[node.id]
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id]["child_nodes"].append(payload_node)
        else:
            roots.append(payload_node)

    return roots


def list_text_versions(
    session: Session,
    *,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    work_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(TextVersion)
        .options(
            selectinload(TextVersion.language),
            selectinload(TextVersion.source),
            selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(TextVersion.work).selectinload(Work.collection),
        )
        .order_by(TextVersion.title)
    )
    joined_work = False
    if tradition_id or collection_id:
        stmt = stmt.join(TextVersion.work)
        joined_work = True
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    if collection_id:
        stmt = stmt.where(Work.collection_id == collection_id)
    if language_id:
        stmt = stmt.where(TextVersion.language_id == language_id)
    if work_id:
        if joined_work:
            stmt = stmt.where(Work.id == work_id)
        else:
            stmt = stmt.where(TextVersion.work_id == work_id)
    versions = session.scalars(stmt).unique().all()
    return [serialize_text_version_summary(version) for version in versions]


def get_text_version_detail(session: Session, text_version_id: str) -> Optional[dict[str, Any]]:
    stmt = (
        select(TextVersion)
        .where(TextVersion.id == text_version_id)
        .options(
            selectinload(TextVersion.language),
            selectinload(TextVersion.source),
            selectinload(TextVersion.person_roles).selectinload(TextVersionPersonRole.person),
            selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(TextVersion.work).selectinload(Work.collection),
            selectinload(TextVersion.structural_units),
            selectinload(TextVersion.segments),
        )
    )
    text_version = session.scalars(stmt).first()
    if not text_version:
        return None
    payload = serialize_text_version_summary(text_version)
    payload.update(
        {
            "work_id": text_version.work.id,
            "work_title": text_version.work.title,
            "tradition_id": text_version.work.tradition.id,
            "tradition_name": text_version.work.tradition.name,
            "collection_id": text_version.work.collection.id,
            "collection_title": text_version.work.collection.title,
            "summary": text_version.summary,
            "script_note": text_version.script_note,
            "language_script": text_version.language.script,
            "date_note": text_version.date_note,
            "source_url": text_version.source.url if text_version.source else None,
            "roles": serialize_person_roles(text_version.person_roles),
            "structure": _build_structure_tree(text_version),
        }
    )
    return payload


def get_text_version_page_detail(session: Session, text_version_id: str) -> Optional[dict[str, Any]]:
    stmt = (
        select(TextVersion)
        .where(TextVersion.id == text_version_id)
        .options(
            selectinload(TextVersion.language),
            selectinload(TextVersion.source),
            selectinload(TextVersion.person_roles).selectinload(TextVersionPersonRole.person),
            selectinload(TextVersion.work).selectinload(Work.tradition),
            selectinload(TextVersion.work).selectinload(Work.collection),
            selectinload(TextVersion.structural_units),
        )
    )
    text_version = session.scalars(stmt).first()
    if not text_version:
        return None
    payload = serialize_text_version_summary(text_version)
    payload.update(
        {
            "work_id": text_version.work.id,
            "work_title": text_version.work.title,
            "tradition_id": text_version.work.tradition.id,
            "tradition_name": text_version.work.tradition.name,
            "collection_id": text_version.work.collection.id,
            "collection_title": text_version.work.collection.title,
            "summary": text_version.summary,
            "script_note": text_version.script_note,
            "language_script": text_version.language.script,
            "date_note": text_version.date_note,
            "source_url": text_version.source.url if text_version.source else None,
            "roles": serialize_person_roles(text_version.person_roles),
            "segment_count": session.scalar(
                select(func.count(Segment.id)).where(Segment.text_version_id == text_version.id)
            )
            or 0,
            "gloss_segment_count": session.scalar(
                select(func.count(Segment.id)).where(
                    Segment.text_version_id == text_version.id,
                    Segment.content_gloss.is_not(None),
                )
            )
            or 0,
            "structure": _build_structure_outline(text_version.structural_units),
        }
    )
    return payload


def list_text_version_reading_segments(
    session: Session,
    *,
    text_version_id: str,
    structural_unit_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    stmt = select(Segment).where(Segment.text_version_id == text_version_id).order_by(Segment.position)
    
    if structural_unit_id:
        stmt = stmt.where(Segment.structural_unit_id == structural_unit_id)
    
    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    segments = session.scalars(stmt).all()
    return [
        {
            "id": segment.id,
            "segment_key": segment.segment_key,
            "title": segment.title,
            "position": segment.position,
            "content": segment.content,
            "content_gloss": segment.content_gloss,
        }
        for segment in segments
    ]


def count_text_version_segments(
    session: Session,
    *,
    text_version_id: str,
    structural_unit_id: Optional[str] = None,
) -> int:
    from sqlalchemy import func
    
    stmt = select(func.count(Segment.id)).where(Segment.text_version_id == text_version_id)
    if structural_unit_id:
        stmt = stmt.where(Segment.structural_unit_id == structural_unit_id)
    return session.scalar(stmt) or 0


def list_structural_units(
    session: Session,
    *,
    text_version_id: str,
    unit_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """获取文本版本的结构单元（如卷、章等）"""
    from sqlalchemy import select
    
    stmt = select(StructuralUnit).where(StructuralUnit.text_version_id == text_version_id).order_by(StructuralUnit.position)
    
    if unit_type:
        stmt = stmt.where(StructuralUnit.unit_type == unit_type)
    
    units = session.scalars(stmt).all()
    return [
        {
            "id": unit.id,
            "unit_type": unit.unit_type,
            "label": unit.label,
            "title": unit.title,
            "position": unit.position,
            "depth": unit.depth,
        }
        for unit in units
    ]


def get_generated_summary(
    session: Session,
    *,
    owner_type: str,
    owner_id: str,
    summary_kind: str = "rag_context",
) -> Optional[dict[str, Any]]:
    summary_map = _latest_summary_map(
        session,
        owner_type=owner_type,
        owner_ids=[owner_id],
        summary_kind=summary_kind,
    )
    return summary_map.get(owner_id)


def list_work_summary_entries(
    session: Session,
    *,
    tradition_id: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 160,
) -> list[dict[str, Any]]:
    stmt = (
        select(Work)
        .join(
            TextUnitSummary,
            and_(
                TextUnitSummary.owner_type == "work",
                TextUnitSummary.summary_kind == "rag_context",
                TextUnitSummary.owner_id == Work.id,
            ),
        )
        .options(
            selectinload(Work.tradition),
            selectinload(Work.collection),
            selectinload(Work.text_versions),
        )
        .order_by(Work.tradition_id, Work.title)
        .limit(limit)
    )
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Work.title.ilike(pattern),
                Work.title_english.ilike(pattern),
                Work.title_transliterated.ilike(pattern),
                Work.canonical_code.ilike(pattern),
            )
        )

    works = session.scalars(stmt).unique().all()
    work_ids = [item.id for item in works]
    summary_map = _latest_summary_map(session, owner_type="work", owner_ids=work_ids)

    unit_count_rows = []
    if work_ids:
        unit_count_rows = session.execute(
            select(TextVersion.work_id, func.count(TextUnitSummary.id))
            .join(StructuralUnit, StructuralUnit.id == TextUnitSummary.owner_id)
            .join(TextVersion, TextVersion.id == StructuralUnit.text_version_id)
            .where(
                TextUnitSummary.owner_type == "structural_unit",
                TextUnitSummary.summary_kind == "rag_context",
                TextVersion.work_id.in_(work_ids),
            )
            .group_by(TextVersion.work_id)
        ).all()
    unit_count_map = {work_id: int(count or 0) for work_id, count in unit_count_rows}

    entries: list[dict[str, Any]] = []
    for work in works:
        payload = serialize_work_summary(work)
        generated_summary = summary_map.get(work.id)
        payload.update(
            {
                "generated_summary": generated_summary,
                "generated_summary_preview": generated_summary["summary_preview"] if generated_summary else None,
                "unit_summary_count": unit_count_map.get(work.id, 0),
            }
        )
        entries.append(payload)
    return entries


def list_work_unit_summaries(
    session: Session,
    *,
    work_id: str,
    text_version_id: Optional[str] = None,
    unit_type: Optional[str] = "juan",
) -> list[dict[str, Any]]:
    stmt = (
        select(StructuralUnit, TextVersion)
        .join(TextVersion, TextVersion.id == StructuralUnit.text_version_id)
        .where(
            TextVersion.work_id == work_id,
            TextVersion.is_catalog_only.is_(False),
        )
        .order_by(TextVersion.title, StructuralUnit.position, StructuralUnit.id)
    )
    if text_version_id:
        stmt = stmt.where(TextVersion.id == text_version_id)
    if unit_type:
        stmt = stmt.where(StructuralUnit.unit_type == unit_type)

    rows = session.execute(stmt).all()
    unit_ids = [unit.id for unit, _ in rows]
    summary_map = _latest_summary_map(session, owner_type="structural_unit", owner_ids=unit_ids)

    items: list[dict[str, Any]] = []
    for unit, text_version in rows:
        summary_row = summary_map.get(unit.id)
        if not summary_row:
            continue
        items.append(
            {
                **summary_row,
                "text_version_id": text_version.id,
                "text_version_title": text_version.title,
                "unit_type": unit.unit_type,
                "label": unit.label,
                "unit_title": unit.title,
                "position": unit.position,
                "path": unit.path,
            }
        )
    return items


def list_segments(
    session: Session,
    *,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    work_id: Optional[str] = None,
    text_version_id: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    stmt = (
        select(Segment)
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
        )
        .order_by(Segment.position)
        .limit(limit)
    )
    joined_text_version = False
    if text_version_id:
        stmt = stmt.where(Segment.text_version_id == text_version_id)
    if work_id or tradition_id or collection_id:
        stmt = stmt.join(Segment.text_version).join(TextVersion.work)
        joined_text_version = True
        if work_id:
            stmt = stmt.where(Work.id == work_id)
        if tradition_id:
            stmt = stmt.where(Work.tradition_id == tradition_id)
        if collection_id:
            stmt = stmt.where(Work.collection_id == collection_id)
    if language_id:
        if not joined_text_version:
            stmt = stmt.join(Segment.text_version)
            joined_text_version = True
        stmt = stmt.where(TextVersion.language_id == language_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Segment.content.ilike(pattern),
                Segment.content_gloss.ilike(pattern),
                Segment.title.ilike(pattern),
            )
        )
    segments = session.scalars(stmt).unique().all()
    return [serialize_segment_summary(segment) for segment in segments]


def get_parallel_links_for_segment(session: Session, segment_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(ParallelLink)
        .where(or_(ParallelLink.source_segment_id == segment_id, ParallelLink.target_segment_id == segment_id))
        .options(
            selectinload(ParallelLink.source_segment)
            .selectinload(Segment.text_version)
            .selectinload(TextVersion.work)
            .selectinload(Work.tradition),
            selectinload(ParallelLink.source_segment).selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(ParallelLink.target_segment)
            .selectinload(Segment.text_version)
            .selectinload(TextVersion.work)
            .selectinload(Work.tradition),
            selectinload(ParallelLink.target_segment).selectinload(Segment.text_version).selectinload(TextVersion.language),
        )
        .order_by(ParallelLink.id)
    )
    links = session.scalars(stmt).all()
    payload: list[dict[str, Any]] = []
    for link in links:
        other_segment = link.target_segment if link.source_segment_id == segment_id else link.source_segment
        payload.append(
            {
                "link_id": link.id,
                "relation_type": link.relation_type,
                "confidence": link.confidence,
                "note": link.note,
                "target_segment_id": other_segment.id,
                "target_segment_key": other_segment.segment_key,
                "target_work_title": other_segment.text_version.work.title,
                "target_text_version_title": other_segment.text_version.title,
                "target_tradition_name": other_segment.text_version.work.tradition.name,
                "target_language_name": other_segment.text_version.language.name,
                "target_content_preview": build_preview(other_segment.content),
            }
        )
    return payload


def get_citation_links_for_segment(session: Session, segment_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(CitationLink)
        .where(or_(CitationLink.source_segment_id == segment_id, CitationLink.target_segment_id == segment_id))
        .options(
            selectinload(CitationLink.source_segment)
            .selectinload(Segment.text_version)
            .selectinload(TextVersion.work),
            selectinload(CitationLink.target_segment)
            .selectinload(Segment.text_version)
            .selectinload(TextVersion.work),
        )
        .order_by(CitationLink.id)
    )
    links = session.scalars(stmt).all()
    payload: list[dict[str, Any]] = []
    for link in links:
        other_segment = link.target_segment if link.source_segment_id == segment_id else link.source_segment
        payload.append(
            {
                "link_id": link.id,
                "relation_type": link.relation_type,
                "note": link.note,
                "target_segment_id": other_segment.id,
                "target_segment_key": other_segment.segment_key,
                "target_work_title": other_segment.text_version.work.title,
            }
        )
    return payload


def get_segment_detail(session: Session, segment_id: str) -> Optional[dict[str, Any]]:
    stmt = (
        select(Segment)
        .where(Segment.id == segment_id)
        .options(
            selectinload(Segment.structural_unit),
            selectinload(Segment.concept_links).selectinload(SegmentConceptTag.concept_tag),
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version)
            .selectinload(TextVersion.work)
            .selectinload(Work.tradition),
            selectinload(Segment.text_version)
            .selectinload(TextVersion.work)
            .selectinload(Work.collection),
        )
    )
    segment = session.scalars(stmt).first()
    if not segment:
        return None
    return {
        "id": segment.id,
        "segment_key": segment.segment_key,
        "position": segment.position,
        "title": segment.title,
        "content": segment.content,
        "content_gloss": segment.content_gloss,
        "note": segment.note,
        "metadata_json": segment.metadata_json,
        "work_id": segment.text_version.work.id,
        "work_title": segment.text_version.work.title,
        "text_version_id": segment.text_version.id,
        "text_version_title": segment.text_version.title,
        "language_name": segment.text_version.language.name,
        "language_script": segment.text_version.language.script,
        "tradition_id": segment.text_version.work.tradition.id,
        "tradition_name": segment.text_version.work.tradition.name,
        "collection_id": segment.text_version.work.collection.id,
        "collection_title": segment.text_version.work.collection.title,
        "structural_unit_path": segment.structural_unit.path if segment.structural_unit else None,
        "concept_tags": [
            {
                "id": link.concept_tag.id,
                "slug": link.concept_tag.slug,
                "label": link.concept_tag.label,
                "tradition_scope": link.concept_tag.tradition_scope,
                "confidence": link.confidence,
            }
            for link in segment.concept_links
        ],
        "parallel_links": get_parallel_links_for_segment(session, segment.id),
        "citation_links": get_citation_links_for_segment(session, segment.id),
    }


def list_parallel_links(session: Session) -> list[dict[str, Any]]:
    stmt = (
        select(ParallelLink)
        .options(
            selectinload(ParallelLink.source_segment)
            .selectinload(Segment.text_version)
            .selectinload(TextVersion.work)
            .selectinload(Work.tradition),
            selectinload(ParallelLink.target_segment)
            .selectinload(Segment.text_version)
            .selectinload(TextVersion.work)
            .selectinload(Work.tradition),
        )
        .order_by(ParallelLink.id)
    )
    links = session.scalars(stmt).all()
    return [
        {
            "id": link.id,
            "relation_type": link.relation_type,
            "confidence": link.confidence,
            "note": link.note,
            "source_segment_id": link.source_segment.id,
            "source_work_title": link.source_segment.text_version.work.title,
            "source_tradition_name": link.source_segment.text_version.work.tradition.name,
            "source_preview": build_preview(link.source_segment.content, 90),
            "target_segment_id": link.target_segment.id,
            "target_work_title": link.target_segment.text_version.work.title,
            "target_tradition_name": link.target_segment.text_version.work.tradition.name,
            "target_preview": build_preview(link.target_segment.content, 90),
        }
        for link in links
    ]


def list_concepts(session: Session) -> list[dict[str, Any]]:
    count_subquery = (
        select(
            SegmentConceptTag.concept_tag_id.label("concept_tag_id"),
            func.count(SegmentConceptTag.id).label("segment_count"),
        )
        .group_by(SegmentConceptTag.concept_tag_id)
        .subquery()
    )
    concepts = session.execute(
        select(ConceptTag, func.coalesce(count_subquery.c.segment_count, 0))
        .outerjoin(count_subquery, count_subquery.c.concept_tag_id == ConceptTag.id)
        .order_by(ConceptTag.label)
    ).all()
    return [
        {
            "id": concept.id,
            "slug": concept.slug,
            "label": concept.label,
            "tradition_scope": concept.tradition_scope,
            "description": concept.description,
            "segment_count": segment_count,
        }
        for concept, segment_count in concepts
    ]


def get_concept_detail(session: Session, concept_slug: str) -> Optional[dict[str, Any]]:
    concept = session.scalars(select(ConceptTag).where(ConceptTag.slug == concept_slug)).first()
    if not concept:
        return None
    segment_count = session.scalar(
        select(func.count(SegmentConceptTag.id)).where(SegmentConceptTag.concept_tag_id == concept.id)
    ) or 0
    segment_rows = session.scalars(
        select(Segment)
        .join(SegmentConceptTag, SegmentConceptTag.segment_id == Segment.id)
        .where(SegmentConceptTag.concept_tag_id == concept.id)
        .options(
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
        )
        .order_by(Segment.position)
        .limit(120)
    ).all()
    return {
        "id": concept.id,
        "slug": concept.slug,
        "label": concept.label,
        "tradition_scope": concept.tradition_scope,
        "description": concept.description,
        "segment_count": segment_count,
        "segments": [serialize_segment_summary(segment) for segment in segment_rows],
        "analysis": concept_analysis_service.get_concept_analytics(session, concept_slug),
    }


def get_han_catalog_overview(session: Session) -> Optional[dict[str, Any]]:
    collection = session.scalars(
        select(Collection)
        .where(Collection.id == HAN_COLLECTION_ID)
        .options(selectinload(Collection.tradition))
    ).first()
    if not collection:
        return None

    nodes = session.scalars(
        select(CatalogNode)
        .where(CatalogNode.collection_id == HAN_COLLECTION_ID)
        .options(selectinload(CatalogNode.work).selectinload(Work.text_versions))
        .order_by(CatalogNode.depth, CatalogNode.position, CatalogNode.path)
    ).all()
    division_rows = session.execute(
        select(Work.pitaka_division, func.count(Work.id))
        .where(Work.collection_id == HAN_COLLECTION_ID)
        .group_by(Work.pitaka_division)
    ).all()

    division_counts: list[dict[str, Any]] = []
    for division, work_count in division_rows:
        if not division:
            continue
        meta = DIVISION_META.get(division, {"label": division})
        division_counts.append({"division": division, "label": meta["label"], "work_count": work_count})

    return {
        "tradition_id": collection.tradition.id,
        "tradition_name": collection.tradition.name,
        "collection_id": collection.id,
        "collection_title": collection.title,
        "work_count": session.scalar(select(func.count(Work.id)).where(Work.collection_id == HAN_COLLECTION_ID)) or 0,
        "catalog_node_count": len(nodes),
        "ingested_work_count": session.scalar(
            select(func.count(Work.id)).where(
                Work.collection_id == HAN_COLLECTION_ID,
                Work.is_catalog_only.is_(False),
            )
        ) or 0,
        "ingested_segment_count": session.scalar(
            select(func.count(Segment.id))
            .join(Segment.text_version)
            .join(TextVersion.work)
            .where(Work.collection_id == HAN_COLLECTION_ID)
        ) or 0,
        "division_counts": sorted(
            division_counts,
            key=lambda item: DIVISION_META.get(item["division"], {}).get("position", 999),
        ),
        "tree": _build_catalog_tree(nodes),
    }


def get_overview(session: Session) -> dict[str, Any]:
    traditions = session.scalars(select(Tradition).order_by(Tradition.name)).all()
    tradition_rows: list[dict[str, Any]] = []
    for tradition in traditions:
        collection_count = session.scalar(
            select(func.count(Collection.id)).where(Collection.tradition_id == tradition.id)
        ) or 0
        work_count = session.scalar(select(func.count(Work.id)).where(Work.tradition_id == tradition.id)) or 0
        text_version_count = session.scalar(
            select(func.count(TextVersion.id)).join(TextVersion.work).where(Work.tradition_id == tradition.id)
        ) or 0
        segment_count = session.scalar(
            select(func.count(Segment.id))
            .join(Segment.text_version)
            .join(TextVersion.work)
            .where(Work.tradition_id == tradition.id)
        ) or 0
        tradition_rows.append(
            {
                "tradition_id": tradition.id,
                "tradition_name": tradition.name,
                "collection_count": collection_count,
                "work_count": work_count,
                "text_version_count": text_version_count,
                "segment_count": segment_count,
            }
        )
    return {
        "app_name": "Buddhist Text Analysis Platform MVP",
        "is_sample_corpus": not bool(
            session.scalar(select(func.count(Collection.id)).where(Collection.is_sample.is_(False))) or 0
        ),
        "traditions": tradition_rows,
        "total_collections": session.scalar(select(func.count(Collection.id))) or 0,
        "total_works": session.scalar(select(func.count(Work.id))) or 0,
        "total_text_versions": session.scalar(select(func.count(TextVersion.id))) or 0,
        "total_segments": session.scalar(select(func.count(Segment.id))) or 0,
        "total_parallel_links": session.scalar(select(func.count(ParallelLink.id))) or 0,
        "total_concepts": session.scalar(select(func.count(ConceptTag.id))) or 0,
    }


def get_vector_placeholder(session: Session) -> dict[str, Any]:
    try:
        runtime = vector_service.resolve_embedding_runtime()
        indexed_owners = vector_service.indexed_owner_count(session, embedding_model=runtime.model)
    except ValueError as exc:
        return {
            "status": "misconfigured",
            "message": str(exc),
            "configured_backend": "pgvector" if session.bind and session.bind.dialect.name == "postgresql" else "reserved",
            "embedding_model": settings.embedding_model or "unconfigured",
            "indexed_owners": 0,
            "results": [],
            "pgvector_hint": (
                "Use EMBEDDING_PROVIDER=local-hash for the built-in baseline, or configure "
                "EMBEDDING_API_URL, EMBEDDING_MODEL, and EMBEDDING_DIMENSION for an external worker."
            ),
        }

    return {
        "status": "ready" if indexed_owners else "reserved",
        "message": (
            f"{runtime.provider} embeddings are available for MVP retrieval. "
            "Next step: expand coverage, evaluate recall, and improve chunking only after the provider stabilizes."
        ),
        "configured_backend": "pgvector" if indexed_owners else "reserved",
        "embedding_model": runtime.model,
        "indexed_owners": indexed_owners,
        "results": [],
        "pgvector_hint": "Backfill more embeddings to improve recall and keep metadata in sync with the active model.",
    }
