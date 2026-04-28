from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app import models  # noqa: F401
from backend.app.services.han_catalog_loader import seed_han_catalog_snapshot
from backend.app.services.han_cbeta_xml_loader import seed_han_cbeta_xml_texts
from backend.app.services.han_core_text_loader import seed_han_core_texts
from backend.app.services.search_service import ensure_postgres_search_objects
from backend.app.services.sample_loader import seed_sample_corpus
from backend.app.services.vector_service import ensure_postgres_vector_objects, resolve_embedding_runtime


def ensure_postgres_extensions() -> None:
    if not settings.uses_postgres:
        return

    runtime = resolve_embedding_runtime()
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        ensure_postgres_search_objects(connection)
        ensure_postgres_vector_objects(connection, dimension=runtime.dimension)


def initialize_database(*, reset_schema: bool = False) -> None:
    if settings.uses_sqlite:
        Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    ensure_postgres_extensions()
    if reset_schema:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if settings.enable_auto_seed:
        with SessionLocal() as session:
            seed_sample_corpus(session)
            seed_han_catalog_snapshot(session)
            if settings.han_core_text_source_path.exists():
                seed_han_core_texts(session)
            if settings.han_cbeta_manifest_path.exists():
                seed_han_cbeta_xml_texts(session)
