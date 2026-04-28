from __future__ import annotations

import pytest

from backend.app.services import retrieval_service


def test_merge_retrieval_results_combines_overlapping_hits() -> None:
    keyword_hits = [
        {
            "id": "seg-1",
            "segment_key": "S1",
            "position": 1,
            "match_score": 2.0,
            "match_reason": "keyword",
        },
        {
            "id": "seg-2",
            "segment_key": "S2",
            "position": 2,
            "match_score": 1.0,
            "match_reason": "keyword",
        },
    ]
    vector_hits = [
        {
            "id": "seg-2",
            "segment_key": "S2",
            "position": 2,
            "match_score": 0.9,
            "match_reason": "vector",
        },
        {
            "id": "seg-3",
            "segment_key": "S3",
            "position": 3,
            "match_score": 0.8,
            "match_reason": "vector",
        },
    ]

    results = retrieval_service.merge_retrieval_results(
        keyword_hits=keyword_hits,
        vector_hits=vector_hits,
        top_k=3,
    )

    result_by_id = {item["id"]: item for item in results}
    assert set(result_by_id) == {"seg-1", "seg-2", "seg-3"}
    assert result_by_id["seg-2"]["match_reason"] == "hybrid"
    assert result_by_id["seg-2"]["retrieval_channels"] == ["keyword", "vector"]


def test_hybrid_search_returns_partial_when_vector_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        retrieval_service.search_service,
        "retrieve_segment_matches",
        lambda *args, **kwargs: [
            {
                "id": "seg-1",
                "segment_key": "S1",
                "title": None,
                "position": 1,
                "work_title": "Demo Work",
                "text_version_title": "Demo Version",
                "tradition_name": "汉传",
                "language_name": "汉文",
                "content_preview": "demo preview",
                "match_score": 2.0,
                "match_reason": "keyword",
                "concept_labels": [],
            }
        ],
    )
    monkeypatch.setattr(
        retrieval_service.vector_service,
        "vector_search",
        lambda *args, **kwargs: {
            "status": "misconfigured",
            "message": "EMBEDDING_API_URL must be set.",
            "configured_backend": "python-fallback",
            "embedding_model": "unconfigured",
            "indexed_owners": 0,
            "results": [],
            "pgvector_hint": "Configure the embedding provider.",
        },
    )

    payload = retrieval_service.hybrid_search(
        session=None,  # type: ignore[arg-type]
        query_text="无我",
        top_k=3,
    )

    assert payload["status"] == "partial"
    assert payload["keyword_result_count"] == 1
    assert payload["vector_result_count"] == 0
    assert payload["results"][0]["retrieval_channels"] == ["keyword"]
