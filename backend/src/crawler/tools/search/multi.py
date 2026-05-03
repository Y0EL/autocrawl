"""Multi-source search aggregator.

Fans out to all free search sources + Firecrawl /search (key-gated, quota-aware)
in parallel, dedupes by canonical URL, and returns merged hits ordered by
source priority and recency. Region-aware: queries hinting at China/Japan/
Korea/Russia also hit the relevant local engine (Baidu / Yahoo Japan / Naver /
Yandex-via-ddgs).
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict

from ...observability.logger import get_logger
from ..firecrawl.client import search as firecrawl_search
from ..url_utils import canonical_url
from . import baidu, ddg, google_news_rss, naver, wikipedia, yahoo_japan
from .base import SearchHit
from .region import detect_regions

_log = get_logger(__name__)


async def search_all(query: str, *, per_source_limit: int = 15) -> list[SearchHit]:
    tasks: dict[str, "asyncio.Future | asyncio.Task | object"] = {
        "firecrawl": firecrawl_search(query, limit=per_source_limit),
        "ddg": ddg.search(query, max_results=per_source_limit),  # ddgs internally hits Yandex too
        "google_news": google_news_rss.search(query, max_results=per_source_limit),
        "wikipedia": wikipedia.search(query, max_results=min(per_source_limit, 10)),
    }

    regions = detect_regions(query)
    if "cn" in regions:
        tasks["baidu"] = baidu.search(query, max_results=per_source_limit)
    if "kr" in regions:
        tasks["naver"] = naver.search(query, max_results=per_source_limit)
    if "jp" in regions:
        tasks["yahoo_japan"] = yahoo_japan.search(query, max_results=per_source_limit)
    # Russian queries — ddg already proxies to Yandex; nothing extra needed.

    if regions:
        _log.info("multi_search.regions_detected", query=query, regions=regions, engines=list(tasks.keys()))

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    merged: OrderedDict[str, SearchHit] = OrderedDict()
    for (source, _), result in zip(tasks.items(), results, strict=True):
        if isinstance(result, BaseException):
            _log.debug("multi_search.source_failed", source=source, error=str(result))
            continue
        hits: list[SearchHit] = []
        if source == "firecrawl":
            # FirecrawlResult shape
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

        for h in hits:
            if not h.url:
                continue
            key = canonical_url(h.url)
            if key not in merged:
                merged[key] = h
    return list(merged.values())
