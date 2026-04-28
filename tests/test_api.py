from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


TEST_DB_PATH = Path(tempfile.gettempdir()) / f"buddha_mvp_test_{os.getpid()}.db"
if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except PermissionError:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["APP_ENV"] = "test"
os.environ["ENABLE_AUTO_SEED"] = "true"

from fastapi.testclient import TestClient

from backend.app.api import search as search_api
from backend.app.main import app
from backend.app.services import vector_service


def test_overview_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["is_sample_corpus"] is False
    assert payload["total_collections"] >= 5
    assert payload["total_works"] >= 38
    assert payload["total_text_versions"] >= 70
    assert payload["total_segments"] >= 175000
    assert payload["total_parallel_links"] >= 5
    assert payload["total_concepts"] >= 32
    assert any(item["tradition_name"] == "汉传" for item in payload["traditions"])


def test_filtered_work_listing() -> None:
    with TestClient(app) as client:
        response = client.get("/api/works", params={"tradition_id": "trad-pali"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert {item["id"] for item in payload} == {
        "work-dhammacakkappavattana",
        "work-metta-sutta",
        "work-anattalakkhana",
    }


def test_segment_detail_contains_parallel_links() -> None:
    with TestClient(app) as client:
        response = client.get("/api/segments/seg-xj-001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["segment_key"] == "XJ.1"
    assert payload["parallel_links"][0]["target_segment_id"] == "seg-th-001"


def test_search_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/search/segments", params={"q": "metta"})
    assert response.status_code == 200
    payload = response.json()
    assert any(item["segment_key"] == "ME.2" for item in payload)


def test_vector_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "local-hash")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "local-hash-v1")
    with TestClient(app) as client:
        response = client.post("/api/vector/search", json={"query_text": "emptiness", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["configured_backend"] in {"pgvector", "python-fallback"}
    assert payload["embedding_model"] == vector_service.resolve_embedding_runtime().model
    assert payload["results"]


def test_vector_search_reports_embedding_misconfiguration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 0)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "")

    with TestClient(app) as client:
        response = client.post("/api/vector/search", json={"query_text": "emptiness", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "misconfigured"
    assert "EMBEDDING_API_URL" in payload["message"]


def test_hybrid_search_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        search_api.retrieval_service,
        "hybrid_search",
        lambda *args, **kwargs: {
            "status": "ready",
            "message": "Hybrid retrieval merged keyword and vector candidates.",
            "configured_backend": "python-fallback",
            "embedding_model": "local-hash-v1",
            "indexed_owners": 0,
            "keyword_result_count": 2,
            "vector_result_count": 2,
            "results": [
                {
                    "id": "seg-demo-001",
                    "segment_key": "DEMO.1",
                    "title": None,
                    "position": 1,
                    "work_title": "Demo Work",
                    "text_version_title": "Demo Version",
                    "tradition_name": "汉传",
                    "language_name": "汉文",
                    "content_preview": "demo preview",
                    "match_score": 0.8,
                    "match_reason": "hybrid",
                    "retrieval_score": 1.2,
                    "retrieval_channels": ["keyword", "vector"],
                    "concept_labels": [],
                }
            ],
            "pgvector_hint": "Backfill more rows with the embedding script for broader recall.",
        },
    )

    with TestClient(app) as client:
        response = client.post("/api/hybrid/search", json={"query_text": "无我", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["keyword_result_count"] == 2
    assert payload["vector_result_count"] == 2
    assert payload["results"][0]["retrieval_channels"] == ["keyword", "vector"]


def test_rag_query_returns_context_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "local-hash")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "local-hash-v1")
    with TestClient(app) as client:
        response = client.post(
            "/api/rag/query",
            json={"query_text": "无我", "top_k": 3, "retrieval_mode": "hybrid"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_mode"] == "hybrid"
    assert payload["contexts"]
    assert payload["system_prompt"]
    assert payload["user_prompt"]


def test_han_catalog_overview() -> None:
    with TestClient(app) as client:
        response = client.get("/api/catalog/han")
    assert response.status_code == 200
    payload = response.json()
    assert payload["collection_id"] == "coll-han-canon-catalog"
    assert payload["work_count"] >= 30
    assert payload["catalog_node_count"] >= 43
    assert payload["ingested_work_count"] >= 27
    assert payload["ingested_segment_count"] >= 175000
    assert any(item["division"] == "sutra" and item["work_count"] >= 21 for item in payload["division_counts"])
    assert payload["tree"][0]["label"] == "汉传三藏"


def test_han_core_text_version_detail() -> None:
    with TestClient(app) as client:
        response = client.get("/api/text-versions/tv-xinjing-xuanzang-pilot")
    assert response.status_code == 200
    payload = response.json()
    assert payload["work_id"] == "work-xinjing-xuanzang"
    assert payload["is_catalog_only"] is False
    assert payload["is_sample"] is True
    assert len(payload["structure"]) == 1
    assert payload["structure"][0]["segments"][0]["segment_key"] == "T0251-1"


def test_search_endpoint_includes_han_core_pilot() -> None:
    with TestClient(app) as client:
        response = client.get("/api/search/segments", params={"q": "佛知见"})
    assert response.status_code == 200
    payload = response.json()
    assert any(item["segment_key"] == "T0262-2" for item in payload)


def test_official_han_core_text_is_exposed_when_imported() -> None:
    with TestClient(app) as client:
        work_response = client.get("/api/works/work-xinjing-xuanzang")
    assert work_response.status_code == 200
    work_payload = work_response.json()

    official_version = next(
        (
            item
            for item in work_payload["text_versions"]
            if not item["is_sample"] and not item["is_catalog_only"]
        ),
        None,
    )
    if official_version is None:
        pytest.skip("Official Han XML text has not been imported in this workspace yet")

    assert official_version["source_id"] is not None
    assert official_version["source_title"] is not None

    with TestClient(app) as client:
        detail_response = client.get(f"/api/text-versions/{official_version['id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["work_id"] == "work-xinjing-xuanzang"
    assert detail_payload["is_sample"] is False
    assert detail_payload["is_catalog_only"] is False
    assert detail_payload["structure"]

    first_segments = detail_payload["structure"][0]["segments"]
    if not first_segments and detail_payload["structure"][0]["child_units"]:
        first_segments = detail_payload["structure"][0]["child_units"][0]["segments"]
    assert first_segments
    first_segment = first_segments[0]
    search_needle = "".join(first_segment["preview"].split())[:4]
    if len(search_needle) < 2:
        pytest.skip("Official segment preview is too short to exercise keyword search")

    with TestClient(app) as client:
        search_response = client.get("/api/search/segments", params={"q": search_needle})
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert any(item["text_version_title"] == detail_payload["title"] for item in search_payload)


def test_multi_juan_official_text_exposes_juan_structure() -> None:
    with TestClient(app) as client:
        detail_response = client.get("/api/text-versions/tv-miaofa-lianhua-jing-cbeta")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["is_sample"] is False
    assert detail_payload["is_catalog_only"] is False
    assert detail_payload["structure"]

    root_unit = detail_payload["structure"][0]
    assert len(root_unit["child_units"]) == 7
    assert root_unit["child_units"][0]["label"] == "卷1"
    assert root_unit["child_units"][-1]["label"] == "卷7"
    assert root_unit["child_units"][0]["child_units"][0]["segments"][0]["segment_key"] == "T0262-CBETA-001"

    with TestClient(app) as client:
        search_response = client.get("/api/search/segments", params={"q": "唯一佛乘"})
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert any(item["text_version_title"] == "妙法蓮華經" for item in search_payload)


def test_official_text_exposes_pin_structure_within_juan() -> None:
    with TestClient(app) as client:
        detail_response = client.get("/api/text-versions/tv-miaofa-lianhua-jing-cbeta")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()

    root_unit = detail_payload["structure"][0]
    first_juan = root_unit["child_units"][0]
    assert first_juan["unit_type"] == "juan"
    assert first_juan["child_units"]

    first_pin = first_juan["child_units"][0]
    assert first_pin["unit_type"] == "pin"
    assert first_pin["title"] == "序品"
    assert first_pin["segments"][0]["segment_key"] == "T0262-CBETA-001"
    assert any(item["title"] == "方便品" for item in first_juan["child_units"])


def test_official_text_uses_pin_jhead_for_juan_continuations() -> None:
    with TestClient(app) as client:
        detail_response = client.get("/api/text-versions/tv-da-ban-niepan-jing-cbeta")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()

    root_unit = detail_payload["structure"][0]
    second_juan = root_unit["child_units"][1]
    assert second_juan["unit_type"] == "juan"
    assert second_juan["child_units"]
    assert second_juan["child_units"][0]["unit_type"] == "pin"
    assert "壽命品" in second_juan["child_units"][0]["title"]
    assert second_juan["child_units"][0]["segments"]


def test_new_official_han_batch_is_exposed_when_imported() -> None:
    expected = {
        "tv-da-banruo-boluomiduo-jing-cbeta": ("work-da-banruo-boluomiduo-jing", 600),
        "tv-fangguang-banruo-jing-cbeta": ("work-fangguang-banruo-jing", 20),
        "tv-guangzan-jing-cbeta": ("work-guangzan-jing", 10),
        "tv-mohe-banruo-boluomi-jing-cbeta": ("work-mohe-banruo-boluomi-jing", 27),
        "tv-damingdu-jing-cbeta": ("work-damingdu-jing", 6),
        "tv-mohe-banruochao-jing-cbeta": ("work-mohe-banruochao-jing", 5),
        "tv-xiaopin-banruo-boluomi-jing-cbeta": ("work-xiaopin-banruo-boluomi-jing", 10),
        "tv-zhong-ahan-jing-cbeta": ("work-zhong-ahan-jing", 60),
        "tv-za-ahan-jing-cbeta": ("work-za-ahan-jing", 50),
        "tv-zengyi-ahan-jing-cbeta": ("work-zengyi-ahan-jing", 51),
        "tv-dazhidu-lun-cbeta": ("work-dazhidu-lun", 100),
        "tv-huayan-jing-t278-cbeta": ("work-huayan-jing-t278", 60),
        "tv-huayan-jing-cbeta": ("work-huayan-jing", 80),
        "tv-da-baoji-jing-cbeta": ("work-da-baoji-jing", 120),
        "tv-da-ban-niepan-jing-cbeta": ("work-da-ban-niepan-jing", 40),
        "tv-da-fangdeng-daji-jing-cbeta": ("work-da-fangdeng-daji-jing", 60),
        "tv-zhengfa-nianchu-jing-cbeta": ("work-zhengfa-nianchu-jing", 70),
    }

    with TestClient(app) as client:
        for text_version_id, (work_id, juan_count) in expected.items():
            response = client.get(f"/api/text-versions/{text_version_id}")
            assert response.status_code == 200
            payload = response.json()
            assert payload["work_id"] == work_id
            assert payload["is_sample"] is False
            assert payload["is_catalog_only"] is False
            assert payload["structure"]
            assert len(payload["structure"][0]["child_units"]) == juan_count


def test_multifile_official_text_exposes_segment_source_bundle() -> None:
    with TestClient(app) as client:
        response = client.get("/api/segments/seg-cbeta-t0220-001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["text_version_id"] == "tv-da-banruo-boluomiduo-jing-cbeta"
    assert payload["metadata_json"]["canonical_code"] == "T0220"
    assert payload["metadata_json"]["xml_path"].endswith("T05n0220a.xml")
    assert len(payload["metadata_json"]["display_urls"]) == 15
