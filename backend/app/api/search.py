from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas.api import (
    HybridSearchRequest,
    HybridSearchResponse,
    RagQueryRequest,
    RagQueryResponse,
    SegmentSummary,
    SutraExplainRequest,
    SutraExplainResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)
from backend.app.services import rag_service, retrieval_service, search_service, sutra_explainer_service, vector_service


router = APIRouter(tags=["search"])


@router.get("/search/segments", response_model=list[SegmentSummary])
def search_segments(
    q: str = Query(min_length=1),
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return search_service.search_segments(
        db,
        q=q,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        limit=limit,
    )


@router.post("/vector/search", response_model=VectorSearchResponse)
def vector_search(payload: VectorSearchRequest, db: Session = Depends(get_db)) -> dict:
    return vector_service.vector_search(
        db,
        query_text=payload.query_text,
        top_k=payload.top_k,
        tradition_id=payload.tradition_id,
        collection_id=payload.collection_id,
        language_id=payload.language_id,
    )


@router.post("/hybrid/search", response_model=HybridSearchResponse)
def hybrid_search(payload: HybridSearchRequest, db: Session = Depends(get_db)) -> dict:
    return retrieval_service.hybrid_search(
        db,
        query_text=payload.query_text,
        top_k=payload.top_k,
        tradition_id=payload.tradition_id,
        collection_id=payload.collection_id,
        language_id=payload.language_id,
    )


@router.post("/rag/query", response_model=RagQueryResponse)
def rag_query(payload: RagQueryRequest, db: Session = Depends(get_db)) -> dict:
    return rag_service.build_rag_context(
        db,
        query_text=payload.query_text,
        top_k=payload.top_k,
        retrieval_mode=payload.retrieval_mode,
        tradition_id=payload.tradition_id,
        collection_id=payload.collection_id,
        language_id=payload.language_id,
    )


@router.post("/rag/explain", response_model=SutraExplainResponse)
def sutra_explain(payload: SutraExplainRequest, db: Session = Depends(get_db)) -> dict:
    return sutra_explainer_service.explain_sutra_query(
        db,
        query_text=payload.query_text,
        top_k=payload.top_k,
        retrieval_mode=payload.retrieval_mode,
        tradition_id=payload.tradition_id,
        collection_id=payload.collection_id,
        language_id=payload.language_id,
        explanation_style=payload.explanation_style,
        generate_answer=payload.generate_answer,
    )
