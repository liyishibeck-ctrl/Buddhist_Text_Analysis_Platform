from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


def _default_sqlite_url() -> str:
    db_path = (ROOT_DIR / "data" / "processed" / "buddha_mvp.db").resolve()
    return f"sqlite:///{db_path.as_posix()}"


def _default_postgres_url() -> str:
    return "postgresql+psycopg://postgres:postgres@localhost:5432/buddha_corpus"


def _default_database_url() -> str:
    explicit_database_url = os.getenv("DATABASE_URL")
    if explicit_database_url:
        return explicit_database_url
    if os.getenv("APP_ENV", "development").lower() == "test":
        return _default_sqlite_url()
    return _default_postgres_url()


def _default_enable_auto_seed() -> bool:
    default_value = "true" if os.getenv("APP_ENV", "development").lower() == "test" else "false"
    return os.getenv("ENABLE_AUTO_SEED", default_value).lower() == "true"


def _default_embedding_provider() -> str:
    return os.getenv("EMBEDDING_PROVIDER", "local-hash").strip().lower()


def _default_embedding_model() -> str:
    explicit_embedding_model = os.getenv("EMBEDDING_MODEL")
    if explicit_embedding_model:
        return explicit_embedding_model
    if _default_embedding_provider() == "local-hash":
        return "local-hash-v1"
    return ""


def _default_embedding_dimension() -> int:
    explicit_dimension = os.getenv("EMBEDDING_DIMENSION")
    if explicit_dimension:
        return int(explicit_dimension)
    if _default_embedding_provider() == "local-hash":
        return 64
    return 0


@dataclass(slots=True)
class Settings:
    app_name: str = "Buddhist Text Analysis Platform MVP"
    api_prefix: str = "/api"
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = _default_database_url()
    enable_auto_seed: bool = _default_enable_auto_seed()
    sample_corpus_path: Path = Path(
        os.getenv("SAMPLE_CORPUS_PATH") or ROOT_DIR / "data" / "sample" / "sample_corpus.json"
    ).resolve()
    han_catalog_source_path: Path = Path(
        os.getenv("HAN_CATALOG_SOURCE_PATH") or ROOT_DIR / "data" / "raw" / "han" / "han_canon_catalog_seed.csv"
    ).resolve()
    han_catalog_bundle_path: Path = Path(
        os.getenv("HAN_CATALOG_BUNDLE_PATH") or ROOT_DIR / "data" / "processed" / "han" / "han_catalog_bundle.json"
    ).resolve()
    han_core_text_source_path: Path = Path(
        os.getenv("HAN_CORE_TEXT_SOURCE_PATH") or ROOT_DIR / "data" / "raw" / "han" / "han_core_texts_pilot.json"
    ).resolve()
    han_core_text_bundle_path: Path = Path(
        os.getenv("HAN_CORE_TEXT_BUNDLE_PATH") or ROOT_DIR / "data" / "processed" / "han" / "han_core_texts_pilot_bundle.json"
    ).resolve()
    han_cbeta_manifest_path: Path = Path(
        os.getenv("HAN_CBETA_MANIFEST_PATH") or ROOT_DIR / "data" / "raw" / "han" / "han_cbeta_xml_manifest.json"
    ).resolve()
    sql_echo: bool = os.getenv("SQL_ECHO", "false").lower() == "true"
    pgvector_schema_hint: str = os.getenv("PGVECTOR_SCHEMA_HINT", "public")
    embedding_provider: str = _default_embedding_provider()
    embedding_model: str = _default_embedding_model()
    embedding_dimension: int = _default_embedding_dimension()
    embedding_api_url: str = os.getenv("EMBEDDING_API_URL", "").strip()
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "").strip()
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    embedding_timeout_seconds: float = float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "30"))
    llm_api_url: str = (
        os.getenv("LLM_API_URL")
        or os.getenv("OPENAI_API_URL")
        or "https://api.openai.com/v1/responses"
    ).strip()
    llm_api_key: str = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    llm_model: str = (os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    templates_dir: Path = (ROOT_DIR / "backend" / "app" / "templates").resolve()
    static_dir: Path = (ROOT_DIR / "backend" / "app" / "static").resolve()

    @property
    def uses_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def uses_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


settings = Settings()
