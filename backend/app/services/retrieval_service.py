from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.services import search_service, vector_service

KEYWORD_RANK_BONUS = 1.0
VECTOR_RANK_BONUS = 0.5
KEYWORD_SAMPLE_PENALTY = 4.25
VECTOR_SAMPLE_PENALTY = 1.0
HYBRID_OVERLAP_BONUS = 0.25


def _sample_penalty(item: dict[str, Any], *, channel: str) -> float:
    if not item.get("is_sample"):
        return 0.0
    if channel == "keyword":
        return KEYWORD_SAMPLE_PENALTY
    if channel == "vector":
        return VECTOR_SAMPLE_PENALTY
    return 0.0


def merge_retrieval_results(
    *,
    keyword_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for rank, item in enumerate(keyword_hits, start=1):
        payload = dict(item)
        payload["retrieval_channels"] = ["keyword"]
        payload["retrieval_score"] = (
            float(item.get("match_score") or 0.0)
            + (KEYWORD_RANK_BONUS / rank)
            - _sample_penalty(item, channel="keyword")
        )
        merged[item["id"]] = payload

    for rank, item in enumerate(vector_hits, start=1):
        existing = merged.get(item["id"])
        vector_score = (
            float(item.get("match_score") or 0.0)
            + (VECTOR_RANK_BONUS / rank)
            - _sample_penalty(item, channel="vector")
        )
        if existing:
            existing["retrieval_score"] += vector_score + HYBRID_OVERLAP_BONUS
            existing["retrieval_channels"] = sorted(set(existing["retrieval_channels"] + ["vector"]))
            existing["match_reason"] = "hybrid"
            continue

        payload = dict(item)
        payload["retrieval_channels"] = ["vector"]
        payload["retrieval_score"] = vector_score
        merged[item["id"]] = payload

    ranked = sorted(
        merged.values(),
        key=lambda item: (-float(item.get("retrieval_score") or 0.0), item.get("position", 0)),
    )
    return ranked[:top_k]


def hybrid_search(
    session: Session,
    *,
    query_text: str,
    top_k: int = 8,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    include_content: bool = False,
) -> dict[str, Any]:
    keyword_hits = search_service.retrieve_segment_matches(
        session,
        q=query_text,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        limit=max(top_k, 8),
        include_content=include_content,
    )
    vector_payload = vector_service.vector_search(
        session,
        query_text=query_text,
        top_k=max(top_k, 8),
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
    )
    vector_hits = vector_payload["results"]
    results = merge_retrieval_results(
        keyword_hits=keyword_hits,
        vector_hits=vector_hits,
        top_k=top_k,
    )

    vector_status = vector_payload.get("status") or "ready"
    if vector_status == "ready":
        status = "ready"
        message = "Hybrid retrieval merged keyword and vector candidates."
    else:
        status = "partial"
        message = (
            "Hybrid retrieval returned keyword results while vector retrieval was unavailable: "
            f"{vector_payload.get('message') or 'unknown vector issue'}"
        )

    return {
        "status": status,
        "message": message,
        "configured_backend": vector_payload["configured_backend"],
        "embedding_model": vector_payload["embedding_model"],
        "indexed_owners": vector_payload["indexed_owners"],
        "keyword_result_count": len(keyword_hits),
        "vector_result_count": len(vector_hits),
        "results": results,
        "pgvector_hint": vector_payload["pgvector_hint"],
    }
