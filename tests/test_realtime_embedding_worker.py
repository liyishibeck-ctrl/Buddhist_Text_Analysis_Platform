from __future__ import annotations

import base64
from array import array

from backend.app.models import EmbeddingIndexMetadata
from backend.app.services.realtime_embedding_worker import (
    RealtimeEmbeddingCandidate,
    decode_base64_embedding,
    pack_realtime_batches,
    validate_realtime_runtime,
    _needs_realtime_embedding,
)
from backend.app.services.vector_service import EmbeddingRuntime


def test_decode_base64_embedding_round_trips_float32_values() -> None:
    values = array("f", [0.25, -0.5, 1.75, 2.0])
    encoded = base64.b64encode(values.tobytes()).decode("ascii")

    decoded = decode_base64_embedding(encoded, dimension=4)

    assert decoded == [0.25, -0.5, 1.75, 2.0]


def test_pack_realtime_batches_respects_segment_and_token_limits() -> None:
    candidates = [
        RealtimeEmbeddingCandidate(record={"id": "seg-1"}, token_count=30),
        RealtimeEmbeddingCandidate(record={"id": "seg-2"}, token_count=40),
        RealtimeEmbeddingCandidate(record={"id": "seg-3"}, token_count=35),
        RealtimeEmbeddingCandidate(record={"id": "seg-4"}, token_count=500),
    ]

    batches, oversize = pack_realtime_batches(
        candidates,
        max_segments_per_request=2,
        max_tokens_per_request=70,
        max_single_segment_tokens=100,
    )

    assert [batch.token_count for batch in batches] == [70, 35]
    assert [[record["id"] for record in batch.records] for batch in batches] == [["seg-1", "seg-2"], ["seg-3"]]
    assert [candidate.record["id"] for candidate in oversize] == ["seg-4"]


def test_needs_realtime_embedding_detects_matching_and_mismatched_metadata() -> None:
    runtime = EmbeddingRuntime(
        provider="openai-compatible",
        model="text-embedding-3-large",
        dimension=2048,
        api_url="https://api.openai.com/v1/embeddings",
        api_key="demo-key",
    )
    record = {"id": "seg-1", "tradition_id": "trad-pali"}
    matching = EmbeddingIndexMetadata(
        id="embmeta-1",
        owner_type="segment",
        owner_id="seg-1",
        chunk_scope="segment",
        embedding_model="text-embedding-3-large",
        vector_backend="pgvector",
        dimension=2048,
        status="indexed",
        metadata_json={"content_field": "normalized_content", "tradition_id": "trad-pali"},
    )

    assert _needs_realtime_embedding(
        record,
        matching,
        runtime=runtime,
        content_field="normalized_content",
    ) is False

    mismatched_dimension = EmbeddingIndexMetadata(
        id="embmeta-2",
        owner_type="segment",
        owner_id="seg-1",
        chunk_scope="segment",
        embedding_model="text-embedding-3-large",
        vector_backend="pgvector",
        dimension=1536,
        status="indexed",
        metadata_json={"content_field": "normalized_content", "tradition_id": "trad-pali"},
    )

    assert _needs_realtime_embedding(
        record,
        mismatched_dimension,
        runtime=runtime,
        content_field="normalized_content",
    ) is True


def test_validate_realtime_runtime_rejects_wrong_model() -> None:
    runtime = EmbeddingRuntime(
        provider="openai-compatible",
        model="text-embedding-3-small",
        dimension=2048,
        api_url="https://api.openai.com/v1/embeddings",
        api_key="demo-key",
    )

    try:
        validate_realtime_runtime(runtime)
    except ValueError as exc:
        assert "text-embedding-3-large" in str(exc)
    else:
        raise AssertionError("Expected validate_realtime_runtime to reject a non-large model.")
