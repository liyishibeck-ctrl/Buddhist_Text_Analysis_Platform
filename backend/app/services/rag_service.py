from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.services import concept_analysis_service, retrieval_service, search_service, vector_service


def _citation_line(item: dict[str, Any]) -> str:
    return (
        f"{item['segment_key']} | {item['work_title']} | "
        f"{item['text_version_title']} | {item['tradition_name']}"
    )


def _context_block(item: dict[str, Any]) -> str:
    body = item.get("content") or item.get("content_preview") or ""
    return f"[{_citation_line(item)}]\n{body}"


def build_rag_context(
    session: Session,
    *,
    query_text: str,
    top_k: int = 8,
    retrieval_mode: str = "hybrid",
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
) -> dict[str, Any]:
    keyword_hits = search_service.retrieve_segment_matches(
        session,
        q=query_text,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        limit=max(top_k, 8),
        include_content=True,
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

    if retrieval_mode == "keyword":
        contexts = keyword_hits[:top_k]
    elif retrieval_mode == "vector":
        contexts = vector_hits[:top_k]
    else:
        contexts = retrieval_service.merge_retrieval_results(
            keyword_hits=keyword_hits,
            vector_hits=vector_hits,
            top_k=top_k,
        )

    detected_concepts = concept_analysis_service.detect_query_concepts(query_text)
    system_prompt = (
        "You are assisting with Buddhist text analysis. Answer only from the retrieved corpus evidence, "
        "cite segment identifiers inline, and distinguish retrieval evidence from inference."
    )
    user_prompt_parts = [
        f"Question: {query_text}",
        "",
        "Retrieved evidence:",
    ]
    user_prompt_parts.extend(_context_block(item) for item in contexts)
    if detected_concepts:
        user_prompt_parts.append("")
        user_prompt_parts.append(
            "Detected concept cues: " + ", ".join(item["label"] for item in detected_concepts)
        )
    user_prompt = "\n\n".join(user_prompt_parts)

    answer_outline = "\n".join(
        f"- {_citation_line(item)} -> {item.get('content_preview') or (item.get('content') or '')[:120]}"
        for item in contexts[:5]
    )

    return {
        "query_text": query_text,
        "retrieval_mode": retrieval_mode,
        "detected_concepts": detected_concepts,
        "keyword_result_count": len(keyword_hits),
        "vector_result_count": len(vector_hits),
        "vector_backend": vector_payload["configured_backend"],
        "embedding_model": vector_payload["embedding_model"],
        "contexts": contexts,
        "keyword_hits": keyword_hits[:top_k],
        "vector_hits": vector_hits[:top_k],
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "answer_outline": answer_outline,
    }
