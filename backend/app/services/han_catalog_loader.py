from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    CatalogNode,
    Collection,
    Language,
    Person,
    Source,
    TextVersion,
    TextVersionPersonRole,
    Tradition,
    Work,
    WorkPersonRole,
)
from backend.app.services.han_catalog_pipeline import (
    HAN_COLLECTION_ID,
    HAN_LANGUAGE_ID,
    HAN_SOURCE_ID,
    HAN_TRADITION_ID,
    build_han_catalog_payload,
    write_han_catalog_bundle,
)
from backend.app.services.seed_utils import apply_payload


def ensure_han_catalog_dependencies(session: Session) -> None:
    if not session.get(Tradition, HAN_TRADITION_ID):
        session.add(
            Tradition(
                id=HAN_TRADITION_ID,
                slug="han",
                name="汉传",
                description="汉传佛教典籍语料与目录层结构。",
                canonical_scope="汉传三藏",
            )
        )
    if not session.get(Language, HAN_LANGUAGE_ID):
        session.add(
            Language(
                id=HAN_LANGUAGE_ID,
                code="lzh",
                name="文言汉文",
                script="Han",
                direction="ltr",
                description="Classical Chinese / Literary Sinitic used for catalog-level Han canon entries.",
            )
        )
    session.flush()


def clear_han_catalog_data(session: Session) -> None:
    text_version_ids = session.scalars(select(TextVersion.id).where(TextVersion.source_id == HAN_SOURCE_ID)).all()
    work_ids = session.scalars(select(Work.id).where(Work.collection_id == HAN_COLLECTION_ID)).all()

    session.query(CatalogNode).filter(CatalogNode.collection_id == HAN_COLLECTION_ID).delete(synchronize_session=False)

    if text_version_ids:
        session.query(TextVersionPersonRole).filter(
            TextVersionPersonRole.text_version_id.in_(text_version_ids)
        ).delete(synchronize_session=False)
    session.query(TextVersion).filter(TextVersion.source_id == HAN_SOURCE_ID).delete(synchronize_session=False)

    if work_ids:
        session.query(WorkPersonRole).filter(WorkPersonRole.work_id.in_(work_ids)).delete(synchronize_session=False)
    session.query(Work).filter(Work.collection_id == HAN_COLLECTION_ID).delete(synchronize_session=False)

    session.query(Person).filter(Person.id.like("person-han-%")).delete(synchronize_session=False)
    session.query(Collection).filter(Collection.id == HAN_COLLECTION_ID).delete(synchronize_session=False)
    session.query(Source).filter(Source.id == HAN_SOURCE_ID).delete(synchronize_session=False)


def seed_han_catalog_snapshot(
    session: Session,
    *,
    force: bool = False,
    source_path: Path | None = None,
    write_bundle: bool = False,
) -> bool:
    ensure_han_catalog_dependencies(session)
    existing = session.scalar(select(Source.id).where(Source.id == HAN_SOURCE_ID))
    if existing and not force:
        return False

    if force:
        clear_han_catalog_data(session)

    payload = build_han_catalog_payload(source_path)
    apply_payload(session, payload)
    session.commit()

    if write_bundle:
        write_han_catalog_bundle(payload)
    return True
