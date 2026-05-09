from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TraditionStats(BaseModel):
    tradition_id: str
    tradition_name: str
    collection_count: int
    work_count: int
    text_version_count: int
    segment_count: int


class OverviewStats(BaseModel):
    app_name: str
    is_sample_corpus: bool
    traditions: list[TraditionStats]
    total_collections: int
    total_works: int
    total_text_versions: int
    total_segments: int
    total_parallel_links: int
    total_concepts: int


class CollectionSummary(BaseModel):
    id: str
    slug: str
    title: str
    tradition_id: str
    tradition_name: str
    is_sample: bool
    description: Optional[str] = None


class PersonRoleInfo(BaseModel):
    person_id: str
    display_name: str
    native_name: Optional[str] = None
    role: str
    note: Optional[str] = None


class TextVersionSummary(BaseModel):
    id: str
    slug: str
    title: str
    version_label: str
    language_id: str
    language_name: str
    source_id: Optional[str] = None
    source_title: Optional[str] = None
    is_sample: bool
    sample_note: Optional[str] = None
    is_catalog_only: bool = False
    catalog_note: Optional[str] = None


class WorkSummary(BaseModel):
    id: str
    slug: str
    title: str
    title_english: Optional[str] = None
    genre: str
    tradition_id: str
    tradition_name: str
    collection_id: str
    collection_title: str
    is_sample: bool
    text_version_count: int
    pitaka_division: Optional[str] = None
    canonical_code: Optional[str] = None
    fascicle_count: Optional[int] = None
    catalog_order: Optional[int] = None
    is_catalog_only: bool = False
    has_full_text: bool = False
    full_text_version_count: int = 0
    primary_text_version_id: Optional[str] = None
    primary_text_version_title: Optional[str] = None


class WorkDetail(WorkSummary):
    title_transliterated: Optional[str] = None
    summary: Optional[str] = None
    authenticity_note: Optional[str] = None
    catalog_note: Optional[str] = None
    person_roles: list[PersonRoleInfo]
    text_versions: list[TextVersionSummary]


class DivisionCount(BaseModel):
    division: str
    label: str
    work_count: int


class CatalogNode(BaseModel):
    id: str
    node_type: str
    node_key: str
    label: str
    title: Optional[str] = None
    pitaka_division: Optional[str] = None
    section_key: Optional[str] = None
    path: str
    depth: int
    position: int
    note: Optional[str] = None
    is_terminal: bool = False
    work_id: Optional[str] = None
    work_title: Optional[str] = None
    canonical_code: Optional[str] = None
    fascicle_count: Optional[int] = None
    has_full_text: bool = False
    full_text_version_id: Optional[str] = None
    child_nodes: list["CatalogNode"] = Field(default_factory=list)


class HanCatalogOverview(BaseModel):
    tradition_id: str
    tradition_name: str
    collection_id: str
    collection_title: str
    work_count: int
    catalog_node_count: int
    ingested_work_count: int
    ingested_segment_count: int
    division_counts: list[DivisionCount]
    tree: list[CatalogNode]


class StructuralUnitNode(BaseModel):
    id: str
    unit_type: str
    label: str
    title: Optional[str] = None
    path: str
    depth: int
    position: int
    child_units: list["StructuralUnitNode"] = Field(default_factory=list)
    segments: list[dict[str, Any]] = Field(default_factory=list)


class TextVersionDetail(TextVersionSummary):
    work_id: str
    work_title: str
    tradition_id: str
    tradition_name: str
    collection_id: str
    collection_title: str
    summary: Optional[str] = None
    script_note: Optional[str] = None
    language_script: Optional[str] = None
    date_note: Optional[str] = None
    source_url: Optional[str] = None
    roles: list[PersonRoleInfo]
    structure: list[StructuralUnitNode]


class SegmentSummary(BaseModel):
    id: str
    segment_key: str
    title: Optional[str] = None
    position: int
    work_title: str
    text_version_title: str
    tradition_name: str
    language_name: str
    content_preview: str
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    retrieval_score: Optional[float] = None
    retrieval_channels: list[str] = Field(default_factory=list)
    concept_labels: list[str] = Field(default_factory=list)


class ParallelLinkTarget(BaseModel):
    link_id: str
    relation_type: str
    confidence: float
    note: Optional[str] = None
    target_segment_id: str
    target_segment_key: str
    target_work_title: str
    target_text_version_title: str
    target_tradition_name: str
    target_language_name: str
    target_content_preview: str


class SegmentDetail(BaseModel):
    id: str
    segment_key: str
    position: int
    title: Optional[str] = None
    content: str
    content_gloss: Optional[str] = None
    note: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    work_id: str
    work_title: str
    text_version_id: str
    text_version_title: str
    tradition_id: str
    tradition_name: str
    collection_id: str
    collection_title: str
    structural_unit_path: Optional[str] = None
    concept_tags: list[dict[str, Any]]
    parallel_links: list[ParallelLinkTarget]
    citation_links: list[dict[str, Any]]


class SegmentSimilarityResponse(BaseModel):
    status: str
    message: str
    configured_backend: str
    embedding_model: str
    indexed_owners: int
    source_segment: SegmentSummary
    results: list[SegmentSummary] = Field(default_factory=list)
    pgvector_hint: str


class ConceptTagSummary(BaseModel):
    id: str
    slug: str
    label: str
    tradition_scope: str
    description: Optional[str] = None
    segment_count: int


class ConceptTagDetail(ConceptTagSummary):
    segments: list[SegmentSummary]
    analysis: Optional[dict[str, Any]] = None


class VectorSearchRequest(BaseModel):
    query_text: str
    top_k: int = 5
    tradition_id: Optional[str] = None
    collection_id: Optional[str] = None
    language_id: Optional[str] = None


class VectorSearchResponse(BaseModel):
    status: str
    message: str
    configured_backend: str
    embedding_model: str
    indexed_owners: int
    results: list[SegmentSummary] = Field(default_factory=list)
    pgvector_hint: str


class HybridSearchRequest(BaseModel):
    query_text: str
    top_k: int = 8
    tradition_id: Optional[str] = None
    collection_id: Optional[str] = None
    language_id: Optional[str] = None


class HybridSearchResponse(BaseModel):
    status: str
    message: str
    configured_backend: str
    embedding_model: str
    indexed_owners: int
    keyword_result_count: int
    vector_result_count: int
    results: list[SegmentSummary] = Field(default_factory=list)
    pgvector_hint: str


class RagQueryRequest(BaseModel):
    query_text: str
    top_k: int = 8
    retrieval_mode: str = "hybrid"
    tradition_id: Optional[str] = None
    collection_id: Optional[str] = None
    language_id: Optional[str] = None


class RagQueryResponse(BaseModel):
    query_text: str
    retrieval_mode: str
    detected_concepts: list[dict[str, Any]] = Field(default_factory=list)
    keyword_result_count: int
    vector_result_count: int
    vector_backend: str
    embedding_model: str
    contexts: list[SegmentSummary] = Field(default_factory=list)
    keyword_hits: list[SegmentSummary] = Field(default_factory=list)
    vector_hits: list[SegmentSummary] = Field(default_factory=list)
    system_prompt: str
    user_prompt: str
    answer_outline: str


class SutraExplainRequest(BaseModel):
    query_text: str
    top_k: int = 12
    retrieval_mode: str = "hybrid"
    explanation_style: str = "comparative"
    tradition_id: Optional[str] = None
    collection_id: Optional[str] = None
    language_id: Optional[str] = None
    generate_answer: bool = True


class SutraExplainResponse(BaseModel):
    status: str
    message: str
    query_text: str
    retrieval_mode: str
    explanation_style: str
    answer_plan: list[dict[str, Any]] = Field(default_factory=list)
    detected_concepts: list[dict[str, Any]] = Field(default_factory=list)
    expanded_terms: list[dict[str, Any]] = Field(default_factory=list)
    selected_traditions: list[str] = Field(default_factory=list)
    embedding_models_by_tradition: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    vector_statuses: list[dict[str, Any]] = Field(default_factory=list)
    keyword_result_count: int
    vector_result_count: int
    contexts: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    system_prompt: str
    user_prompt: str
    answer: str
    llm_model: str = ""


StructuralUnitNode.model_rebuild()
CatalogNode.model_rebuild()
