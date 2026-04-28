# Data Model

## Design goal

The platform models Buddhist corpora as a structured, extensible corpus system rather than a single flat text search index. The first design priority is to support:

- corpus cataloging
- version-aware metadata
- segment-level retrieval
- cross-tradition alignment
- concept analysis
- future embedding and graph expansion

## Core entities

### `tradition`

Top-level tradition bucket such as 汉传, 藏传, 巴利 / 上座部.

Why it exists:

- supports top-level filtering
- preserves tradition-specific catalog context
- provides a clean axis for cross-tradition comparison

### `collection`

Represents a canon collection or bounded corpus collection under a tradition.

Examples:

- 汉传大藏经样本集
- 巴利三藏样本集
- 藏文甘珠尔样本集

Why it exists:

- collections are a stable curation unit
- real-world ingestion often happens by collection
- lets the UI and APIs expose tradition and collection separately

### `work`

Represents an intellectual work, such as a sutra, sutta, treatise, commentary, or vinaya text.

Why it exists:

- a work may have multiple versions or witnesses
- work-level metadata differs from version-level metadata
- cross-tradition correspondences can exist between works even when they are not the same version

Current catalog-oriented extensions:

- `pitaka_division` for 经 / 律 / 论 filtering
- `canonical_code` for identifiers such as Taisho numbers
- `fascicle_count` and `catalog_order` for directory browsing
- `is_catalog_only` and `catalog_note` for placeholder rows that exist before full text is imported

This allows a staged path:

1. import the canon directory first
2. attach pilot text versions to existing `work` rows
3. later replace pilot versions with official XML/TEI-derived versions without changing the higher-level catalog tree

## Three Han ingestion layers

The Han side of the model is intentionally split into three layers so that directory structure, validation text, and authoritative full text can evolve independently:

### `catalog` layer

Directory-first rows and tree nodes that represent the canon outline before full text is available.

Typical records:

- `catalog_node` rows for 经藏 / 律藏 / 论藏 branches
- `work` rows with `is_catalog_only = true`
- `text_version` rows that may exist only as catalog placeholders

Why it exists:

- preserves the canon structure early
- lets browsing and filtering work before full text arrives
- provides stable anchors for later version attachment

### `pilot` layer

Curated excerpt or paraphrase records tied to existing catalog `work` anchors.

Typical records:

- `text_version` rows with `is_sample = true`
- small, manually curated `segment` rows used to verify search and structure rendering
- metadata that proves the segment pipeline before official ingestion

Why it exists:

- validates import logic before a large XML source is wired in
- exercises the API and UI without pretending to be a full canon mirror
- keeps sample data clearly separated from real-source text

### `official XML` layer

Source-backed full-text versions derived from official XML / TEI inputs such as CBETA XML P5.

Typical records:

- `text_version` rows with `is_sample = false`
- `text_version` rows with `is_catalog_only = false`
- `source` rows pointing to the XML / TEI provenance
- stable `structural_unit` and `segment` rows derived from the source structure

Why it exists:

- becomes the authoritative textual layer for scholarly work
- preserves source provenance and reproducibility
- supports later alignment, citation, embedding, and RAG workflows without changing the catalog hierarchy

Current implementation note:

- the first official lane imports local CBETA XML P5 files through a manifest
- each imported paragraph stores XML-oriented provenance such as `xml_id`, source path, display URL, division type, and juan metadata in `segment.metadata_json`
- official imports reuse the same `work` anchors that the catalog and pilot layers already use
- the loader now supports CBETA body divisions such as `jing`, `pin`, and `other`, which is necessary for sutra and sastra texts that do not wrap the main body in a single `cb:div type="jing"`
- multi-juan imports create separate `structural_unit` rows for each juan instead of collapsing everything into one placeholder volume

### `text_version`

Represents a concrete textual version, translation, language form, or editorial witness of a work.

Why it exists:

- supports different translators, scripts, and editorial states
- allows source-specific provenance
- forms the boundary for structure trees and segment indexing

### `catalog_node`

Represents a directory-tree node for catalog-first ingestion, such as 经藏, 阿含部, or a catalog-only work leaf.

Why it exists:

- full canon onboarding should start from directory structure before full text
- keeps pitaka hierarchy explicit without overloading `structural_unit`
- provides a stable bridge between external catalog files and later work / text ingestion

### `structural_unit`

Represents a hierarchy node inside a text version such as volume, chapter, section, or other structural division.

Why it exists:

- canonical texts are hierarchical
- segment retrieval needs context inside a larger structure
- future ingestion adapters can map source-specific structure markers here

### `segment`

Represents the smallest retrieval and analysis unit in the MVP, currently paragraph-like.

Why it exists:

- retrieval is more useful at paragraph granularity than whole-text granularity
- later embeddings, RAG, and alignment models will most often operate on this level
- segment IDs become stable anchors for citations and parallel links

### `person`

Represents people or collective agents such as authors, translators, editors, compilers, annotators.

Why it exists:

- Buddhist textual history is role-heavy
- author and translator are not the same thing
- one person may relate to works and versions in different roles

### `language`

Represents the language or script system of a text version.

Why it exists:

- supports filtering and multilingual analytics
- becomes important for tokenization and embedding strategy later

### `source`

Represents provenance for a version or imported dataset.

Why it exists:

- keeps ingestion provenance explicit
- makes sample/mock vs real-source status visible
- later supports trust scoring and reproducibility

### `parallel_link`

Represents a relation between two segments that are aligned, parallel, or thematically corresponding.

Why it exists:

- cross-tradition comparison is one of the central platform goals
- alignment quality and type need their own relational object
- later can support editorial workflows and machine-assisted suggestions

### `concept_tag`

Represents a curated concept or doctrinal theme assigned to segments.

Why it exists:

- concept analysis is a core user goal
- curated tags provide a stable bridge before more advanced NLP layers exist
- later this can connect to ontology / knowledge graph layers

### `citation_link`

Represents one segment citing, echoing, or referencing another segment.

Why it exists:

- citation-like relations matter for scholastic corpora
- allows future graph traversal beyond simple parallelism

### `embedding_index_metadata`

Stores metadata about planned or completed embedding coverage.

Why it exists:

- avoids mixing vector index lifecycle into the segment table itself
- lets the platform track which owners were embedded, with what model, and under what chunking strategy
- keeps embedding coverage metadata separate from the actual vector store

Current runtime note:

- the PostgreSQL runtime now also uses a dedicated `segment_embeddings` table backed by `pgvector`
- the first embedding model is `local-hash-v1`, a deterministic lexical baseline used to validate vector plumbing and retrieval APIs
- this baseline is intentionally replaceable; stronger external embedding workers can be swapped in later without changing the corpus model

## Relationship summary

```text
tradition 1─* collection
tradition 1─* work
tradition 1─* catalog_node
collection 1─* work
collection 1─* catalog_node
work 1─* text_version
work 1─* catalog_node
catalog_node 1─* catalog_node (self hierarchy)
text_version 1─* structural_unit
structural_unit 1─* structural_unit (self hierarchy)
text_version 1─* segment
structural_unit 1─* segment
work *─* person via work_person_roles
text_version *─* person via text_version_person_roles
segment *─* concept_tag via segment_concept_tags
segment *─* segment via parallel_link
segment *─* segment via citation_link
embedding_index_metadata -> owner_type + owner_id
```

## Why not a single flat `text` table

A flat table would be faster to prototype, but it would quickly break when we need:

- multiple versions of the same work
- explicit structural browsing
- translator and source metadata
- segment-level parallel alignment
- graph-like relations between passages
- vector indexing at more than one granularity

The current model is still lightweight, but it preserves those future paths.

## PostgreSQL + pgvector fit

This schema is designed for PostgreSQL as the long-term default:

- stable relational metadata in PostgreSQL
- segment retrieval via SQL filters, trigram search, and PostgreSQL full-text ranking
- embeddings stored in pgvector-backed tables or materialized indexes

The MVP ships with SQLite fallback only so the project can run immediately in a bare repository without making local PostgreSQL a hard prerequisite.
