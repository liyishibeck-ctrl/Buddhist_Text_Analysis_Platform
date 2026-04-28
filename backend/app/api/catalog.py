from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas.api import (
    CollectionSummary,
    HanCatalogOverview,
    ParallelLinkTarget,
    SegmentDetail,
    SegmentSimilarityResponse,
    SegmentSummary,
    TextVersionDetail,
    TextVersionSummary,
    WorkDetail,
    WorkSummary,
)
from backend.app.services import catalog_service, vector_service


router = APIRouter(tags=["catalog"])


@router.get("/collections", response_model=list[CollectionSummary])
def get_collections(tradition_id: Optional[str] = None, db: Session = Depends(get_db)) -> list[dict]:
    return catalog_service.list_collections(db, tradition_id=tradition_id)


@router.get("/works", response_model=list[WorkSummary])
def get_works(
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    pitaka_division: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return catalog_service.list_works(
        db,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        pitaka_division=pitaka_division,
        q=q,
    )


@router.get("/works/{work_id}", response_model=WorkDetail)
def get_work(work_id: str, db: Session = Depends(get_db)) -> dict:
    work = catalog_service.get_work_detail(db, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work


@router.get("/text-versions", response_model=list[TextVersionSummary])
def get_text_versions(
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    work_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return catalog_service.list_text_versions(
        db,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
    )


@router.get("/text-versions/{text_version_id}", response_model=TextVersionDetail)
def get_text_version(text_version_id: str, db: Session = Depends(get_db)) -> dict:
    text_version = catalog_service.get_text_version_detail(db, text_version_id)
    if not text_version:
        raise HTTPException(status_code=404, detail="Text version not found")
    return text_version


@router.get("/text-versions/{text_version_id}/structure", response_model=list[dict])
def get_text_version_structure(text_version_id: str, db: Session = Depends(get_db)) -> list[dict]:
    text_version = catalog_service.get_text_version_detail(db, text_version_id)
    if not text_version:
        raise HTTPException(status_code=404, detail="Text version not found")
    return text_version["structure"]


@router.get("/segments", response_model=list[SegmentSummary])
def get_segments(
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    work_id: Optional[str] = None,
    text_version_id: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    return catalog_service.list_segments(
        db,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        work_id=work_id,
        text_version_id=text_version_id,
        q=q,
        limit=limit,
    )


@router.get("/segments/{segment_id}", response_model=SegmentDetail)
def get_segment(segment_id: str, db: Session = Depends(get_db)) -> dict:
    segment = catalog_service.get_segment_detail(db, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.get("/segments/{segment_id}/similar", response_model=SegmentSimilarityResponse)
def get_similar_segments(
    segment_id: str,
    top_k: int = Query(default=5, le=20),
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return vector_service.find_similar_segments(
            db,
            segment_id=segment_id,
            top_k=top_k,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/segments/{segment_id}/parallel-links", response_model=list[ParallelLinkTarget])
def get_segment_parallel_links(segment_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return catalog_service.get_parallel_links_for_segment(db, segment_id)


@router.get("/parallels", response_model=list[dict])
def get_parallels(db: Session = Depends(get_db)) -> list[dict]:
    return catalog_service.list_parallel_links(db)


@router.get("/catalog/han", response_model=HanCatalogOverview)
def get_han_catalog(db: Session = Depends(get_db)) -> dict:
    overview = catalog_service.get_han_catalog_overview(db)
    if not overview:
        raise HTTPException(status_code=404, detail="Han catalog not found")
    return overview
