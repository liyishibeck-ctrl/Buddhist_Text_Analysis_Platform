from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas.api import OverviewStats
from backend.app.services import catalog_service


router = APIRouter(tags=["system"])


@router.get("/overview", response_model=OverviewStats)
def get_overview(db: Session = Depends(get_db)) -> dict:
    return catalog_service.get_overview(db)


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
