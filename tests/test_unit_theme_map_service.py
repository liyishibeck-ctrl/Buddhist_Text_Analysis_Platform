from __future__ import annotations

from backend.app.services.unit_theme_map_service import UnitThemeMapConfig, build_unit_theme_map_from_rows


def test_build_unit_theme_map_from_rows_clusters_core_units() -> None:
    config = UnitThemeMapConfig(
        tradition_id="trad-han",
        label="汉传卷单位主题星图",
        short_label="汉传",
        preferred_embedding_model="test-model",
        description="test",
        cluster_count=2,
    )
    rows = [
        {
            "unit_id": "u-1",
            "unit_type": "juan",
            "unit_label": "大般若波罗蜜多经 · 卷1",
            "work_id": "work-prajna",
            "work_title": "大般若波罗蜜多经",
            "canonical_code": "T0220",
            "pitaka_division": "sutra",
            "segment_count": 100,
            "embedding": "[1.0,0.0,0.0]",
        },
        {
            "unit_id": "u-2",
            "unit_type": "juan",
            "unit_label": "大般若波罗蜜多经 · 卷2",
            "work_id": "work-prajna",
            "work_title": "大般若波罗蜜多经",
            "canonical_code": "T0220",
            "pitaka_division": "sutra",
            "segment_count": 90,
            "embedding": "[0.98,0.01,0.0]",
        },
        {
            "unit_id": "u-3",
            "unit_type": "work",
            "unit_label": "杂阿含经",
            "work_id": "work-agama",
            "work_title": "杂阿含经",
            "canonical_code": "T0099",
            "pitaka_division": "sutra",
            "segment_count": 80,
            "embedding": "[0.0,1.0,0.0]",
        },
        {
            "unit_id": "u-4",
            "unit_type": "work",
            "unit_label": "中阿含经",
            "work_id": "work-ma",
            "work_title": "中阿含经",
            "canonical_code": "T0026",
            "pitaka_division": "sutra",
            "segment_count": 75,
            "embedding": "[0.0,0.99,0.01]",
        },
    ]

    snapshot = build_unit_theme_map_from_rows(rows, config=config, embedding_model="test-model")

    assert snapshot["unit_count"] == 4
    assert snapshot["cluster_count"] == 2
    assert len(snapshot["points"]) == 4
    assert len(snapshot["clusters"]) == 2
    assert all(cluster["core_units"] for cluster in snapshot["clusters"])
