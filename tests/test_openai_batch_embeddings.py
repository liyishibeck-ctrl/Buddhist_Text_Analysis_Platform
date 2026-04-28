from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from backend.app.services import openai_batch_embeddings
from backend.app.services.vector_service import EmbeddingRuntime, resolve_storage_embedding_model


def test_derive_batch_api_base_url_uses_embeddings_endpoint() -> None:
    base_url = openai_batch_embeddings.derive_batch_api_base_url("https://api.openai.com/v1/embeddings")

    assert base_url == "https://api.openai.com/v1"


def test_derive_batch_api_base_url_rejects_non_embedding_urls() -> None:
    with pytest.raises(ValueError, match="EMBEDDING_API_URL"):
        openai_batch_embeddings.derive_batch_api_base_url("https://api.openai.com/v1/files")


def test_build_batch_request_lines_uses_requested_content_field() -> None:
    runtime = EmbeddingRuntime(
        provider="openai-compatible",
        model="text-embedding-3-large",
        dimension=2048,
        api_url="https://api.openai.com/v1/embeddings",
        api_key="demo-key",
    )

    lines = openai_batch_embeddings.build_batch_request_lines(
        [
            {
                "id": "seg-1",
                "content": "Namo tassa",
                "normalized_content": "Namo tassa",
                "content_gloss": "Homage to him",
            }
        ],
        runtime=runtime,
        content_field="content_gloss",
    )

    payload = json.loads(lines[0])
    assert payload["custom_id"] == "seg-1"
    assert payload["body"]["model"] == "text-embedding-3-large"
    assert payload["body"]["dimensions"] == 2048
    assert payload["body"]["input"] == "Homage to him"


def test_apply_batch_output_file_upserts_gloss_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_root = Path("data/processed/test-openai-batch") / uuid.uuid4().hex
    output_path = temp_root / "batch.output.jsonl"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "custom_id": "seg-1",
                    "response": {
                        "status_code": 200,
                        "body": {
                            "data": [{"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}],
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        captured: dict[str, object] = {}

        monkeypatch.setattr(
            openai_batch_embeddings,
            "resolve_embedding_runtime",
            lambda embedding_model=None, tradition_id=None: EmbeddingRuntime(
                provider="openai-compatible",
                model=embedding_model or "text-embedding-3-large",
                dimension=4,
                api_url="https://api.openai.com/v1/embeddings",
                api_key="demo-key",
            ),
        )
        monkeypatch.setattr(
            openai_batch_embeddings,
            "hydrate_segment_records",
            lambda session, segment_ids: [
                {
                    "id": segment_ids[0],
                    "content": "བཀྲ་ཤིས།",
                    "normalized_content": "བཀྲ་ཤིས།",
                    "content_gloss": "Auspiciousness",
                }
            ],
        )

        def fake_upsert(session, records, embeddings, *, runtime, content_field=None, ensure_vector_objects=True):  # type: ignore[no-untyped-def]
            del session, ensure_vector_objects
            captured["records"] = records
            captured["embeddings"] = embeddings
            captured["runtime_model"] = runtime.model
            captured["storage_model"] = resolve_storage_embedding_model(runtime.model, content_field=content_field)
            return len(records)

        monkeypatch.setattr(openai_batch_embeddings, "upsert_segment_embeddings", fake_upsert)

        result = openai_batch_embeddings.apply_batch_output_file(
            object(),  # type: ignore[arg-type]
            output_path,
            embedding_model="text-embedding-3-large",
            content_field="content_gloss",
            tradition_id="trad-tibetan",
            chunk_size=1,
        )

        assert result.inserted_count == 1
        assert result.success_count == 1
        assert result.error_count == 0
        assert captured["runtime_model"] == "text-embedding-3-large"
        assert captured["storage_model"] == "text-embedding-3-large::content_gloss"
        assert captured["embeddings"] == [[0.1, 0.2, 0.3, 0.4]]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_inspect_jsonl_file_reports_bad_line_and_missing_custom_ids() -> None:
    temp_root = Path("data/processed/test-openai-batch") / uuid.uuid4().hex
    output_path = temp_root / "batch.output.jsonl"
    request_path = temp_root / "batch.request.jsonl"
    missing_path = temp_root / "batch.missing_custom_ids.txt"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"custom_id": "seg-1", "response": {"status_code": 200, "body": {"data": []}}}, ensure_ascii=False)
            + "\n"
            + '{"custom_id": "seg-2", "response": {"status_code": 200, "body": {"data": [}}\n',
            encoding="utf-8",
        )
        request_path.write_text(
            json.dumps({"custom_id": "seg-1"}, ensure_ascii=False) + "\n" + json.dumps({"custom_id": "seg-2"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result = openai_batch_embeddings.inspect_jsonl_file(
            output_path,
            request_file_path=request_path,
            missing_custom_ids_path=missing_path,
        )

        assert result.ok_lines == 1
        assert result.bad_line == 2
        assert result.bad_offset is not None
        assert result.last_custom_id == "seg-1"
        assert result.output_custom_ids_count == 1
        assert result.missing_custom_ids_count == 1
        assert missing_path.read_text(encoding="utf-8").strip() == "seg-2"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_apply_batch_output_file_salvages_valid_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_root = Path("data/processed/test-openai-batch") / uuid.uuid4().hex
    output_path = temp_root / "batch.output.jsonl"
    request_path = temp_root / "batch.request.jsonl"
    missing_path = temp_root / "batch.missing_custom_ids.txt"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "custom_id": "seg-1",
                    "response": {
                        "status_code": 200,
                        "body": {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}]},
                    },
                },
                ensure_ascii=False,
            )
            + "\n"
            + '{"custom_id": "seg-2", "response": {"status_code": 200, "body": {"data": [}}\n',
            encoding="utf-8",
        )
        request_path.write_text(
            json.dumps({"custom_id": "seg-1"}, ensure_ascii=False) + "\n" + json.dumps({"custom_id": "seg-2"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            openai_batch_embeddings,
            "resolve_embedding_runtime",
            lambda embedding_model=None, tradition_id=None: EmbeddingRuntime(
                provider="openai-compatible",
                model=embedding_model or "text-embedding-3-large",
                dimension=4,
                api_url="https://api.openai.com/v1/embeddings",
                api_key="demo-key",
            ),
        )
        monkeypatch.setattr(
            openai_batch_embeddings,
            "hydrate_segment_records",
            lambda session, segment_ids: [
                {
                    "id": segment_ids[0],
                    "content": "Namo tassa",
                    "normalized_content": "Namo tassa",
                    "content_gloss": "Homage to him",
                }
            ],
        )

        captured: dict[str, object] = {}

        def fake_upsert(session, records, embeddings, *, runtime, content_field=None, ensure_vector_objects=True):  # type: ignore[no-untyped-def]
            del session, ensure_vector_objects
            captured["records"] = records
            captured["embeddings"] = embeddings
            captured["storage_model"] = resolve_storage_embedding_model(runtime.model, content_field=content_field)
            return len(records)

        monkeypatch.setattr(openai_batch_embeddings, "upsert_segment_embeddings", fake_upsert)

        result = openai_batch_embeddings.apply_batch_output_file(
            object(),  # type: ignore[arg-type]
            output_path,
            embedding_model="text-embedding-3-large",
            request_file_path=request_path,
            missing_custom_ids_path=missing_path,
            chunk_size=1,
        )

        assert result.inserted_count == 1
        assert result.success_count == 1
        assert result.error_count == 0
        assert result.ok_lines == 1
        assert result.bad_line == 2
        assert result.last_custom_id == "seg-1"
        assert result.missing_custom_ids_count == 1
        assert missing_path.read_text(encoding="utf-8").strip() == "seg-2"
        assert captured["storage_model"] == "text-embedding-3-large"
        assert captured["embeddings"] == [[0.1, 0.2, 0.3, 0.4]]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
