from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.api import catalog as catalog_api


def test_get_similar_segments_returns_service_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        catalog_api.vector_service,
        "find_similar_segments",
        lambda *args, **kwargs: {
            "status": "ready",
            "message": "Retrieved vector neighbors for segment XJ.1.",
            "configured_backend": "python-fallback",
            "embedding_model": "local-hash-v1",
            "indexed_owners": 0,
            "source_segment": {
                "id": "seg-xj-001",
                "segment_key": "XJ.1",
                "title": None,
                "position": 1,
                "work_title": "心经",
                "text_version_title": "玄奘译本",
                "tradition_name": "汉传",
                "language_name": "汉文",
                "content_preview": "观自在菩萨",
                "match_score": None,
                "match_reason": "source",
                "retrieval_score": None,
                "retrieval_channels": [],
                "concept_labels": [],
            },
            "results": [
                {
                    "id": "seg-th-001",
                    "segment_key": "TH.1",
                    "title": None,
                    "position": 1,
                    "work_title": "ཤེས་རབ་སྙིང་པོ།",
                    "text_version_title": "Wylie transliteration",
                    "tradition_name": "藏传",
                    "language_name": "藏文",
                    "content_preview": "’phags pa shes rab kyi pha rol tu phyin pa’i snying po",
                    "match_score": 0.81,
                    "match_reason": "vector",
                    "retrieval_score": None,
                    "retrieval_channels": [],
                    "concept_labels": [],
                }
            ],
            "pgvector_hint": "Backfill more rows with the embedding script for broader recall.",
        },
    )

    payload = catalog_api.get_similar_segments("seg-xj-001", top_k=3, db=None)  # type: ignore[arg-type]

    assert payload["status"] == "ready"
    assert payload["source_segment"]["segment_key"] == "XJ.1"
    assert payload["results"][0]["segment_key"] == "TH.1"


def test_get_similar_segments_raises_404_for_missing_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_missing(*args, **kwargs):
        raise LookupError("Segment 'missing' not found.")

    monkeypatch.setattr(catalog_api.vector_service, "find_similar_segments", _raise_missing)

    with pytest.raises(HTTPException) as exc:
        catalog_api.get_similar_segments("missing", top_k=3, db=None)  # type: ignore[arg-type]

    assert exc.value.status_code == 404
