from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router, page_router
from backend.app.core.config import settings
from backend.app.db.init_db import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    summary="Structured Buddhist corpus MVP with sample data, browsing, search, and alignment views.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.include_router(page_router)
app.include_router(api_router, prefix=settings.api_prefix)
