"""Runtime configuration sourced from environment + YAML config files.

All settings can be overridden via .env (loaded automatically by pydantic-settings).
Defaults match values in docker-compose.yml so the app boots without manual setup.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import CrawlMode

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ConcurrencyCaps(BaseSettings):
    """Per-stage parallelism caps. Override via env."""

    model_config = SettingsConfigDict(extra="ignore")

    # Discovery makes LLM calls per query — kept low to stay under OpenAI TPM tier limits.
    expo_discovery: int = Field(default=4, alias="EXPO_DISCOVERY_CONCURRENCY")
    exhibitor_extraction: int = Field(default=15, alias="EXHIBITOR_EXTRACTION_CONCURRENCY")
    vendor_resolution: int = Field(default=30, alias="VENDOR_RESOLUTION_CONCURRENCY")
    enrichment: int = Field(default=50, alias="ENRICHMENT_CONCURRENCY")

    def for_mode(self, mode: CrawlMode) -> "ConcurrencyCaps":
        if mode == CrawlMode.DEV:
            return ConcurrencyCaps(
                EXPO_DISCOVERY_CONCURRENCY=2,
                EXHIBITOR_EXTRACTION_CONCURRENCY=3,
                VENDOR_RESOLUTION_CONCURRENCY=5,
                ENRICHMENT_CONCURRENCY=5,
            )
        if mode == CrawlMode.AGGRESSIVE:
            return ConcurrencyCaps(
                EXPO_DISCOVERY_CONCURRENCY=8,  # higher would burn TPM
                EXHIBITOR_EXTRACTION_CONCURRENCY=30,
                VENDOR_RESOLUTION_CONCURRENCY=60,
                ENRICHMENT_CONCURRENCY=100,
            )
        return self  # normal

    def for_provider(self, provider: str) -> "ConcurrencyCaps":
        """When using Ollama on a single consumer GPU, throttle stages that
        burst LLM calls so the GPU isn't overwhelmed (timeouts, queue stalls)."""
        if provider != "ollama":
            return self
        return ConcurrencyCaps(
            EXPO_DISCOVERY_CONCURRENCY=min(self.expo_discovery, 2),
            EXHIBITOR_EXTRACTION_CONCURRENCY=self.exhibitor_extraction,
            VENDOR_RESOLUTION_CONCURRENCY=min(self.vendor_resolution, 8),
            ENRICHMENT_CONCURRENCY=min(self.enrichment, 8),
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === REQUIRED keys (the only two paid services) ===
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    firecrawl_api_key: str = Field(default="", alias="FIRECRAWL_API_KEY")

    # === LLM provider switch ===
    # `openai` (default) → api.openai.com, billed.
    # `ollama`           → self-hosted via host.docker.internal:11434, free + unlimited.
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")  # override; empty = use provider default
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_base_url: str = Field(default="", alias="EMBEDDING_BASE_URL")

    # === Self-hosted services ===
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    chroma_host: str = Field(default="chroma", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    flaresolverr_url: str = Field(default="http://flaresolverr:8191/v1", alias="FLARESOLVERR_URL")

    langfuse_host: str = Field(default="http://langfuse-web:3000", alias="LANGFUSE_HOST")
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_enabled: bool = Field(default=True, alias="LANGFUSE_ENABLED")

    # === Runtime ===
    mode: CrawlMode = Field(default=CrawlMode.NORMAL, alias="CRAWL_MODE")
    run_interval_minutes: int = Field(default=30, alias="RUN_INTERVAL_MINUTES")
    max_vendors_per_run: int = Field(default=200, alias="MAX_VENDORS_PER_RUN")
    max_expos_per_run: int = Field(default=20, alias="MAX_EXPOS_PER_RUN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    data_dir: Path = Field(default=PROJECT_ROOT / "data", alias="DATA_DIR")
    log_dir: Path = Field(default=PROJECT_ROOT / "logs", alias="LOG_DIR")
    config_dir: Path = Field(default=PROJECT_ROOT / "config", alias="CONFIG_DIR")

    browser_pool_size: int = Field(default=20, alias="BROWSER_POOL_SIZE")
    browser_recycle_after: int = Field(default=50, alias="BROWSER_RECYCLE_AFTER")

    # === OpenAI models ===
    openai_model_heavy: str = Field(default="gpt-4o", alias="OPENAI_MODEL_HEAVY")
    openai_model_light: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_LIGHT")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    # === Politeness & quotas ===
    per_domain_rps: float = Field(default=1.0, alias="PER_DOMAIN_RPS")
    global_request_timeout_seconds: int = Field(default=60, alias="GLOBAL_REQUEST_TIMEOUT_SECONDS")
    firecrawl_credit_threshold_pct: float = Field(default=10.0, alias="FIRECRAWL_CREDIT_THRESHOLD_PCT")

    # === Scraper backend toggles ===
    enable_firecrawl: bool = Field(default=False, alias="ENABLE_FIRECRAWL")
    enable_crawl4ai: bool = Field(default=True, alias="ENABLE_CRAWL4AI")
    crawl4ai_browser: str = Field(default="chromium", alias="CRAWL4AI_BROWSER")
    crawl4ai_recycle_after: int = Field(default=100, alias="CRAWL4AI_RECYCLE_AFTER")
    crawl4ai_max_concurrent: int = Field(default=4, alias="CRAWL4AI_MAX_CONCURRENT")
    crawl4ai_extraction_model: str = Field(default="gpt-4o-mini", alias="CRAWL4AI_EXTRACTION_MODEL")

    # === Phase gating ===
    phase_2_vendor_threshold: int = Field(default=100, alias="PHASE_2_VENDOR_THRESHOLD")

    # === Vendor pipeline tuning (Stage 4 + 5) ===
    vendor_completeness_threshold: float = Field(default=0.10, alias="VENDOR_COMPLETENESS_THRESHOLD")
    keep_out_of_scope: bool = Field(default=True, alias="KEEP_OUT_OF_SCOPE")
    persist_unresolved: bool = Field(default=True, alias="PERSIST_UNRESOLVED")
    pdf_relevance_threshold: float = Field(default=0.5, alias="PDF_RELEVANCE_THRESHOLD")

    # === Database ===
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:123@autocrawl-db:5432/autocrawl",
        alias="DATABASE_URL",
    )
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")
    api_cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:8090",
        alias="API_CORS_ORIGINS",
    )

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    # === Translation (vendor data localization) ===
    translation_enabled: bool = Field(default=True, alias="TRANSLATION_ENABLED")
    translation_provider: str = Field(default="nllb", alias="TRANSLATION_PROVIDER")  # nllb | openai | none
    nllb_model_path: str = Field(default="/app/data/nllb_ct2", alias="NLLB_MODEL_PATH")
    nllb_tokenizer_path: str = Field(default="/app/data/nllb_hf", alias="NLLB_TOKENIZER_PATH")
    target_language: str = Field(default="id", alias="TARGET_LANGUAGE")  # ISO 639-1
    translation_batch_size: int = Field(default=8, alias="TRANSLATION_BATCH_SIZE")
    translation_max_chars: int = Field(default=2000, alias="TRANSLATION_MAX_CHARS")

    # === PDF brochure extraction ===
    pdf_discovery_enabled: bool = Field(default=True, alias="PDF_DISCOVERY_ENABLED")
    ocr_enabled: bool = Field(default=True, alias="OCR_ENABLED")
    surya_device: str = Field(default="auto", alias="SURYA_DEVICE")  # auto | cpu | cuda | mps
    pdf_extraction_concurrency: int = Field(default=4, alias="PDF_EXTRACTION_CONCURRENCY")
    max_pdfs_per_expo: int = Field(default=10, alias="MAX_PDFS_PER_EXPO")
    pdf_max_size_mb: int = Field(default=50, alias="PDF_MAX_SIZE_MB")

    @field_validator("data_dir", "log_dir", "config_dir", mode="before")
    @classmethod
    def _resolve_path(cls, v: str | Path) -> Path:
        p = Path(v) if isinstance(v, str) else v
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    def concurrency(self) -> ConcurrencyCaps:
        return ConcurrencyCaps().for_mode(self.mode).for_provider(self.llm_provider)


# ---------------------------------------------------------------------------
# YAML helpers — load aggregator blacklist + seed topics
# ---------------------------------------------------------------------------


def load_aggregator_blacklist(config_dir: Path) -> set[str]:
    """Returns a flat lowercase set of every domain that must NEVER be a vendor."""
    path = config_dir / "aggregator_blacklist.yaml"
    if not path.exists():
        return set()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    flat: set[str] = set()
    for _bucket, domains in raw.items():
        if not isinstance(domains, list):
            continue
        for d in domains:
            if isinstance(d, str):
                flat.add(d.strip().lower())
    return flat


def load_seed_topics(config_dir: Path) -> dict:
    path = config_dir / "seed_topics.yaml"
    if not path.exists():
        return {"topics": [], "anchor_expos": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_aggregator_blacklist() -> frozenset[str]:
    """Effective blacklist (YAML defaults ∪ user-overlay − disabled).

    Backed by tools.scope_cache, kept fresh in realtime via Redis version
    counter. Falls back to YAML-only on bootstrap before the cache loads.
    """
    from .tools.scope_cache import get_effective_blacklist

    effective = get_effective_blacklist()
    if effective:
        return effective
    # bootstrap fallback — first sync call before async loop has populated cache
    return frozenset(load_aggregator_blacklist(get_settings().config_dir))


def get_seed_topics() -> dict:
    """Effective seed topics + anchor expos (merged YAML + DB overlay)."""
    from .tools.scope_cache import get_effective_seed_topics

    merged = get_effective_seed_topics()
    if merged.get("topics") or merged.get("anchor_expos"):
        return merged
    return load_seed_topics(get_settings().config_dir)
