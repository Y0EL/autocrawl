"""Multi-source search aggregator.

Tier 1: Wikipedia REST (direct API, free, deterministic).
Tier 2: DuckDuckGo via ddgs (free, rate-limited, fallback).
Tier 3: Region-specific engines (baidu, naver, yahoo_japan) when query hints
        at those regions.
Tier 4: Firecrawl `/search` only when ENABLE_FIRECRAWL=true and budget OK
        (paid, off by default).

Results dedupe by canonical URL, preserve insertion order so tier-1 wins ties.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any, Awaitable

from ...config import get_settings
from ...observability.logger import get_logger
from ...observability.metrics import external_search_total
from ..url_utils import canonical_url
from . import baidu, ddg, google_news_rss, naver, wikipedia, yahoo_japan
from .base import SearchHit
from .region import detect_regions

_log = get_logger(__name__)


async def search_all(query: str, *, per_source_limit: int = 15) -> list[SearchHit]:
    settings = get_settings()

    tasks: dict[str, Awaitable[Any]] = {
        "wikipedia": wikipedia.search(query, max_results=min(per_source_limit, 10)),
        "ddg": ddg.search(query, max_results=per_source_limit),
        "google_news": google_news_rss.search(query, max_results=per_source_limit),
    }

    if settings.enable_firecrawl:
        from ..firecrawl.client import search as firecrawl_search

        tasks["firecrawl"] = firecrawl_search(query, limit=per_source_limit)

    regions = detect_regions(query)
    if "cn" in regions:
        tasks["baidu"] = baidu.search(query, max_results=per_source_limit)
    if "kr" in regions:
        tasks["naver"] = naver.search(query, max_results=per_source_limit)
    if "jp" in regions:
        tasks["yahoo_japan"] = yahoo_japan.search(query, max_results=per_source_limit)

    if regions:
        _log.info("multi_search.regions_detected", query=query, regions=regions, engines=list(tasks.keys()))

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    merged: OrderedDict[str, SearchHit] = OrderedDict()
    for (source, _), result in zip(tasks.items(), results, strict=True):
        if isinstance(result, BaseException):
            external_search_total.labels(provider=source, status="error").inc()
            _log.debug("multi_search.source_failed", source=source, error=str(result))
            continue
        hits: list[SearchHit] = []
        if source == "firecrawl":
            data = result.data if hasattr(result, "data") else None  # type: ignore
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
        else:
            hits = result  # type: ignore[assignment]

        external_search_total.labels(provider=source, status="ok").inc()
        for h in hits:
            if not h.url:
                continue
            key = canonical_url(h.url)
            if key not in merged:
                merged[key] = h
    return list(merged.values())
