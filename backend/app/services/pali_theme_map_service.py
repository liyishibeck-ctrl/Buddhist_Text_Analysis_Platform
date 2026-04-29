from __future__ import annotations

import json
import math
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR
from backend.app.models import Segment, TextVersion, Work


PALI_THEME_MAP_SNAPSHOT_PATH = ROOT_DIR / "data" / "processed" / "pali" / "pali_theme_map.json"
PALI_THEME_MAP_TRADITION_ID = "trad-pali"
PALI_THEME_MAP_CONTENT_FIELD = "content_gloss"

PALI_THEME_DEFINITIONS: list[dict[str, Any]] = [
    {
        "slug": "four-noble-truths",
        "label": "四谛",
        "family": "insight",
        "description": "围绕苦、集、灭、道结构的核心教说。",
        "patterns": [
            "four noble truths",
            "suffering, its arising, cessation, and the path",
            "arising of suffering",
            "cessation of suffering",
        ],
    },
    {
        "slug": "dependent-origination",
        "label": "缘起",
        "family": "insight",
        "description": "围绕缘起、条件生起与因果链条的教义。",
        "patterns": [
            "dependent origination",
            "conditioned origination",
            "when this exists",
            "this being, that is",
            "because of this",
        ],
    },
    {
        "slug": "impermanence",
        "label": "无常",
        "family": "insight",
        "description": "围绕生灭、坏散与变化不住的观照。",
        "patterns": [
            "impermanent",
            "impermanence",
            "arising and ceasing",
            "arises and ceases",
            "arising and passing away",
        ],
    },
    {
        "slug": "suffering",
        "label": "苦",
        "family": "insight",
        "description": "围绕苦、逼迫性与不圆满性的分析。",
        "patterns": [
            "suffering",
            "stressful",
            "painful",
            "unsatisfactory",
        ],
    },
    {
        "slug": "non-self",
        "label": "无我",
        "family": "insight",
        "description": "围绕无我、非我、非我所的洞见。",
        "patterns": [
            "not self",
            "non-self",
            "not mine",
            "not me",
            "not my self",
        ],
    },
    {
        "slug": "aggregates",
        "label": "五蕴",
        "family": "insight",
        "description": "围绕色受想行识与五蕴观察的主题。",
        "patterns": [
            "aggregates",
            "five aggregates",
            "form, feeling, perception",
            "form is not self",
            "feeling, perception, formations, and consciousness",
        ],
    },
    {
        "slug": "wisdom",
        "label": "慧",
        "family": "insight",
        "description": "围绕智慧、洞见与如实知见的语汇。",
        "patterns": [
            "wisdom",
            "discernment",
            "clear seeing",
            "insight arises",
            "understanding things as they are",
        ],
    },
    {
        "slug": "mindfulness",
        "label": "念",
        "family": "practice",
        "description": "围绕念住、正念与持续观照的修法。",
        "patterns": [
            "mindfulness",
            "mindful",
            "establishments of mindfulness",
            "satipatthana",
            "recollection",
        ],
    },
    {
        "slug": "concentration",
        "label": "定",
        "family": "practice",
        "description": "围绕禅定、三昧、禅那与专注心。",
        "patterns": [
            "concentration",
            "collected mind",
            "absorption",
            "jhana",
            "samadhi",
            "meditation",
        ],
    },
    {
        "slug": "precepts",
        "label": "戒",
        "family": "practice",
        "description": "围绕戒、德行、调御与行为规范。",
        "patterns": [
            "precepts",
            "virtue",
            "ethical conduct",
            "moral discipline",
            "restraint",
        ],
    },
    {
        "slug": "loving-kindness",
        "label": "慈",
        "family": "heart",
        "description": "围绕慈心、善意、友爱与无量心。",
        "patterns": [
            "loving-kindness",
            "goodwill",
            "friendliness",
            "metta",
            "boundless loving-kindness",
        ],
    },
    {
        "slug": "compassion",
        "label": "悲",
        "family": "heart",
        "description": "围绕悲悯、同情与拔苦关怀。",
        "patterns": [
            "compassion",
            "karuna",
            "sympathy",
            "pity",
        ],
    },
    {
        "slug": "craving-and-clinging",
        "label": "渴爱与执取",
        "family": "samsara",
        "description": "围绕爱、取、执著、贪欲与系缚。",
        "patterns": [
            "craving",
            "thirst",
            "clinging",
            "attachment",
            "grasping",
            "greed",
        ],
    },
    {
        "slug": "karma",
        "label": "业",
        "family": "samsara",
        "description": "围绕业、行为后果与道德因果。",
        "patterns": [
            "karma",
            "kamma",
            "intentional action",
            "deeds",
            "results of action",
        ],
    },
    {
        "slug": "rebirth",
        "label": "再生",
        "family": "samsara",
        "description": "围绕轮回、再生、来世与有情流转。",
        "patterns": [
            "rebirth",
            "reborn",
            "future life",
            "next life",
            "re-arising",
        ],
    },
    {
        "slug": "liberation",
        "label": "解脱",
        "family": "liberation",
        "description": "围绕离系、释放、出离与阿罗汉果。",
        "patterns": [
            "liberated",
            "release",
            "freedom",
            "emancipation",
            "delivered",
        ],
    },
    {
        "slug": "nirvana",
        "label": "涅槃",
        "family": "liberation",
        "description": "围绕涅槃、寂灭、无余依与终极止息。",
        "patterns": [
            "nirvana",
            "nibbana",
            "unbinding",
            "extinguishment",
        ],
    },
]

PALI_THEME_FAMILY_META: dict[str, dict[str, Any]] = {
    "insight": {"label": "观慧", "x": 24.0, "y": 34.0, "color": "#8F4F23"},
    "practice": {"label": "修行", "x": 54.0, "y": 26.0, "color": "#4E7C59"},
    "heart": {"label": "梵住", "x": 74.0, "y": 34.0, "color": "#9D5C63"},
    "samsara": {"label": "轮回", "x": 30.0, "y": 72.0, "color": "#7A5F2F"},
    "liberation": {"label": "解脱", "x": 72.0, "y": 68.0, "color": "#496B8A"},
}


def _normalize_match_text(text_value: str) -> str:
    normalized = unicodedata.normalize("NFKD", text_value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    collapsed = " ".join(ascii_text.lower().split())
    return f" {collapsed} "


def _contains_pattern(normalized_text: str, pattern: str) -> bool:
    return f" {pattern} " in normalized_text or pattern in normalized_text


def _matching_theme_slugs(gloss_text: str) -> list[str]:
    normalized_text = _normalize_match_text(gloss_text)
    matched: list[str] = []
    for definition in PALI_THEME_DEFINITIONS:
        if any(_contains_pattern(normalized_text, pattern) for pattern in definition["patterns"]):
            matched.append(definition["slug"])
    return matched


def _build_theme_positions(theme_slugs: list[str]) -> dict[str, tuple[float, float]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for definition in PALI_THEME_DEFINITIONS:
        if definition["slug"] in theme_slugs:
            grouped[definition["family"]].append(definition["slug"])

    positions: dict[str, tuple[float, float]] = {}
    for family_slug, slugs in grouped.items():
        family_meta = PALI_THEME_FAMILY_META[family_slug]
        base_x = float(family_meta["x"])
        base_y = float(family_meta["y"])
        count = len(slugs)
        radius = 11.0 if count > 2 else 8.0
        for index, slug in enumerate(slugs):
            if count == 1:
                positions[slug] = (base_x, base_y)
                continue
            angle = (-math.pi / 2) + (2 * math.pi * index / count)
            positions[slug] = (
                round(base_x + (radius * math.cos(angle)), 2),
                round(base_y + (radius * math.sin(angle)), 2),
            )
    return positions


def build_pali_theme_map_from_rows(
    rows: Iterable[dict[str, Any]],
    *,
    max_examples_per_theme: int = 4,
    max_top_works: int = 5,
    max_edges: int = 18,
) -> dict[str, Any]:
    theme_counts: Counter[str] = Counter()
    theme_work_counts: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    theme_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edge_counts: Counter[tuple[str, str]] = Counter()
    gloss_segment_count = 0
    matched_segment_count = 0

    for row in rows:
        gloss_text = str(row.get("content_gloss") or "").strip()
        if not gloss_text:
            continue
        gloss_segment_count += 1
        matched_slugs = _matching_theme_slugs(gloss_text)
        if not matched_slugs:
            continue
        matched_segment_count += 1
        unique_slugs = sorted(set(matched_slugs))
        preview = gloss_text[:220] + ("..." if len(gloss_text) > 220 else "")
        work_key = (str(row["work_id"]), str(row["work_title"]))
        for slug in unique_slugs:
            theme_counts[slug] += 1
            theme_work_counts[slug][work_key] += 1
            if len(theme_examples[slug]) < max_examples_per_theme:
                theme_examples[slug].append(
                    {
                        "segment_id": row["segment_id"],
                        "segment_key": row["segment_key"],
                        "text_version_id": row["text_version_id"],
                        "work_id": row["work_id"],
                        "work_title": row["work_title"],
                        "canonical_code": row.get("canonical_code") or "",
                        "preview": preview,
                    }
                )
        for source_slug, target_slug in combinations(unique_slugs, 2):
            edge_counts[(source_slug, target_slug)] += 1

    active_slugs = [definition["slug"] for definition in PALI_THEME_DEFINITIONS if theme_counts[definition["slug"]] > 0]
    positions = _build_theme_positions(active_slugs)
    max_count = max(theme_counts.values(), default=1)
    nodes: list[dict[str, Any]] = []

    for definition in PALI_THEME_DEFINITIONS:
        slug = definition["slug"]
        count = theme_counts[slug]
        if count <= 0:
            continue
        family_meta = PALI_THEME_FAMILY_META[definition["family"]]
        x, y = positions.get(slug, (family_meta["x"], family_meta["y"]))
        share = round((count / gloss_segment_count) * 100, 2) if gloss_segment_count else 0.0
        size_px = int(round(84 + 72 * math.sqrt(count / max_count)))
        top_works = [
            {
                "work_id": work_id,
                "work_title": work_title,
                "segment_count": work_count,
            }
            for (work_id, work_title), work_count in theme_work_counts[slug].most_common(max_top_works)
        ]
        nodes.append(
            {
                "slug": slug,
                "label": definition["label"],
                "family_slug": definition["family"],
                "family_label": family_meta["label"],
                "family_color": family_meta["color"],
                "description": definition["description"],
                "segment_count": count,
                "share_percent": share,
                "size_px": size_px,
                "x": x,
                "y": y,
                "top_works": top_works,
                "examples": theme_examples[slug],
            }
        )

    edge_rows: list[dict[str, Any]] = []
    for (source_slug, target_slug), count in edge_counts.most_common(max_edges):
        if count <= 1:
            continue
        source_pos = positions.get(source_slug)
        target_pos = positions.get(target_slug)
        if not source_pos or not target_pos:
            continue
        edge_rows.append(
            {
                "source": source_slug,
                "target": target_slug,
                "count": count,
                "stroke_width": round(1.2 + 4.8 * (count / max(edge_counts.values(), default=1)), 2),
                "x1": source_pos[0],
                "y1": source_pos[1],
                "x2": target_pos[0],
                "y2": target_pos[1],
            }
        )

    family_counts: Counter[str] = Counter()
    for node in nodes:
        family_counts[node["family_slug"]] += node["segment_count"]

    families = [
        {
            "slug": slug,
            "label": meta["label"],
            "color": meta["color"],
            "segment_count": family_counts.get(slug, 0),
        }
        for slug, meta in PALI_THEME_FAMILY_META.items()
        if family_counts.get(slug, 0) > 0
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tradition_id": PALI_THEME_MAP_TRADITION_ID,
        "content_field": PALI_THEME_MAP_CONTENT_FIELD,
        "gloss_segment_count": gloss_segment_count,
        "matched_segment_count": matched_segment_count,
        "unmatched_segment_count": max(0, gloss_segment_count - matched_segment_count),
        "theme_count": len(nodes),
        "families": families,
        "nodes": nodes,
        "edges": edge_rows,
    }


def build_pali_theme_map_snapshot(
    session: Session,
    *,
    max_examples_per_theme: int = 4,
    max_top_works: int = 5,
    max_edges: int = 18,
) -> dict[str, Any]:
    stmt = (
        select(
            Segment.id.label("segment_id"),
            Segment.segment_key,
            Segment.content_gloss,
            TextVersion.id.label("text_version_id"),
            Work.id.label("work_id"),
            Work.title.label("work_title"),
            Work.canonical_code,
        )
        .join(Segment.text_version)
        .join(TextVersion.work)
        .where(
            Work.tradition_id == PALI_THEME_MAP_TRADITION_ID,
            Segment.content_gloss.is_not(None),
            Segment.content_gloss != "",
        )
        .order_by(Segment.id)
    )
    rows = (
        {
            "segment_id": row.segment_id,
            "segment_key": row.segment_key,
            "content_gloss": row.content_gloss,
            "text_version_id": row.text_version_id,
            "work_id": row.work_id,
            "work_title": row.work_title,
            "canonical_code": row.canonical_code,
        }
        for row in session.execute(stmt.execution_options(yield_per=1000))
    )
    return build_pali_theme_map_from_rows(
        rows,
        max_examples_per_theme=max_examples_per_theme,
        max_top_works=max_top_works,
        max_edges=max_edges,
    )


def save_pali_theme_map_snapshot(snapshot: dict[str, Any], path: Path = PALI_THEME_MAP_SNAPSHOT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_pali_theme_map_snapshot(path: Path = PALI_THEME_MAP_SNAPSHOT_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
