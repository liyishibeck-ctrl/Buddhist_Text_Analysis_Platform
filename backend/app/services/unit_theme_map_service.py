from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR
from backend.app.services.embedding_theme_map_service import (
    THEME_COLORS,
    _numeric_stack,
    _parse_pgvector_text,
    _scale_positions,
    select_embedding_model,
)


UNIT_THEME_MAP_SNAPSHOT_PATH = ROOT_DIR / "data" / "processed" / "theme_maps" / "unit_embedding_theme_map.json"
UNIT_THEME_MAP_REPORT_PATH = ROOT_DIR / "data" / "processed" / "theme_maps" / "unit_embedding_core_report.md"
DEFAULT_UNIT_CLUSTER_COUNT = 12
DEFAULT_CORE_UNITS_PER_CLUSTER = 10
DEFAULT_MIN_SEGMENTS_PER_UNIT = 2
TIBETAN_SECTION_SEGMENT_SPAN = 120


@dataclass(frozen=True, slots=True)
class UnitThemeMapConfig:
    tradition_id: str
    label: str
    short_label: str
    preferred_embedding_model: Optional[str]
    description: str
    min_segments_per_unit: int = DEFAULT_MIN_SEGMENTS_PER_UNIT
    cluster_count: int = DEFAULT_UNIT_CLUSTER_COUNT


UNIT_TRADITION_CONFIGS: dict[str, UnitThemeMapConfig] = {
    "trad-han": UnitThemeMapConfig(
        tradition_id="trad-han",
        label="汉传卷单位主题星图",
        short_label="汉传",
        preferred_embedding_model="doubao-embedding-vision",
        description="长文本按卷聚合，短文本按整部作品聚合；每个点是一卷或一部短经。",
    ),
    "trad-pali": UnitThemeMapConfig(
        tradition_id="trad-pali",
        label="巴利作品单位主题星图",
        short_label="巴利",
        preferred_embedding_model="text-embedding-3-large",
        description="巴利文本没有卷结构，先按 sutta/text 单元聚合；每个点是一部经或文本单元。",
    ),
    "trad-tibetan": UnitThemeMapConfig(
        tradition_id="trad-tibetan",
        label="藏传章级主题星图",
        short_label="藏传",
        preferred_embedding_model="text-embedding-3-large",
        description="84000 长经按连续段落切成约 120 段一个的 section window；每个点是一个章级主题窗口。",
    ),
}


def fetch_unit_embedding_rows(
    session: Session,
    *,
    tradition_id: str,
    embedding_model: str,
    min_segments_per_unit: int = DEFAULT_MIN_SEGMENTS_PER_UNIT,
) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            WITH base_segments AS (
                SELECT
                    s.id AS segment_id,
                    s.position AS segment_position,
                    floor((greatest(s.position, 1) - 1)::numeric / :tibetan_section_segment_span)::int + 1
                        AS tibetan_section_index,
                    su.id AS structural_unit_id,
                    su.unit_type AS structural_unit_type,
                    su.label AS structural_unit_label,
                    su.title AS structural_unit_title,
                    su.position AS structural_unit_position,
                    w.id AS work_id,
                    w.title AS work_title,
                    w.title_english AS work_title_english,
                    w.canonical_code AS canonical_code,
                    w.pitaka_division AS pitaka_division,
                    coalesce(w.fascicle_count, 1) AS fascicle_count,
                    tv.id AS text_version_id,
                    tv.title AS text_version_title,
                    se.embedding AS embedding
                FROM segments s
                JOIN text_versions tv ON tv.id = s.text_version_id
                JOIN works w ON w.id = tv.work_id
                LEFT JOIN structural_units su ON su.id = s.structural_unit_id
                JOIN segment_embeddings se ON se.segment_id = s.id
                WHERE w.tradition_id = :tradition_id
                  AND se.embedding_model = :embedding_model
            ),
            segment_units AS (
                SELECT
                    CASE
                        WHEN :tradition_id = 'trad-tibetan'
                            THEN 'tibetan-section:' || work_id || ':' || lpad(tibetan_section_index::text, 4, '0')
                        WHEN :tradition_id = 'trad-han' AND structural_unit_type = 'juan' THEN structural_unit_id
                        WHEN structural_unit_type IN ('text', 'sutta', 'sutra', 'treatise') THEN structural_unit_id
                        ELSE 'work:' || work_id
                    END AS unit_id,
                    CASE
                        WHEN :tradition_id = 'trad-tibetan' THEN 'section-window'
                        WHEN :tradition_id = 'trad-han' AND structural_unit_type = 'juan' THEN 'juan'
                        ELSE 'work'
                    END AS unit_type,
                    CASE
                        WHEN :tradition_id = 'trad-tibetan'
                            THEN concat(
                                coalesce(nullif(work_title_english, ''), work_title),
                                ' · section ',
                                lpad(tibetan_section_index::text, 3, '0')
                            )
                        WHEN :tradition_id = 'trad-han' AND structural_unit_type = 'juan'
                            THEN concat(work_title, ' · ', coalesce(nullif(structural_unit_label, ''), nullif(structural_unit_title, ''), '卷'))
                        WHEN structural_unit_type IN ('text', 'sutta', 'sutra', 'treatise')
                            THEN coalesce(nullif(structural_unit_title, ''), nullif(structural_unit_label, ''), text_version_title, work_title)
                        ELSE work_title
                    END AS unit_label,
                    CASE
                        WHEN :tradition_id = 'trad-tibetan' THEN tibetan_section_index
                        ELSE coalesce(structural_unit_position, 0)
                    END AS unit_position,
                    segment_id,
                    work_id,
                    work_title,
                    work_title_english,
                    canonical_code,
                    pitaka_division,
                    fascicle_count,
                    text_version_id,
                    text_version_title,
                    embedding
                FROM base_segments
            )
            SELECT
                unit_id,
                min(unit_type) AS unit_type,
                min(unit_label) AS unit_label,
                min(unit_position) AS unit_position,
                min(work_id) AS work_id,
                min(work_title) AS work_title,
                min(work_title_english) AS work_title_english,
                min(canonical_code) AS canonical_code,
                min(pitaka_division) AS pitaka_division,
                min(fascicle_count) AS fascicle_count,
                min(text_version_id) AS text_version_id,
                min(text_version_title) AS text_version_title,
                count(*) AS segment_count,
                avg(embedding)::text AS embedding
            FROM segment_units
            GROUP BY unit_id
            HAVING count(*) >= :min_segments_per_unit
            ORDER BY min(unit_type), min(work_title), min(unit_position), unit_id
            """
        ),
        {
            "tradition_id": tradition_id,
            "embedding_model": embedding_model,
            "min_segments_per_unit": min_segments_per_unit,
            "tibetan_section_segment_span": TIBETAN_SECTION_SEGMENT_SPAN,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def _unit_title(row: dict[str, Any]) -> str:
    label = str(row.get("unit_label") or row.get("work_title") or row.get("unit_id") or "")
    return " ".join(label.split())


def _display_work_title(row: dict[str, Any]) -> str:
    title = str(row.get("work_title_english") or row.get("work_title") or row.get("unit_label") or "")
    return " ".join(title.split())


def _cluster_subtitle(core_units: list[dict[str, Any]]) -> str:
    if not core_units:
        return "核心未明"
    work_counts = Counter(_display_work_title(item) for item in core_units)
    titles = [title for title, _count in work_counts.most_common(2) if title]
    return " / ".join(title[:16] for title in titles) if titles else _unit_title(core_units[0])[:16]


def build_unit_theme_map_from_rows(
    rows: list[dict[str, Any]],
    *,
    config: UnitThemeMapConfig,
    embedding_model: str,
    core_units_per_cluster: int = DEFAULT_CORE_UNITS_PER_CLUSTER,
) -> dict[str, Any]:
    if not rows:
        return {
            "tradition_id": config.tradition_id,
            "tradition_label": config.label,
            "tradition_short_label": config.short_label,
            "description": config.description,
            "embedding_model": embedding_model,
            "unit_count": 0,
            "cluster_count": 0,
            "clusters": [],
            "points": [],
        }

    np, MiniBatchKMeans, PCA, normalize = _numeric_stack()
    vectors = np.vstack([_parse_pgvector_text(str(row["embedding"])) for row in rows])
    vectors = normalize(vectors, norm="l2")
    cluster_count = min(config.cluster_count, len(rows))
    if cluster_count <= 1:
        labels = np.zeros(len(rows), dtype=np.int32)
        centers = np.asarray([vectors.mean(axis=0)])
    else:
        kmeans = MiniBatchKMeans(
            n_clusters=cluster_count,
            random_state=42,
            batch_size=min(512, len(rows)),
            n_init=8,
            max_iter=120,
        )
        labels = kmeans.fit_predict(vectors)
        centers = kmeans.cluster_centers_
    centers = normalize(centers, norm="l2")

    if len(rows) >= 2:
        pca = PCA(n_components=2, random_state=42).fit(vectors)
        projected_units = pca.transform(vectors)
        projected_centers = pca.transform(centers)
        point_positions = _scale_positions([(float(point[0]), float(point[1])) for point in projected_units])
        center_positions = _scale_positions([(float(point[0]), float(point[1])) for point in projected_centers])
    else:
        point_positions = [(50.0, 50.0)]
        center_positions = [(50.0, 50.0)]

    points: list[dict[str, Any]] = []
    clusters: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        cluster_index = int(labels[index])
        x, y = point_positions[index]
        points.append(
            {
                "unit_id": row["unit_id"],
                "unit_type": row["unit_type"],
                "unit_label": _unit_title(row),
                "work_id": row["work_id"],
                "work_title": row["work_title"],
                "work_title_english": row.get("work_title_english") or "",
                "canonical_code": row.get("canonical_code") or "",
                "pitaka_division": row.get("pitaka_division") or "",
                "segment_count": int(row["segment_count"]),
                "cluster_index": cluster_index + 1,
                "color": THEME_COLORS[cluster_index % len(THEME_COLORS)],
                "radius": round(0.9 + min(2.8, math.log10(max(2, int(row["segment_count"]))) * 0.72), 2),
                "x": x,
                "y": y,
            }
        )

    for cluster_index in range(cluster_count):
        member_indices = np.where(labels == cluster_index)[0]
        if len(member_indices) == 0:
            continue
        similarities = vectors[member_indices] @ centers[cluster_index]
        nearest_order = np.argsort(-similarities)
        core_units: list[dict[str, Any]] = []
        for order_index in nearest_order[:core_units_per_cluster]:
            member_index = int(member_indices[int(order_index)])
            row = rows[member_index]
            core_units.append(
                {
                    "unit_id": row["unit_id"],
                    "unit_type": row["unit_type"],
                    "unit_label": _unit_title(row),
                    "work_id": row["work_id"],
                    "work_title": row["work_title"],
                    "work_title_english": row.get("work_title_english") or "",
                    "canonical_code": row.get("canonical_code") or "",
                    "pitaka_division": row.get("pitaka_division") or "",
                    "segment_count": int(row["segment_count"]),
                    "similarity": round(float(similarities[int(order_index)]), 4),
                }
            )
        x, y = center_positions[cluster_index]
        top_works = [
            {"work_title": title, "unit_count": count}
            for title, count in Counter(_display_work_title(rows[int(index)]) for index in member_indices).most_common(5)
        ]
        clusters.append(
            {
                "cluster_index": cluster_index + 1,
                "label": f"星系 {cluster_index + 1:02d}",
                "subtitle": _cluster_subtitle(core_units),
                "unit_count": int(len(member_indices)),
                "segment_count": int(sum(int(rows[int(index)]["segment_count"]) for index in member_indices)),
                "x": x,
                "y": y,
                "color": THEME_COLORS[cluster_index % len(THEME_COLORS)],
                "core_units": core_units,
                "top_works": top_works,
            }
        )

    clusters.sort(key=lambda item: item["unit_count"], reverse=True)
    return {
        "tradition_id": config.tradition_id,
        "tradition_label": config.label,
        "tradition_short_label": config.short_label,
        "description": config.description,
        "embedding_model": embedding_model,
        "unit_count": len(rows),
        "cluster_count": len(clusters),
        "clusters": clusters,
        "points": points,
    }


def build_unit_theme_map(
    session: Session,
    *,
    config: UnitThemeMapConfig,
    core_units_per_cluster: int = DEFAULT_CORE_UNITS_PER_CLUSTER,
) -> dict[str, Any]:
    embedding_model = select_embedding_model(
        session,
        tradition_id=config.tradition_id,
        preferred_model=config.preferred_embedding_model,
    )
    if not embedding_model:
        return build_unit_theme_map_from_rows([], config=config, embedding_model="")
    rows = fetch_unit_embedding_rows(
        session,
        tradition_id=config.tradition_id,
        embedding_model=embedding_model,
        min_segments_per_unit=config.min_segments_per_unit,
    )
    return build_unit_theme_map_from_rows(
        rows,
        config=config,
        embedding_model=embedding_model,
        core_units_per_cluster=core_units_per_cluster,
    )


def build_unit_theme_maps_snapshot(
    session: Session,
    *,
    tradition_ids: Optional[list[str]] = None,
    core_units_per_cluster: int = DEFAULT_CORE_UNITS_PER_CLUSTER,
) -> dict[str, Any]:
    selected_ids = tradition_ids or list(UNIT_TRADITION_CONFIGS)
    maps = [
        build_unit_theme_map(
            session,
            config=UNIT_TRADITION_CONFIGS[tradition_id],
            core_units_per_cluster=core_units_per_cluster,
        )
        for tradition_id in selected_ids
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "method": "unit-level averaged segment embeddings + Tibetan 120-segment section windows + k=12 MiniBatchKMeans + PCA projection",
        "map_count": len(maps),
        "maps": maps,
    }


def save_unit_theme_maps_snapshot(
    snapshot: dict[str, Any],
    *,
    path: Path = UNIT_THEME_MAP_SNAPSHOT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_unit_theme_maps_snapshot(
    *,
    path: Path = UNIT_THEME_MAP_SNAPSHOT_PATH,
) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_unit_theme_core_report(
    snapshot: dict[str, Any],
    *,
    path: Path = UNIT_THEME_MAP_REPORT_PATH,
) -> Path:
    lines = [
        "# Unit-Level Embedding Theme Core Report",
        "",
        "每个 cluster 的 core units 是离该星系 centroid 最近的卷/章级/作品单元。",
        "",
    ]
    for item in snapshot["maps"]:
        lines.append(f"## {item['tradition_short_label']} ({item['tradition_id']})")
        lines.append("")
        lines.append(f"- embedding: `{item['embedding_model']}`")
        lines.append(f"- units: `{item['unit_count']}`")
        lines.append(f"- clusters: `{item['cluster_count']}`")
        lines.append("")
        for cluster in item["clusters"]:
            lines.append(f"### {cluster['label']} · {cluster['subtitle']}")
            lines.append("")
            lines.append(f"- unit_count: `{cluster['unit_count']}`")
            lines.append(f"- segment_count: `{cluster['segment_count']}`")
            lines.append("- core units:")
            for core in cluster["core_units"]:
                code = f" · {core['canonical_code']}" if core.get("canonical_code") else ""
                lines.append(
                    f"  - `{core['unit_type']}` {core['unit_label']}{code} "
                    f"(segments={core['segment_count']}, sim={core['similarity']})"
                )
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
