from __future__ import annotations

from backend.app.services.pali_theme_map_service import build_pali_theme_map_from_rows


def test_build_pali_theme_map_from_rows_counts_themes_and_edges() -> None:
    rows = [
        {
            "segment_id": "seg-1",
            "segment_key": "dn-1",
            "content_gloss": "The discourse frames suffering, its arising, cessation, and the path.",
            "text_version_id": "tv-1",
            "work_id": "work-1",
            "work_title": "Dhammacakkappavattana",
            "canonical_code": "SN 56.11",
        },
        {
            "segment_id": "seg-2",
            "segment_key": "dn-2",
            "content_gloss": "Seeing suffering and its cessation, the path is understood through the four noble truths.",
            "text_version_id": "tv-1",
            "work_id": "work-1",
            "work_title": "Dhammacakkappavattana",
            "canonical_code": "SN 56.11",
        },
        {
            "segment_id": "seg-3",
            "segment_key": "sn-2",
            "content_gloss": "Form is not self and should not be grasped as mine or me.",
            "text_version_id": "tv-2",
            "work_id": "work-2",
            "work_title": "Anattalakkhaṇa",
            "canonical_code": "SN 22.59",
        },
        {
            "segment_id": "seg-4",
            "segment_key": "khp-3",
            "content_gloss": "Like a mother guarding her only child, one should cultivate boundless loving-kindness.",
            "text_version_id": "tv-3",
            "work_id": "work-3",
            "work_title": "Karaṇīyametta",
            "canonical_code": "Sn 1.8",
        },
    ]

    snapshot = build_pali_theme_map_from_rows(rows, max_examples_per_theme=2, max_top_works=3, max_edges=10)

    assert snapshot["gloss_segment_count"] == 4
    assert snapshot["matched_segment_count"] == 4
    assert snapshot["theme_count"] >= 4

    nodes_by_slug = {node["slug"]: node for node in snapshot["nodes"]}
    assert nodes_by_slug["four-noble-truths"]["segment_count"] == 2
    assert nodes_by_slug["suffering"]["segment_count"] == 2
    assert nodes_by_slug["non-self"]["segment_count"] == 1
    assert nodes_by_slug["loving-kindness"]["segment_count"] == 1

    edges = {(edge["source"], edge["target"]): edge["count"] for edge in snapshot["edges"]}
    assert ("four-noble-truths", "suffering") in edges or ("suffering", "four-noble-truths") in edges
