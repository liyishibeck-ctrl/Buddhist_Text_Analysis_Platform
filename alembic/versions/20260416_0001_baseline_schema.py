"""baseline schema

Revision ID: 20260416_0001
Revises:
Create Date: 2026-04-16 15:30:00
"""
from __future__ import annotations

from alembic import op

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app import models  # noqa: F401


revision = "20260416_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if settings.uses_postgres:
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
