"""Multi-source search aggregator with 6 tier orchestration.

Strategi: fan out paralel ke setiap provider yang aktif, dedupe by canonical
URL di akhir. Setiap provider tag `source` field unik untuk metrics. Kalau
satu provider down, sisanya tetap kontribusi.

Tier breakdown.

Tier 1 — DDGS legacy + Wikipedia direct + Google News RSS. Always-on.
Tier 2 — Self-hosted meta-search (SearXNG).
Tier 3 — Free APIs with optional key (Tavily, Brave, Bing).
Tier 4 — Niche public APIs (Reddit, HackerNews, GitHub, arXiv, OpenAlex,
         Semantic Scholar, Internet Archive, Wayback CDX).
Tier 5 — OpenSERP container (Google, Bing, Yandex, Baidu via headless).
Tier 6 — Region-specific engines (Baidu, Naver, Yahoo Japan) when query hints.

Hasil tiap provider digabung lewat OrderedDict by `canonical_url(hit.url)`,
preserving insertion order so the higher-tier hits win when there's a tie.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any, Awaitable

from ...config import get_settings
from ...observability.logger import get_logger
from ...observability.metrics import external_search_total
from ..url_utils import canonical_url
from . import (
    arxiv,
    baidu,
    bing,
    brave,
    ddg,
    github_search,
    google_news_rss,
    hackernews,
    internet_archive,
    naver,
    openalex,
    openserp,
    reddit,
    searxng,
    semantic_scholar,
    tavily,
    wayback_cdx,
    wikipedia,
    yahoo_japan,
)
from .base import SearchHit
from .region import detect_regions

_log = get_logger(__name__)


def _build_tasks(query: str, per_source_limit: int) -> dict[str, Awaitable[Any]]:
    """Compose the dict of provider coroutines based on current settings."""
    settings = get_settings()
    tasks: dict[str, Awaitable[Any]] = {}

    # Tier 1 — always-on lightweight sources.
    tasks["wikipedia"] = wikipedia.search(query, max_results=min(per_source_limit, 10))
    tasks["ddg"] = ddg.search(query, max_results=per_source_limit)
    tasks["google_news"] = google_news_rss.search(query, max_results=per_source_limit)

    # Tier 2 — self-hosted meta-search.
    if settings.enable_searxng:
        tasks["searxng"] = searxng.search(query, max_results=per_source_limit * 2)

    # Tier 3 — free-tier APIs with optional key (each module checks its own key).
    if settings.enable_tavily:
        tasks["tavily"] = tavily.search(query, max_results=per_source_limit)
    if settings.enable_brave:
        tasks["brave"] = brave.search(query, max_results=per_source_limit)
    if settings.enable_bing:
        tasks["bing"] = bing.search(query, max_results=per_source_limit)

    # Tier 4 — niche public APIs (each module checks its own enable flag).
    if settings.enable_reddit:
        tasks["reddit"] = reddit.search(query, max_results=per_source_limit)
    if settings.enable_hackernews:
        tasks["hackernews"] = hackernews.search(query, max_results=per_source_limit)
    if settings.enable_github_search:
        tasks["github"] = github_search.search(query, max_results=per_source_limit)
    if settings.enable_arxiv:
        tasks["arxiv"] = arxiv.search(query, max_results=per_source_limit)
    if settings.enable_openalex:
        tasks["openalex"] = openalex.search(query, max_results=per_source_limit)
    if settings.enable_semantic_scholar:
        tasks["semantic_scholar"] = semantic_scholar.search(query, max_results=per_source_limit)
    if settings.enable_internet_archive:
        tasks["internet_archive"] = internet_archive.search(query, max_results=per_source_limit)
    if settings.enable_wayback_cdx:
        tasks["wayback_cdx"] = wayback_cdx.search(query, max_results=per_source_limit)

    # Tier 5 — OpenSERP container (off by default; enable via env when ready).
    if settings.enable_openserp:
        tasks["openserp"] = openserp.search(query, max_results=per_source_limit)

    # Legacy Firecrawl (paid; keep wired but off by default).
    if settings.enable_firecrawl:
        from ..firecrawl.client import search as firecrawl_search

        tasks["firecrawl"] = firecrawl_search(query, limit=per_source_limit)

    # Tier 6 — region-specific engines, conditional on query language hints.
    regions = detect_regions(query)
    if "cn" in regions:
        tasks["baidu"] = baidu.search(query, max_results=per_source_limit)
    if "kr" in regions:
        tasks["naver"] = naver.search(query, max_results=per_source_limit)
    if "jp" in regions:
        tasks["yahoo_japan"] = yahoo_japan.search(query, max_results=per_source_limit)

    if regions:
        _log.info(
            "multi_search.regions_detected",
            query=query[:60],
            regions=regions,
            engines=list(tasks.keys()),
        )

    return tasks


def _coerce_hits(source: str, result: Any) -> list[SearchHit]:
    """Normalize per-provider responses into a list[SearchHit]."""
    if source == "firecrawl":
        # firecrawl returns a custom response object with `.data`.
        data = result.data if hasattr(result, "data") else None
        hits: list[SearchHit] = []
        if data:
            for r in (data.get("results") or data.get("data") or []):
                if isinstance(r, dict):
                    hits.append(
                        SearchHit(
                            title=r.get("title", "") or "",
                            url=r.get("url", "") or r.get("link", "") or "",
                            snippet=r.get("description", "") or r.get("snippet", "") or "",
                            source="firecrawl",
                        )
                    )
        return hits
    # Every other provider already returns list[SearchHit].
    if isinstance(result, list):
        return result
    return []


async def search_all(query: str, *, per_source_limit: int = 15) -> list[SearchHit]:
    tasks = _build_tasks(query, per_source_limit)
    if not tasks:
        return []

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    merged: OrderedDict[str, SearchHit] = OrderedDict()
    per_source_counts: dict[str, int] = {}
    for (source, _), result in zip(tasks.items(), results, strict=True):
        if isinstance(result, BaseException):
            external_search_total.labels(provider=source, status="error").inc()
            _log.debug("multi_search.source_failed", source=source, error=str(result)[:200])
            continue
        hits = _coerce_hits(source, result)
        external_search_total.labels(provider=source, status="ok").inc()
        per_source_counts[source] = len(hits)
        for h in hits:
            if not h.url:
                continue
            key = canonical_url(h.url)
            if key not in merged:
                merged[key] = h

    _log.info(
        "multi_search.tier_complete",
        query=query[:60],
        total_unique=len(merged),
        per_source=per_source_counts,
    )
    return list(merged.values())
