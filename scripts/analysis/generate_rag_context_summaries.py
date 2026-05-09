from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.db.init_db import initialize_database
from backend.app.db.session import SessionLocal
from backend.app.models import Segment, StructuralUnit, TextUnitSummary, TextVersion, Work
from backend.app.services.sutra_explainer_service import _call_llm, _truncate_text


SUMMARY_KIND = "rag_context"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(slots=True)
class SummaryTarget:
    owner_type: str
    owner_id: str
    title: str
    metadata: str


def _existing_owner_ids(session: Session, *, owner_type: str, model: str) -> set[str]:
    return set(
        session.scalars(
            select(TextUnitSummary.owner_id).where(
                TextUnitSummary.owner_type == owner_type,
                TextUnitSummary.summary_kind == SUMMARY_KIND,
                TextUnitSummary.model == model,
            )
        ).all()
    )


def _work_targets(
    session: Session,
    *,
    owner_id: Optional[str],
    tradition_id: Optional[str],
    include_existing: bool,
    model: str,
    limit: int,
) -> list[SummaryTarget]:
    stmt = (
        select(Work)
        .options(selectinload(Work.tradition), selectinload(Work.collection))
        .order_by(Work.id)
    )
    if owner_id:
        stmt = stmt.where(Work.id == owner_id)
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    existing = set() if include_existing else _existing_owner_ids(session, owner_type="work", model=model)
    targets: list[SummaryTarget] = []
    for work in session.scalars(stmt).unique():
        if work.id in existing:
            continue
        metadata = "；".join(
            bit
            for bit in [
                work.tradition.name,
                work.collection.title,
                work.canonical_code,
                work.pitaka_division,
                f"{work.fascicle_count} 卷" if work.fascicle_count else "",
            ]
            if bit
        )
        targets.append(SummaryTarget("work", work.id, work.title, metadata))
        if len(targets) >= limit:
            break
    return targets


def _text_version_targets(
    session: Session,
    *,
    owner_id: Optional[str],
    tradition_id: Optional[str],
    include_existing: bool,
    model: str,
    limit: int,
) -> list[SummaryTarget]:
    stmt = (
        select(TextVersion)
        .join(TextVersion.work)
        .options(
            selectinload(TextVersion.language),
            selectinload(TextVersion.work).selectinload(Work.tradition),
        )
        .order_by(TextVersion.id)
    )
    if owner_id:
        stmt = stmt.where(TextVersion.id == owner_id)
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    existing = (
        set()
        if include_existing
        else _existing_owner_ids(session, owner_type="text_version", model=model)
    )
    targets: list[SummaryTarget] = []
    for version in session.scalars(stmt).unique():
        if version.id in existing:
            continue
        metadata = "；".join(
            bit
            for bit in [
                version.work.tradition.name,
                version.language.name,
                version.version_label,
                version.script_note,
                version.date_note,
            ]
            if bit
        )
        targets.append(SummaryTarget("text_version", version.id, version.title, metadata))
        if len(targets) >= limit:
            break
    return targets


def _structural_unit_targets(
    session: Session,
    *,
    owner_id: Optional[str],
    tradition_id: Optional[str],
    unit_type: str,
    include_existing: bool,
    model: str,
    limit: int,
) -> list[SummaryTarget]:
    stmt = (
        select(StructuralUnit)
        .join(StructuralUnit.text_version)
        .join(TextVersion.work)
        .options(
            selectinload(StructuralUnit.text_version).selectinload(TextVersion.language),
            selectinload(StructuralUnit.text_version).selectinload(TextVersion.work).selectinload(Work.tradition),
        )
        .where(StructuralUnit.unit_type == unit_type)
        .order_by(StructuralUnit.id)
    )
    if owner_id:
        stmt = stmt.where(StructuralUnit.id == owner_id)
    if tradition_id:
        stmt = stmt.where(Work.tradition_id == tradition_id)
    existing = (
        set()
        if include_existing
        else _existing_owner_ids(session, owner_type="structural_unit", model=model)
    )
    targets: list[SummaryTarget] = []
    for unit in session.scalars(stmt).unique():
        if unit.id in existing:
            continue
        version = unit.text_version
        metadata = "；".join(
            bit
            for bit in [
                version.work.tradition.name,
                version.work.title,
                version.language.name,
                unit.unit_type,
                unit.label,
                unit.title,
                unit.path,
            ]
            if bit
        )
        targets.append(SummaryTarget("structural_unit", unit.id, unit.title or unit.label, metadata))
        if len(targets) >= limit:
            break
    return targets


def _targets_for_args(session: Session, args: argparse.Namespace) -> list[SummaryTarget]:
    common = {
        "owner_id": args.owner_id,
        "tradition_id": args.tradition_id,
        "include_existing": args.include_existing,
        "model": args.model,
        "limit": args.limit,
    }
    if args.owner_type == "work":
        return _work_targets(session, **common)
    if args.owner_type == "text_version":
        return _text_version_targets(session, **common)
    return _structural_unit_targets(session, unit_type=args.unit_type, **common)


def _segment_filter_for_target(target: SummaryTarget):
    if target.owner_type == "work":
        return TextVersion.work_id == target.owner_id
    if target.owner_type == "text_version":
        return Segment.text_version_id == target.owner_id
    return Segment.structural_unit_id == target.owner_id


def _sample_segments(session: Session, target: SummaryTarget, *, max_segments: int) -> tuple[int, list[Segment]]:
    filter_clause = _segment_filter_for_target(target)
    total = int(
        session.scalar(
            select(func.count())
            .select_from(Segment)
            .join(Segment.text_version)
            .where(filter_clause)
        )
        or 0
    )
    stmt = (
        select(Segment)
        .join(Segment.text_version)
        .where(filter_clause)
        .order_by(TextVersion.id, Segment.position, Segment.id)
        .limit(max_segments)
    )
    return total, list(session.scalars(stmt).all())


def _build_summary_prompts(target: SummaryTarget, *, total_segments: int, segments: Iterable[Segment]) -> tuple[str, str]:
    excerpts = []
    for index, segment in enumerate(segments, start=1):
        body = segment.content_gloss or segment.normalized_content or segment.content
        excerpts.append(f"[S{index}] {segment.segment_key}: {_truncate_text(body, 700)}")
    system_prompt = (
        "你是佛典研究助手。请只依据给出的文本摘录和元数据写中文摘要；"
        "如果摘录只是抽样，要明确说这是基于抽样的工作摘要。"
    )
    user_prompt = (
        f"摘要对象类型：{target.owner_type}\n"
        f"摘要对象ID：{target.owner_id}\n"
        f"标题：{target.title}\n"
        f"元数据：{target.metadata}\n"
        f"总段落数：{total_segments}\n\n"
        "请输出适合 RAG 使用的摘要，包含：核心主题、主要教义、关键术语、文本语气/结构、"
        "以及一段 150-300 字的可直接放入检索上下文的摘要。\n\n"
        "文本摘录：\n"
        + "\n".join(excerpts)
    )
    return system_prompt, user_prompt


def _upsert_summary(
    session: Session,
    target: SummaryTarget,
    *,
    model: str,
    summary: str,
    source_segment_count: int,
    total_segments: int,
) -> None:
    row = session.scalars(
        select(TextUnitSummary).where(
            TextUnitSummary.owner_type == target.owner_type,
            TextUnitSummary.owner_id == target.owner_id,
            TextUnitSummary.summary_kind == SUMMARY_KIND,
            TextUnitSummary.model == model,
        )
    ).first()
    metadata = {
        "title": target.title,
        "metadata": target.metadata,
        "total_segments": total_segments,
    }
    if row is None:
        session.add(
            TextUnitSummary(
                owner_type=target.owner_type,
                owner_id=target.owner_id,
                summary_kind=SUMMARY_KIND,
                model=model,
                summary=summary,
                source_segment_count=source_segment_count,
                metadata_json=metadata,
            )
        )
        return
    row.summary = summary
    row.source_segment_count = source_segment_count
    row.metadata_json = metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate work/version/juan summaries for richer RAG context.")
    parser.add_argument("--owner-type", choices=["work", "text_version", "structural_unit"], default="structural_unit")
    parser.add_argument("--owner-id", default=None)
    parser.add_argument("--tradition-id", default=None)
    parser.add_argument("--unit-type", default="juan", help="Used when --owner-type=structural_unit.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-segments-per-unit", type=int, default=24)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--include-existing", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Call the LLM and write summaries. Omit for dry run.")
    return parser.parse_args()


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _process_target(target: SummaryTarget, args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    with SessionLocal() as session:
        total_segments, segments = _sample_segments(session, target, max_segments=args.max_segments_per_unit)
        result: dict[str, object] = {
            "owner_type": target.owner_type,
            "owner_id": target.owner_id,
            "title": target.title,
            "total_segments": total_segments,
            "sampled_segments": len(segments),
            "status": "dry_run",
            "summary_chars": 0,
            "elapsed_seconds": 0.0,
        }
        if not args.apply:
            result["elapsed_seconds"] = time.monotonic() - started
            return result
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY/OPENAI_API_KEY is required when --apply is used.")
        if not segments:
            result["status"] = "skipped_no_segments"
            result["elapsed_seconds"] = time.monotonic() - started
            return result

        system_prompt, user_prompt = _build_summary_prompts(target, total_segments=total_segments, segments=segments)
        summary, error = _call_llm(system_prompt=system_prompt, user_prompt=user_prompt, model=args.model)
        if error:
            session.rollback()
            result["status"] = "error"
            result["error"] = error
            result["elapsed_seconds"] = time.monotonic() - started
            return result
        _upsert_summary(
            session,
            target,
            model=args.model,
            summary=summary,
            source_segment_count=len(segments),
            total_segments=total_segments,
        )
        session.commit()
        result["status"] = "written"
        result["summary_chars"] = len(summary)
        result["elapsed_seconds"] = time.monotonic() - started
        return result


def _print_progress(
    *,
    done: int,
    total: int,
    written: int,
    skipped: int,
    errors: int,
    started: float,
) -> None:
    elapsed = time.monotonic() - started
    rate = done / elapsed * 60 if elapsed > 0 else 0.0
    remaining = total - done
    eta = remaining / rate * 60 if rate > 0 else 0.0
    print(
        f"progress={done}/{total} written={written} skipped={skipped} errors={errors} "
        f"rate={rate:.2f}/min elapsed={_format_duration(elapsed)} eta={_format_duration(eta)}",
        flush=True,
    )


def main() -> int:
    args = parse_args()
    args.limit = max(1, int(args.limit))
    args.concurrency = max(1, int(args.concurrency))
    args.progress_every = max(1, int(args.progress_every))
    initialize_database()
    with SessionLocal() as session:
        targets = _targets_for_args(session, args)
    print(
        f"targets={len(targets)} owner_type={args.owner_type} apply={args.apply} "
        f"model={args.model} concurrency={args.concurrency}",
        flush=True,
    )

    started = time.monotonic()
    done = 0
    written = 0
    skipped = 0
    errors = 0

    def handle_result(result: dict[str, object]) -> None:
        nonlocal done, written, skipped, errors
        done += 1
        status = str(result["status"])
        if status == "written":
            written += 1
        elif status.startswith("skipped"):
            skipped += 1
        elif status == "error":
            errors += 1
            print(
                f"error owner={result['owner_type']}:{result['owner_id']} "
                f"title={result['title']} message={result.get('error')}",
                file=sys.stderr,
                flush=True,
            )
        if done <= 5 or done % args.progress_every == 0 or done == len(targets):
            print(
                f"{status} owner={result['owner_type']}:{result['owner_id']} "
                f"title={result['title']} segments={result['total_segments']} "
                f"sampled={result['sampled_segments']} chars={result['summary_chars']} "
                f"elapsed={_format_duration(float(result['elapsed_seconds']))}",
                flush=True,
            )
            _print_progress(
                done=done,
                total=len(targets),
                written=written,
                skipped=skipped,
                errors=errors,
                started=started,
            )

    if args.concurrency == 1:
        for target in targets:
            handle_result(_process_target(target, args))
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(_process_target, target, args) for target in targets]
            for future in as_completed(futures):
                handle_result(future.result())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
