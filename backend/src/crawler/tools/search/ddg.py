"""DuckDuckGo search via the `ddgs` lib. Free, no key."""

from __future__ import annotations

import asyncio

from ...observability.logger import get_logger
from ...observability.metrics import errors_total
from .base import SearchHit

_log = get_logger(__name__)


async def search(query: str, *, max_results: int = 20, region: str = "wt-wt") -> list[SearchHit]:
    def _run() -> list[SearchHit]:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore  # legacy name

        out: list[SearchHit] = []
        try:
            with DDGS() as ddg:
                for r in ddg.text(query, region=region, safesearch="moderate", max_results=max_results):
                    out.append(
                        SearchHit(
                            title=r.get("title", "") or "",
                            url=r.get("href", "") or r.get("url", "") or "",
                            snippet=r.get("body", "") or "",
                            source="duckduckgo",
                        )
                    )
        except Exception as e:  # noqa: BLE001
            errors_total.labels(stage="search", category="ddg").inc()
            _log.warning("ddg.search_failed", query=query, error=str(e))
        return out

    return await asyncio.to_thread(_run)
