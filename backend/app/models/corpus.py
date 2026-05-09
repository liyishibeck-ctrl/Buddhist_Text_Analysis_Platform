from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Tradition(Base):
    __tablename__ = "traditions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    canonical_scope: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    collections: Mapped[list["Collection"]] = relationship(back_populates="tradition")
    works: Mapped[list["Work"]] = relationship(back_populates="tradition")
    catalog_nodes: Mapped[list["CatalogNode"]] = relationship(back_populates="tradition")


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    script: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), default="ltr")
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    text_versions: Mapped[list["TextVersion"]] = relationship(back_populates="language")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(64))
    citation: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    access_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean(), default=True)

    text_versions: Mapped[list["TextVersion"]] = relationship(back_populates="source")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    tradition_id: Mapped[str] = mapped_column(ForeignKey("traditions.id"), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    coverage_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean(), default=True)

    tradition: Mapped["Tradition"] = relationship(back_populates="collections")
    works: Mapped[list["Work"]] = relationship(back_populates="collection")
    catalog_nodes: Mapped[list["CatalogNode"]] = relationship(back_populates="collection")


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    native_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tradition_affiliation: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    role_summary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    work_roles: Mapped[list["WorkPersonRole"]] = relationship(back_populates="person")
    text_version_roles: Mapped[list["TextVersionPersonRole"]] = relationship(back_populates="person")


class Work(Base):
    __tablename__ = "works"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    tradition_id: Mapped[str] = mapped_column(ForeignKey("traditions.id"), index=True)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    title_english: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title_transliterated: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    genre: Mapped[str] = mapped_column(String(64))
    summary: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    authenticity_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    pitaka_division: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    canonical_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    fascicle_count: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    catalog_order: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    catalog_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    is_catalog_only: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_sample: Mapped[bool] = mapped_column(Boolean(), default=True)

    tradition: Mapped["Tradition"] = relationship(back_populates="works")
    collection: Mapped["Collection"] = relationship(back_populates="works")
    text_versions: Mapped[list["TextVersion"]] = relationship(back_populates="work")
    person_roles: Mapped[list["WorkPersonRole"]] = relationship(back_populates="work")
    catalog_nodes: Mapped[list["CatalogNode"]] = relationship(back_populates="work")


class WorkPersonRole(Base):
    __tablename__ = "work_person_roles"
    __table_args__ = (UniqueConstraint("work_id", "person_id", "role"),)

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.id"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    role: Mapped[str] = mapped_column(String(64))
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    work: Mapped["Work"] = relationship(back_populates="person_roles")
    person: Mapped["Person"] = relationship(back_populates="work_roles")


class TextVersion(Base):
    __tablename__ = "text_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    work_id: Mapped[str] = mapped_column(ForeignKey("works.id"), index=True)
    language_id: Mapped[str] = mapped_column(ForeignKey("languages.id"), index=True)
    source_id: Mapped[Optional[str]] = mapped_column(ForeignKey("sources.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    version_label: Mapped[str] = mapped_column(String(255))
    script_note: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    date_note: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    sample_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    catalog_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    is_catalog_only: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_sample: Mapped[bool] = mapped_column(Boolean(), default=True)

    work: Mapped["Work"] = relationship(back_populates="text_versions")
    language: Mapped["Language"] = relationship(back_populates="text_versions")
    source: Mapped[Optional["Source"]] = relationship(back_populates="text_versions")
    person_roles: Mapped[list["TextVersionPersonRole"]] = relationship(back_populates="text_version")
    structural_units: Mapped[list["StructuralUnit"]] = relationship(back_populates="text_version")
    segments: Mapped[list["Segment"]] = relationship(back_populates="text_version")


class TextVersionPersonRole(Base):
    __tablename__ = "text_version_person_roles"
    __table_args__ = (UniqueConstraint("text_version_id", "person_id", "role"),)

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    text_version_id: Mapped[str] = mapped_column(ForeignKey("text_versions.id"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    role: Mapped[str] = mapped_column(String(64))
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    text_version: Mapped["TextVersion"] = relationship(back_populates="person_roles")
    person: Mapped["Person"] = relationship(back_populates="text_version_roles")


class CatalogNode(Base):
    __tablename__ = "catalog_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id"), index=True)
    tradition_id: Mapped[str] = mapped_column(ForeignKey("traditions.id"), index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("catalog_nodes.id"), nullable=True, index=True)
    work_id: Mapped[Optional[str]] = mapped_column(ForeignKey("works.id"), nullable=True, index=True)
    node_type: Mapped[str] = mapped_column(String(64))
    node_key: Mapped[str] = mapped_column(String(128), index=True)
    label: Mapped[str] = mapped_column(String(128))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pitaka_division: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    section_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    depth: Mapped[int] = mapped_column(Integer(), default=0)
    position: Mapped[int] = mapped_column(Integer(), default=0)
    path: Mapped[str] = mapped_column(String(255), index=True)
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    is_terminal: Mapped[bool] = mapped_column(Boolean(), default=False)

    tradition: Mapped["Tradition"] = relationship(back_populates="catalog_nodes")
    collection: Mapped["Collection"] = relationship(back_populates="catalog_nodes")
    work: Mapped[Optional["Work"]] = relationship(back_populates="catalog_nodes")
    parent: Mapped[Optional["CatalogNode"]] = relationship(back_populates="children", remote_side="CatalogNode.id")
    children: Mapped[list["CatalogNode"]] = relationship(back_populates="parent")


class StructuralUnit(Base):
    __tablename__ = "structural_units"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text_version_id: Mapped[str] = mapped_column(ForeignKey("text_versions.id"), index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("structural_units.id"), nullable=True, index=True)
    unit_type: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(128))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer(), default=0)
    depth: Mapped[int] = mapped_column(Integer(), default=0)
    path: Mapped[str] = mapped_column(String(255), index=True)

    text_version: Mapped["TextVersion"] = relationship(back_populates="structural_units")
    parent: Mapped[Optional["StructuralUnit"]] = relationship(back_populates="children", remote_side="StructuralUnit.id")
    children: Mapped[list["StructuralUnit"]] = relationship(back_populates="parent")
    segments: Mapped[list["Segment"]] = relationship(back_populates="structural_unit")


class TextUnitSummary(Base):
    __tablename__ = "text_unit_summaries"
    __table_args__ = (UniqueConstraint("owner_type", "owner_id", "summary_kind", "model"),)

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    owner_type: Mapped[str] = mapped_column(String(32), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    summary_kind: Mapped[str] = mapped_column(String(64), default="rag_context", index=True)
    model: Mapped[str] = mapped_column(String(128), index=True)
    summary: Mapped[str] = mapped_column(Text())
    source_segment_count: Mapped[int] = mapped_column(Integer(), default=0)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text_version_id: Mapped[str] = mapped_column(ForeignKey("text_versions.id"), index=True)
    structural_unit_id: Mapped[Optional[str]] = mapped_column(ForeignKey("structural_units.id"), nullable=True, index=True)
    segment_key: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text())
    content_gloss: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    normalized_content: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    position: Mapped[int] = mapped_column(Integer(), default=0)
    char_count: Mapped[int] = mapped_column(Integer(), default=0)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON(), nullable=True)

    text_version: Mapped["TextVersion"] = relationship(back_populates="segments")
    structural_unit: Mapped[Optional["StructuralUnit"]] = relationship(back_populates="segments")
    concept_links: Mapped[list["SegmentConceptTag"]] = relationship(back_populates="segment")
    outgoing_parallel_links: Mapped[list["ParallelLink"]] = relationship(
        back_populates="source_segment",
        foreign_keys="ParallelLink.source_segment_id",
    )
    incoming_parallel_links: Mapped[list["ParallelLink"]] = relationship(
        back_populates="target_segment",
        foreign_keys="ParallelLink.target_segment_id",
    )
    outgoing_citation_links: Mapped[list["CitationLink"]] = relationship(
        back_populates="source_segment",
        foreign_keys="CitationLink.source_segment_id",
    )
    incoming_citation_links: Mapped[list["CitationLink"]] = relationship(
        back_populates="target_segment",
        foreign_keys="CitationLink.target_segment_id",
    )


class ConceptTag(Base):
    __tablename__ = "concept_tags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255))
    tradition_scope: Mapped[str] = mapped_column(String(128), default="cross-tradition")
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    segment_links: Mapped[list["SegmentConceptTag"]] = relationship(back_populates="concept_tag")


class SegmentConceptTag(Base):
    __tablename__ = "segment_concept_tags"
    __table_args__ = (UniqueConstraint("segment_id", "concept_tag_id"),)

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"), index=True)
    concept_tag_id: Mapped[str] = mapped_column(ForeignKey("concept_tags.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float(), default=1.0)
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    segment: Mapped["Segment"] = relationship(back_populates="concept_links")
    concept_tag: Mapped["ConceptTag"] = relationship(back_populates="segment_links")


class ParallelLink(Base):
    __tablename__ = "parallel_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"), index=True)
    target_segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float(), default=0.5)
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    source_segment: Mapped["Segment"] = relationship(
        back_populates="outgoing_parallel_links",
        foreign_keys=[source_segment_id],
    )
    target_segment: Mapped["Segment"] = relationship(
        back_populates="incoming_parallel_links",
        foreign_keys=[target_segment_id],
    )


class CitationLink(Base):
    __tablename__ = "citation_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"), index=True)
    target_segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(64))
    note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    source_segment: Mapped["Segment"] = relationship(
        back_populates="outgoing_citation_links",
        foreign_keys=[source_segment_id],
    )
    target_segment: Mapped["Segment"] = relationship(
        back_populates="incoming_citation_links",
        foreign_keys=[target_segment_id],
    )


class EmbeddingIndexMetadata(Base):
    __tablename__ = "embedding_index_metadata"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_scope: Mapped[str] = mapped_column(String(64), default="segment")
    embedding_model: Mapped[str] = mapped_column(String(128))
    vector_backend: Mapped[str] = mapped_column(String(64), default="pgvector")
    dimension: Mapped[int] = mapped_column(Integer(), default=1536)
    status: Mapped[str] = mapped_column(String(64), default="planned")
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON(), nullable=True)
