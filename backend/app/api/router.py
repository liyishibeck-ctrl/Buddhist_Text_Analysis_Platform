from __future__ import annotations

from fastapi import APIRouter

from backend.app.api import catalog, concepts, pages, search, system


api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(catalog.router)
api_router.include_router(search.router)
api_router.include_router(concepts.router)

page_router = APIRouter()
page_router.include_router(pages.router)
