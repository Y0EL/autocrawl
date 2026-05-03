"""Wikipedia REST API search. Free, no key. Useful for landmark expos."""

from __future__ import annotations

import httpx

from ...config import get_settings
from ...observability.logger import get_logger
from ...observability.metrics import errors_total
from .base import SearchHit

_log = get_logger(__name__)
_API = "https://en.wikipedia.org/w/rest.php/v1/search/page"


async def search(query: str, *, max_results: int = 10) -> list[SearchHit]:
    timeout = get_settings().global_request_timeout_seconds
    params = {"q": query, "limit": max_results}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                _API,
                params=params,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AutoCrawl/0.1; +https://example.com/bot)",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 403:
                _log.debug("wikipedia.forbidden", query=query)
                return []
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="search", category="wikipedia").inc()
        _log.warning("wikipedia.search_failed", query=query, error=str(e))
        return []

    out: list[SearchHit] = []
    for page in data.get("pages", []):
        slug = page.get("key") or page.get("title", "").replace(" ", "_")
        out.append(
            SearchHit(
                title=page.get("title", "") or "",
                url=f"https://en.wikipedia.org/wiki/{slug}",
                snippet=page.get("excerpt", "") or page.get("description", "") or "",
                source="wikipedia",
            )
        )
    return out
