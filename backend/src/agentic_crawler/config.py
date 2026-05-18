"""Standalone settings for the agentic crawler.

Kept separate from `crawler.config` so the two producers stay independent —
turning agentic off (or removing this package) leaves the base crawler intact.
Shared infra (Redis URL, DB URL, data_dir) is read from `crawler.config`
where it makes sense, since that's the single source of truth for those.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from crawler.config import PROJECT_ROOT
from crawler.config import get_settings as _get_crawler_settings


def _default_seeds_yaml() -> Path:
    return _get_crawler_settings().config_dir / "agentic_seeds.yaml"


def _default_recordings_dir() -> Path:
    return _get_crawler_settings().data_dir / "agentic_recordings"


class AgenticSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Master toggle. Default OFF — opt-in via .env or compose profile.
    enabled: bool = Field(default=False, alias="AGENTIC_ENABLED")

    llm_base_url: str = Field(default="http://10.83.81.246:11434", alias="AGENTIC_LLM_BASE_URL")
    vision_model: str = Field(default="qwen3-vl:30b", alias="AGENTIC_VISION_MODEL")
    use_vision: bool = Field(default=True, alias="AGENTIC_USE_VISION")
    max_actions: int = Field(default=15, alias="AGENTIC_MAX_ACTIONS")
    task_timeout_seconds: int = Field(default=1200, alias="AGENTIC_TASK_TIMEOUT")

    run_interval_minutes: int = Field(default=60, alias="AGENTIC_RUN_INTERVAL_MIN")

    seeds_yaml: Path = Field(
        default_factory=_default_seeds_yaml,
        alias="AGENTIC_SEEDS_YAML",
    )

    headless: bool = Field(default=True, alias="AGENTIC_HEADLESS")

    record_screenshots: bool = Field(default=True, alias="AGENTIC_RECORD_SCREENSHOTS")
    record_conversation: bool = Field(default=True, alias="AGENTIC_RECORD_CONVERSATION")
    recordings_dir: Path = Field(
        default_factory=_default_recordings_dir,
        alias="AGENTIC_RECORDINGS_DIR",
    )

    # Self-learning knowledge base. JSON file at data/agentic_knowledge.json
    # accumulates per-expo memory (successful URLs, vendors seen, run stats)
    # plus a global domain blacklist. Persists via host bind-mount.
    knowledge_path: Path = Field(
        default_factory=lambda: _get_crawler_settings().data_dir / "agentic_knowledge.json",
        alias="AGENTIC_KNOWLEDGE_PATH",
    )
    # Cosine threshold for declaring a freshly-extracted vendor "already seen".
    # Matches the base crawler dedup (crawler/store/vector_store.py). Higher =
    # only near-identical strings dedupe (catches typos), lower = more aggressive.
    vendor_dedup_threshold: float = Field(default=0.92, alias="AGENTIC_VENDOR_DEDUP_THRESHOLD")
    # Domain stays in blacklist this many days after fail count exceeds threshold.
    blacklist_days: int = Field(default=7, alias="AGENTIC_BLACKLIST_DAYS")
    blacklist_fail_threshold: int = Field(default=3, alias="AGENTIC_BLACKLIST_FAIL_THRESHOLD")
    # Probability we ignore a blacklist entry on a given check — gives blocked
    # domains a chance to come back after their cooldown. 0.05 = 5%.
    blacklist_curiosity: float = Field(default=0.05, alias="AGENTIC_BLACKLIST_CURIOSITY")

    # Number of seeds to run concurrently per pass — each spawns its own
    # Chromium tab in the same Xvfb display so noVNC shows N workspaces
    # tiled / overlapping. 4 is conservative for a typical workstation
    # (~2-4GB RAM per Chromium); bump higher if you have headroom.
    parallel_seeds: int = Field(default=4, alias="AGENTIC_PARALLEL_SEEDS")

    # ---- Mode C — autonomous discovery -----------------------------------
    # When true, every pass also generates fresh seeds from the topic taxonomy
    # in agentic_seeds.yaml: LLM expands topics → multilingual queries →
    # Bing/Baidu/Yandex search → URL scoring → top-N injected into seed queue.
    discovery_enabled: bool = Field(default=False, alias="AGENTIC_DISCOVERY_ENABLED")
    discovery_max_topics_per_pass: int = Field(
        default=3, alias="AGENTIC_DISCOVERY_MAX_TOPICS_PER_PASS"
    )
    discovery_max_queries_per_topic: int = Field(
        default=4, alias="AGENTIC_DISCOVERY_MAX_QUERIES_PER_TOPIC"
    )
    discovery_max_seeds_per_pass: int = Field(
        default=8, alias="AGENTIC_DISCOVERY_MAX_SEEDS_PER_PASS"
    )
    discovery_url_score_threshold: float = Field(
        default=0.55, alias="AGENTIC_DISCOVERY_URL_SCORE_THRESHOLD"
    )
    discovery_history_lookback_days: int = Field(
        default=14, alias="AGENTIC_DISCOVERY_HISTORY_LOOKBACK_DAYS"
    )

    # ---- Lesson archive --------------------------------------------------
    # Per-run human-readable + raw thinking dumps under data/agentic_lessons/.
    # Operator reads `failure/<expo>__<category>/thinking.md` to understand
    # *why* a seed failed without spelunking through Loki.
    lessons_dir: Path = Field(
        default_factory=lambda: _get_crawler_settings().data_dir / "agentic_lessons",
        alias="AGENTIC_LESSONS_DIR",
    )
    lessons_retention_days: int = Field(
        default=60, alias="AGENTIC_LESSONS_RETENTION_DAYS"
    )
    # When true, recordings dir gets MOVED into the lesson; false = COPIED.
    # Move keeps disk bounded (recordings_dir doesn't accumulate); copy keeps
    # the original for diagnostic tooling that scans recordings_dir directly.
    lessons_archive_recordings: bool = Field(
        default=True, alias="AGENTIC_LESSONS_ARCHIVE_RECORDINGS"
    )

    # ---- Dead YAML seed quarantine (returning-pattern fix) --------------
    # Skip a YAML seed if it produced N consecutive `empty_result` lessons
    # within `dead_seed_recent_window_hours`. Quarantine lasts
    # `dead_seed_quarantine_hours` from the most recent failure. Curiosity
    # bypass: random retry probability — a permanently broken page might
    # have been fixed since last visit. Defaults sized for hourly pass
    # interval: 3 strikes in 24h → 7-day quarantine, 10% retry chance.
    dead_seed_strikes: int = Field(default=5, alias="AGENTIC_DEAD_SEED_STRIKES")
    dead_seed_recent_window_hours: int = Field(
        default=12, alias="AGENTIC_DEAD_SEED_WINDOW_HOURS"
    )
    dead_seed_quarantine_hours: int = Field(
        default=72, alias="AGENTIC_DEAD_SEED_QUARANTINE_HOURS"
    )
    dead_seed_curiosity: float = Field(
        default=0.25, alias="AGENTIC_DEAD_SEED_CURIOSITY"
    )

    # ---- Phase 2 — multi-region search + multilingual expansion ---------
    # When true, force `expand_seeds(force_multilingual=True)` so every topic
    # produces EN + zh-Hans + ja-Kana + ko-Hangul + ru-Cyrillic queries, and
    # call `search_all(force_regions=True)` so Baidu/Naver/Yahoo Japan fire
    # regardless of detected query language. Phase 2 baseline; defaults ON.
    agentic_force_multilingual: bool = Field(
        default=True, alias="AGENTIC_FORCE_MULTILINGUAL"
    )

    # ---- Phase 3.1 — Persistent Chromium profiles + cross-twin sharding --
    # Each parallel worker (listing slot 0/1, enrich slot 0/1) gets a stable
    # user-data-dir under `agentic_profiles_dir`. History + cookies + cache
    # accumulate across runs → less captcha, real-user feel, faster repeat
    # visits. Bind-mounted via the host `./data` volume so profiles survive
    # `docker compose down -v` (only knowledge-store is wiped, not browser
    # state).
    agentic_profiles_dir: Path = Field(
        default_factory=lambda: _get_crawler_settings().data_dir / "agentic_profiles",
        alias="AGENTIC_PROFILES_DIR",
    )
    agentic_persistent_profiles: bool = Field(
        default=True, alias="AGENTIC_PERSISTENT_PROFILES"
    )
    # Pre-warm idle enrich BrowserSession at worker start so VNC workspace 2
    # always shows enrich Chromium tabs. KNOWN ISSUE: shared session across
    # tasks = single point of failure. If Chromium crashes mid-task, all
    # subsequent tasks on that slot fail with "BrowserStateRequestEvent
    # returned None". Default OFF after observed cascading failures —
    # tradeoff is invisible idle enrich slots but reliable per-task fresh
    # browsers. Keep per-task `acquire_enrich_slot` for cookie persistence.
    agentic_enrich_prewarm: bool = Field(
        default=False, alias="AGENTIC_ENRICH_PREWARM"
    )

    # Cross-twin seed sharding. With two twin containers (`agentic-a` /
    # `agentic-b`) loading the same YAML, both would pick the same seeds
    # by default and duplicate work. Each twin gets `AGENTIC_SHARD_INDEX`
    # 0..N-1 and `AGENTIC_SHARD_TOTAL` N; the scheduler hashes
    # (seed.name + pass_timestamp) and only handles seeds where
    # `hash % total == index`. Pass timestamp is folded in so shard
    # membership reshuffles every pass — twin A might own shotshow on
    # pass 1 and defenceiq on pass 2.
    agentic_shard_index: int = Field(default=0, alias="AGENTIC_SHARD_INDEX")
    agentic_shard_total: int = Field(default=1, alias="AGENTIC_SHARD_TOTAL")

    # ---- Phase 3 — Dual-pool listing + enrichment ------------------------
    # When false (default), agentic vendors flow through the deterministic
    # crawler.graph Stage 03 + 04 (resolve + enrich via httpx/WHOIS/Wikipedia
    # — chronically fails for vendor names like "REPKON" that need search-
    # then-visit). When true, listing pool publishes EnrichTasks to
    # `agentic:enrich:queue`; a separate enrich-worker pool runs Browser-Use
    # agents that search → pick domain → visit → extract, then persist via
    # the same `reporter_agent.persist_vendor` writer (no DB schema fork).
    agentic_enrich_enabled: bool = Field(default=False, alias="AGENTIC_ENRICH_ENABLED")
    agentic_enrich_parallel: int = Field(default=4, alias="AGENTIC_ENRICH_PARALLEL")
    # Bumped 25→40 + 600→900 in Phase 4: step budget often exhausted at step
    # 22-25 right when agent reaches /contact page. Trade ~50% elapsed for
    # higher per-task success rate; net data/hour improves.
    enrich_max_steps: int = Field(default=40, alias="AGENTIC_ENRICH_MAX_STEPS")
    enrich_task_timeout_seconds: int = Field(
        default=900, alias="AGENTIC_ENRICH_TASK_TIMEOUT_SECONDS"
    )
    # Phase 4 PR 3 — try deterministic HTTP scrape on common contact paths
    # before spawning Browser-Use. ~30-40% of vendors with known domain
    # have static pages; this saves ~4 min/vendor. Default ON, reversible.
    enrich_static_pre_pass_enabled: bool = Field(
        default=True, alias="AGENTIC_ENRICH_STATIC_PRE_PASS"
    )
    # Phase 5 — Product catalog enrichment + DOI scoring. Live path enqueues
    # vendor_id to backfill queue post-persist; backfill worker drains.
    product_catalog_live_enabled: bool = Field(
        default=True, alias="AGENTIC_PRODUCT_CATALOG_LIVE"
    )
    product_backfill_parallel: int = Field(
        default=4, alias="AGENTIC_PRODUCT_BACKFILL_PARALLEL"
    )
    # Phase 5 — 24h ops watchdog. Browser-Use 0.12.6 has a CDP-cascade
    # bug that gradually degrades chromium subprocess health after several
    # hours of sustained operation. Self-restart at this interval forces
    # a clean process tree before degradation kicks in. Combined with
    # `restart: unless-stopped` in compose, the container comes back up
    # automatically. Set to 0 to disable.
    self_restart_hours: float = Field(
        default=4.0, alias="AGENTIC_SELF_RESTART_HOURS"
    )
    # Few-shot exemplar counts in the enrich agent's system prompt. Caps
    # context bloat — 3+2 with ≤300 chars each = ~2KB token overhead.
    enrich_few_shot_success_n: int = Field(
        default=3, alias="AGENTIC_ENRICH_FEW_SHOT_SUCCESS_N"
    )
    enrich_few_shot_failure_n: int = Field(
        default=2, alias="AGENTIC_ENRICH_FEW_SHOT_FAILURE_N"
    )
    enrich_lessons_dir: Path = Field(
        default_factory=lambda: _get_crawler_settings().data_dir / "agentic_enrich_lessons",
        alias="AGENTIC_ENRICH_LESSONS_DIR",
    )
    # XAUTOCLAIM idle threshold for re-delivering pending entries from a
    # crashed worker's PEL.
    enrich_pel_reclaim_idle_seconds: int = Field(
        default=300, alias="AGENTIC_ENRICH_PEL_RECLAIM_IDLE_SECONDS"
    )

    # VNC fluxbox workspace assignment (PR4 lands the helper; settings live
    # here so PR2 can reference enrich_workspace_id without circular imports).
    listing_workspace_id: int = Field(default=1, alias="AGENTIC_LISTING_WORKSPACE_ID")
    enrich_workspace_id: int = Field(default=2, alias="AGENTIC_ENRICH_WORKSPACE_ID")
    vnc_workspace_assignment_enabled: bool = Field(
        default=True, alias="AGENTIC_VNC_WORKSPACE_ASSIGNMENT_ENABLED"
    )

    # ---- Preflight HEAD probe -------------------------------------------
    # Discovery URLs go through a HEAD request before being queued so we
    # don't burn agent turns on 404s, image-only pages, or non-HTML payloads.
    # Mode A+B seeds skip preflight (preserves existing behavior).
    preflight_enabled: bool = Field(default=True, alias="AGENTIC_PREFLIGHT_ENABLED")
    preflight_min_html_bytes: int = Field(
        default=5120, alias="AGENTIC_PREFLIGHT_MIN_HTML_BYTES"
    )
    preflight_head_timeout_s: float = Field(
        default=8.0, alias="AGENTIC_PREFLIGHT_HEAD_TIMEOUT_S"
    )
    # F2: DNS hard-fail. NXDOMAIN/SERVFAIL on a discovery seed → blacklist
    # immediately with reason "dns_dead". Cuts the 20-min Chromium navigation
    # timeout we observed on `ewanz.com`-class dead domains. Timeout / other
    # resolver errors fail-open (transient blip is cheaper than dropping a
    # possibly-good URL).
    preflight_dns_check_enabled: bool = Field(
        default=True, alias="AGENTIC_PREFLIGHT_DNS_CHECK_ENABLED"
    )
    preflight_dns_timeout_s: float = Field(
        default=3.0, alias="AGENTIC_PREFLIGHT_DNS_TIMEOUT_S"
    )


@lru_cache(maxsize=1)
def get_agentic_settings() -> AgenticSettings:
    return AgenticSettings()
