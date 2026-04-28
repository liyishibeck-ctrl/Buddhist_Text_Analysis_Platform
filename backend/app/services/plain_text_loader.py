from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR, settings
from backend.app.models import (
    CitationLink,
    EmbeddingIndexMetadata,
    ParallelLink,
    Person,
    Segment,
    Source,
    StructuralUnit,
    TextVersion,
    TextVersionPersonRole,
    Work,
)
from backend.app.services.seed_utils import load_json_payload


PLAIN_TEXT_SOURCE_ID_FORMAT = "source-{tradition}-plain-text"
DELETE_BATCH_SIZE = 400


def load_plain_text_manifest(tradition_dir: str, path: Path | None = None) -> dict[str, Any]:
    """Load the plain text manifest for a tradition.

    tradition_dir is the directory name like "pali" or "tibetan", not the full tradition_id.
    """
    payload_path = Path(path or ROOT_DIR / "data" / "raw" / tradition_dir / f"{tradition_dir}_plain_text_manifest.json")
    return load_json_payload(payload_path)


def _resolve_data_path(raw_path: str) -> Path:
    """Resolve data path from possibly relative form."""
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (ROOT_DIR / candidate).resolve()


def _relative_display_path(path: Path) -> str:
    """Return relative path for display in metadata."""
    try:
        return path.resolve().relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def _canonical_code_slug(canonical_code: str) -> str:
    """Normalize canonical codes for stable plain-text segment IDs."""
    slug = re.sub(r"[^\w]+", "-", canonical_code.lower(), flags=re.UNICODE)
    slug = slug.strip("-_").replace("_", "-")
    return slug or "unknown"


def _stable_segment_id(canonical_code: str, position: int) -> str:
    """Generate stable segment ID from canonical code and position."""
    return f"seg-plain-{_canonical_code_slug(canonical_code)}-{position:03d}"


def _segment_key(canonical_code: str, position: int) -> str:
    """Generate stable segment key."""
    return f"{canonical_code}-PLAIN-{position:03d}"


def _iter_batches(items: list[str], batch_size: int | None = None):
    """Yield stable batches small enough for SQL parameter limits."""
    size = batch_size or DELETE_BATCH_SIZE
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _delete_in_batches(
    ids: list[str],
    delete_query_factory,
    *,
    batch_size: int | None = None,
) -> None:
    """Delete rows in chunks to avoid database parameter limits."""
    for batch in _iter_batches(ids, batch_size=batch_size):
        delete_query_factory(batch).delete(synchronize_session=False)


def clear_plain_text_data(
    session: Session,
    *,
    source_id: str,
) -> None:
    """Clear existing plain text data for this source."""
    text_versions = session.scalars(select(TextVersion).where(TextVersion.source_id == source_id)).all()
    if not text_versions:
        session.query(Source).filter(Source.id == source_id).delete(synchronize_session=False)
        return

    text_version_ids = [item.id for item in text_versions]
    work_ids = sorted({item.work_id for item in text_versions})
    structural_unit_ids = session.scalars(
        select(StructuralUnit.id).where(StructuralUnit.text_version_id.in_(text_version_ids))
    ).all()
    segment_ids = session.scalars(select(Segment.id).where(Segment.text_version_id.in_(text_version_ids))).all()

    if segment_ids:
        _delete_in_batches(
            segment_ids,
            lambda batch: session.query(EmbeddingIndexMetadata).filter(
                EmbeddingIndexMetadata.owner_type == "segment",
                EmbeddingIndexMetadata.owner_id.in_(batch),
            ),
        )
        _delete_in_batches(
            segment_ids,
            lambda batch: session.query(ParallelLink).filter(
                or_(ParallelLink.source_segment_id.in_(batch), ParallelLink.target_segment_id.in_(batch))
            ),
        )
        _delete_in_batches(
            segment_ids,
            lambda batch: session.query(CitationLink).filter(
                or_(CitationLink.source_segment_id.in_(batch), CitationLink.target_segment_id.in_(batch))
            ),
        )
        _delete_in_batches(
            segment_ids,
            lambda batch: session.query(Segment).filter(Segment.id.in_(batch)),
        )

    if structural_unit_ids:
        _delete_in_batches(
            structural_unit_ids,
            lambda batch: session.query(StructuralUnit).filter(StructuralUnit.id.in_(batch)),
        )

    _delete_in_batches(
        text_version_ids,
        lambda batch: session.query(TextVersionPersonRole).filter(TextVersionPersonRole.text_version_id.in_(batch)),
    )
    _delete_in_batches(
        text_version_ids,
        lambda batch: session.query(TextVersion).filter(TextVersion.id.in_(batch)),
    )
    session.query(Source).filter(Source.id == source_id).delete(synchronize_session=False)

    for work_id in work_ids:
        remaining_fulltext_work_ids = set(
            session.scalars(
                select(TextVersion.work_id).where(
                    TextVersion.work_id.in_(work_ids),
                    TextVersion.is_catalog_only.is_(False),
                )
            ).all()
        )
        if work_id not in remaining_fulltext_work_ids:
            work = session.get(Work, work_id)
            if work:
                work.is_catalog_only = True
                work.is_sample = True


def _parse_plain_text(
    text_path: Path,
    segment_by: str = "paragraph",
) -> dict[str, Any]:
    """Parse plain text file into segments.

    segment_by can be "paragraph" (split on blank lines) or "line" (split on each line).

    If a line contains "|||", it is split into original content (left) and gloss/translation (right).
    """
    with text_path.open("r", encoding="utf-8") as f:
        content = f.read()

    segments: list[dict[str, str]] = []
    position = 1

    if segment_by == "paragraph":
        # Split on one or more blank lines
        raw_paragraphs = [p.strip() for p in content.split("\n\n")]
        for para in raw_paragraphs:
            if not para:
                continue
            lines = para.split("\n")
            if len(lines) > 1:
                # Keep multi-line paragraphs joined with spaces
                cleaned = " ".join(line.strip() for line in lines)
            else:
                cleaned = para
            if cleaned:
                # Check for translation separator |||
                if "|||" in cleaned:
                    parts = cleaned.split("|||", 1)
                    orig = parts[0].strip()
                    gloss = parts[1].strip()
                    segments.append({
                        "position": position,
                        "content": orig,
                        "content_gloss": gloss,
                        "normalized_content": orig.replace("\n", " ").strip(),
                    })
                else:
                    segments.append({
                        "position": position,
                        "content": cleaned,
                        "normalized_content": cleaned.replace("\n", " ").strip(),
                    })
                position += 1
    elif segment_by == "line":
        # Split on each non-empty line
        for line in content.splitlines():
            cleaned = line.strip()
            if cleaned:
                # Check for translation separator |||
                if "|||" in cleaned:
                    parts = cleaned.split("|||", 1)
                    orig = parts[0].strip()
                    gloss = parts[1].strip()
                    segments.append({
                        "position": position,
                        "content": orig,
                        "content_gloss": gloss,
                        "normalized_content": orig,
                    })
                else:
                    segments.append({
                        "position": position,
                        "content": cleaned,
                        "normalized_content": cleaned,
                    })
                position += 1
    else:
        raise ValueError(f"Unknown segment_by value: {segment_by}")

    if not segments:
        raise ValueError(f"No segments found in plain text file: {text_path}")

    return {
        "segments": segments,
        "total_segments": len(segments),
    }


def seed_plain_text_works(
    session: Session,
    tradition_id: str,
    *,
    force: bool = False,
    resume: bool = False,
    progress_every_texts: int = 10,
    progress_every_segments: int = 1000,
    segment_commit_batch_size: int = 1000,
    manifest_path: Path | None = None,
) -> bool:
    """Seed plain text works for a given tradition from a manifest."""
    # Extract directory name from tradition id (trad-pali -> pali)
    tradition_dir = tradition_id.split('-')[-1]
    payload = load_plain_text_manifest(tradition_dir, manifest_path)
    source_record = payload["source"]
    source_id = source_record["id"]

    existing = session.scalar(select(Source.id).where(Source.id == source_id))
    if existing and not force and not resume:
        return False
    if force:
        clear_plain_text_data(session, source_id=source_id)

    source = session.get(Source, source_id)
    if source:
        for key, value in source_record.items():
            setattr(source, key, value)
    else:
        session.add(Source(**source_record))

    added_count = 0
    texts = payload.get("texts", [])
    total_texts = len(texts)
    imported_texts = 0
    pending_segment_count = 0

    for text_item in texts:
        work = session.get(Work, text_item["work_id"])
        if not work:
            # Create work from metadata if it doesn't exist
            if "work_metadata" not in text_item:
                raise ValueError(f"Unknown work_id and no work_metadata in manifest: {text_item['work_id']}")
            work = Work(**text_item["work_metadata"])
            session.add(work)
            print(f"Created new work: {text_item['work_id']}")

        text_path = _resolve_data_path(text_item["text_path"])
        if not text_path.exists():
            raise FileNotFoundError(f"Missing plain text file: {text_path}")

        work.is_catalog_only = False
        work.is_sample = text_item.get("is_sample", False)
        note_suffix = f"已接入 {source_record['title']} 纯文本版本。"
        existing_note = (work.catalog_note or "").strip()
        if note_suffix not in existing_note:
            work.catalog_note = f"{existing_note} {note_suffix}".strip()

        text_version_record = dict(text_item["text_version"])
        text_version_record["work_id"] = work.id
        text_version_record["language_id"] = text_version_record.get("language_id") or text_item.get("language_id")
        text_version_record["source_id"] = source_id
        text_version_record["is_sample"] = text_item.get("is_sample", True)
        text_version_record["is_catalog_only"] = False
        text_version_id = text_version_record["id"]
        if resume and session.get(TextVersion, text_version_id):
            continue
        session.add(TextVersion(**text_version_record))

        for role_record in text_item.get("person_roles", []):
            person_id = role_record["person_id"]
            if not session.get(Person, person_id):
                _upsert_person(
                    session,
                    {
                        "id": person_id,
                        "slug": person_id.replace("person-", ""),
                        "display_name": role_record.get("display_name") or person_id,
                        "native_name": role_record.get("native_name"),
                        "tradition_affiliation": tradition_id,
                        "role_summary": role_record.get("role", "translator"),
                        "note": "Created from plain text manifest role assignment.",
                    },
                )
            session.add(
                TextVersionPersonRole(
                    text_version_id=text_version_id,
                    person_id=person_id,
                    role=role_record["role"],
                    note=role_record.get("note"),
                )
            )

        parsed = _parse_plain_text(text_path, segment_by=text_item.get("segment_by", "paragraph"))
        text_segment_total = parsed["total_segments"]

        root_unit_id = f"su-{text_version_id}-root"
        session.add(
            StructuralUnit(
                id=root_unit_id,
                text_version_id=text_version_id,
                parent_id=None,
                unit_type=text_item.get("root_type", "text"),
                label=text_version_record["title"],
                title=text_version_record["title"],
                position=1,
                depth=0,
                path="text",
            )
        )

        for seg in parsed["segments"]:
            metadata_json = {
                "source_path": _relative_display_path(text_path),
                "source_scope": "plain_text",
                "segment_by": text_item.get("segment_by", "paragraph"),
            }
            if "title" in seg:
                title = seg["title"]
            elif len(seg["content"]) > 30:
                    title = seg["content"][:27].strip() + "..."
            else:
                title = seg["content"]
            session.add(
                Segment(
                    id=_stable_segment_id(text_item["canonical_code"], seg["position"]),
                    text_version_id=text_version_id,
                    structural_unit_id=root_unit_id,
                    segment_key=_segment_key(text_item["canonical_code"], seg["position"]),
                    title=title,
                    content=seg["content"],
                    content_gloss=seg.get("content_gloss"),
                    normalized_content=seg.get("normalized_content", seg["content"]),
                    note=f"Imported from plain text source.",
                    position=seg["position"],
                    char_count=len(seg["content"]),
                    metadata_json=metadata_json,
                )
            )
            added_count += 1
            pending_segment_count += 1

            if segment_commit_batch_size and pending_segment_count >= segment_commit_batch_size:
                session.commit()
                pending_segment_count = 0

            if progress_every_segments and seg["position"] % progress_every_segments == 0:
                print(
                    f"Progress {tradition_id}: text={text_version_id}, text_segments={seg['position']}/{text_segment_total}, total_segments={added_count}",
                    flush=True,
                )

        imported_texts += 1
        if pending_segment_count:
            session.commit()
            pending_segment_count = 0

        if progress_every_texts and imported_texts % progress_every_texts == 0:
            print(
                f"Progress {tradition_id}: texts={imported_texts}/{total_texts}, segments={added_count}",
                flush=True,
            )

    session.commit()
    print(f"Imported {added_count} segments for {tradition_id}.")
    return True


def _upsert_person(session: Session, person_record: dict[str, Any]) -> None:
    existing = session.get(Person, person_record["id"])
    if existing:
        for key, value in person_record.items():
            setattr(existing, key, value)
        return
    session.add(Person(**person_record))
