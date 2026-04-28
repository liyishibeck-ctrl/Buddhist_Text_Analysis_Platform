from __future__ import annotations

import io
import json
import urllib.error

import pytest

from backend.app.services import vector_service


def test_resolve_embedding_runtime_defaults_to_local_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "local-hash")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "local-hash-v1")

    runtime = vector_service.resolve_embedding_runtime()

    assert runtime.provider == vector_service.LOCAL_EMBEDDING_PROVIDER
    assert runtime.model == "local-hash-v1"
    assert runtime.dimension == vector_service.LOCAL_EMBEDDING_DIMENSION


def test_embed_text_values_returns_local_vectors_for_each_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "local-hash")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "local-hash-v1")

    runtime, embeddings = vector_service.embed_text_values(["空", "无我"])

    assert runtime.provider == vector_service.LOCAL_EMBEDDING_PROVIDER
    assert len(embeddings) == 2
    assert all(len(item) == runtime.dimension for item in embeddings)


def test_resolve_embedding_runtime_requires_external_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "demo-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 768)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "")

    with pytest.raises(ValueError, match="EMBEDDING_API_URL"):
        vector_service.resolve_embedding_runtime()


def test_resolve_embedding_runtime_uses_tradition_specific_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "global-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 2048)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://global.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "global-key")
    monkeypatch.setenv("EMBEDDING_API_URL_TRAD_PALI", "https://pali.invalid/v1/embeddings")
    monkeypatch.setenv("EMBEDDING_API_KEY_TRAD_PALI", "pali-key")
    monkeypatch.setenv("EMBEDDING_MODEL_TRAD_PALI", "pali-model")

    runtime = vector_service.resolve_embedding_runtime(tradition_id="trad-pali")

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert runtime.model == "pali-model"
    assert runtime.dimension == 2048
    assert runtime.api_url == "https://pali.invalid/v1/embeddings"
    assert runtime.api_key == "pali-key"


def test_openai_compatible_provider_sends_requested_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_payload: dict[str, object] = {}
    captured_batch_sizes: list[int] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self._payload).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        payload = json.loads(request.data.decode("utf-8"))
        captured_payload.update(payload)
        batch_inputs = payload["input"]
        captured_batch_sizes.append(len(batch_inputs))
        return FakeResponse(
            {
                "data": [
                    {"index": index, "embedding": [0.0, 1.0, 0.0, 1.0]}
                    for index, _ in enumerate(batch_inputs)
                ]
            }
        )

    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "demo-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 4)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://example.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "demo-key")
    monkeypatch.setattr(vector_service.settings, "embedding_batch_size", 1)
    monkeypatch.setattr(vector_service.urllib.request, "urlopen", fake_urlopen)

    runtime, embeddings = vector_service.embed_text_values(["无我", "空"])

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert captured_payload["dimensions"] == 4
    assert captured_batch_sizes == [1, 1]
    assert embeddings == [[0.0, 1.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]]


def test_embed_text_values_uses_tradition_specific_api_key_and_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"data": [{"index": 0, "embedding": [0.0, 1.0, 0.0, 1.0]}]}).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        captured_request["url"] = request.full_url
        captured_request["authorization"] = request.headers.get("Authorization")
        return FakeResponse()

    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "global-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 4)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://global.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "global-key")
    monkeypatch.setenv("EMBEDDING_API_URL_TRAD_TIBETAN", "https://tibetan.invalid/v1/embeddings")
    monkeypatch.setenv("EMBEDDING_API_KEY_TRAD_TIBETAN", "tibetan-key")
    monkeypatch.setenv("EMBEDDING_DIMENSION_TRAD_TIBETAN", "4")
    monkeypatch.setattr(vector_service.urllib.request, "urlopen", fake_urlopen)

    runtime, embeddings = vector_service.embed_text_values(["བཀྲ་ཤིས།"], tradition_id="trad-tibetan")

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert captured_request["url"] == "https://tibetan.invalid/v1/embeddings"
    assert captured_request["authorization"] == "Bearer tibetan-key"
    assert embeddings == [[0.0, 1.0, 0.0, 1.0]]


def test_openai_compatible_provider_retries_smaller_batches_on_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_batch_sizes: list[int] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self._payload).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        payload = json.loads(request.data.decode("utf-8"))
        batch_inputs = payload["input"]
        captured_batch_sizes.append(len(batch_inputs))
        if len(batch_inputs) > 1:
            raise urllib.error.HTTPError(
                request.full_url,
                500,
                "Internal Server Error",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"server"}'),
            )
        return FakeResponse({"data": [{"index": 0, "embedding": [0.0, 1.0, 0.0, 1.0]}]})

    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "demo-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 4)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://example.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "demo-key")
    monkeypatch.setattr(vector_service.settings, "embedding_batch_size", 2)
    monkeypatch.setattr(vector_service.urllib.request, "urlopen", fake_urlopen)

    runtime, embeddings = vector_service.embed_text_values(["无我", "空"])

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert captured_batch_sizes == [2, 1, 1]
    assert embeddings == [[0.0, 1.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]]


def test_openai_compatible_provider_retries_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"data": [{"index": 0, "embedding": [0.0, 1.0, 0.0, 1.0]}]}).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del request, timeout
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise urllib.error.HTTPError(
                "https://example.invalid/v1/embeddings",
                429,
                "Too Many Requests",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"rate_limit"}'),
            )
        return FakeResponse()

    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "demo-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 4)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://example.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "demo-key")
    monkeypatch.setattr(vector_service.settings, "embedding_batch_size", 1)
    monkeypatch.setattr(vector_service.time, "sleep", lambda _: None)
    monkeypatch.setattr(vector_service.urllib.request, "urlopen", fake_urlopen)

    runtime, embeddings = vector_service.embed_text_values(["无我"])

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert attempts["count"] == 2
    assert embeddings == [[0.0, 1.0, 0.0, 1.0]]


def test_openai_compatible_provider_retries_incomplete_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise vector_service.http.client.IncompleteRead(b"{}", 10)
            return json.dumps({"data": [{"index": 0, "embedding": [0.0, 1.0, 0.0, 1.0]}]}).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del request, timeout
        return FakeResponse()

    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "demo-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 4)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://example.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "demo-key")
    monkeypatch.setattr(vector_service.settings, "embedding_batch_size", 1)
    monkeypatch.setattr(vector_service.time, "sleep", lambda _: None)
    monkeypatch.setattr(vector_service.urllib.request, "urlopen", fake_urlopen)

    runtime, embeddings = vector_service.embed_text_values(["无我"])

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert attempts["count"] == 2
    assert embeddings == [[0.0, 1.0, 0.0, 1.0]]


def test_openai_compatible_provider_retries_read_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise TimeoutError("The read operation timed out")
            return json.dumps({"data": [{"index": 0, "embedding": [0.0, 1.0, 0.0, 1.0]}]}).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del request, timeout
        return FakeResponse()

    monkeypatch.setattr(vector_service.settings, "embedding_provider", "openai-compatible")
    monkeypatch.setattr(vector_service.settings, "embedding_model", "demo-model")
    monkeypatch.setattr(vector_service.settings, "embedding_dimension", 4)
    monkeypatch.setattr(vector_service.settings, "embedding_api_url", "https://example.invalid/v1/embeddings")
    monkeypatch.setattr(vector_service.settings, "embedding_api_key", "demo-key")
    monkeypatch.setattr(vector_service.settings, "embedding_batch_size", 1)
    monkeypatch.setattr(vector_service.time, "sleep", lambda _: None)
    monkeypatch.setattr(vector_service.urllib.request, "urlopen", fake_urlopen)

    runtime, embeddings = vector_service.embed_text_values(["无我"])

    assert runtime.provider == vector_service.OPENAI_COMPATIBLE_EMBEDDING_PROVIDER
    assert attempts["count"] == 2
    assert embeddings == [[0.0, 1.0, 0.0, 1.0]]
