# Roadmap

## Phase 1: current MVP

Current scope:

- one independent FastAPI project
- normalized corpus schema
- sample/mock corpus for three traditions
- paragraph-level browsing plus PostgreSQL-aware ranked search
- manual parallel links and concept tags
- core concept auto-tagging and distribution views
- pgvector-backed local embedding baseline
- RAG context assembly and research tools page

## Phase 2: move from sample corpus to real corpora

### Ingestion path

1. Pick one real source per tradition first.
2. Build source-specific adapters under `scripts/ingest/`.
3. Normalize imported records into a canonical intermediate format.
4. Map source-native structure markers into `structural_unit`.
5. Segment texts into stable `segment` records.
6. Preserve provenance in `source` and import logs.

### Suggested sequence

1. 汉传: one stable metadata source plus one short public-domain text set
2. 巴利: one Romanized Pali source with predictable structure
3. 藏传: one Tibetan source with stable catalog identifiers

### Current Han-first path

The current repository now includes a CSV-driven Han catalog snapshot pipeline:

1. curate rows in `data/raw/han/han_canon_catalog_seed.csv`
2. normalize them into a processed bundle with `scripts/preprocessing/han/build_han_catalog_bundle.py`
3. import them with `scripts/ingest/han/import_han_catalog.py`
4. browse them through `/han/catalog` and `/api/catalog/han`
5. attach full-text loaders later by matching `canonical_code`, `work_slug`, and `text_version` placeholders

### Current Han core-text pilot

The repository now also includes a curated Han core-text pilot:

1. maintain pilot text assets in `data/raw/han/han_core_texts_pilot.json`
2. validate and flatten them with `scripts/preprocessing/han/build_han_core_texts_pilot_bundle.py`
3. import them with `scripts/ingest/han/import_han_core_texts.py`
4. keep them tied to existing catalog `work_id` records so later official imports can replace the pilot without redesigning the model
5. treat the current pilot as excerpt/paraphrase validation data, not as a final canonical full-text source

### Official XML lane now in repo

The repository now also includes a first official XML / TEI ingestion lane built on top of local CBETA XML P5 files:

1. keep manifest records in `data/raw/han/han_cbeta_xml_manifest.json`
2. place XML source files under `data/raw/han/cbeta_xml/`
3. import them with `scripts/ingest/han/import_han_cbeta_xml.py`
4. store these versions as non-sample, non-catalog-only records
5. preserve source provenance in `source` and per-segment XML metadata
6. keep the same `work` anchors that the catalog and pilot layers already use
7. support multi-file works such as `T0220` and capture TEI verse-line segments under `<l>`

Current scope of this lane:

- Heart Sutra (`T0251`)
- Diamond Sutra (`T0235`)
- Amitabha Sutra (`T0366`)
- Lotus Sutra (`T0262`)
- Mahaprajnaparamita Sutra (`T0220`)
- Fangguang Prajna Sutra (`T0221`)
- Guangzan Sutra (`T0222`)
- Maha Prajna Paramita Sutra (`T0223`)
- Damingdu Sutra (`T0225`)
- Maha Prajna Excerpt Sutra (`T0226`)
- Smaller Prajna Paramita Sutra (`T0227`)
- Avatamsaka Sutra, Buddhabhadra translation (`T0278`)
- Avatamsaka Sutra, Shiksananda translation (`T0279`)
- Maharatnakuta Sutra (`T0310`)
- Mahaparinirvana Sutra (`T0374`)
- Mahasamnipata Sutra (`T0397`)
- Digha-agama / Chang Ahan Jing (`T0001`)
- Madhyama-agama / Zhong Ahan Jing (`T0026`)
- Samyukta-agama / Za Ahan Jing (`T0099`)
- Ekottarikagama / Zeng Yi Ahan Jing (`T0125`)
- Zhengfa Nianchu Jing (`T0721`)
- Mahaprajnaparamita-sastra / Dazhidu Lun (`T1509`)
- Brahma Net Sutra Bodhisattva Precepts (`T1484`)
- Zhong Lun (`T1564`)
- Twelve Gate Treatise (`T1568`)
- Bai Lun (`T1569`)
- Cheng Weishi Lun (`T1585`)

Current milestone:

- the local rebuild now covers the full non-esoteric Taisho sutra range `T0001-T0847`, using official CBETA XML P5 sources plus the existing catalog anchors

Next expansion step:

- keep expanding the same importer to a larger Han core-text batch before attempting broad canon coverage
- add richer structure mapping for `pin` / chapter-level nodes on top of the new juan-aware parser
- prioritize the remaining large-scale Agama or treatise works only after this batch stabilizes in tests and docs

Current repository note:

- a separate rebuild script now exists at `scripts/ingest/han/rebuild_taisho_non_esoteric_sutra_corpus.py`
- it is intentionally kept outside the default auto-seed path so tests and small local startups remain manageable
- use it when you want the broad `T0001-T0847` Han sutra corpus locally, then run the app with `ENABLE_AUTO_SEED=false`

## Phase 3: real PostgreSQL + pgvector runtime

Current status:

- PostgreSQL is now the default runtime target in config and docs
- the repo includes `docker-compose.yml` for a local `pgvector/pgvector` database
- startup ensures `vector` and `pg_trgm` extensions when running against PostgreSQL
- Alembic baseline scaffolding is included for schema management
- PostgreSQL runtime now also creates search indexes and the `segment_embeddings` store

Recommended move:

- keep SQLite only for smoke testing
- keep local development and the full corpus on PostgreSQL
- use `alembic upgrade head` before first seed or rebuild
- keep large rebuilds as explicit scripts instead of automatic startup work

At that point:

- `segment` remains the retrieval anchor
- `embedding_index_metadata` tracks coverage
- `catalog_node` remains the pre-text directory layer for large canon ingestion
- vector rows can be generated into a dedicated table or attached to a materialized index layer

## Phase 4: embeddings and vector search

### Minimal embedding architecture

1. Replace the current `local-hash-v1` baseline with an external embedding worker or batch job.
2. Select one chunking policy per owner type.
3. Keep writing vectors into pgvector-backed storage.
4. Update `embedding_index_metadata` with model, dimension, and status.
5. Upgrade the current `/api/vector/search` endpoint from lexical-hash baseline to stronger semantic retrieval.

### Recommended retrieval layers

- lexical retrieval over segments
- vector retrieval over segments
- optional hybrid reranking
- alignment-aware expansion using `parallel_link`
- concept-aware boosting using `concept_tag`

This shape is compatible with Haystack, LangChain, or a custom retrieval pipeline.

## Phase 5: RAG and LLM workflows

Current repository note:

- `POST /api/rag/query` already assembles traceable segment contexts plus prompt scaffolding
- `/research` exposes keyword search, vector search, and RAG context assembly in one page
- this is still retrieval-first, not final answer generation

Once retrieval is stable:

1. add citation-preserving answer generation
2. use segment IDs as traceable evidence anchors
3. expand retrieved context through parallel and citation links
4. add role-aware prompts for doctrinal comparison, translation comparison, and concept tracing

The platform should answer from structured evidence, not from opaque freeform prompting alone.

## Phase 6: knowledge graph support

### Graph candidates

- `work` -> `text_version`
- `work` -> `person` with role
- `segment` -> `concept_tag`
- `segment` -> `segment` via parallel or citation link
- `work` -> `collection` -> `tradition`

### Suggested graph rollout

1. export edges from relational DB into graph-ready tables or JSONL
2. introduce stable concept identifiers
3. normalize person identity resolution
4. track alignment confidence and editorial status on links

This gives a clean bridge to Neo4j, RDF tooling, or a lightweight property-graph pipeline later.

## Phase 7: editorial and research workflows

Later research-oriented features:

- suggested parallels awaiting review
- concept-tag review queues
- source witness comparison
- editorial note layers
- TEI / XML export
- scholar workspaces and saved collections
