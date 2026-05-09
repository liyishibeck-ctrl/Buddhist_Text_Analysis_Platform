from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models import Segment, StructuralUnit, TextUnitSummary, TextVersion, Tradition, Work
from backend.app.services import concept_analysis_service, search_service, vector_service


TRADITION_ORDER = ["trad-han", "trad-pali", "trad-tibetan"]
MAX_EXPANDED_TERMS = 12
MAX_KEYWORD_TERMS = 9
MAX_KEYWORD_RESULTS_PER_TERM = 6
NEARBY_CONTEXT_WINDOW = 2
CONTEXT_TEXT_LIMIT = 320
SUMMARY_TEXT_LIMIT = 520
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
PALI_CONTENT_HINTS = ("suñ", "ññ", "paṭ", "nibb", "mett", "anic", "dukk", "anatt", "ṭ", "ḍ", "ḷ", "ṃ", "ṁ")
WYLIE_CONTENT_HINTS = (
    "'",
    "stong",
    "nyid",
    "rnam",
    "snang",
    "mdzad",
    "bdag",
    "med",
    "chos",
    "kyi",
    "dbyings",
    "byang",
    "chub",
    "sems",
    "snying",
    "rje",
)

CONCEPT_QUERY_LEXICON: list[dict[str, Any]] = [
    {
        "slug": "emptiness",
        "label": "空性 / emptiness",
        "triggers": ["空", "空性", "性空", "śūnyatā", "sunyata", "suññatā", "emptiness"],
        "aliases": ["空", "空性", "性空", "emptiness", "empty", "voidness", "śūnyatā", "suññatā", "stong pa nyid"],
    },
    {
        "slug": "vairocana",
        "label": "大日如来 / Vairocana",
        "triggers": ["大日", "大日如来", "毘卢遮那", "毗卢遮那", "vairocana", "mahāvairocana", "maha vairocana"],
        "aliases": [
            "大日如来",
            "毘卢遮那",
            "毗卢遮那",
            "Vairocana",
            "Mahāvairocana",
            "Mahavairocana",
            "Great Vairocana",
            "rnam par snang mdzad",
        ],
    },
    {
        "slug": "akshobhya",
        "label": "阿閦佛 / Akṣobhya",
        "triggers": ["阿閦佛", "阿閦如来", "阿閦如來", "不动佛", "不動佛", "akṣobhya", "aksobhya", "mi 'khrugs pa"],
        "aliases": [
            "阿閦佛",
            "阿閦如来",
            "阿閦如來",
            "不动佛",
            "不動佛",
            "Akṣobhya",
            "Aksobhya",
            "mi 'khrugs pa",
        ],
    },
    {
        "slug": "ratnasambhava",
        "label": "宝生佛 / Ratnasambhava",
        "triggers": ["宝生佛", "寶生佛", "宝生如来", "寶生如來", "ratnasambhava", "rin chen 'byung gnas"],
        "aliases": [
            "宝生佛",
            "寶生佛",
            "宝生如来",
            "寶生如來",
            "Ratnasambhava",
            "rin chen 'byung gnas",
        ],
    },
    {
        "slug": "amitabha",
        "label": "阿弥陀佛 / Amitābha",
        "triggers": ["阿弥陀佛", "阿彌陀佛", "阿弥陀如来", "阿彌陀如來", "amitābha", "amitabha", "'od dpag med"],
        "aliases": [
            "阿弥陀佛",
            "阿彌陀佛",
            "阿弥陀如来",
            "阿彌陀如來",
            "Amitābha",
            "Amitabha",
            "'od dpag med",
        ],
    },
    {
        "slug": "amoghasiddhi",
        "label": "不空成就佛 / Amoghasiddhi",
        "triggers": [
            "不空成就",
            "不空成就如来",
            "不空成就如來",
            "不空成就世尊",
            "不空成就佛",
            "amoghasiddhi",
            "don yod grub pa",
        ],
        "aliases": [
            "不空成就",
            "不空成就世尊",
            "不空成就佛",
            "不空成就如来",
            "不空成就如來",
            "Amoghasiddhi",
            "don yod grub pa",
        ],
    },
    {
        "slug": "avalokitesvara",
        "label": "观世音 / Avalokiteśvara",
        "triggers": [
            "观音",
            "觀音",
            "观世音",
            "觀世音",
            "观自在",
            "觀自在",
            "guanyin",
            "avalokiteśvara",
            "avalokitesvara",
            "chenrezig",
            "spyan ras gzigs",
        ],
        "aliases": [
            "观音",
            "觀音",
            "观世音",
            "觀世音",
            "观自在",
            "觀自在",
            "Avalokiteśvara",
            "Avalokitesvara",
            "spyan ras gzigs",
            "spyan ras gzigs dbang phyug",
            "Guanyin",
            "Lokeśvara",
            "Lokeshvara",
            "Chenrezig",
        ],
    },
    {
        "slug": "dependent-origination",
        "label": "缘起 / dependent origination",
        "triggers": ["缘起", "因缘", "十二因缘", "dependent origination", "paṭiccasamuppāda", "pratītyasamutpāda"],
        "aliases": [
            "缘起",
            "因缘",
            "十二因缘",
            "dependent origination",
            "conditioned arising",
            "paṭiccasamuppāda",
            "pratītyasamutpāda",
            "rten cing 'brel bar 'byung ba",
        ],
    },
    {
        "slug": "non-self",
        "label": "无我 / non-self",
        "triggers": ["无我", "非我", "anattā", "anatman", "non-self", "not self"],
        "aliases": ["无我", "非我", "non-self", "not self", "anattā", "anatta", "anatman", "bdag med"],
    },
    {
        "slug": "nirvana",
        "label": "涅槃 / nirvāṇa",
        "triggers": ["涅槃", "寂灭", "般涅槃", "nirvāṇa", "nibbāna"],
        "aliases": ["涅槃", "寂灭", "般涅槃", "nirvāṇa", "nirvana", "nibbāna", "nibbana", "myang 'das"],
    },
    {
        "slug": "bodhicitta",
        "label": "菩提心 / bodhicitta",
        "triggers": ["菩提心", "发菩提心", "bodhicitta", "byang chub sems"],
        "aliases": ["菩提心", "发菩提心", "bodhicitta", "mind of awakening", "awakening mind", "byang chub sems"],
    },
    {
        "slug": "compassion",
        "label": "慈悲 / compassion",
        "triggers": ["慈悲", "大悲", "悲心", "karuṇā", "compassion"],
        "aliases": ["慈悲", "大悲", "悲心", "compassion", "great compassion", "karuṇā", "karuna", "snying rje"],
    },
    {
        "slug": "loving-kindness",
        "label": "慈 / loving-kindness",
        "triggers": ["慈心", "慈爱", "慈愍", "loving-kindness", "mettā", "maitrī"],
        "aliases": ["慈心", "慈", "loving-kindness", "mettā", "metta", "maitrī", "maitri", "byams pa"],
    },
    {
        "slug": "prajna",
        "label": "般若 / prajñā",
        "triggers": ["般若", "智慧", "prajñā", "prajna", "wisdom", "shes rab"],
        "aliases": ["般若", "智慧", "prajñā", "prajna", "wisdom", "transcendent wisdom", "shes rab"],
    },
    {
        "slug": "samadhi",
        "label": "三昧 / samādhi",
        "triggers": ["三昧", "禅定", "samādhi", "samadhi", "ting nge"],
        "aliases": ["三昧", "禅定", "samādhi", "samadhi", "absorption", "meditative absorption", "ting nge 'dzin"],
    },
    {
        "slug": "buddha-nature",
        "label": "佛性 / tathāgatagarbha",
        "triggers": ["佛性", "如来藏", "tathāgatagarbha", "buddha nature"],
        "aliases": [
            "佛性",
            "如来藏",
            "buddha nature",
            "tathāgatagarbha",
            "tathagatagarbha",
            "de bzhin gshegs pa'i snying po",
        ],
    },
    {
        "slug": "dharmadhatu",
        "label": "法界 / dharmadhātu",
        "triggers": ["法界", "dharmadhātu", "dharmadhatu", "chos kyi dbyings"],
        "aliases": ["法界", "dharmadhātu", "dharmadhatu", "realm of phenomena", "chos kyi dbyings"],
    },
    {
        "slug": "middle-way",
        "label": "中道 / middle way",
        "triggers": ["中道", "不二", "离二边", "middle way", "madhyamā", "dbu ma"],
        "aliases": ["中道", "不二", "离二边", "middle way", "madhyamā", "madhyama", "dbu ma"],
    },
    {
        "slug": "four-noble-truths",
        "label": "四圣谛 / four noble truths",
        "triggers": ["四谛", "四圣谛", "苦集灭道", "four noble truths", "ariyasacca"],
        "aliases": ["四谛", "四圣谛", "苦集灭道", "four noble truths", "noble truths", "ariyasacca", "bden pa bzhi"],
    },
    {
        "slug": "impermanence",
        "label": "无常 / impermanence",
        "triggers": ["无常", "anicca", "impermanence", "mi rtag"],
        "aliases": ["无常", "impermanence", "impermanent", "anicca", "anitya", "mi rtag pa"],
    },
    {
        "slug": "precepts",
        "label": "戒 / śīla",
        "triggers": ["戒", "戒律", "持戒", "净戒", "śīla", "sīla"],
        "aliases": ["戒", "戒律", "持戒", "净戒", "precepts", "ethics", "discipline", "śīla", "sīla", "tshul khrims"],
    },
]


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _truncate_text(value: Any, limit: int) -> str:
    text_value = _normalise_text(str(value or ""))
    if len(text_value) <= limit:
        return text_value
    return f"{text_value[: max(0, limit - 1)]}..."


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _find_trigger_spans(query_text: str, trigger: str) -> list[tuple[int, int]]:
    clean_query = _normalise_text(query_text)
    clean_trigger = _normalise_text(trigger)
    if not clean_query or not clean_trigger:
        return []

    haystack = clean_query.casefold()
    needle = clean_trigger.casefold()
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            break
        spans.append((index, index + len(needle)))
        start = index + 1
    return spans


def _span_is_protected(
    span: tuple[int, int],
    *,
    concept_slug: str,
    protected_spans: list[tuple[int, int, str]],
) -> bool:
    start, end = span
    for other_start, other_end, other_slug in protected_spans:
        if other_slug == concept_slug:
            continue
        if other_start <= start and end <= other_end:
            return True
    return False


def expand_query_terms(query_text: str) -> list[dict[str, Any]]:
    clean_query = _normalise_text(query_text)
    terms: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(term: str, *, source: str, label: str, weight: float) -> None:
        clean_term = _normalise_text(term)
        if not clean_term:
            return
        key = clean_term.casefold()
        if key in seen:
            return
        seen.add(key)
        terms.append({"term": clean_term, "source": source, "label": label, "weight": weight})

    add(clean_query, source="original", label="原始查询", weight=1.0)
    matched_concepts: list[tuple[dict[str, Any], list[tuple[str, tuple[int, int]]]]] = []
    protected_spans: list[tuple[int, int, str]] = []
    for concept in CONCEPT_QUERY_LEXICON:
        trigger_hits: list[tuple[str, tuple[int, int]]] = []
        for trigger in concept["triggers"]:
            for span in _find_trigger_spans(clean_query, trigger):
                trigger_hits.append((trigger, span))
                compact_trigger = _compact_text(trigger)
                if CJK_PATTERN.search(compact_trigger) and len(compact_trigger) >= 2:
                    protected_spans.append((span[0], span[1], str(concept["slug"])))
        if not trigger_hits:
            continue
        matched_concepts.append((concept, trigger_hits))

    for concept, trigger_hits in matched_concepts:
        matched = False
        for trigger, span in trigger_hits:
            compact_trigger = _compact_text(trigger)
            if CJK_PATTERN.search(compact_trigger) and len(compact_trigger) == 1:
                if _span_is_protected(span, concept_slug=str(concept["slug"]), protected_spans=protected_spans):
                    continue
            matched = True
            break
        if not matched:
            continue
        for index, alias in enumerate(concept["aliases"]):
            add(
                alias,
                source=concept["slug"],
                label=concept["label"],
                weight=max(0.68, 0.96 - index * 0.035),
            )

    return terms[:MAX_EXPANDED_TERMS]


def _selected_tradition_ids(session: Session, tradition_id: Optional[str]) -> list[str]:
    if tradition_id:
        return [tradition_id]
    existing = {row.id for row in session.scalars(select(Tradition)).all()}
    ordered = [item for item in TRADITION_ORDER if item in existing]
    ordered.extend(sorted(existing - set(ordered)))
    return ordered


def _available_embedding_models_by_tradition(session: Session) -> dict[str, list[dict[str, Any]]]:
    if not settings.uses_postgres:
        return {}
    try:
        rows = session.execute(
            text(
                """
                SELECT
                    w.tradition_id,
                    se.embedding_model,
                    COALESCE(MAX(eim.dimension), 0) AS dimension,
                    COUNT(*) AS indexed_count
                FROM segment_embeddings se
                JOIN segments s ON s.id = se.segment_id
                JOIN text_versions tv ON tv.id = s.text_version_id
                JOIN works w ON w.id = tv.work_id
                LEFT JOIN embedding_index_metadata eim
                    ON eim.owner_type = 'segment'
                    AND eim.owner_id = se.segment_id
                    AND eim.embedding_model = se.embedding_model
                WHERE se.embedding_model NOT LIKE '%::%'
                GROUP BY w.tradition_id, se.embedding_model
                ORDER BY w.tradition_id, COUNT(*) DESC, se.embedding_model
                """
            )
        ).mappings().all()
    except Exception:
        session.rollback()
        return {}

    payload: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        payload[str(row["tradition_id"])].append(
            {
                "embedding_model": str(row["embedding_model"]),
                "dimension": int(row["dimension"] or 0),
                "content_field": "normalized_content",
                "indexed_count": int(row["indexed_count"]),
            }
        )
    return dict(payload)


def _vector_runtime_skip_reason(model: str, tradition_id: str) -> str:
    try:
        runtime = vector_service.resolve_embedding_runtime(embedding_model=model, tradition_id=tradition_id)
    except Exception as exc:
        return str(exc)
    if runtime.provider == vector_service.LOCAL_EMBEDDING_PROVIDER and model != vector_service.LOCAL_EMBEDDING_MODEL:
        return (
            "Stored vectors use a non-local embedding model, but the current query embedding provider "
            "is local-hash. Configure EMBEDDING_PROVIDER=openai-compatible with the matching model/dimension."
        )
    return ""


def _merge_candidate(
    merged: dict[str, dict[str, Any]],
    item: dict[str, Any],
    *,
    retrieval_score: float,
    channel: str,
    query_term: str,
) -> None:
    segment_id = item["id"]
    existing = merged.get(segment_id)
    incoming_terms = list(item.get("matched_query_terms") or [])
    if query_term:
        incoming_terms.append(query_term)
    incoming_terms = sorted({term for term in incoming_terms if term})
    if existing is None:
        payload = dict(item)
        payload["retrieval_score"] = round(retrieval_score, 6)
        payload["retrieval_channels"] = [channel]
        payload["matched_query_terms"] = incoming_terms
        merged[segment_id] = payload
        return

    existing["retrieval_score"] = round(float(existing.get("retrieval_score") or 0.0) + retrieval_score, 6)
    existing["retrieval_channels"] = sorted(set(existing.get("retrieval_channels", []) + [channel]))
    existing["matched_query_terms"] = sorted(set(existing.get("matched_query_terms", []) + incoming_terms))
    if item.get("content_gloss") and not existing.get("content_gloss"):
        existing["content_gloss"] = item["content_gloss"]
    if item.get("content") and not existing.get("content"):
        existing["content"] = item["content"]
    if item.get("normalized_content") and not existing.get("normalized_content"):
        existing["normalized_content"] = item["normalized_content"]


def _semantic_query(query_text: str, expanded_terms: list[dict[str, Any]]) -> str:
    semantic_terms = [query_text]
    semantic_terms.extend(item["term"] for item in expanded_terms[1:7])
    return " ; ".join(_normalise_text(item) for item in semantic_terms if _normalise_text(item))


def _keyword_expanded_terms(expanded_terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_terms: list[dict[str, Any]] = []
    for item in expanded_terms:
        term = str(item.get("term") or "").strip()
        compact = re.sub(r"\s+", "", term)
        if CJK_PATTERN.search(compact) and len(compact) < 2 and item.get("source") != "original":
            continue
        if not CJK_PATTERN.search(compact) and len(compact) < 4:
            continue
        safe_terms.append(item)
    return safe_terms[:MAX_KEYWORD_TERMS]


def _keyword_terms_for_tradition(expanded_terms: list[dict[str, Any]], tradition_id: str) -> list[dict[str, Any]]:
    safe_terms = _keyword_expanded_terms(expanded_terms)
    cjk_terms = [item for item in safe_terms if CJK_PATTERN.search(str(item.get("term") or ""))]
    non_cjk_terms = [item for item in safe_terms if not CJK_PATTERN.search(str(item.get("term") or ""))]
    if tradition_id == "trad-han":
        return (cjk_terms or safe_terms)[:4]
    if tradition_id == "trad-pali":
        preferred = [
            item
            for item in non_cjk_terms
            if any(mark in str(item.get("term") or "").casefold() for mark in ["ñ", "ṭ", "ḍ", "ā", "ī", "ū", "nibb", "mett", "pali"])
        ]
        return (preferred + [item for item in non_cjk_terms if item not in preferred])[:4]
    if tradition_id == "trad-tibetan":
        preferred = [
            item
            for item in non_cjk_terms
            if "'" in str(item.get("term") or "") or " " in str(item.get("term") or "")
        ]
        return (preferred + [item for item in non_cjk_terms if item not in preferred])[:4]
    return safe_terms[:4]


def _should_search_body_content(term: str, tradition_id: Optional[str]) -> bool:
    clean = term.casefold()
    if tradition_id == "trad-han":
        return bool(CJK_PATTERN.search(clean))
    if tradition_id == "trad-pali":
        return any(hint in clean for hint in PALI_CONTENT_HINTS)
    if tradition_id == "trad-tibetan":
        return any(hint in clean for hint in WYLIE_CONTENT_HINTS)
    return (
        bool(CJK_PATTERN.search(clean))
        or any(hint in clean for hint in PALI_CONTENT_HINTS)
        or any(hint in clean for hint in WYLIE_CONTENT_HINTS)
    )


def _fast_keyword_matches(
    session: Session,
    *,
    terms: list[str],
    tradition_id: Optional[str],
    collection_id: Optional[str],
    language_id: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    terms = [_normalise_text(term) for term in terms if _normalise_text(term)]
    if not terms:
        return []
    if not settings.uses_postgres:
        merged: dict[str, dict[str, Any]] = {}
        for term in terms:
            for row in search_service.retrieve_segment_matches(
                session,
                q=term,
                tradition_id=tradition_id,
                collection_id=collection_id,
                language_id=language_id,
                limit=max(1, limit // max(len(terms), 1)),
                include_content=True,
            ):
                row.setdefault("matched_query_terms", []).append(term)
                merged[row["id"]] = row
        return list(merged.values())[:limit]

    candidate_queries: list[str] = []
    params: dict[str, Any] = {
        "limit": limit,
        "candidate_limit": max(limit * 20, 300),
        "branch_limit": max(limit * 4, 80),
    }
    for index, term in enumerate(terms):
        term_param = f"term_{index}"
        pattern_param = f"pattern_{index}"
        params[term_param] = term
        params[pattern_param] = f"%{term}%"
        candidate_queries.append(
            f"""
            (
                SELECT s.id AS segment_id, 1.25 AS score, :{term_param} AS matched_term, 'gloss' AS match_reason
                FROM segments s
                WHERE COALESCE(s.content_gloss, '') ILIKE :{pattern_param}
                LIMIT :branch_limit
            )
            """
        )
        if _should_search_body_content(term, tradition_id):
            candidate_queries.append(
                f"""
                (
                    SELECT s.id AS segment_id, 1.0 AS score, :{term_param} AS matched_term, 'keyword' AS match_reason
                    FROM segments s
                    WHERE COALESCE(s.normalized_content, s.content, '') ILIKE :{pattern_param}
                    LIMIT :branch_limit
                )
                """
            )
        candidate_queries.append(
            f"""
            (
                SELECT s.id AS segment_id, 3.0 AS score, :{term_param} AS matched_term, 'title' AS match_reason
                FROM works w
                JOIN text_versions tv ON tv.work_id = w.id
                JOIN segments s ON s.text_version_id = tv.id
                WHERE
                    COALESCE(w.title, '') ILIKE :{pattern_param}
                    OR COALESCE(tv.title, '') ILIKE :{pattern_param}
                    OR COALESCE(w.canonical_code, '') ILIKE :{pattern_param}
                ORDER BY s.position
                LIMIT :branch_limit
            )
            """
        )

    candidate_sql = "\nUNION ALL\n".join(candidate_queries)
    where_clauses: list[str] = []
    if tradition_id:
        where_clauses.append("w.tradition_id = :tradition_id")
        params["tradition_id"] = tradition_id
    if collection_id:
        where_clauses.append("w.collection_id = :collection_id")
        params["collection_id"] = collection_id
    if language_id:
        where_clauses.append("tv.language_id = :language_id")
        params["language_id"] = language_id
    final_where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = session.execute(
        text(
            f"""
            WITH candidate_ids AS (
                {candidate_sql}
            ),
            ranked AS MATERIALIZED (
                SELECT
                    segment_id,
                    SUM(score) AS match_score,
                    STRING_AGG(DISTINCT matched_term, ' || ') AS matched_terms,
                    STRING_AGG(DISTINCT match_reason, ', ') AS match_reason
                FROM candidate_ids
                GROUP BY segment_id
                ORDER BY SUM(score) DESC
                LIMIT :candidate_limit
            )
            SELECT
                s.id,
                s.segment_key,
                s.title,
                s.position,
                s.structural_unit_id,
                s.content,
                COALESCE(s.normalized_content, s.content, '') AS normalized_content,
                s.content_gloss,
                LEFT(COALESCE(s.normalized_content, s.content, ''), 120) AS content_preview,
                w.id AS work_id,
                w.title AS work_title,
                tv.id AS text_version_id,
                tv.title AS text_version_title,
                w.collection_id,
                w.tradition_id,
                tr.name AS tradition_name,
                tv.language_id,
                lang.name AS language_name,
                r.match_score,
                r.match_reason,
                r.matched_terms
            FROM ranked r
            JOIN segments s ON s.id = r.segment_id
            JOIN text_versions tv ON tv.id = s.text_version_id
            JOIN works w ON w.id = tv.work_id
            JOIN traditions tr ON tr.id = w.tradition_id
            JOIN languages lang ON lang.id = tv.language_id
            {final_where_sql}
            ORDER BY r.match_score DESC, s.position
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()

    payloads: list[dict[str, Any]] = []
    for row in rows:
        matched_terms = [term for term in str(row["matched_terms"] or "").split(" || ") if term]
        payloads.append(
            {
            "id": str(row["id"]),
            "segment_key": str(row["segment_key"]),
            "title": row["title"],
            "position": int(row["position"] or 0),
            "structural_unit_id": str(row["structural_unit_id"]) if row["structural_unit_id"] else None,
            "work_title": str(row["work_title"]),
            "text_version_title": str(row["text_version_title"]),
            "tradition_name": str(row["tradition_name"]),
            "language_name": str(row["language_name"]),
            "content_preview": str(row["content_preview"] or ""),
            "content": str(row["content"] or ""),
            "normalized_content": str(row["normalized_content"] or ""),
            "content_gloss": row["content_gloss"],
            "is_sample": False,
            "work_id": str(row["work_id"]),
            "text_version_id": str(row["text_version_id"]),
            "collection_id": str(row["collection_id"]),
            "tradition_id": str(row["tradition_id"]),
            "language_id": str(row["language_id"]),
            "match_reason": str(row["match_reason"]),
            "match_score": float(row["match_score"] or 0.0),
            "matched_query_terms": matched_terms,
            "concept_labels": [],
        }
        )
    return payloads


def _balanced_contexts(items: list[dict[str, Any]], *, top_k: int, balance: bool) -> list[dict[str, Any]]:
    ranked = sorted(items, key=lambda item: (-float(item.get("retrieval_score") or 0.0), item.get("position", 0)))
    if not balance:
        return ranked[:top_k]

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in ranked:
        groups[str(item.get("tradition_id") or item.get("tradition_name") or "")].append(item)

    ordered_traditions = [item for item in TRADITION_ORDER if item in groups]
    ordered_traditions.extend(sorted(set(groups) - set(ordered_traditions)))
    balanced: list[dict[str, Any]] = []
    while len(balanced) < top_k and any(groups.values()):
        for tradition in ordered_traditions:
            if not groups[tradition]:
                continue
            balanced.append(groups[tradition].pop(0))
            if len(balanced) >= top_k:
                break
    return balanced


def _load_text_unit_summary_map(
    session: Session,
    owner_refs: set[tuple[str, str]],
) -> dict[tuple[str, str], str]:
    if not owner_refs:
        return {}
    owner_types = sorted({owner_type for owner_type, _owner_id in owner_refs})
    owner_ids = sorted({owner_id for _owner_type, owner_id in owner_refs})
    try:
        rows = session.scalars(
            select(TextUnitSummary).where(
                TextUnitSummary.summary_kind == "rag_context",
                TextUnitSummary.owner_type.in_(owner_types),
                TextUnitSummary.owner_id.in_(owner_ids),
            ).order_by(TextUnitSummary.id.desc())
        ).all()
    except Exception:
        session.rollback()
        return {}

    summary_map: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row.owner_type, row.owner_id)
        if key not in owner_refs or key in summary_map:
            continue
        summary_map[key] = _truncate_text(row.summary, SUMMARY_TEXT_LIMIT)
    return summary_map


def _indexed_summary(
    summary_map: dict[tuple[str, str], str],
    owner_type: str,
    owner_id: Optional[str],
) -> str:
    if not owner_id:
        return ""
    return summary_map.get((owner_type, owner_id), "")


def _work_context_summary(
    segment: Segment,
    item: dict[str, Any],
    summary_map: dict[tuple[str, str], str],
) -> tuple[str, str]:
    work = segment.text_version.work
    indexed_summary = _indexed_summary(summary_map, "work", work.id)
    if indexed_summary:
        return indexed_summary, "generated"
    stored_summary = _truncate_text(work.summary, SUMMARY_TEXT_LIMIT)
    if stored_summary:
        return stored_summary, "stored"

    title_bits = [work.title]
    if work.title_english:
        title_bits.append(work.title_english)
    if work.title_transliterated:
        title_bits.append(work.title_transliterated)
    metadata_bits = [
        " / ".join(bit for bit in title_bits if bit),
        str(item.get("tradition_name") or work.tradition.name),
        str(item.get("language_name") or segment.text_version.language.name),
    ]
    if work.canonical_code:
        metadata_bits.append(f"编号 {work.canonical_code}")
    if work.pitaka_division:
        metadata_bits.append(f"部类 {work.pitaka_division}")
    if work.fascicle_count:
        metadata_bits.append(f"{work.fascicle_count} 卷")
    return _truncate_text("；".join(bit for bit in metadata_bits if bit), SUMMARY_TEXT_LIMIT), "metadata"


def _text_version_context_summary(
    segment: Segment,
    summary_map: dict[tuple[str, str], str],
) -> tuple[str, str]:
    text_version = segment.text_version
    indexed_summary = _indexed_summary(summary_map, "text_version", text_version.id)
    if indexed_summary:
        return indexed_summary, "generated"
    stored_summary = _truncate_text(text_version.summary, SUMMARY_TEXT_LIMIT)
    if stored_summary:
        return stored_summary, "stored"

    metadata_bits = [
        text_version.title,
        text_version.version_label,
        text_version.language.name,
    ]
    if text_version.script_note:
        metadata_bits.append(text_version.script_note)
    if text_version.date_note:
        metadata_bits.append(text_version.date_note)
    return _truncate_text("；".join(bit for bit in metadata_bits if bit), SUMMARY_TEXT_LIMIT), "metadata"


def _structural_unit_context(unit: Optional[StructuralUnit]) -> Optional[dict[str, Any]]:
    if unit is None:
        return None
    return {
        "id": unit.id,
        "unit_type": unit.unit_type,
        "label": unit.label,
        "title": unit.title,
        "path": unit.path,
        "position": unit.position,
        "depth": unit.depth,
    }


def _nearby_segment_payload(segment: Segment, *, center_position: int) -> dict[str, Any]:
    relation = "命中段"
    if segment.position < center_position:
        relation = "前文"
    elif segment.position > center_position:
        relation = "后文"
    return {
        "id": segment.id,
        "segment_key": segment.segment_key,
        "title": segment.title,
        "position": segment.position,
        "relation": relation,
        "is_hit": segment.position == center_position,
        "content_preview": _truncate_text(segment.normalized_content or segment.content, CONTEXT_TEXT_LIMIT),
        "content_gloss": _truncate_text(segment.content_gloss, CONTEXT_TEXT_LIMIT),
    }


def _enrich_contexts_with_neighborhood(
    session: Session,
    contexts: list[dict[str, Any]],
    *,
    window: int = NEARBY_CONTEXT_WINDOW,
) -> list[dict[str, Any]]:
    segment_ids = [str(item.get("id")) for item in contexts if item.get("id")]
    if not segment_ids:
        return contexts

    stmt = (
        select(Segment)
        .where(Segment.id.in_(segment_ids))
        .options(
            selectinload(Segment.structural_unit),
            selectinload(Segment.text_version).selectinload(TextVersion.language),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.collection),
            selectinload(Segment.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
        )
    )
    segment_by_id = {segment.id: segment for segment in session.scalars(stmt).unique().all()}
    owner_refs: set[tuple[str, str]] = set()
    for segment in segment_by_id.values():
        owner_refs.add(("work", segment.text_version.work_id))
        owner_refs.add(("text_version", segment.text_version_id))
        if segment.structural_unit_id:
            owner_refs.add(("structural_unit", segment.structural_unit_id))
    summary_map = _load_text_unit_summary_map(session, owner_refs)
    nearby_cache: dict[tuple[str, int], list[Segment]] = {}

    for item in contexts:
        segment = segment_by_id.get(str(item.get("id") or ""))
        if segment is None:
            continue

        work_summary, work_summary_source = _work_context_summary(segment, item, summary_map)
        version_summary, version_summary_source = _text_version_context_summary(segment, summary_map)
        item["work_summary"] = work_summary
        item["work_summary_source"] = work_summary_source
        item["text_version_summary"] = version_summary
        item["text_version_summary_source"] = version_summary_source
        item["structural_unit_summary"] = _indexed_summary(summary_map, "structural_unit", segment.structural_unit_id)
        item["structural_unit_id"] = segment.structural_unit_id
        item["structural_unit_context"] = _structural_unit_context(segment.structural_unit)
        item["context_window"] = window

        cache_key = (segment.text_version_id, int(segment.position or 0))
        if cache_key not in nearby_cache:
            center_position = cache_key[1]
            nearby_stmt = (
                select(Segment)
                .where(
                    Segment.text_version_id == segment.text_version_id,
                    Segment.position >= center_position - window,
                    Segment.position <= center_position + window,
                )
                .order_by(Segment.position, Segment.id)
            )
            nearby_cache[cache_key] = list(session.scalars(nearby_stmt).all())
        item["nearby_segments"] = [
            _nearby_segment_payload(nearby_segment, center_position=cache_key[1])
            for nearby_segment in nearby_cache[cache_key]
        ]

    return contexts


def retrieve_cross_tradition_contexts(
    session: Session,
    *,
    query_text: str,
    top_k: int = 12,
    retrieval_mode: str = "hybrid",
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
) -> dict[str, Any]:
    expanded_terms = expand_query_terms(query_text)
    selected_traditions = _selected_tradition_ids(session, tradition_id)
    embedding_models_by_tradition = _available_embedding_models_by_tradition(session)
    merged: dict[str, dict[str, Any]] = {}
    keyword_result_count = 0
    vector_result_count = 0
    vector_statuses: list[dict[str, Any]] = []

    use_keyword = retrieval_mode in {"hybrid", "keyword"}
    use_vector = retrieval_mode in {"hybrid", "vector"}
    per_query_limit = min(max(top_k, MAX_KEYWORD_RESULTS_PER_TERM), MAX_KEYWORD_RESULTS_PER_TERM)

    if use_keyword:
        for trad_index, tradition in enumerate(selected_traditions):
            keyword_terms = _keyword_terms_for_tradition(expanded_terms, tradition)
            term_weights = {str(item["term"]).casefold(): float(item["weight"]) for item in keyword_terms}
            try:
                hits = _fast_keyword_matches(
                    session,
                    terms=[str(item["term"]) for item in keyword_terms],
                    tradition_id=tradition,
                    collection_id=collection_id,
                    language_id=language_id,
                    limit=max(top_k * 4, per_query_limit),
                )
            except Exception:
                session.rollback()
                continue
            keyword_result_count += len(hits)
            for rank, item in enumerate(hits, start=1):
                base_score = float(item.get("match_score") or 0.0)
                matched_terms = item.get("matched_query_terms") or []
                query_bonus = max([term_weights.get(str(term).casefold(), 0.72) for term in matched_terms] or [0.72])
                tradition_bonus = max(0.0, 0.06 - trad_index * 0.01)
                retrieval_score = query_bonus + tradition_bonus + min(base_score, 6.0) * 0.2 + 0.42 / rank
                _merge_candidate(
                    merged,
                    item,
                    retrieval_score=retrieval_score,
                    channel="keyword",
                    query_term=", ".join(matched_terms),
                )

    if use_vector:
        semantic_query = _semantic_query(query_text, expanded_terms)
        vector_groups: dict[str, list[str]] = defaultdict(list)
        for tradition in selected_traditions:
            models = embedding_models_by_tradition.get(tradition) or []
            if not models:
                vector_statuses.append(
                    {
                        "tradition_id": tradition,
                        "status": "skipped",
                        "message": "No persisted segment embedding model was found for this tradition.",
                    }
                )
                continue
            model = models[0]["embedding_model"]
            skip_reason = _vector_runtime_skip_reason(model, tradition)
            if skip_reason:
                vector_statuses.append(
                    {
                        "tradition_id": tradition,
                        "status": "skipped",
                        "embedding_model": model,
                        "message": skip_reason,
                    }
                )
                continue
            vector_groups[model].append(tradition)

        for model, traditions_for_model in vector_groups.items():
            search_tradition = traditions_for_model[0] if len(traditions_for_model) == 1 else None
            try:
                payload = vector_service.vector_search(
                    session,
                    query_text=semantic_query,
                    top_k=max(top_k, 10),
                    tradition_id=search_tradition,
                    collection_id=collection_id,
                    language_id=language_id,
                    embedding_model=model,
                )
            except Exception as exc:
                session.rollback()
                for tradition in traditions_for_model:
                    vector_statuses.append(
                        {
                            "tradition_id": tradition,
                            "status": "error",
                            "embedding_model": model,
                            "message": str(exc),
                        }
                    )
                continue
            for tradition in traditions_for_model:
                vector_statuses.append(
                    {
                        "tradition_id": tradition,
                        "status": payload.get("status"),
                        "embedding_model": payload.get("embedding_model"),
                        "indexed_owners": payload.get("indexed_owners"),
                        "message": payload.get("message"),
                    }
                )
            allowed_traditions = set(traditions_for_model)
            results = [
                item
                for item in (payload.get("results") or [])
                if str(item.get("tradition_id") or "") in allowed_traditions
            ]
            vector_result_count += len(results)
            for rank, item in enumerate(results, start=1):
                # Raw cosine scores come from different embedding models, so rank carries most of the weight.
                raw_score = max(0.0, min(1.0, float(item.get("match_score") or 0.0)))
                retrieval_score = 1.25 + (0.78 / rank) + raw_score * 0.22
                _merge_candidate(
                    merged,
                    item,
                    retrieval_score=retrieval_score,
                    channel="vector",
                    query_term=semantic_query,
                )

    all_results = list(merged.values())
    contexts = _balanced_contexts(
        all_results,
        top_k=top_k,
        balance=tradition_id is None and len(selected_traditions) > 1,
    )
    contexts = _enrich_contexts_with_neighborhood(session, contexts)
    return {
        "query_text": query_text,
        "retrieval_mode": retrieval_mode,
        "expanded_terms": expanded_terms,
        "selected_traditions": selected_traditions,
        "embedding_models_by_tradition": embedding_models_by_tradition,
        "vector_statuses": vector_statuses,
        "keyword_result_count": keyword_result_count,
        "vector_result_count": vector_result_count,
        "results": sorted(
            all_results,
            key=lambda item: (-float(item.get("retrieval_score") or 0.0), item.get("position", 0)),
        ),
        "contexts": contexts,
    }


def _citation_line(item: dict[str, Any], index: int) -> str:
    return (
        f"[E{index}] {item.get('segment_key')} | {item.get('work_title')} | "
        f"{item.get('text_version_title')} | {item.get('tradition_name')}"
    )


def build_answer_plan(
    *,
    query_text: str,
    contexts: list[dict[str, Any]],
    expanded_terms: list[dict[str, Any]],
    detected_concepts: list[dict[str, Any]],
    explanation_style: str,
) -> list[dict[str, Any]]:
    traditions = sorted({str(item.get("tradition_name") or item.get("tradition_id") or "") for item in contexts if item})
    has_nearby = any(item.get("nearby_segments") for item in contexts)
    has_structural_summary = any(item.get("structural_unit_summary") for item in contexts)
    has_work_summary = any(item.get("work_summary") for item in contexts)
    concept_labels = [str(item.get("label") or item.get("slug") or "") for item in detected_concepts if item]
    expanded_preview = [str(item.get("term") or "") for item in expanded_terms[:8]]
    style_label = {
        "plain": "白话导读",
        "scholarly": "学术注释",
        "comparative": "三传承比较",
        "line_by_line": "逐句/逐层解释",
    }.get(explanation_style, "综合解说")
    question_type = "概念/问题"
    if "？" in query_text or "?" in query_text or len(query_text) > 8:
        question_type = "解释型问题"
    if any(mark in query_text for mark in ["经", "sutta", "sutra", "Toh", "T0"]):
        question_type = "经名/文本型问题"

    return [
        {
            "step": 1,
            "title": "识别问题",
            "description": f"把“{_truncate_text(query_text, 80)}”判断为{question_type}，采用{style_label}回答。",
            "uses": "原始问题、解说风格、已识别概念",
            "status": "ready",
            "details": concept_labels[:6],
        },
        {
            "step": 2,
            "title": "跨语种展开",
            "description": "把中文概念扩展为中文、英文、巴利/梵语、藏文转写等检索词，避免只搜到单一传统。",
            "uses": "概念词表、原始问题",
            "status": "ready" if expanded_preview else "missing",
            "details": expanded_preview,
        },
        {
            "step": 3,
            "title": "分轨检索",
            "description": "关键词和向量分开召回；不同传统的向量模型不强行混算，只融合名次和证据通道。",
            "uses": "关键词结果、向量结果、传统平衡",
            "status": "ready" if contexts else "missing",
            "details": traditions[:6],
        },
        {
            "step": 4,
            "title": "扩展上下文",
            "description": "每个命中段向外看前后文，并补入卷/结构摘要与作品摘要，避免只凭一句话解释。",
            "uses": "命中段、前后文、卷/结构摘要、作品摘要",
            "status": "ready" if has_nearby or has_structural_summary or has_work_summary else "partial",
            "details": [
                "前后文" if has_nearby else "前后文不足",
                "卷/结构摘要" if has_structural_summary else "卷/结构摘要待生成",
                "作品摘要" if has_work_summary else "作品摘要不足",
            ],
        },
        {
            "step": 5,
            "title": "综合解说",
            "description": "先给简明结论，再引用关键证据，最后比较传统差异和标注证据不足处。",
            "uses": "证据编号、传统分布、上下文层级",
            "status": "ready" if contexts else "blocked",
            "details": ["结论", "证据", "概念分层", "传统差异", "误解提醒"],
        },
    ]


def _evidence_text(item: dict[str, Any], *, limit: int = 680) -> str:
    content = item.get("normalized_content") or item.get("content") or item.get("content_preview") or ""
    gloss = item.get("content_gloss") or ""
    pieces = []
    work_summary = item.get("work_summary") or ""
    version_summary = item.get("text_version_summary") or ""
    unit = item.get("structural_unit_context") or {}
    if work_summary:
        source = {
            "generated": "生成摘要",
            "stored": "已有摘要",
        }.get(str(item.get("work_summary_source") or ""), "元数据背景")
        pieces.append(f"作品背景({source}): " + _truncate_text(work_summary, SUMMARY_TEXT_LIMIT))
    if version_summary and version_summary != work_summary:
        source = {
            "generated": "生成摘要",
            "stored": "已有摘要",
        }.get(str(item.get("text_version_summary_source") or ""), "版本背景")
        pieces.append(f"版本背景({source}): " + _truncate_text(version_summary, SUMMARY_TEXT_LIMIT))
    structural_summary = item.get("structural_unit_summary") or ""
    if structural_summary:
        pieces.append("卷/结构摘要(生成摘要): " + _truncate_text(structural_summary, SUMMARY_TEXT_LIMIT))
    if unit:
        unit_bits = [unit.get("unit_type"), unit.get("label"), unit.get("title"), unit.get("path")]
        pieces.append("结构位置: " + _truncate_text(" / ".join(str(bit) for bit in unit_bits if bit), 240))
    if content:
        pieces.append("命中段正文: " + _truncate_text(content, limit))
    if gloss:
        pieces.append("命中段译文/gloss: " + _truncate_text(gloss, limit))
    nearby_segments = item.get("nearby_segments") or []
    if nearby_segments:
        nearby_lines = []
        for nearby in nearby_segments:
            body = nearby.get("content_gloss") or nearby.get("content_preview") or ""
            nearby_lines.append(
                f"- {nearby.get('relation')} {nearby.get('segment_key')}: "
                f"{_truncate_text(body, 220)}"
            )
        pieces.append("前后文窗口:\n" + "\n".join(nearby_lines))
    return "\n".join(pieces)


def build_explainer_prompts(
    *,
    query_text: str,
    contexts: list[dict[str, Any]],
    expanded_terms: list[dict[str, Any]],
    explanation_style: str,
) -> dict[str, str]:
    style_note = {
        "plain": "面向普通读者，用白话解释，但不要牺牲准确性。",
        "scholarly": "用学术注释风格，强调术语、文本证据和不同传统的边界。",
        "comparative": "重点做汉传、巴利、藏传三传承对读。",
        "line_by_line": "如果问题包含具体经文，尽量逐句/逐层解释。",
    }.get(explanation_style, "兼顾白话导读和学术准确性。")
    system_prompt = (
        "你是一个谨慎的佛典 RAG 解说助手。你必须用中文回答。"
        "只能依据给定的 retrieved evidence 进行解释；可以做推论，但必须明确标注为推论。"
        "每个关键判断都要引用 [E1] 这样的证据编号。"
        "如果证据不足，直接说证据不足，不要凭空补充宗派常识。"
        "遇到跨语种材料时，要说明这是正文、英译/gloss，还是术语对应。"
        "证据中的作品背景、版本背景、结构位置和前后文窗口只能用来帮助理解命中段，不要把元数据当成直接经文。"
    )
    evidence_blocks = []
    for index, item in enumerate(contexts, start=1):
        evidence_blocks.append(
            "\n".join(
                [
                    _citation_line(item, index),
                    f"检索通道: {', '.join(item.get('retrieval_channels') or [])}",
                    f"匹配词: {', '.join(item.get('matched_query_terms') or [])}",
                    _evidence_text(item),
                ]
            )
        )
    answer_plan = build_answer_plan(
        query_text=query_text,
        contexts=contexts,
        expanded_terms=expanded_terms,
        detected_concepts=[],
        explanation_style=explanation_style,
    )
    plan_lines = [
        f"{item['step']}. {item['title']}: {item['description']} [{item['status']}]"
        for item in answer_plan
    ]
    expanded_line = ", ".join(item["term"] for item in expanded_terms)
    user_prompt = (
        f"问题：{query_text}\n"
        f"讲解风格：{style_note}\n"
        f"跨语种扩展查询词：{expanded_line}\n\n"
        "建议解题计划：\n"
        + "\n".join(plan_lines)
        + "\n\n"
        "请按下面结构回答：\n"
        "1. 先给一个简明结论。\n"
        "2. 列出最关键的经文证据，并引用编号。\n"
        "3. 分层解释概念本身。\n"
        "4. 如证据覆盖多个传统，请比较汉传、巴利、藏传的差异。\n"
        "5. 说明容易误解的地方。\n"
        "6. 给出下一步可以继续追问的问题。\n\n"
        "Retrieved evidence:\n\n"
        + "\n\n".join(evidence_blocks)
    )
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def _call_llm(*, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> tuple[str, Optional[str]]:
    if not settings.llm_api_key:
        return "", "LLM_API_KEY/OPENAI_API_KEY is not configured; returned prompt-only answer."

    if settings.llm_api_url.rstrip("/").endswith("/chat/completions"):
        request_body = {
            "model": model or settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    else:
        request_body = {
            "model": model or settings.llm_model,
            "input": [
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "store": False,
        }
    encoded_body = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    last_error = ""
    for attempt in range(3):
        request = urllib.request.Request(
            settings.llm_api_url,
            data=encoded_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = f"LLM request failed with HTTP {exc.code}: {body[:500]}"
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                return "", last_error
            time.sleep(1.5 * (2**attempt))
        except Exception as exc:
            last_error = f"LLM request failed: {exc}"
            if attempt == 2:
                return "", last_error
            time.sleep(1.5 * (2**attempt))
    else:
        return "", last_error or "LLM request failed."

    if payload.get("output_text"):
        return str(payload["output_text"]).strip(), None
    choices = payload.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip(), None
        if isinstance(content, list):
            text_values = [
                str(item.get("text") or "")
                for item in content
                if isinstance(item, dict) and item.get("text")
            ]
            if text_values:
                return "\n".join(text_values).strip(), None
    output_parts: list[str] = []
    for item in payload.get("output") or []:
        for content_item in item.get("content") or []:
            if isinstance(content_item, dict):
                text_value = content_item.get("text")
                if text_value:
                    output_parts.append(str(text_value))
            elif isinstance(content_item, str):
                output_parts.append(content_item)
    if output_parts:
        return "\n".join(output_parts).strip(), None
    if payload.get("error"):
        return "", f"LLM response error: {payload['error']}"
    return "", "LLM response did not contain a usable answer."


def _extractive_fallback_answer(query_text: str, contexts: list[dict[str, Any]], expanded_terms: list[dict[str, Any]]) -> str:
    if not contexts:
        return (
            "当前没有检索到足够证据。可以尝试换一个术语，或使用更具体的经名/概念名。"
        )

    by_tradition: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, item in enumerate(contexts, start=1):
        by_tradition[str(item.get("tradition_name") or "未分类")].append((index, item))

    lines = [
        f"当前先给出基于检索证据的抽取式解说，问题是：{query_text}",
        "",
        "简明结论：",
        "这些证据可以作为讲解入口；系统已尽量补入作品/版本背景和命中段前后文，完整讲解需要 LLM 成功综合生成。",
        "",
        "跨语种扩展词：",
        ", ".join(item["term"] for item in expanded_terms),
        "",
        "证据分布：",
    ]
    for tradition, items in by_tradition.items():
        citations = ", ".join(f"[E{index}]" for index, _item in items[:4])
        lines.append(f"- {tradition}: {citations}")
    lines.append("")
    lines.append("可读证据摘录：")
    for index, item in enumerate(contexts[:6], start=1):
        nearby = item.get("nearby_segments") or []
        preview = _normalise_text(item.get("content_gloss") or item.get("content_preview") or item.get("content") or "")
        if nearby:
            preview = _normalise_text(" / ".join((seg.get("content_gloss") or seg.get("content_preview") or "") for seg in nearby[:3]))
        lines.append(f"- [E{index}] {item.get('work_title')}：{preview[:180]}")
    return "\n".join(lines)


def explain_sutra_query(
    session: Session,
    *,
    query_text: str,
    top_k: int = 12,
    retrieval_mode: str = "hybrid",
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    explanation_style: str = "comparative",
    generate_answer: bool = True,
) -> dict[str, Any]:
    query_text = _normalise_text(query_text)
    top_k = max(1, min(int(top_k or 12), 24))
    if retrieval_mode not in {"hybrid", "keyword", "vector"}:
        retrieval_mode = "hybrid"
    if explanation_style not in {"plain", "scholarly", "comparative", "line_by_line"}:
        explanation_style = "comparative"

    retrieval = retrieve_cross_tradition_contexts(
        session,
        query_text=query_text,
        top_k=top_k,
        retrieval_mode=retrieval_mode,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
    )
    detected_concepts = concept_analysis_service.detect_query_concepts(query_text)
    answer_plan = build_answer_plan(
        query_text=query_text,
        contexts=retrieval["contexts"],
        expanded_terms=retrieval["expanded_terms"],
        detected_concepts=detected_concepts,
        explanation_style=explanation_style,
    )
    prompts = build_explainer_prompts(
        query_text=query_text,
        contexts=retrieval["contexts"],
        expanded_terms=retrieval["expanded_terms"],
        explanation_style=explanation_style,
    )
    answer = ""
    llm_error = None
    status = "prompt_only"
    if generate_answer:
        answer, llm_error = _call_llm(
            system_prompt=prompts["system_prompt"],
            user_prompt=prompts["user_prompt"],
        )
        status = "generated" if answer and not llm_error else "llm_error"
    if not answer:
        answer = _extractive_fallback_answer(query_text, retrieval["contexts"], retrieval["expanded_terms"])
        if llm_error and status == "llm_error":
            status = "fallback"

    return {
        "status": status,
        "message": llm_error or "Sutra explainer response generated from cross-tradition RAG evidence.",
        "query_text": query_text,
        "retrieval_mode": retrieval_mode,
        "explanation_style": explanation_style,
        "answer_plan": answer_plan,
        "detected_concepts": detected_concepts,
        "expanded_terms": retrieval["expanded_terms"],
        "selected_traditions": retrieval["selected_traditions"],
        "embedding_models_by_tradition": retrieval["embedding_models_by_tradition"],
        "vector_statuses": retrieval["vector_statuses"],
        "keyword_result_count": retrieval["keyword_result_count"],
        "vector_result_count": retrieval["vector_result_count"],
        "contexts": retrieval["contexts"],
        "results": retrieval["results"][: max(top_k * 3, top_k)],
        "system_prompt": prompts["system_prompt"],
        "user_prompt": prompts["user_prompt"],
        "answer": answer,
        "llm_model": settings.llm_model if settings.llm_api_key else "",
    }
