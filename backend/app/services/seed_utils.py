from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.models import (
    CatalogNode,
    CitationLink,
    Collection,
    ConceptTag,
    EmbeddingIndexMetadata,
    Language,
    ParallelLink,
    Person,
    Segment,
    SegmentConceptTag,
    Source,
    StructuralUnit,
    TextVersion,
    TextVersionPersonRole,
    Tradition,
    Work,
    WorkPersonRole,
)


SEED_ORDER: list[tuple[str, type[Any]]] = [
    ("traditions", Tradition),
    ("languages", Language),
    ("sources", Source),
    ("collections", Collection),
    ("persons", Person),
    ("works", Work),
    ("work_person_roles", WorkPersonRole),
    ("text_versions", TextVersion),
    ("text_version_person_roles", TextVersionPersonRole),
    ("catalog_nodes", CatalogNode),
    ("structural_units", StructuralUnit),
    ("segments", Segment),
    ("concept_tags", ConceptTag),
    ("segment_concept_tags", SegmentConceptTag),
    ("parallel_links", ParallelLink),
    ("citation_links", CitationLink),
    ("embedding_index_metadata", EmbeddingIndexMetadata),
]


def load_json_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def records_to_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    frame = pd.DataFrame(records)
    frame = frame.where(pd.notnull(frame), None)
    return frame.to_dict(orient="records")


def clear_seed_data(session: Session) -> None:
    for _, model in reversed(SEED_ORDER):
        session.query(model).delete()


def apply_payload(session: Session, payload: dict[str, Any]) -> None:
    for list_name, model in SEED_ORDER:
        for record in records_to_rows(payload.get(list_name, [])):
            if model is Segment:
                record["char_count"] = record.get("char_count") or len(record.get("content", ""))
                record["normalized_content"] = record.get("normalized_content") or record.get("content", "")
            session.add(model(**record))
