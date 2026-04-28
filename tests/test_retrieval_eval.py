from __future__ import annotations

import pytest

from backend.app.services import retrieval_eval


def test_load_retrieval_eval_set_reads_curated_cases() -> None:
    payload = retrieval_eval.load_retrieval_eval_set()

    assert payload["id"] == "han-retrieval-eval-v1"
    assert payload["default_top_k"] == 5
    assert any(case["id"] == "han-anatman-term" for case in payload["cases"])


def test_evaluate_retrieval_case_marks_hits_by_segment_and_work_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = {
        "id": "demo-case",
        "query_text": "无我",
        "tradition_id": "trad-han",
        "expected_segment_ids": ["seg-hit"],
        "expected_work_ids": ["work-hit"],
    }

    monkeypatch.setattr(
        retrieval_eval.search_service,
        "retrieve_segment_matches",
        lambda *args, **kwargs: [
            {
                "id": "seg-keyword-miss",
                "segment_key": "KW.1",
                "work_id": "work-other",
                "work_title": "Keyword Miss",
                "match_score": 0.2,
                "content_preview": "keyword miss",
            }
        ],
    )
    monkeypatch.setattr(
        retrieval_eval.vector_service,
        "vector_search",
        lambda *args, **kwargs: {
            "status": "ready",
            "message": "vector ok",
            "results": [
                {
                    "id": "seg-vector-miss",
                    "segment_key": "V.1",
                    "work_id": "work-other",
                    "work_title": "Vector Miss",
                    "match_score": 0.61,
                    "content_preview": "vector miss",
                },
                {
                    "id": "seg-hit",
                    "segment_key": "V.2",
                    "work_id": "work-hit",
                    "work_title": "Vector Hit",
                    "match_score": 0.59,
                    "content_preview": "vector hit",
                },
            ],
        },
    )
    monkeypatch.setattr(
        retrieval_eval.retrieval_service,
        "hybrid_search",
        lambda *args, **kwargs: {
            "status": "partial",
            "message": "hybrid partial",
            "results": [
                {
                    "id": "seg-hybrid-miss",
                    "segment_key": "H.1",
                    "work_id": "work-other",
                    "work_title": "Hybrid Miss",
                    "retrieval_score": 0.7,
                    "retrieval_channels": ["keyword"],
                    "content_preview": "hybrid miss",
                },
                {
                    "id": "seg-other",
                    "segment_key": "H.2",
                    "work_id": "work-hit",
                    "work_title": "Hybrid Work Hit",
                    "retrieval_score": 0.6,
                    "retrieval_channels": ["vector"],
                    "content_preview": "hybrid work hit",
                },
            ],
        },
    )

    result = retrieval_eval.evaluate_retrieval_case(
        session=None,  # type: ignore[arg-type]
        case=case,
        modes=("keyword", "vector", "hybrid"),
        default_top_k=5,
    )

    assert result["modes"]["keyword"]["hit"] is False
    assert result["modes"]["vector"]["hit"] is True
    assert result["modes"]["vector"]["first_hit_rank"] == 2
    assert result["modes"]["hybrid"]["hit"] is True
    assert result["modes"]["hybrid"]["first_hit_rank"] == 2

    summary = retrieval_eval.summarize_retrieval_evaluation([result], modes=("keyword", "vector", "hybrid"))

    assert summary["modes"]["keyword"]["hit_rate"] == 0.0
    assert summary["modes"]["vector"]["hit_rate"] == 1.0
    assert summary["modes"]["vector"]["mrr"] == 0.5
    assert summary["modes"]["hybrid"]["statuses"] == {"partial": 1}
