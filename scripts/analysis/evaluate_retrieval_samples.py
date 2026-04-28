from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.services import retrieval_eval


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate keyword, vector, and hybrid retrieval against a curated sample set.")
    parser.add_argument("--sample-file", type=Path, default=retrieval_eval.DEFAULT_EVAL_SET_PATH)
    parser.add_argument("--mode", dest="modes", action="append", choices=retrieval_eval.SUPPORTED_RETRIEVAL_MODES)
    parser.add_argument("--case-id", action="append", default=[], help="Limit evaluation to one or more case ids.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def _print_text_report(report: dict[str, object], *, modes: tuple[str, ...]) -> None:
    print(f"Sample set: {report['title']} ({report['eval_set_id']})")
    print(f"Cases run: {report['case_count']}")
    print("")
    print("Mode Summary")
    for mode in modes:
        summary = report["summary"]["modes"][mode]  # type: ignore[index]
        print(
            f"- {mode}: hits={summary['hit_count']}/{summary['case_count']} "
            f"hit_rate={summary['hit_rate']:.2%} mrr={summary['mrr']:.3f} statuses={summary['statuses']}"
        )

    print("")
    print("Case Details")
    for case in report["cases"]:  # type: ignore[index]
        print(f"[{case['id']}] {case['query_text']}")
        if case.get("notes"):
            print(f"  note: {case['notes']}")
        for mode in modes:
            mode_payload = case["modes"][mode]
            first_hit_rank = mode_payload["first_hit_rank"]
            if first_hit_rank is None:
                print(f"  {mode}: miss | status={mode_payload['status']}")
            else:
                print(f"  {mode}: hit@{first_hit_rank} | status={mode_payload['status']}")
            for index, result in enumerate(mode_payload["top_results"][:3], start=1):
                score = result.get("retrieval_score")
                if score is None:
                    score = result.get("match_score")
                channels = result.get("retrieval_channels")
                channel_suffix = f" | channels={channels}" if channels else ""
                print(
                    f"    {index}. {result['segment_key']} | {result['work_title']} | "
                    f"score={score}{channel_suffix} | {result['content_preview']}"
                )
        print("")


def main() -> None:
    args = parse_args()
    eval_set = retrieval_eval.load_retrieval_eval_set(args.sample_file)
    modes = tuple(args.modes or retrieval_eval.SUPPORTED_RETRIEVAL_MODES)
    case_ids = set(args.case_id) or None

    with SessionLocal() as session:
        report = retrieval_eval.evaluate_retrieval_sample_set(
            session,
            eval_set=eval_set,
            modes=modes,
            case_ids=case_ids,
        )

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    _print_text_report(report, modes=modes)


if __name__ == "__main__":
    main()
