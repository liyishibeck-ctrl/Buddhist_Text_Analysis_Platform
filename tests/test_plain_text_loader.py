from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.models import (
    Collection,
    EmbeddingIndexMetadata,
    Language,
    Segment,
    Source,
    TextVersion,
    Tradition,
    Work,
)
from backend.app.services import plain_text_loader


def _make_workspace_test_root() -> Path:
    root = Path("D:/Buddhist_Text_Analysis_Platform/data/processed/test_tmp") / f"plain-loader-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_delete_in_batches_splits_large_id_lists() -> None:
    seen_batches: list[list[str]] = []
    seen_flags: list[bool] = []

    class FakeQuery:
        def __init__(self, batch: list[str]) -> None:
            self.batch = batch

        def delete(self, *, synchronize_session: bool = False) -> None:
            seen_batches.append(list(self.batch))
            seen_flags.append(synchronize_session)

    plain_text_loader._delete_in_batches(
        [f"id-{idx}" for idx in range(9)],
        lambda batch: FakeQuery(batch),
        batch_size=4,
    )

    assert seen_batches == [
        ["id-0", "id-1", "id-2", "id-3"],
        ["id-4", "id-5", "id-6", "id-7"],
        ["id-8"],
    ]
    assert seen_flags == [False, False, False]


def test_clear_plain_text_data_handles_large_segment_sets() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        tradition = Tradition(id="trad-test", slug="trad-test", name="Test Tradition")
        collection = Collection(
            id="coll-test",
            slug="coll-test",
            title="Test Collection",
            tradition_id=tradition.id,
        )
        language = Language(id="lang-test", code="tst", name="Test Language")
        source = Source(
            id="source-test",
            slug="source-test",
            title="Test Source",
            source_type="plain-text",
            is_sample=False,
        )
        work = Work(
            id="work-test",
            slug="work-test",
            tradition_id=tradition.id,
            collection_id=collection.id,
            title="Test Work",
            genre="sutra",
            is_sample=False,
        )
        text_version = TextVersion(
            id="tv-test",
            slug="tv-test",
            work_id=work.id,
            language_id=language.id,
            source_id=source.id,
            title="Test Version",
            version_label="v1",
            is_sample=False,
        )

        session.add_all([tradition, collection, language, source, work, text_version])
        session.add_all(
            Segment(
                id=f"seg-{idx:03d}",
                text_version_id=text_version.id,
                segment_key=f"SEG-{idx:03d}",
                content=f"segment {idx}",
                normalized_content=f"segment {idx}",
                position=idx,
                char_count=9,
            )
            for idx in range(25)
        )
        session.add_all(
            EmbeddingIndexMetadata(
                id=f"meta-{idx:03d}",
                owner_type="segment",
                owner_id=f"seg-{idx:03d}",
                embedding_model="test-model",
                vector_backend="python-fallback",
                dimension=8,
                status="ready",
            )
            for idx in range(25)
        )
        session.commit()

        plain_text_loader.clear_plain_text_data(session, source_id=source.id)
        session.commit()

        assert session.scalar(select(func.count()).select_from(Segment)) == 0
        assert session.scalar(select(func.count()).select_from(EmbeddingIndexMetadata)) == 0
        assert session.scalar(select(func.count()).select_from(TextVersion)) == 0
        assert session.scalar(select(func.count()).select_from(Source)) == 0

        refreshed_work = session.get(Work, work.id)
        assert refreshed_work is not None
        assert refreshed_work.is_catalog_only is True
        assert refreshed_work.is_sample is True


def test_seed_plain_text_works_resume_skips_existing_text_versions() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    root = _make_workspace_test_root()

    try:
        existing_text_path = root / "existing.txt"
        new_text_path = root / "new.txt"
        existing_text_path.write_text("existing line\n", encoding="utf-8")
        new_text_path.write_text("new line ||| gloss\n", encoding="utf-8")

        manifest_path = root / "test_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "source": {
                        "id": "source-test",
                        "slug": "source-test",
                        "title": "Test Source",
                        "source_type": "plain-text",
                        "citation": "test",
                        "url": None,
                        "access_note": None,
                        "is_sample": False,
                    },
                    "texts": [
                        {
                            "work_id": "work-existing",
                            "canonical_code": "EX 1",
                            "language_id": "lang-test",
                            "text_path": existing_text_path.as_posix(),
                            "segment_by": "line",
                            "is_sample": False,
                            "text_version": {
                                "id": "tv-existing",
                                "slug": "tv-existing",
                                "title": "Existing Version",
                                "version_label": "v1",
                                "summary": None,
                                "sample_note": None,
                                "is_sample": False,
                            },
                            "person_roles": [],
                        },
                        {
                            "work_id": "work-new",
                            "canonical_code": "EX 2",
                            "language_id": "lang-test",
                            "text_path": new_text_path.as_posix(),
                            "segment_by": "line",
                            "is_sample": False,
                            "work_metadata": {
                                "id": "work-new",
                                "slug": "work-new",
                                "tradition_id": "trad-test",
                                "collection_id": "coll-test",
                                "title": "New Work",
                                "genre": "sutra",
                                "is_catalog_only": False,
                                "is_sample": False,
                            },
                            "text_version": {
                                "id": "tv-new",
                                "slug": "tv-new",
                                "title": "New Version",
                                "version_label": "v1",
                                "summary": None,
                                "sample_note": None,
                                "is_sample": False,
                            },
                            "person_roles": [],
                        },
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        with Session(engine) as session:
            tradition = Tradition(id="trad-test", slug="trad-test", name="Test Tradition")
            collection = Collection(id="coll-test", slug="coll-test", title="Test Collection", tradition_id="trad-test")
            language = Language(id="lang-test", code="tst", name="Test Language")
            source = Source(id="source-test", slug="source-test", title="Test Source", source_type="plain-text", is_sample=False)
            work = Work(
                id="work-existing",
                slug="work-existing",
                tradition_id="trad-test",
                collection_id="coll-test",
                title="Existing Work",
                genre="sutra",
                is_sample=False,
            )
            text_version = TextVersion(
                id="tv-existing",
                slug="tv-existing",
                work_id="work-existing",
                language_id="lang-test",
                source_id="source-test",
                title="Existing Version",
                version_label="v1",
                is_sample=False,
            )
            segment = Segment(
                id="seg-existing",
                text_version_id="tv-existing",
                segment_key="EX 1-PLAIN-001",
                content="existing line",
                normalized_content="existing line",
                position=1,
                char_count=13,
            )
            session.add_all([tradition, collection, language, source, work, text_version, segment])
            session.commit()

            seeded = plain_text_loader.seed_plain_text_works(
                session,
                tradition_id="trad-test",
                resume=True,
                manifest_path=manifest_path,
            )

            assert seeded is True
            assert session.scalar(select(func.count()).select_from(TextVersion)) == 2
            assert session.scalar(select(func.count()).select_from(Segment)) == 2
            new_segment = session.scalar(select(Segment).where(Segment.text_version_id == "tv-new"))
            assert new_segment is not None
            assert new_segment.content == "new line"
            assert new_segment.content_gloss == "gloss"
    finally:
        shutil.rmtree(root, ignore_errors=True)
