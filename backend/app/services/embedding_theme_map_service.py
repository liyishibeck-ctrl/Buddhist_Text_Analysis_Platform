from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import ROOT_DIR


EMBEDDING_THEME_MAP_SNAPSHOT_PATH = ROOT_DIR / "data" / "processed" / "theme_maps" / "embedding_theme_maps.json"
DEFAULT_SAMPLE_LIMIT = 12_000
DEFAULT_CLUSTER_COUNT = 12
DEFAULT_MAX_EXAMPLES_PER_THEME = 4
DEFAULT_MAX_TOP_WORKS = 5
DEFAULT_MAX_EDGES = 28


@dataclass(frozen=True, slots=True)
class ThemeMapTraditionConfig:
    tradition_id: str
    label: str
    short_label: str
    description: str
    preferred_embedding_model: Optional[str]
    content_field: str
    sample_limit: int = DEFAULT_SAMPLE_LIMIT
    cluster_count: int = DEFAULT_CLUSTER_COUNT


TRADITION_CONFIGS: dict[str, ThemeMapTraditionConfig] = {
    "trad-han": ThemeMapTraditionConfig(
        tradition_id="trad-han",
        label="汉传主题地图",
        short_label="汉传",
        description="基于汉传正文 segment embedding 的抽样聚类，帮助快速观察经藏内部的主题地形。",
        preferred_embedding_model="doubao-embedding-vision",
        content_field="content",
        sample_limit=30_000,
    ),
    "trad-pali": ThemeMapTraditionConfig(
        tradition_id="trad-pali",
        label="巴利主题地图",
        short_label="巴利",
        description="基于巴利正文 normalized_content embedding 的抽样聚类，显示尼柯耶语料中的主题近邻。",
        preferred_embedding_model="text-embedding-3-large",
        content_field="normalized_content",
        sample_limit=12_000,
    ),
    "trad-tibetan": ThemeMapTraditionConfig(
        tradition_id="trad-tibetan",
        label="藏传主题地图",
        short_label="藏传",
        description="基于 84000 藏文经部正文 embedding 的抽样聚类，辅助浏览藏传经部的主题区块。",
        preferred_embedding_model="text-embedding-3-large",
        content_field="normalized_content",
        sample_limit=18_000,
    ),
}

THEME_COLORS = [
    "#8F4F23",
    "#4E7C59",
    "#496B8A",
    "#9D5C63",
    "#7A5F2F",
    "#6E5C8C",
    "#A05D38",
    "#3F7F75",
    "#8A6B36",
    "#5F6F3E",
    "#8B4B5F",
    "#4B6F8B",
]

CHINESE_THEME_TERMS = [
    "佛",
    "如来",
    "如來",
    "菩萨",
    "菩薩",
    "菩提",
    "菩提心",
    "功德",
    "声闻",
    "聲聞",
    "阿罗汉",
    "阿羅漢",
    "般若",
    "空",
    "自性空",
    "無性",
    "无相",
    "無相",
    "无我",
    "無我",
    "无常",
    "無常",
    "苦",
    "苦諦",
    "涅槃",
    "解脱",
    "解脫",
    "因缘",
    "因緣",
    "缘起",
    "緣起",
    "四谛",
    "四諦",
    "十二因缘",
    "十二因緣",
    "戒",
    "定",
    "慧",
    "禅",
    "禪",
    "三昧",
    "慈悲",
    "眾生",
    "布施",
    "波羅蜜",
    "波罗蜜",
    "净土",
    "淨土",
]

LATIN_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "but",
    "can",
    "could",
    "does",
    "dont",
    "from",
    "had",
    "has",
    "have",
    "having",
    "heard",
    "here",
    "into",
    "its",
    "may",
    "not",
    "one",
    "only",
    "other",
    "our",
    "out",
    "over",
    "said",
    "shall",
    "should",
    "such",
    "than",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "thats",
    "theyre",
    "those",
    "thus",
    "upon",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
    "youre",
}

LATIN_THEME_TERMS = [
    "buddha",
    "bodhisattva",
    "dharma",
    "dhamma",
    "sangha",
    "monk",
    "bhikkhu",
    "wisdom",
    "prajna",
    "emptiness",
    "compassion",
    "loving-kindness",
    "mindfulness",
    "concentration",
    "samadhi",
    "jhana",
    "suffering",
    "dukkha",
    "impermanence",
    "non-self",
    "nirvana",
    "nibbana",
    "liberation",
    "karma",
    "rebirth",
    "dependent",
    "origination",
    "aggregate",
    "meditation",
    "precepts",
]

THEME_LABEL_RULES: list[dict[str, Any]] = [
    {
        "label": "空性与般若",
        "terms": {
            "trad-han": ["空", "般若", "無相", "无相", "無所得", "无所得", "實相", "实相", "性空", "自性空", "無性"],
            "trad-pali": ["emptiness", "empty", "wisdom", "prajna", "not-self", "non-self"],
            "trad-tibetan": ["emptiness", "empty", "wisdom", "prajna", "insight"],
        },
    },
    {
        "label": "苦与四谛",
        "terms": {
            "trad-han": ["苦", "四諦", "四谛", "苦集", "滅道", "灭道", "苦諦", "集諦", "滅諦", "道諦", "集谛", "灭谛", "道谛"],
            "trad-pali": ["suffering", "dukkha", "four noble truths", "cessation", "path"],
            "trad-tibetan": ["suffering", "cessation", "truth", "path"],
        },
    },
    {
        "label": "缘起因果",
        "terms": {
            "trad-han": ["因緣", "因缘", "緣起", "缘起", "十二因緣", "十二因缘", "因果", "生起"],
            "trad-pali": ["dependent", "origination", "condition", "arising", "cause"],
            "trad-tibetan": ["dependent", "origination", "condition", "cause"],
        },
    },
    {
        "label": "无常无我",
        "terms": {
            "trad-han": ["無常", "无常", "無我", "无我", "非我", "生滅", "生灭", "五蘊", "五蕴"],
            "trad-pali": ["impermanence", "impermanent", "non-self", "not self", "aggregates"],
            "trad-tibetan": ["impermanent", "nonself", "aggregates", "selfless"],
        },
    },
    {
        "label": "戒定慧修行",
        "terms": {
            "trad-han": ["戒", "定", "慧", "禪", "禅", "三昧", "修行", "正念", "修心"],
            "trad-pali": ["precepts", "virtue", "concentration", "samadhi", "jhana", "mindfulness", "meditation"],
            "trad-tibetan": ["discipline", "concentration", "meditation", "samadhi", "mindfulness"],
        },
    },
    {
        "label": "菩萨行愿",
        "terms": {
            "trad-han": ["菩薩", "菩萨", "菩提", "菩提心", "菩提願", "發心", "发心", "行願", "行愿", "六度", "布施", "忍辱", "波羅蜜", "波罗蜜", "摩訶薩", "摩诃萨", "功德"],
            "trad-pali": ["bodhisattva", "perfection", "generosity", "aspiration"],
            "trad-tibetan": ["bodhisattva", "bodhicitta", "aspiration", "perfection", "generosity"],
        },
    },
    {
        "label": "慈悲利生",
        "terms": {
            "trad-han": ["慈悲", "大悲", "慈", "悲", "眾生", "众生", "救度", "利益", "有情"],
            "trad-pali": ["compassion", "loving-kindness", "metta", "karuna", "beings"],
            "trad-tibetan": ["compassion", "loving-kindness", "beings", "benefit"],
        },
    },
    {
        "label": "涅槃解脱",
        "terms": {
            "trad-han": ["涅槃", "解脫", "解脱", "寂滅", "寂灭", "滅度", "灭度", "無為", "无为"],
            "trad-pali": ["nirvana", "nibbana", "liberation", "release", "unbinding"],
            "trad-tibetan": ["nirvana", "liberation", "release", "freedom"],
        },
    },
    {
        "label": "佛陀说法",
        "terms": {
            "trad-han": ["佛告", "佛言", "如來", "如来", "世尊", "說法", "说法", "宣說", "宣说", "法門", "法门"],
            "trad-pali": ["buddha", "blessed one", "teaching", "dharma", "dhamma"],
            "trad-tibetan": ["buddha", "thus-gone", "teaching", "dharma"],
        },
    },
    {
        "label": "僧团与戒律",
        "terms": {
            "trad-han": ["比丘", "比丘尼", "僧", "僧伽", "戒律", "律"],
            "trad-pali": ["monk", "mendicant", "bhikkhu", "sangha", "discipline"],
            "trad-tibetan": ["monk", "sangha", "discipline", "vows"],
        },
    },
    {
        "label": "净土信愿",
        "terms": {
            "trad-han": ["淨土", "净土", "佛土", "阿彌陀", "阿弥陀", "極樂", "极乐", "往生", "念佛"],
            "trad-pali": ["faith", "devotion", "recollection"],
            "trad-tibetan": ["pure land", "amitabha", "devotion", "recollection"],
        },
    },
    {
        "label": "神通护法",
        "terms": {
            "trad-han": ["神通", "天", "龍", "龙", "鬼神", "護法", "护法", "陀羅尼", "陀罗尼", "咒"],
            "trad-pali": ["deva", "divine", "miracle", "spirit", "guardian"],
            "trad-tibetan": ["deva", "divine", "mantra", "guardian", "dharani"],
        },
    },
]


def _numeric_stack():  # type: ignore[no-untyped-def]
    try:
        import numpy as np
        from sklearn.cluster import MiniBatchKMeans
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import normalize
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError(
            "Embedding theme map generation requires numpy and scikit-learn. "
            "Install project dependencies before running the build script."
        ) from exc

    return np, MiniBatchKMeans, PCA, normalize


def _parse_pgvector_text(vector_text: str):  # type: ignore[no-untyped-def]
    np, _, _, _ = _numeric_stack()
    stripped = (vector_text or "").strip()
    if not stripped.startswith("[") or not stripped.endswith("]"):
        raise ValueError("Expected pgvector text in '[...]' format.")
    return np.fromstring(stripped[1:-1], sep=",", dtype=np.float32)


def _normalize_label_text(text_value: str) -> str:
    normalized = unicodedata.normalize("NFKD", text_value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def _preview_text(row: dict[str, Any], *, max_chars: int = 220) -> str:
    text_value = row.get("content_gloss") or row.get("normalized_content") or row.get("content") or ""
    collapsed = " ".join(str(text_value).split())
    return collapsed[:max_chars] + ("..." if len(collapsed) > max_chars else "")


def _label_source_text(row: dict[str, Any], *, tradition_id: str) -> str:
    if tradition_id == "trad-tibetan" and row.get("content_gloss"):
        return str(row["content_gloss"])
    if row.get("content_gloss"):
        return str(row["content_gloss"])
    return str(row.get("normalized_content") or row.get("content") or "")


def _keyword_counts(rows: Iterable[dict[str, Any]], *, tradition_id: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        text_value = _label_source_text(row, tradition_id=tradition_id)
        if tradition_id == "trad-han":
            for term in CHINESE_THEME_TERMS:
                count = text_value.count(term)
                if count:
                    counter[term] += count
            continue

        normalized = _normalize_label_text(text_value)
        for term in LATIN_THEME_TERMS:
            if term in normalized:
                counter[term] += normalized.count(term)
        for token in re.findall(r"[a-z][a-z-]{3,}", normalized):
            if token not in LATIN_STOPWORDS:
                counter[token] += 1
    return counter


def _term_count(text_value: str, term: str, *, tradition_id: str) -> int:
    if tradition_id == "trad-han":
        return text_value.count(term)
    normalized_text = _normalize_label_text(text_value)
    normalized_term = _normalize_label_text(term)
    if not normalized_term:
        return 0
    return normalized_text.count(normalized_term)


def _theme_scores(rows: Iterable[dict[str, Any]], *, tradition_id: str, weight: float = 1.0) -> Counter[str]:
    scores: Counter[str] = Counter()
    for row in rows:
        text_value = _label_source_text(row, tradition_id=tradition_id)
        for rule in THEME_LABEL_RULES:
            terms = rule["terms"].get(tradition_id) or []
            hit_count = sum(_term_count(text_value, term, tradition_id=tradition_id) for term in terms)
            if hit_count:
                scores[str(rule["label"])] += hit_count * weight
    return scores


def _ranked_theme_labels(
    center_rows: list[dict[str, Any]],
    cluster_rows: list[dict[str, Any]],
    *,
    tradition_id: str,
) -> list[tuple[str, float]]:
    scores = _theme_scores(center_rows, tradition_id=tradition_id, weight=4.0)
    scores.update(_theme_scores(cluster_rows, tradition_id=tradition_id, weight=0.5))
    return [(label, float(score)) for label, score in scores.most_common()]


def _theme_label_from_rows(
    center_rows: list[dict[str, Any]],
    cluster_rows: list[dict[str, Any]],
    *,
    tradition_id: str,
    fallback_keywords: list[str],
    cluster_number: int,
) -> str:
    ranked = _ranked_theme_labels(center_rows, cluster_rows, tradition_id=tradition_id)
    if ranked:
        best_label, best_score = ranked[0]
        if best_label == "佛陀说法" and len(ranked) > 1 and ranked[1][1] >= best_score * 0.32:
            return ranked[1][0]
        return best_label
    return _node_label(fallback_keywords, cluster_number=cluster_number)


def _generic_subtitle_terms(tradition_id: str) -> set[str]:
    return {
        "trad-han": {"佛", "如来", "如來"},
        "trad-pali": {
            "buddha",
            "dhamma",
            "dharma",
            "mendicant",
            "mendicants",
            "things",
            "fine",
            "time",
            "declared",
            "five",
            "four",
            "chapter",
        },
        "trad-tibetan": {
            "buddha",
            "dharma",
            "beings",
            "blessed",
            "lord",
            "great",
            "them",
            "always",
            "just",
        },
    }.get(tradition_id, set())


def _short_work_title(title: str) -> str:
    cleaned = " ".join((title or "").split())
    for prefix in ["大方广佛", "大方廣佛", "佛说", "佛說"]:
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix) + 2:
            cleaned = cleaned[len(prefix) :]
    return cleaned[:14]


def _subtitle_candidates(
    *,
    primary_label: str,
    center_rows: list[dict[str, Any]],
    cluster_rows: list[dict[str, Any]],
    keywords: list[str],
    top_work_titles: list[str],
    tradition_id: str,
    cluster_number: int,
) -> list[str]:
    candidates: list[str] = []
    for label, _score in _ranked_theme_labels(center_rows, cluster_rows, tradition_id=tradition_id):
        if label and label != primary_label and label != "佛陀说法":
            candidates.append(label)

    generic_terms = _generic_subtitle_terms(tradition_id)
    for keyword in keywords:
        if keyword and keyword not in generic_terms and keyword not in primary_label:
            candidates.append(keyword)

    for title in top_work_titles:
        short_title = _short_work_title(title)
        if short_title and short_title not in primary_label:
            candidates.append(short_title)

    candidates.append(f"簇 {cluster_number:02d}")
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _assign_unique_subtitles(nodes: list[dict[str, Any]]) -> None:
    used_display_labels: set[str] = set()
    for node in nodes:
        candidates = list(node.pop("subtitle_candidates", []))
        if not candidates:
            candidates = [f"簇 {node['cluster_index']:02d}"]

        chosen = candidates[-1]
        for candidate in candidates:
            display_label = f"{node['label']} · {candidate}"
            if display_label not in used_display_labels:
                chosen = candidate
                break

        display_label = f"{node['label']} · {chosen}"
        if display_label in used_display_labels:
            chosen = f"{chosen} · 簇 {node['cluster_index']:02d}"
            display_label = f"{node['label']} · {chosen}"
        node["subtitle"] = chosen
        node["display_label"] = display_label
        used_display_labels.add(display_label)


def _node_label(keywords: list[str], *, cluster_number: int) -> str:
    if not keywords:
        return f"主题 {cluster_number:02d}"
    if len(keywords) == 1:
        return keywords[0]
    return " / ".join(keywords[:2])


def _scale_positions(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(value: float, low: float, high: float) -> float:
        if math.isclose(low, high):
            return 50.0
        return 8.0 + ((value - low) / (high - low)) * 84.0

    return [(round(scale(x, min_x, max_x), 2), round(scale(y, min_y, max_y), 2)) for x, y in points]


def _relax_overlapping_positions(
    positions: list[tuple[float, float]],
    radii: list[float],
    *,
    min_gap: float = 1.8,
    iterations: int = 160,
) -> list[tuple[float, float]]:
    if len(positions) <= 1:
        return positions

    mutable = [[float(x), float(y)] for x, y in positions]
    for _ in range(iterations):
        moved = False
        for left_index in range(len(mutable)):
            for right_index in range(left_index + 1, len(mutable)):
                left = mutable[left_index]
                right = mutable[right_index]
                dx = right[0] - left[0]
                dy = right[1] - left[1]
                distance = math.hypot(dx, dy)
                required_distance = radii[left_index] + radii[right_index] + min_gap
                if distance >= required_distance:
                    continue
                if distance < 0.001:
                    angle = (left_index * 37 + right_index * 53) % 360
                    dx = math.cos(math.radians(angle))
                    dy = math.sin(math.radians(angle))
                    distance = 1.0
                push = (required_distance - distance) / 2.0
                ux = dx / distance
                uy = dy / distance
                left[0] -= ux * push
                left[1] -= uy * push
                right[0] += ux * push
                right[1] += uy * push
                moved = True
        for point, radius in zip(mutable, radii):
            margin = max(6.0, radius + 1.2)
            point[0] = min(100.0 - margin, max(margin, point[0]))
            point[1] = min(100.0 - margin, max(margin, point[1]))
        if not moved:
            break
    return [(round(point[0], 2), round(point[1], 2)) for point in mutable]


def select_embedding_model(session: Session, *, tradition_id: str, preferred_model: Optional[str]) -> Optional[str]:
    rows = session.execute(
        text(
            """
            SELECT se.embedding_model, COUNT(*) AS row_count
            FROM segment_embeddings se
            JOIN segments s ON s.id = se.segment_id
            JOIN text_versions tv ON tv.id = s.text_version_id
            JOIN works w ON w.id = tv.work_id
            WHERE w.tradition_id = :tradition_id
            GROUP BY se.embedding_model
            ORDER BY row_count DESC, se.embedding_model
            """
        ),
        {"tradition_id": tradition_id},
    ).mappings().all()
    if not rows:
        return None
    if preferred_model and any(row["embedding_model"] == preferred_model for row in rows):
        return preferred_model
    return str(rows[0]["embedding_model"])


def count_indexed_segments(session: Session, *, tradition_id: str, embedding_model: str) -> int:
    return int(
        session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM segment_embeddings se
                JOIN segments s ON s.id = se.segment_id
                JOIN text_versions tv ON tv.id = s.text_version_id
                JOIN works w ON w.id = tv.work_id
                WHERE w.tradition_id = :tradition_id
                  AND se.embedding_model = :embedding_model
                """
            ),
            {"tradition_id": tradition_id, "embedding_model": embedding_model},
        ).scalar_one()
    )


def fetch_embedding_sample_rows(
    session: Session,
    *,
    tradition_id: str,
    embedding_model: str,
    sample_limit: int,
    indexed_segment_count: int,
) -> list[dict[str, Any]]:
    hash_modulus = 100_000
    if indexed_segment_count <= 0:
        bucket_limit = hash_modulus
    else:
        bucket_limit = min(
            hash_modulus,
            max(1, math.ceil((sample_limit / indexed_segment_count) * hash_modulus * 6)),
        )
    rows = session.execute(
        text(
            """
            SELECT
                se.segment_id,
                se.embedding::text AS embedding,
                s.segment_key,
                s.content,
                s.content_gloss,
                s.normalized_content,
                s.position,
                tv.id AS text_version_id,
                tv.title AS text_version_title,
                w.id AS work_id,
                w.title AS work_title,
                w.title_english,
                w.canonical_code,
                w.pitaka_division,
                l.name AS language_name
            FROM segment_embeddings se
            JOIN segments s ON s.id = se.segment_id
            JOIN text_versions tv ON tv.id = s.text_version_id
            JOIN works w ON w.id = tv.work_id
            JOIN languages l ON l.id = tv.language_id
            WHERE w.tradition_id = :tradition_id
              AND se.embedding_model = :embedding_model
              AND mod(hashtext(se.segment_id)::bigint + 2147483648, :hash_modulus) < :bucket_limit
            ORDER BY md5(se.segment_id)
            LIMIT :sample_limit
            """
        ),
        {
            "tradition_id": tradition_id,
            "embedding_model": embedding_model,
            "sample_limit": sample_limit,
            "hash_modulus": hash_modulus,
            "bucket_limit": bucket_limit,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def build_embedding_theme_map_from_rows(
    rows: list[dict[str, Any]],
    *,
    config: ThemeMapTraditionConfig,
    embedding_model: str,
    indexed_segment_count: int,
    max_examples_per_theme: int = DEFAULT_MAX_EXAMPLES_PER_THEME,
    max_top_works: int = DEFAULT_MAX_TOP_WORKS,
    max_edges: int = DEFAULT_MAX_EDGES,
) -> dict[str, Any]:
    if not rows:
        return {
            "tradition_id": config.tradition_id,
            "tradition_label": config.label,
            "tradition_short_label": config.short_label,
            "description": config.description,
            "embedding_model": embedding_model,
            "content_field": config.content_field,
            "indexed_segment_count": indexed_segment_count,
            "sampled_segment_count": 0,
            "cluster_count": 0,
            "nodes": [],
            "edges": [],
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
            n_init=5,
            max_iter=80,
        )
        labels = kmeans.fit_predict(vectors)
        centers = kmeans.cluster_centers_
    centers = normalize(centers, norm="l2")

    if cluster_count >= 2:
        projected = PCA(n_components=2, random_state=42).fit_transform(centers)
        positions = _scale_positions([(float(point[0]), float(point[1])) for point in projected])
    else:
        positions = [(50.0, 50.0)]

    max_cluster_size = max(int((labels == cluster_id).sum()) for cluster_id in range(cluster_count))
    cluster_member_counts = [int((labels == cluster_id).sum()) for cluster_id in range(cluster_count)]
    cluster_node_sizes = [
        int(round(74 + 72 * math.sqrt(member_count / max_cluster_size)))
        for member_count in cluster_member_counts
    ]
    relaxed_positions = _relax_overlapping_positions(
        positions,
        [size_px / 14.0 for size_px in cluster_node_sizes],
    )
    nodes: list[dict[str, Any]] = []
    cluster_slug_by_id: dict[int, str] = {}
    for cluster_id in range(cluster_count):
        member_indices = np.where(labels == cluster_id)[0]
        if len(member_indices) == 0:
            continue
        cluster_rows = [rows[int(index)] for index in member_indices]
        similarities = vectors[member_indices] @ centers[cluster_id]
        nearest_order = np.argsort(-similarities)
        center_rows = [
            rows[int(member_indices[int(order_index)])]
            for order_index in nearest_order[: max(12, max_examples_per_theme)]
        ]
        keyword_counter = _keyword_counts(center_rows, tradition_id=config.tradition_id)
        keyword_counter.update(_keyword_counts(cluster_rows[:80], tradition_id=config.tradition_id))
        keywords = [keyword for keyword, _ in keyword_counter.most_common(5)]
        label = _theme_label_from_rows(
            center_rows,
            cluster_rows,
            tradition_id=config.tradition_id,
            fallback_keywords=keywords,
            cluster_number=cluster_id + 1,
        )
        slug = f"{config.tradition_id}-cluster-{cluster_id + 1:02d}"
        cluster_slug_by_id[cluster_id] = slug
        work_counts: Counter[tuple[str, str]] = Counter(
            (str(row["work_id"]), str(row["work_title"])) for row in cluster_rows
        )
        top_works = [
            {"work_id": work_id, "work_title": work_title, "segment_count": count}
            for (work_id, work_title), count in work_counts.most_common(max_top_works)
        ]
        examples: list[dict[str, Any]] = []
        for order_index in nearest_order[:max_examples_per_theme]:
            member_index = int(member_indices[int(order_index)])
            row = rows[member_index]
            examples.append(
                {
                    "segment_id": row["segment_id"],
                    "segment_key": row["segment_key"],
                    "text_version_id": row["text_version_id"],
                    "work_id": row["work_id"],
                    "work_title": row["work_title"],
                    "canonical_code": row.get("canonical_code") or "",
                    "similarity": round(float(similarities[int(order_index)]), 4),
                    "preview": _preview_text(row),
                }
            )

        member_count = int(len(member_indices))
        estimated_total = int(round((member_count / len(rows)) * indexed_segment_count))
        x, y = relaxed_positions[cluster_id]
        nodes.append(
            {
                "slug": slug,
                "label": label,
                "cluster_index": cluster_id + 1,
                "description": "由 segment embedding 自动聚类生成；主题名优先根据质心附近代表段匹配佛学主题词表。",
                "keywords": keywords,
                "subtitle_candidates": _subtitle_candidates(
                    primary_label=label,
                    center_rows=center_rows,
                    cluster_rows=cluster_rows,
                    keywords=keywords,
                    top_work_titles=[item["work_title"] for item in top_works],
                    tradition_id=config.tradition_id,
                    cluster_number=cluster_id + 1,
                ),
                "segment_count": member_count,
                "estimated_total_segments": estimated_total,
                "sample_share_percent": round(member_count / len(rows) * 100, 2),
                "size_px": cluster_node_sizes[cluster_id],
                "x": x,
                "y": y,
                "family_color": THEME_COLORS[cluster_id % len(THEME_COLORS)],
                "top_works": top_works,
                "examples": examples,
            }
        )

    edge_candidates: list[dict[str, Any]] = []
    for left_id, right_id in combinations(range(cluster_count), 2):
        left_slug = cluster_slug_by_id.get(left_id)
        right_slug = cluster_slug_by_id.get(right_id)
        if not left_slug or not right_slug:
            continue
        similarity = float(centers[left_id] @ centers[right_id])
        if similarity < 0.35:
            continue
        left_pos = relaxed_positions[left_id]
        right_pos = relaxed_positions[right_id]
        edge_candidates.append(
            {
                "source": left_slug,
                "target": right_slug,
                "similarity": round(similarity, 4),
                "count": int(round(similarity * 100)),
                "x1": left_pos[0],
                "y1": left_pos[1],
                "x2": right_pos[0],
                "y2": right_pos[1],
            }
        )
    edge_candidates.sort(key=lambda item: item["similarity"], reverse=True)
    selected_edges = edge_candidates[:max_edges]
    max_similarity = max((edge["similarity"] for edge in selected_edges), default=1.0)
    min_similarity = min((edge["similarity"] for edge in selected_edges), default=max_similarity)
    for edge in selected_edges:
        if math.isclose(max_similarity, min_similarity):
            edge["stroke_width"] = 2.8
        else:
            edge["stroke_width"] = round(
                1.2 + 4.0 * ((edge["similarity"] - min_similarity) / (max_similarity - min_similarity)),
                2,
            )

    _assign_unique_subtitles(nodes)

    nodes.sort(key=lambda item: item["segment_count"], reverse=True)
    return {
        "tradition_id": config.tradition_id,
        "tradition_label": config.label,
        "tradition_short_label": config.short_label,
        "description": config.description,
        "embedding_model": embedding_model,
        "content_field": config.content_field,
        "indexed_segment_count": indexed_segment_count,
        "sampled_segment_count": len(rows),
        "cluster_count": len(nodes),
        "nodes": nodes,
        "edges": selected_edges,
    }


def build_embedding_theme_map(
    session: Session,
    *,
    config: ThemeMapTraditionConfig,
    sample_limit: Optional[int] = None,
    cluster_count: Optional[int] = None,
    max_examples_per_theme: int = DEFAULT_MAX_EXAMPLES_PER_THEME,
    max_top_works: int = DEFAULT_MAX_TOP_WORKS,
    max_edges: int = DEFAULT_MAX_EDGES,
) -> dict[str, Any]:
    embedding_model = select_embedding_model(
        session,
        tradition_id=config.tradition_id,
        preferred_model=config.preferred_embedding_model,
    )
    if not embedding_model:
        return build_embedding_theme_map_from_rows(
            [],
            config=config,
            embedding_model=config.preferred_embedding_model or "",
            indexed_segment_count=0,
        )

    indexed_segment_count = count_indexed_segments(
        session,
        tradition_id=config.tradition_id,
        embedding_model=embedding_model,
    )
    effective_config = ThemeMapTraditionConfig(
        tradition_id=config.tradition_id,
        label=config.label,
        short_label=config.short_label,
        description=config.description,
        preferred_embedding_model=config.preferred_embedding_model,
        content_field=config.content_field,
        sample_limit=sample_limit or config.sample_limit,
        cluster_count=cluster_count or config.cluster_count,
    )
    rows = fetch_embedding_sample_rows(
        session,
        tradition_id=config.tradition_id,
        embedding_model=embedding_model,
        sample_limit=effective_config.sample_limit,
        indexed_segment_count=indexed_segment_count,
    )
    return build_embedding_theme_map_from_rows(
        rows,
        config=effective_config,
        embedding_model=embedding_model,
        indexed_segment_count=indexed_segment_count,
        max_examples_per_theme=max_examples_per_theme,
        max_top_works=max_top_works,
        max_edges=max_edges,
    )


def build_embedding_theme_maps_snapshot(
    session: Session,
    *,
    tradition_ids: Optional[list[str]] = None,
    sample_limit: Optional[int] = None,
    cluster_count: Optional[int] = None,
    max_examples_per_theme: int = DEFAULT_MAX_EXAMPLES_PER_THEME,
    max_top_works: int = DEFAULT_MAX_TOP_WORKS,
    max_edges: int = DEFAULT_MAX_EDGES,
) -> dict[str, Any]:
    selected_ids = tradition_ids or list(TRADITION_CONFIGS)
    maps = [
        build_embedding_theme_map(
            session,
            config=TRADITION_CONFIGS[tradition_id],
            sample_limit=sample_limit,
            cluster_count=cluster_count,
            max_examples_per_theme=max_examples_per_theme,
            max_top_works=max_top_works,
            max_edges=max_edges,
        )
        for tradition_id in selected_ids
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "method": "large deterministic embedding sample + k=12 MiniBatchKMeans + centroid-neighbor theme labeling",
        "map_count": len(maps),
        "maps": maps,
    }


def save_embedding_theme_maps_snapshot(
    snapshot: dict[str, Any],
    *,
    path: Path = EMBEDDING_THEME_MAP_SNAPSHOT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_embedding_theme_maps_snapshot(
    *,
    path: Path = EMBEDDING_THEME_MAP_SNAPSHOT_PATH,
) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
