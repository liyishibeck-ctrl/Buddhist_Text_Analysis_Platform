from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models import TextUnitSummary


DEFAULT_PATH = Path("data/processed/rag_summaries/text_unit_summaries_export.jsonl.gz")


def _open_text(path: Path, mode: str):
    if path.suffix == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8")
    return path.open(mode, encoding="utf-8")


def _dt_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _dt_from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _row_to_payload(row: TextUnitSummary) -> dict[str, Any]:
    return {
        "owner_type": row.owner_type,
        "owner_id": row.owner_id,
        "summary_kind": row.summary_kind,
        "model": row.model,
        "summary": row.summary,
        "source_segment_count": row.source_segment_count,
        "metadata_json": row.metadata_json,
        "created_at": _dt_to_iso(row.created_at),
        "updated_at": _dt_to_iso(row.updated_at),
    }


def export_summaries(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with SessionLocal() as session, _open_text(output_path, "w") as handle:
        rows = session.scalars(
            select(TextUnitSummary).order_by(
                TextUnitSummary.owner_type,
                TextUnitSummary.owner_id,
                TextUnitSummary.summary_kind,
                TextUnitSummary.model,
            )
        )
        for row in rows:
            handle.write(json.dumps(_row_to_payload(row), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    print(f"exported={count} output={output_path}")


def _iter_payloads(input_path: Path) -> Iterable[dict[str, Any]]:
    with _open_text(input_path, "r") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc


def import_summaries(input_path: Path, *, apply: bool, chunk_size: int) -> None:
    inserted = 0
    updated = 0
    seen = 0
    with SessionLocal() as session:
        for payload in _iter_payloads(input_path):
            seen += 1
            row = session.scalars(
                select(TextUnitSummary).where(
                    TextUnitSummary.owner_type == payload["owner_type"],
                    TextUnitSummary.owner_id == payload["owner_id"],
                    TextUnitSummary.summary_kind == payload["summary_kind"],
                    TextUnitSummary.model == payload["model"],
                )
            ).first()
            if row is None:
                inserted += 1
                if apply:
                    session.add(
                        TextUnitSummary(
                            owner_type=payload["owner_type"],
                            owner_id=payload["owner_id"],
                            summary_kind=payload["summary_kind"],
                            model=payload["model"],
                            summary=payload["summary"],
                            source_segment_count=payload.get("source_segment_count") or 0,
                            metadata_json=payload.get("metadata_json"),
                            created_at=_dt_from_iso(payload.get("created_at")),
                            updated_at=_dt_from_iso(payload.get("updated_at")),
                        )
                    )
            else:
                updated += 1
                if apply:
                    row.summary = payload["summary"]
                    row.source_segment_count = payload.get("source_segment_count") or 0
                    row.metadata_json = payload.get("metadata_json")
                    row.updated_at = _dt_from_iso(payload.get("updated_at")) or row.updated_at
            if apply and seen % chunk_size == 0:
                session.commit()
                print(f"processed={seen} inserted={inserted} updated={updated}")
        if apply:
            session.commit()
    mode = "applied" if apply else "dry_run"
    print(f"{mode}=true processed={seen} inserted={inserted} updated={updated}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export/import generated text unit summaries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--output", type=Path, default=DEFAULT_PATH)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--input", type=Path, default=DEFAULT_PATH)
    import_parser.add_argument("--chunk-size", type=int, default=500)
    import_parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "export":
        export_summaries(args.output)
        return
    import_summaries(args.input, apply=args.apply, chunk_size=args.chunk_size)


if __name__ == "__main__":
    main()
