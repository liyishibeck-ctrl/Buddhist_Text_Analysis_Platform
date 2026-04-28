from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings


connect_args: dict[str, object] = {}
if settings.uses_sqlite:
    connect_args["check_same_thread"] = False


engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=not settings.uses_sqlite,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
