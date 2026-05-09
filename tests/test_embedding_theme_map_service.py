from __future__ import annotations

from backend.app.services.embedding_theme_map_service import (
    ThemeMapTraditionConfig,
    build_embedding_theme_map_from_rows,
)


def test_build_embedding_theme_map_from_rows_clusters_examples_and_edges() -> None:
    config = ThemeMapTraditionConfig(
        tradition_id="trad-pali",
        label="巴利主题地图",
        short_label="巴利",
        description="test",
        preferred_embedding_model="text-embedding-3-large",
        content_field="normalized_content",
        cluster_count=2,
    )
    rows = [
        {
            "segment_id": "seg-1",
            "segment_key": "dn-1",
            "embedding": "[1.0,0.0,0.0]",
            "content": "dukkha dhamma",
            "content_gloss": "suffering and dhamma",
            "normalized_content": "dukkha dhamma",
            "text_version_id": "tv-1",
            "work_id": "work-1",
            "work_title": "Dukkha Text",
            "canonical_code": "DN 1",
        },
        {
            "segment_id": "seg-2",
            "segment_key": "dn-2",
            "embedding": "[0.98,0.02,0.0]",
            "content": "dukkha",
            "content_gloss": "suffering and impermanence",
            "normalized_content": "dukkha",
            "text_version_id": "tv-1",
            "work_id": "work-1",
            "work_title": "Dukkha Text",
            "canonical_code": "DN 1",
        },
        {
            "segment_id": "seg-3",
            "segment_key": "sn-1",
            "embedding": "[0.0,1.0,0.0]",
            "content": "samadhi jhana",
            "content_gloss": "concentration and meditation",
            "normalized_content": "samadhi jhana",
            "text_version_id": "tv-2",
            "work_id": "work-2",
            "work_title": "Samadhi Text",
            "canonical_code": "SN 1",
        },
        {
            "segment_id": "seg-4",
            "segment_key": "sn-2",
            "embedding": "[0.0,0.99,0.01]",
            "content": "samadhi",
            "content_gloss": "jhana concentration",
            "normalized_content": "samadhi",
            "text_version_id": "tv-2",
            "work_id": "work-2",
            "work_title": "Samadhi Text",
            "canonical_code": "SN 1",
        },
    ]

    snapshot = build_embedding_theme_map_from_rows(
        rows,
        config=config,
        embedding_model="text-embedding-3-large",
        indexed_segment_count=40,
        max_examples_per_theme=2,
        max_edges=3,
    )

    assert snapshot["sampled_segment_count"] == 4
    assert snapshot["cluster_count"] == 2
    assert len(snapshot["nodes"]) == 2
    assert all(node["examples"] for node in snapshot["nodes"])
    assert all(node["subtitle"] for node in snapshot["nodes"])
    assert len({node["display_label"] for node in snapshot["nodes"]}) == len(snapshot["nodes"])
    assert sum(node["estimated_total_segments"] for node in snapshot["nodes"]) == 40
