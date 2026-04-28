from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas.api import ConceptTagDetail, ConceptTagSummary
from backend.app.services import catalog_service


router = APIRouter(tags=["concepts"])


@router.get("/concepts", response_model=list[ConceptTagSummary])
def get_concepts(db: Session = Depends(get_db)) -> list[dict]:
    return catalog_service.list_concepts(db)


@router.get("/concepts/{concept_slug}", response_model=ConceptTagDetail)
def get_concept(concept_slug: str, db: Session = Depends(get_db)) -> dict:
    concept = catalog_service.get_concept_detail(db, concept_slug)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concept
