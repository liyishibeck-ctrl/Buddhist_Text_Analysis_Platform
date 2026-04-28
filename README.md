# Buddhist Text Analysis Platform MVP

This repository is a first runnable MVP for a structured Buddhist text analysis platform spanning three traditions:

- 汉传大藏经 sample
- 藏传佛典 / 藏文大藏经相关文本 sample
- 巴利三藏 / 上座部佛典 sample

The goal is not to build a flashy chatbot first. The goal is to lay down a stable corpus platform foundation for cataloging, metadata management, segment-level retrieval, cross-tradition comparison, concept analysis, and later embeddings / pgvector / RAG / knowledge graph work.

## Why this is a standalone project

This Buddhist corpus platform is intentionally structured as an independent project so it can use a more suitable architecture:

- Backend-first
- FastAPI as the core runtime
- Relational corpus model first
- PostgreSQL + pgvector as the default local and production deployment shape
- SQLite reserved for tests and smoke checks

## Architecture

### Current MVP stack

- API framework: FastAPI
- ORM / relational layer: SQLAlchemy
- Data processing: pandas-backed sample loader
- Rendering: Jinja2 templates for lightweight internal validation pages
- Database target: PostgreSQL + pgvector
- Migration tooling: Alembic baseline included
- SQLite scope: tests and smoke validation only

### What this MVP already supports

- Structured entities for traditions, collections, works, text versions, structure units, segments, persons, sources, concepts, parallels, citations, and embedding metadata
- Small sample corpus across Chinese, Tibetan, and Pali traditions
- Segment-level browsing and metadata inspection
- Basic keyword search over sample segments
- Parallel link display across traditions
- Concept tag aggregation pages
- Han canon catalog snapshot with pitaka hierarchy and catalog-only placeholders
- Han core-text pilot tied to catalog work IDs for first full-text ingestion tests
- Official CBETA XML P5 imports for a growing Han core corpus, including multi-file works such as `T0220`
- CSV-driven Han catalog preprocessing and import scripts
- PostgreSQL-aware retrieval with full-text ranking, trigram fallback, and score-aware segment search
- pgvector-backed local embedding baseline plus a lightweight RAG context assembly flow
- Core concept analytics with tradition distribution, top-work counts, and co-occurrence summaries
- A lightweight research tools page that exposes keyword search, vector search, and RAG prompt assembly

## Three Han ingestion layers

The Han side of the platform is intentionally staged into three layers so the catalog model stays stable while text provenance becomes richer:

- `catalog` layer: directory-first rows and `catalog_node` trees, including catalog-only work placeholders
- `pilot` layer: curated excerpt/paraphrase validation data used to prove the segment and search pipeline
- `official XML` layer: source-backed full-text imports from official XML/TEI inputs such as CBETA XML P5

The pilot layer is a bridge, not the end state. Official XML should become the authoritative textual layer for research use while keeping source provenance and version metadata explicit.

## Directory layout

```text
repository-root/
├─ backend/
│  └─ app/
│     ├─ api/
│     ├─ core/
│     ├─ db/
│     ├─ models/
│     ├─ schemas/
│     ├─ services/
│     ├─ static/
│     └─ templates/
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ sample/
├─ docs/
├─ scripts/
│  ├─ ingest/
│  ├─ preprocessing/
│  └─ seed/
└─ tests/
```

## Sample data note

The seed corpus in `data/sample/sample_corpus.json` is explicitly **sample/mock**:

- metadata structure is real in shape
- IDs and relationships are stable and usable
- passages are representative excerpts or condensed paraphrases
- this is not a complete canon
- this is not a critical scholarly edition

Separately, `data/raw/han/han_canon_catalog_seed.csv` is a curated **catalog snapshot**:

- it preserves real directory structure patterns such as Taisho-style identifiers and 经 / 律 / 论 grouping
- it is still only a partial import scaffold
- it does not include the full Han canon
- it does not include full text, structure units, or segments yet

`data/raw/han/han_core_texts_pilot.json` is a **curated core-text pilot**:

- it is tied to existing Han catalog `work_id` records
- it adds the first text-version / structure / segment ingestion path for selected core works
- it currently contains excerpt/paraphrase pilot content only
- it is not a full CBETA mirror and not a complete Han canon import

When the official XML layer is imported, those text versions should be stored as non-sample, non-catalog-only records with explicit XML/TEI provenance in `source`.

`data/raw/han/han_cbeta_xml_manifest.json` plus `data/raw/han/cbeta_xml/` is the first **official-source XML lane**:

- it points to local CBETA XML P5 files for selected Han core texts
- it imports those files as non-sample, non-catalog-only `text_version` rows
- it derives `structural_unit` and `segment` rows from CBETA main-body divisions such as `jing`, `pin`, and `other`
- it also captures verse-line content stored under TEI `<l>` nodes so large sutras do not undercount poetic sections
- it preserves juan-aware structure so multi-volume texts render as real卷级 nodes instead of a single placeholder volume
- it keeps explicit source provenance and a non-commercial usage note

## Quick start

### 1. Install dependencies

From the project directory:

```powershell
pip install -e .[dev]
```

### 2. Configure environment

Copy `.env.example` to `.env`. The app now assumes PostgreSQL for normal local development; SQLite is kept for tests and smoke validation.

PostgreSQL target example:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/buddha_corpus
ENABLE_AUTO_SEED=false
EMBEDDING_PROVIDER=local-hash
EMBEDDING_MODEL=local-hash-v1
EMBEDDING_DIMENSION=64
```

For a stronger external embedding worker, switch to the `openai-compatible` provider and set:

```env
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_API_URL=https://your-worker.example/v1/embeddings
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSION=your-vector-size
EMBEDDING_API_KEY=optional-token
```

Fastest local setup with Docker:

```powershell
docker compose up -d postgres
```

The compose stack uses the official `pgvector/pgvector` image and initializes both `vector` and `pg_trgm`.

To create or update the schema with Alembic:

```powershell
alembic upgrade head
```

### 3. Run the app

```powershell
$env:ENABLE_AUTO_SEED='false'
uvicorn backend.app.main:app --reload
```

Then open:

- UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Optional explicit seed / rebuild

```powershell
python scripts/seed/bootstrap_sample_db.py
```

To recreate the schema and re-seed both the sample corpus and the Han catalog snapshot:

```powershell
python scripts/seed/bootstrap_sample_db.py --force
```

### 5. Han catalog preprocessing / import

Build a processed JSON bundle from the curated CSV seed:

```powershell
python scripts/preprocessing/han/build_han_catalog_bundle.py
```

Import or refresh only the Han catalog snapshot:

```powershell
python scripts/ingest/han/import_han_catalog.py --force --write-bundle
```

### 6. Han core-text pilot preprocessing / import

Build the processed pilot bundle:

```powershell
python scripts/preprocessing/han/build_han_core_texts_pilot_bundle.py
```

Import the first Han core-text pilot into the same catalog-backed works:

```powershell
python scripts/ingest/han/import_han_core_texts.py --force
```

### 7. Official CBETA XML import

Import the current batch of official Han XML texts:

```powershell
python scripts/ingest/han/import_han_cbeta_xml.py --force
```

### 7. Pali plain text import

Import the Pali sample texts from the CST4 open access corpus:

```powershell
python scripts/ingest/pali/import_pali_plain_text.py --force
```

This imports full Pali texts including:
- Dhammapada
- Mūlapariyāya Sutta (MN 1)
- Sāmaññaphala Sutta (DN 2)
- Anattalakkhaṇa Sutta (SN 22.59)
- Aṭṭhaṅgika Magga (AN 8.2)

### 8. Tibetan plain text (Wylie) import

Import Tibetan texts in Wylie transliteration from open access sources:

```powershell
python scripts/ingest/tibetan/import_tibetan_plain_text.py --force
```

This imports Tibetan texts including:
- Shes rab snying po (Heart Sutra) from the Kangyur
- Bodhicaryavatara Chapter 1 (by Shantideva) from the Tengyur

### 9. Optional full Taisho non-esoteric sutra rebuild

To rebuild the local database with the full `T0001-T0847` non-esoteric Taisho sutra corpus from official CBETA metadata and XML files:

```powershell
python scripts/ingest/han/rebuild_taisho_non_esoteric_sutra_corpus.py
```

This script:

- fetches the official CBETA work list for the non-esoteric Taisho sutra range
- generates a combined Han catalog CSV and combined CBETA XML manifest under `data/processed/han/`
- downloads missing XML files into `data/raw/han/cbeta_xml/`
- rebuilds the local database from scratch

After running the full rebuild once, start the app with `ENABLE_AUTO_SEED=false` so the server uses the existing local database instead of trying to reseed on startup:

```powershell
$env:ENABLE_AUTO_SEED='false'
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 9. PostgreSQL-first rebuild flow

Once PostgreSQL is up, rebuild the schema and corpus into PostgreSQL with:

```powershell
$env:DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/buddha_corpus'
alembic upgrade head
python scripts/ingest/han/rebuild_taisho_non_esoteric_sutra_corpus.py
```

This keeps the full corpus in PostgreSQL while tests can continue using their isolated SQLite temp databases.

### 10. Optional concept and vector backfill

After the corpus is in PostgreSQL, you can backfill the MVP concept and vector layers:

```powershell
python scripts/analysis/backfill_core_concepts.py --batch-size 1000
python scripts/analysis/backfill_segment_embeddings.py --batch-size 500
```

These scripts:

- create or refresh the core concept lexicon rows
- auto-tag segments with a curated concept lexicon for distribution analysis
- build embeddings into the pgvector store using the configured provider

The built-in default remains intentionally modest: `local-hash-v1`. It proves the retrieval stack and pgvector plumbing while the new provider layer leaves room for a stronger external embedding worker without changing the retrieval API shape.

## Key API endpoints

- `GET /api/overview`
- `GET /api/collections`
- `GET /api/works`
- `GET /api/works/{work_id}`
- `GET /api/catalog/han`
- `GET /api/text-versions`
- `GET /api/text-versions/{text_version_id}`
- `GET /api/text-versions/{text_version_id}/structure`
- `GET /api/segments`
- `GET /api/segments/{segment_id}`
- `GET /api/segments/{segment_id}/parallel-links`
- `GET /api/search/segments?q=...`
- `GET /api/concepts`
- `GET /api/concepts/{concept_slug}`
- `POST /api/vector/search`
- `POST /api/rag/query`

## Current MVP scope

Included now:

- sample corpus for segmented text browsing
- Han catalog snapshot imported from `data/raw/han/han_canon_catalog_seed.csv`
- Han core-text pilot imported from `data/raw/han/han_core_texts_pilot.json`
- full non-esoteric Taisho sutra coverage for `T0001-T0847`, rebuilt into PostgreSQL from official CBETA metadata and XML
- Official CBETA XML imports for:
  - Heart Sutra (`T0251`)
  - Diamond Sutra (`T0235`)
  - Amitabha Sutra (`T0366`)
  - Lotus Sutra (`T0262`)
  - Mahaprajnaparamita Sutra / Da Banruo Boluomiduo Jing (`T0220`)
  - Fangguang Prajna Sutra / Fangguang Banruo Jing (`T0221`)
  - Guangzan Sutra (`T0222`)
  - Maha Prajna Paramita Sutra / Mohe Banruo Boluomi Jing (`T0223`)
  - Damingdu Sutra (`T0225`)
  - Maha Prajna Excerpt Sutra / Mohe Banruochao Jing (`T0226`)
  - Smaller Prajna Paramita Sutra / Xiaopin Banruo Boluomi Jing (`T0227`)
  - Avatamsaka Sutra / Huayan Jing, Buddhabhadra translation (`T0278`)
  - Avatamsaka Sutra / Huayan Jing, Shiksananda translation (`T0279`)
  - Maharatnakuta Sutra / Da Baoji Jing (`T0310`)
  - Mahaparinirvana Sutra / Da Ban Niepan Jing (`T0374`)
  - Mahasamnipata Sutra / Da Fangdeng Daji Jing (`T0397`)
  - Digha-agama / Chang Ahan Jing (`T0001`)
  - Madhyama-agama / Zhong Ahan Jing (`T0026`)
  - Samyukta-agama / Za Ahan Jing (`T0099`)
  - Ekottarikagama / Zeng Yi Ahan Jing (`T0125`)
  - Saddharma-smrty-upasthana Sutra / Zhengfa Nianchu Jing (`T0721`)
  - Mahaprajnaparamita-sastra / Dazhidu Lun (`T1509`)
  - Brahma Net Sutra Bodhisattva Precepts (`T1484`)
  - Madhyamaka Treatise / Zhong Lun (`T1564`)
  - Twelve Gate Treatise (`T1568`)
  - Hundred Treatise / Bai Lun (`T1569`)
  - Cheng Weishi Lun (`T1585`)
- Pali Tipitaka plain text imports with core suttas:
  - Dhammapada
  - Mūlapariyāya Sutta (MN 1)
  - Sāmaññaphala Sutta (DN 2)
  - Anattalakkhaṇa Sutta (SN 22.59)
  - Aṭṭhaṅgika Magga (AN 8.2)
- Tibetan Kangyur/Tengyur plain text imports (Wylie transliteration):
  - Shes rab snying po (Heart Sutra) from Kangyur
  - Bodhicaryavatara Chapter 1 by Shantideva from Tengyur
- manually curated parallel links across three traditions
- manually curated concept tags
- relational metadata model
- lightweight HTML validation pages
- explicit separation of catalog, pilot, and official XML ingestion layers in docs and tests
- optional full non-esoteric Taisho sutra rebuild script for broad Han coverage without slowing down default test startup
- PostgreSQL-first retrieval path with ranked keyword search, trigram-assisted fuzzy matching, and pgvector-backed local embeddings
- research tools page with keyword search, vector search, and RAG prompt assembly
- core concept analysis with lexicon-backed auto-tagging, tradition distribution, top-work aggregation, and concept co-occurrence summaries

Not included yet:

- full Han canon metadata dump
- full canon ingestion
- generalized official CBETA XML/TEI ingestion pipeline beyond the current imported Han batch
- OCR / TEI / XML normalization
- external API-backed embedding generation
- automated alignment pipeline
- knowledge graph materialization
- answer generation orchestration beyond retrieval-context assembly

## Recommended next steps

1. **Done**: Add ingestion adapters for one real source per tradition. ✓
2. Expand the Han XML importer beyond the current non-esoteric sutra batch while keeping the same `work` anchors.
3. Expand the Han catalog seed into a larger canonical directory ingest with import-job tracking.
4. Add automated cross-tradition parallel alignment discovery using vector similarity + concept matching.
5. Normalize citations, chapter markers, and segment boundaries from source-specific formats.
6. Replace `local-hash-v1` with a multilingual embedding model for better semantic retrieval across three traditions.
7. Add alignment confidence workflows and editorial review states.
8. Add graph-ready exports for people, works, concepts, and citations.
9. Add answer-generation orchestration on top of the current RAG retrieval package.

See also:

- [docs/data_model.md](docs/data_model.md)
- [docs/roadmap.md](docs/roadmap.md)
