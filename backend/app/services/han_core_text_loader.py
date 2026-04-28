from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models import (
    CitationLink,
    ConceptTag,
    EmbeddingIndexMetadata,
    ParallelLink,
    Person,
    Segment,
    SegmentConceptTag,
    Source,
    StructuralUnit,
    TextVersion,
    TextVersionPersonRole,
    Work,
)
from backend.app.services.seed_utils import load_json_payload


HAN_CORE_SOURCE_ID = "source-han-core-text-pilot"


def load_han_core_text_payload(path: Path | None = None) -> dict[str, Any]:
    payload_path = Path(path or settings.han_core_text_source_path)
    return load_json_payload(payload_path)


def _upsert_person(session: Session, person_record: dict[str, Any]) -> None:
    existing = session.get(Person, person_record["id"])
    if existing:
        for key, value in person_record.items():
            setattr(existing, key, value)
        return
    session.add(Person(**person_record))


def _upsert_concept_tag(
    session: Session,
    *,
    slug: str,
    label: str,
    description: str | None = None,
    tradition_scope: str = "han",
) -> str:
    concept_id = f"concept-{slug}"
    pending = next(
        (
            item
            for item in session.new
            if isinstance(item, ConceptTag) and item.id == concept_id
        ),
        None,
    )
    if pending:
        return pending.id
    existing = session.get(ConceptTag, concept_id)
    if existing:
        if label:
            existing.label = label
        if description and not existing.description:
            existing.description = description
        return existing.id

    session.add(
        ConceptTag(
            id=concept_id,
            slug=slug,
            label=label,
            tradition_scope=tradition_scope,
            description=description,
        )
    )
    return concept_id


def _stable_segment_id(canonical_code: str, position: int) -> str:
    return f"seg-han-{canonical_code.lower()}-{position:03d}"


def clear_han_core_text_data(session: Session, *, source_id: str = HAN_CORE_SOURCE_ID) -> None:
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
        session.query(SegmentConceptTag).filter(
            SegmentConceptTag.segment_id.in_(segment_ids)
        ).delete(synchronize_session=False)
        session.query(ParallelLink).filter(
            or_(ParallelLink.source_segment_id.in_(segment_ids), ParallelLink.target_segment_id.in_(segment_ids))
        ).delete(synchronize_session=False)
        session.query(CitationLink).filter(
            or_(CitationLink.source_segment_id.in_(segment_ids), CitationLink.target_segment_id.in_(segment_ids))
        ).delete(synchronize_session=False)
        session.query(Segment).filter(Segment.id.in_(segment_ids)).delete(synchronize_session=False)

    if structural_unit_ids:
        session.query(StructuralUnit).filter(StructuralUnit.id.in_(structural_unit_ids)).delete(synchronize_session=False)

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


def seed_han_core_texts(
    session: Session,
    *,
    force: bool = False,
    source_path: Path | None = None,
) -> bool:
    payload_path = Path(source_path or settings.han_core_text_source_path)
    if not payload_path.exists():
        return False

    payload = load_han_core_text_payload(payload_path)
    source_record = payload["source"]
    source_id = source_record["id"]

    existing = session.scalar(select(Source.id).where(Source.id == source_id))
    if existing and not force:
        return False
    if force:
        clear_han_core_text_data(session, source_id=source_id)

    source = session.get(Source, source_id)
    if source:
        for key, value in source_record.items():
            setattr(source, key, value)
    else:
        session.add(Source(**source_record))

    for person_record in payload.get("persons", []):
        _upsert_person(session, person_record)
    session.flush()

    for text_item in payload.get("texts", []):
        work = session.get(Work, text_item["work_id"])
        if not work:
            raise ValueError(f"Unknown work_id in Han core text pilot: {text_item['work_id']}")

        note_suffix = "已接入核心正文试点版本。"
        existing_note = (work.catalog_note or "").strip()
        if note_suffix not in existing_note:
            work.catalog_note = f"{existing_note} {note_suffix}".strip()
        work.is_catalog_only = False
        if not work.summary or "目录项" in work.summary:
            work.summary = (
                f"{work.title} 已接入汉传核心正文试点，当前为 {text_item.get('import_scope', 'excerpt')} 级别内容，"
                "用于验证正文导入、结构浏览与分段检索链路。"
            )
        for key, value in text_item.get("work_update", {}).items():
            setattr(work, key, value)

        canonical_code = text_item["canonical_code"]
        text_version_record = dict(text_item["text_version"])
        text_version_record["work_id"] = text_version_record.get("work_id") or work.id
        text_version_record["language_id"] = text_version_record.get("language_id") or "lang-lzh"
        text_version_record["source_id"] = text_version_record.get("source_id") or source_id
        text_version_record["is_sample"] = text_version_record.get("is_sample", source_record.get("is_sample", True))
        text_version_record["is_catalog_only"] = text_version_record.get("is_catalog_only", False)
        text_version_record.setdefault(
            "catalog_note",
            f"汉传核心正文试点：{text_item.get('import_scope', 'excerpt')} 内容，绑定目录编号 {canonical_code}。",
        )
        text_version_id = text_version_record["id"]
        session.add(TextVersion(**text_version_record))

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
                        "note": "Created from Han core-text pilot role assignment.",
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

        structural_unit_id_map: dict[str, str] = {}
        for structural_unit_record in text_item.get("structural_units", []):
            source_unit_id = structural_unit_record["unit_id"]
            unit_id = f"su-{text_version_id}-{source_unit_id}"
            parent_source_unit_id = structural_unit_record.get("parent_unit_id")
            structural_unit_id_map[source_unit_id] = unit_id
            session.add(
                StructuralUnit(
                    id=unit_id,
                    text_version_id=text_version_id,
                    parent_id=structural_unit_id_map.get(parent_source_unit_id) if parent_source_unit_id else None,
                    unit_type=structural_unit_record["unit_type"],
                    label=structural_unit_record["label"],
                    title=structural_unit_record.get("title"),
                    position=structural_unit_record.get("position", 0),
                    depth=structural_unit_record.get("depth", 0),
                    path=structural_unit_record["path"],
                )
            )

        segment_key_to_id: dict[str, str] = {}
        import_scope = text_item.get("import_scope", "excerpt")
        for segment_record in text_item.get("segments", []):
            position = segment_record["position"]
            segment_id = _stable_segment_id(canonical_code, position)
            segment_key_to_id[segment_record["segment_key"]] = segment_id
            content = segment_record["content"]
            session.add(
                Segment(
                    id=segment_id,
                    text_version_id=text_version_id,
                    structural_unit_id=structural_unit_id_map.get(segment_record.get("structural_unit_id")),
                    segment_key=segment_record["segment_key"],
                    title=segment_record.get("title"),
                    content=content,
                    content_gloss=segment_record.get("content_gloss"),
                    normalized_content=segment_record.get("normalized_content") or content,
                    note=segment_record.get("note"),
                    position=position,
                    char_count=segment_record.get("char_count") or len(content),
                    metadata_json={
                        "canonical_code": canonical_code,
                        "import_scope": import_scope,
                        "pilot_source": source_id,
                    },
                )
            )

        for concept_link_record in text_item.get("segment_concept_tags", []):
            concept_slug = concept_link_record["concept_tag_slug"]
            if concept_slug == "no-self":
                concept_slug = "non-self"
            concept_id = _upsert_concept_tag(
                session,
                slug=concept_slug,
                label=concept_link_record["concept_tag_label"],
                description=f"Imported from Han core-text pilot for {canonical_code}.",
            )
            session.add(
                SegmentConceptTag(
                    segment_id=segment_key_to_id[concept_link_record["segment_key"]],
                    concept_tag_id=concept_id,
                    confidence=concept_link_record.get("confidence", 1.0),
                    note=concept_link_record.get("note"),
                )
            )

    session.commit()
    return True
