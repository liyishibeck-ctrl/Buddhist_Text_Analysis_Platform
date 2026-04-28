from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import ConceptTag, Segment, SegmentConceptTag, TextVersion, Tradition, Work
from backend.app.services import catalog_service


CORE_CONCEPTS: list[dict[str, Any]] = [
    {
        "slug": "emptiness",
        "label": "空性",
        "tradition_scope": "cross-tradition",
        "description": "围绕空、性空、空相、诸法空的核心概念。",
        "patterns": ["空性", "性空", "空相", "诸法空", "空"],
    },
    {
        "slug": "non-attachment",
        "label": "无著",
        "tradition_scope": "cross-tradition",
        "description": "围绕不著、不取、无住、离著的修行语汇。",
        "patterns": ["无著", "不著", "不取", "无住", "离著"],
    },
    {
        "slug": "pure-land",
        "label": "净土",
        "tradition_scope": "sino-japanese",
        "description": "净土、极乐世界与往生相关概念。",
        "patterns": ["净土", "极乐", "安乐国", "往生"],
    },
    {
        "slug": "middle-way",
        "label": "中道",
        "tradition_scope": "cross-tradition",
        "description": "中道、离二边、非有非无等中观核心术语。",
        "patterns": ["中道", "离二边", "不二", "非有非无"],
    },
    {
        "slug": "four-noble-truths",
        "label": "四圣谛",
        "tradition_scope": "cross-tradition",
        "description": "苦、集、灭、道与四谛结构。",
        "patterns": ["四谛", "苦集灭道", "圣谛", "苦谛", "灭谛"],
    },
    {
        "slug": "loving-kindness",
        "label": "慈",
        "tradition_scope": "cross-tradition",
        "description": "慈心、慈爱、慈愍相关概念。",
        "patterns": ["慈心", "慈爱", "慈愍", "慈"],
    },
    {
        "slug": "non-self",
        "label": "无我",
        "tradition_scope": "cross-tradition",
        "description": "无我、人无我、法无我等概念。",
        "patterns": ["无我", "人无我", "法无我"],
    },
    {
        "slug": "bodhicitta",
        "label": "菩提心",
        "tradition_scope": "mahayana",
        "description": "发菩提心与求无上菩提的愿行。",
        "patterns": ["菩提心", "发菩提心", "无上菩提"],
    },
    {
        "slug": "compassion",
        "label": "悲",
        "tradition_scope": "cross-tradition",
        "description": "慈悲、悲心、大悲与救苦相关概念。",
        "patterns": ["慈悲", "悲心", "大悲", "悲愍"],
    },
    {
        "slug": "dependent-origination",
        "label": "缘起",
        "tradition_scope": "cross-tradition",
        "description": "缘起、因缘、十二因缘与条件生成结构。",
        "patterns": ["缘起", "因缘", "十二因缘", "缘生"],
    },
    {
        "slug": "nirvana",
        "label": "涅槃",
        "tradition_scope": "cross-tradition",
        "description": "涅槃、寂灭、无余依等解脱终点概念。",
        "patterns": ["涅槃", "寂灭", "无余依", "般涅槃"],
    },
    {
        "slug": "prajna",
        "label": "般若",
        "tradition_scope": "mahayana",
        "description": "般若智慧与观照语汇。",
        "patterns": ["般若", "智慧", "观照"],
    },
    {
        "slug": "buddha-nature",
        "label": "佛性",
        "tradition_scope": "mahayana",
        "description": "佛性、如来藏、真如本觉等概念。",
        "patterns": ["佛性", "如来藏", "真如", "本觉"],
    },
    {
        "slug": "precepts",
        "label": "戒",
        "tradition_scope": "cross-tradition",
        "description": "戒、戒律、持戒、菩萨戒等规范性概念。",
        "patterns": ["戒律", "持戒", "菩萨戒", "净戒", "戒"],
    },
    {
        "slug": "meditation",
        "label": "禅定",
        "tradition_scope": "cross-tradition",
        "description": "禅定、三昧、止观与修定语汇。",
        "patterns": ["禅定", "三昧", "止观", "定心"],
    },
]

CORE_CONCEPTS_BY_SLUG = {item["slug"]: item for item in CORE_CONCEPTS}


def _match_patterns(text_value: str, patterns: list[str]) -> bool:
    if not text_value:
        return False
    return any(pattern in text_value for pattern in patterns)


def detect_query_concepts(query_text: str) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for concept in CORE_CONCEPTS:
        if _match_patterns(query_text, concept["patterns"]):
            matched.append(
                {
                    "slug": concept["slug"],
                    "label": concept["label"],
                    "description": concept["description"],
                }
            )
    return matched


def ensure_core_concept_tags(session: Session) -> int:
    created = 0
    existing_tags = {
        row.slug: row
        for row in session.scalars(select(ConceptTag).where(ConceptTag.slug.in_(CORE_CONCEPTS_BY_SLUG.keys()))).all()
    }
    for concept in CORE_CONCEPTS:
        existing = existing_tags.get(concept["slug"])
        if existing:
            updated = False
            if existing.label != concept["label"]:
                existing.label = concept["label"]
                updated = True
            if existing.description != concept["description"]:
                existing.description = concept["description"]
                updated = True
            if existing.tradition_scope != concept["tradition_scope"]:
                existing.tradition_scope = concept["tradition_scope"]
                updated = True
            if updated:
                session.add(existing)
            continue

        session.add(
            ConceptTag(
                id=f"concept-{concept['slug']}",
                slug=concept["slug"],
                label=concept["label"],
                tradition_scope=concept["tradition_scope"],
                description=concept["description"],
            )
        )
        created += 1
    session.commit()
    return created


def backfill_core_concepts(
    session: Session,
    *,
    batch_size: int = 500,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
) -> int:
    ensure_core_concept_tags(session)
    total_links = 0
    offset = 0
    concept_ids = {
        row.slug: row.id
        for row in session.scalars(select(ConceptTag).where(ConceptTag.slug.in_(CORE_CONCEPTS_BY_SLUG.keys()))).all()
    }

    while True:
        stmt = (
            select(Segment)
            .options(selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition))
            .join(Segment.text_version)
            .join(TextVersion.work)
            .order_by(Segment.id)
            .offset(offset)
            .limit(batch_size)
        )
        if tradition_id:
            stmt = stmt.where(Work.tradition_id == tradition_id)
        if collection_id:
            stmt = stmt.where(Work.collection_id == collection_id)
        if language_id:
            stmt = stmt.where(TextVersion.language_id == language_id)

        segments = session.scalars(stmt).unique().all()
        if not segments:
            break

        segment_ids = [segment.id for segment in segments]
        existing_pairs = {
            (link.segment_id, link.concept_tag_id)
            for link in session.scalars(
                select(SegmentConceptTag).where(SegmentConceptTag.segment_id.in_(segment_ids))
            ).all()
        }

        for segment in segments:
            content = (segment.normalized_content or segment.content or "") + " " + (segment.content_gloss or "")
            for concept in CORE_CONCEPTS:
                if not _match_patterns(content, concept["patterns"]):
                    continue
                pair = (segment.id, concept_ids[concept["slug"]])
                if pair in existing_pairs:
                    continue
                session.add(
                    SegmentConceptTag(
                        segment_id=segment.id,
                        concept_tag_id=concept_ids[concept["slug"]],
                        confidence=0.76,
                        note="auto:core-concept-lexicon-v1",
                    )
                )
                existing_pairs.add(pair)
                total_links += 1

        session.commit()
        offset += batch_size

    return total_links


def get_concept_analytics(
    session: Session,
    concept_slug: str,
    *,
    work_limit: int = 10,
    related_limit: int = 8,
    segment_limit: int = 25,
) -> Optional[dict[str, Any]]:
    concept = session.scalars(select(ConceptTag).where(ConceptTag.slug == concept_slug)).first()
    if not concept:
        return None

    matched_segment_count = session.scalar(
        select(func.count(SegmentConceptTag.id)).where(SegmentConceptTag.concept_tag_id == concept.id)
    ) or 0
    evidence_segments = [
        catalog_service.serialize_segment_summary(segment)
        for segment in session.scalars(
            select(Segment)
            .join(SegmentConceptTag, SegmentConceptTag.segment_id == Segment.id)
            .where(SegmentConceptTag.concept_tag_id == concept.id)
            .options(
                selectinload(Segment.text_version).selectinload(TextVersion.language),
                selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
            )
            .order_by(Segment.position)
            .limit(segment_limit)
        ).all()
    ]

    tradition_rows = session.execute(
        select(Tradition.id, Tradition.name, func.count(SegmentConceptTag.id))
        .join(SegmentConceptTag.segment)
        .join(Segment.text_version)
        .join(TextVersion.work)
        .join(Work.tradition)
        .where(SegmentConceptTag.concept_tag_id == concept.id)
        .group_by(Tradition.id, Tradition.name)
        .order_by(desc(func.count(SegmentConceptTag.id)), Tradition.name)
    ).all()
    top_works = session.execute(
        select(Work.id, Work.title, Tradition.name, func.count(SegmentConceptTag.id))
        .join(TextVersion, TextVersion.work_id == Work.id)
        .join(Segment, Segment.text_version_id == TextVersion.id)
        .join(SegmentConceptTag, SegmentConceptTag.segment_id == Segment.id)
        .join(Work.tradition)
        .where(SegmentConceptTag.concept_tag_id == concept.id)
        .group_by(Work.id, Work.title, Tradition.name)
        .order_by(desc(func.count(SegmentConceptTag.id)), Work.title)
        .limit(work_limit)
    ).all()
    related_rows = session.execute(
        select(ConceptTag.slug, ConceptTag.label, func.count(SegmentConceptTag.id))
        .join(SegmentConceptTag, SegmentConceptTag.concept_tag_id == ConceptTag.id)
        .where(
            SegmentConceptTag.segment_id.in_(
                select(SegmentConceptTag.segment_id).where(SegmentConceptTag.concept_tag_id == concept.id)
            ),
            ConceptTag.id != concept.id,
        )
        .group_by(ConceptTag.slug, ConceptTag.label)
        .order_by(desc(func.count(SegmentConceptTag.id)), ConceptTag.label)
        .limit(related_limit)
    ).all()
    related_concepts = [
        {"slug": slug, "label": label, "count": count}
        for slug, label, count in related_rows
    ]
    return {
        "analysis_mode": "segment_concept_tags",
        "matched_segment_count": matched_segment_count,
        "tradition_distribution": [
            {"tradition_id": tradition_id, "tradition_name": tradition_name, "segment_count": segment_count}
            for tradition_id, tradition_name, segment_count in tradition_rows
        ],
        "top_works": [
            {"work_id": work_id, "work_title": work_title, "tradition_name": tradition_name, "segment_count": segment_count}
            for work_id, work_title, tradition_name, segment_count in top_works
        ],
        "related_concepts": related_concepts,
        "evidence_segments": evidence_segments,
    }
