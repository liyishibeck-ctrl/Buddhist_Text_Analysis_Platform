from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import case, desc, func, literal, or_, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models import Segment, SegmentConceptTag, TextVersion, Work
from backend.app.services import catalog_service


SEARCH_PRELOAD = (
    selectinload(Segment.text_version).selectinload(TextVersion.language),
    selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
    selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
    selectinload(Segment.concept_links).selectinload(SegmentConceptTag.concept_tag),
)

CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def ensure_postgres_search_objects(connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    connection.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_segments_search_content_trgm
        ON segments
        USING GIN ((COALESCE(normalized_content, content, '')) gin_trgm_ops)
        """
    )
    connection.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_segments_search_gloss_trgm
        ON segments
        USING GIN ((COALESCE(content_gloss, '')) gin_trgm_ops)
        """
    )
    connection.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_segments_search_tsv
        ON segments
        USING GIN (to_tsvector('simple', COALESCE(normalized_content, content, '')))
        """
    )
    connection.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_works_title_trgm
        ON works
        USING GIN (title gin_trgm_ops)
        """
    )
    connection.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_text_versions_title_trgm
        ON text_versions
        USING GIN (title gin_trgm_ops)
        """
    )


def _contains_cjk(text: str) -> bool:
    return bool(CJK_PATTERN.search(text))


def _serialize_match(
    segment: Segment,
    *,
    match_score: Optional[float] = None,
    match_reason: Optional[str] = None,
    include_content: bool = False,
) -> dict[str, Any]:
    payload = catalog_service.serialize_segment_summary(segment)
    payload["match_score"] = round(float(match_score), 6) if match_score is not None else None
    payload["match_reason"] = match_reason
    payload["concept_labels"] = [link.concept_tag.label for link in segment.concept_links if link.concept_tag]
    if include_content:
        payload["content"] = segment.content
        payload["normalized_content"] = segment.normalized_content or segment.content
        payload["content_gloss"] = segment.content_gloss
        payload["work_id"] = segment.text_version.work.id
        payload["text_version_id"] = segment.text_version.id
        payload["structural_unit_id"] = segment.structural_unit_id
        payload["collection_id"] = segment.text_version.work.collection.id
        payload["tradition_id"] = segment.text_version.work.tradition.id
        payload["language_id"] = segment.text_version.language.id
    return payload


def _apply_join_filters(
    stmt,
    *,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    work_id: Optional[str],
    text_version_id: Optional[str],
):
    stmt = stmt.join(Segment.text_version).join(TextVersion.work)
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    if collection_id:
        stmt = stmt.where(Work.collection_id == collection_id)
    if language_id:
        stmt = stmt.where(TextVersion.language_id == language_id)
    if work_id:
        stmt = stmt.where(Work.id == work_id)
    if text_version_id:
        stmt = stmt.where(TextVersion.id == text_version_id)
    return stmt


def _postgres_search(
    session: Session,
    *,
    q: str,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    work_id: Optional[str],
    text_version_id: Optional[str],
    limit: int,
    include_content: bool,
) -> list[dict[str, Any]]:
    pattern = f"%{q}%"
    content_expr = func.coalesce(Segment.normalized_content, Segment.content, "")
    gloss_expr = func.coalesce(Segment.content_gloss, "")
    segment_title_expr = func.coalesce(Segment.title, "")
    work_title_expr = func.coalesce(Work.title, "")
    version_title_expr = func.coalesce(TextVersion.title, "")
    canonical_expr = func.coalesce(Work.canonical_code, "")
    combined_expr = func.concat_ws(" ", segment_title_expr, work_title_expr, version_title_expr, content_expr, gloss_expr)

    ts_query = func.plainto_tsquery("simple", q)
    ts_rank = func.ts_rank_cd(func.to_tsvector("simple", combined_expr), ts_query)
    similarity_expr = func.greatest(
        func.similarity(content_expr, q),
        func.similarity(gloss_expr, q),
        func.similarity(segment_title_expr, q),
        func.similarity(work_title_expr, q),
        func.similarity(version_title_expr, q),
        func.similarity(canonical_expr, q),
    )

    ilike_filter = or_(
        content_expr.ilike(pattern),
        gloss_expr.ilike(pattern),
        segment_title_expr.ilike(pattern),
        work_title_expr.ilike(pattern),
        version_title_expr.ilike(pattern),
        canonical_expr.ilike(pattern),
    )
    title_hit = or_(
        segment_title_expr.ilike(pattern),
        work_title_expr.ilike(pattern),
        version_title_expr.ilike(pattern),
        canonical_expr.ilike(pattern),
    )

    similarity_threshold = 0.08 if _contains_cjk(q) else 0.14
    score = (
        case((ilike_filter, literal(3.0)), else_=literal(0.0))
        + case((title_hit, literal(1.25)), else_=literal(0.0))
        + (ts_rank * literal(4.0))
        + (similarity_expr * literal(2.0))
    ).label("match_score")
    match_reason = case(
        (ts_rank > literal(0.01), literal("fts")),
        (similarity_expr > literal(0.2), literal("trigram")),
        (title_hit, literal("title")),
        (ilike_filter, literal("keyword")),
        else_=literal("hybrid"),
    ).label("match_reason")

    stmt = select(Segment, score, match_reason).options(*SEARCH_PRELOAD)
    stmt = _apply_join_filters(
        stmt,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
        text_version_id=text_version_id,
    )
    stmt = stmt.where(or_(ilike_filter, ts_rank > 0, similarity_expr > similarity_threshold))
    stmt = stmt.order_by(desc(score), desc(ts_rank), desc(similarity_expr), Segment.position).limit(limit)

    rows = session.execute(stmt).all()
    return [
        _serialize_match(
            segment,
            match_score=match_score,
            match_reason=match_reason,
            include_content=include_content,
        )
        for segment, match_score, match_reason in rows
    ]


def _sqlite_match_score(payload: dict[str, str], query: str) -> tuple[float, str]:
    query_lower = query.lower()
    score = 0.0
    reason = "keyword"

    haystacks = {
        "segment": (payload.get("content") or "").lower(),
        "gloss": (payload.get("content_gloss") or "").lower(),
        "title": (payload.get("title") or "").lower(),
        "work": (payload.get("work_title") or "").lower(),
        "version": (payload.get("text_version_title") or "").lower(),
    }
    if query_lower in haystacks["title"] or query_lower in haystacks["work"] or query_lower in haystacks["version"]:
        score += 4.0
        reason = "title"
    if query_lower in haystacks["segment"]:
        score += 3.0
    if query_lower in haystacks["gloss"]:
        score += 1.0

    compact_segment = haystacks["segment"].replace(" ", "")
    compact_query = query_lower.replace(" ", "")
    if compact_query and compact_query in compact_segment:
        score += 1.5
    if not score:
        score = 0.25
        reason = "fallback"
    return score, reason


def _fallback_search(
    session: Session,
    *,
    q: str,
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    work_id: Optional[str],
    text_version_id: Optional[str],
    limit: int,
    include_content: bool,
) -> list[dict[str, Any]]:
    pattern = f"%{q}%"
    stmt = select(Segment).options(*SEARCH_PRELOAD)
    stmt = _apply_join_filters(
        stmt,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
        text_version_id=text_version_id,
    )
    stmt = stmt.where(
        or_(
            Segment.content.ilike(pattern),
            Segment.content_gloss.ilike(pattern),
            Segment.title.ilike(pattern),
            Work.title.ilike(pattern),
            TextVersion.title.ilike(pattern),
            Work.canonical_code.ilike(pattern),
        )
    ).limit(max(limit * 8, 200))

    segments = session.scalars(stmt).unique().all()
    ranked_rows: list[tuple[float, str, Segment]] = []
    for segment in segments:
        raw = {
            "content": segment.content,
            "content_gloss": segment.content_gloss or "",
            "title": segment.title or "",
            "work_title": segment.text_version.work.title,
            "text_version_title": segment.text_version.title,
        }
        match_score, match_reason = _sqlite_match_score(raw, q)
        ranked_rows.append((match_score, match_reason, segment))

    ranked_rows.sort(key=lambda item: (-item[0], item[2].position))
    return [
        _serialize_match(
            segment,
            match_score=match_score,
            match_reason=match_reason,
            include_content=include_content,
        )
        for match_score, match_reason, segment in ranked_rows[:limit]
    ]


def retrieve_segment_matches(
    session: Session,
    *,
    q: str,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    work_id: Optional[str] = None,
    text_version_id: Optional[str] = None,
    limit: int = 25,
    include_content: bool = False,
) -> list[dict[str, Any]]:
    clean_query = q.strip()
    if not clean_query:
        return []

    if settings.uses_postgres:
        return _postgres_search(
            session,
            q=clean_query,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
            work_id=work_id,
            text_version_id=text_version_id,
            limit=limit,
            include_content=include_content,
        )
    return _fallback_search(
        session,
        q=clean_query,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
        text_version_id=text_version_id,
        limit=limit,
        include_content=include_content,
    )


def search_segments(
    session: Session,
    *,
    q: str,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    work_id: Optional[str] = None,
    text_version_id: Optional[str] = None,
    limit: int = 25,
) -> list[dict]:
    return retrieve_segment_matches(
        session,
        q=q,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
        text_version_id=text_version_id,
        limit=limit,
        include_content=False,
    )
