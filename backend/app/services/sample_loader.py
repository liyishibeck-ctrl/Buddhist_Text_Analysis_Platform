from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models import Source
from backend.app.services.seed_utils import apply_payload, clear_seed_data, load_json_payload


def load_sample_payload(path: Path | None = None) -> dict[str, Any]:
    payload_path = path or settings.sample_corpus_path
    return load_json_payload(payload_path)


def seed_sample_corpus(session: Session, *, force: bool = False) -> bool:
    existing = session.scalar(select(Source.id).where(Source.id == "source-cst4"))
    if existing and not force:
        return False

    payload = load_sample_payload()
    if force:
        clear_seed_data(session)

    apply_payload(session, payload)
    session.commit()
    return True
