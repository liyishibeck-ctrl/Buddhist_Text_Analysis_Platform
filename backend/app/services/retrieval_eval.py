from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR
from backend.app.services import retrieval_service, search_service, vector_service


DEFAULT_EVAL_SET_PATH = ROOT_DIR / "data" / "evals" / "han_retrieval_eval_v1.json"
SUPPORTED_RETRIEVAL_MODES = ("keyword", "vector", "hybrid")


def load_retrieval_eval_set(path: Path | None = None) -> dict[str, Any]:
    payload_path = Path(path or DEFAULT_EVAL_SET_PATH)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Retrieval evaluation set must define a non-empty 'cases' list: {payload_path}")
    return payload


def _case_top_k(case: dict[str, Any], *, default_top_k: int) -> int:
    case_top_k = int(case.get("top_k") or default_top_k)
    return max(1, case_top_k)


def _case_filters(case: dict[str, Any]) -> dict[str, Optional[str]]:
    return {
        "tradition_id": case.get("tradition_id"),
        "collection_id": case.get("collection_id"),
        "language_id": case.get("language_id"),
    }


def _run_retrieval_mode(
    session: Session,
    *,
    mode: str,
    case: dict[str, Any],
    top_k: int,
) -> dict[str, Any]:
    filters = _case_filters(case)
    query_text = str(case["query_text"])

    if mode == "keyword":
        results = search_service.retrieve_segment_matches(
            session,
            q=query_text,
            tradition_id=filters["tradition_id"],
            collection_id=filters["collection_id"],
            language_id=filters["language_id"],
            limit=top_k,
            include_content=True,
        )
        return {
            "status": "ready",
            "message": "Keyword retrieval completed.",
            "results": results,
        }

    if mode == "vector":
        return vector_service.vector_search(
            session,
            query_text=query_text,
            top_k=top_k,
            tradition_id=filters["tradition_id"],
            collection_id=filters["collection_id"],
            language_id=filters["language_id"],
        )

    if mode == "hybrid":
        return retrieval_service.hybrid_search(
            session,
            query_text=query_text,
            top_k=top_k,
            tradition_id=filters["tradition_id"],
            collection_id=filters["collection_id"],
            language_id=filters["language_id"],
            include_content=True,
        )

    raise ValueError(f"Unsupported retrieval mode '{mode}'. Expected one of {SUPPORTED_RETRIEVAL_MODES}.")


def _result_matches_case(case: dict[str, Any], result: dict[str, Any]) -> bool:
    expected_segment_ids = set(case.get("expected_segment_ids") or [])
    expected_work_ids = set(case.get("expected_work_ids") or [])
    return result.get("id") in expected_segment_ids or result.get("work_id") in expected_work_ids


def _trim_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": result.get("id"),
        "segment_key": result.get("segment_key"),
        "work_id": result.get("work_id"),
        "work_title": result.get("work_title"),
        "match_score": result.get("match_score"),
        "retrieval_score": result.get("retrieval_score"),
        "retrieval_channels": result.get("retrieval_channels"),
        "match_reason": result.get("match_reason"),
        "content_preview": result.get("content_preview"),
    }


def evaluate_retrieval_case(
    session: Session,
    *,
    case: dict[str, Any],
    modes: tuple[str, ...] = SUPPORTED_RETRIEVAL_MODES,
    default_top_k: int = 5,
) -> dict[str, Any]:
    top_k = _case_top_k(case, default_top_k=default_top_k)
    mode_results: dict[str, dict[str, Any]] = {}

    for mode in modes:
        payload = _run_retrieval_mode(session, mode=mode, case=case, top_k=top_k)
        results = list(payload.get("results") or [])
        matched_expected_ids: list[str] = []
        first_hit_rank: int | None = None
        for index, result in enumerate(results, start=1):
            if _result_matches_case(case, result):
                if first_hit_rank is None:
                    first_hit_rank = index
                matched_expected_ids.append(str(result["id"]))

        reciprocal_rank = 0.0 if first_hit_rank is None else 1.0 / first_hit_rank
        mode_results[mode] = {
            "status": payload.get("status") or "ready",
            "message": payload.get("message") or "",
            "result_count": len(results),
            "hit": first_hit_rank is not None,
            "first_hit_rank": first_hit_rank,
            "reciprocal_rank": reciprocal_rank,
            "matched_expected_ids": matched_expected_ids,
            "top_results": [_trim_result(item) for item in results[:top_k]],
        }

    return {
        "id": case["id"],
        "query_text": case["query_text"],
        "tradition_id": case.get("tradition_id"),
        "top_k": top_k,
        "tags": case.get("tags") or [],
        "notes": case.get("notes"),
        "expected_segment_ids": case.get("expected_segment_ids") or [],
        "expected_work_ids": case.get("expected_work_ids") or [],
        "modes": mode_results,
    }


def summarize_retrieval_evaluation(
    case_results: list[dict[str, Any]],
    *,
    modes: tuple[str, ...] = SUPPORTED_RETRIEVAL_MODES,
) -> dict[str, Any]:
    summary: dict[str, Any] = {"case_count": len(case_results), "modes": {}}

    for mode in modes:
        mode_payloads = [case["modes"][mode] for case in case_results if mode in case["modes"]]
        hit_count = sum(1 for payload in mode_payloads if payload["hit"])
        reciprocal_rank_total = sum(float(payload["reciprocal_rank"]) for payload in mode_payloads)
        statuses: dict[str, int] = {}
        for payload in mode_payloads:
            status = str(payload["status"])
            statuses[status] = statuses.get(status, 0) + 1
        case_count = len(mode_payloads)
        summary["modes"][mode] = {
            "case_count": case_count,
            "hit_count": hit_count,
            "hit_rate": 0.0 if case_count == 0 else round(hit_count / case_count, 4),
            "mrr": 0.0 if case_count == 0 else round(reciprocal_rank_total / case_count, 4),
            "statuses": statuses,
        }

    return summary


def evaluate_retrieval_sample_set(
    session: Session,
    *,
    eval_set: dict[str, Any],
    modes: tuple[str, ...] = SUPPORTED_RETRIEVAL_MODES,
    case_ids: Optional[set[str]] = None,
) -> dict[str, Any]:
    default_top_k = int(eval_set.get("default_top_k") or 5)
    cases = [
        case
        for case in eval_set["cases"]
        if case_ids is None or str(case.get("id")) in case_ids
    ]
    case_results = [
        evaluate_retrieval_case(
            session,
            case=case,
            modes=modes,
            default_top_k=default_top_k,
        )
        for case in cases
    ]
    return {
        "eval_set_id": eval_set.get("id"),
        "title": eval_set.get("title"),
        "description": eval_set.get("description"),
        "default_top_k": default_top_k,
        "case_count": len(case_results),
        "summary": summarize_retrieval_evaluation(case_results, modes=modes),
        "cases": case_results,
    }
