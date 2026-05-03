"""PDF Finder — discover PDF brochure URLs for a given Expo.

Combines four strategies:
  1. Scrape <a href="*.pdf"> from aggregator/official URL
  2. Targeted multi-source search: '"<expo>" filetype:pdf'
  3. Firecrawl /search with brochure-oriented query
  4. Plus any URLs already attached on `expo.pdf_brochure_urls`

Returns a deduped, capped list of PDF URLs.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from ..config import get_settings
from ..observability.logger import get_logger
from ..observability.metrics import errors_total
from ..schemas import Expo
from ..tools.url_utils import canonical_url

_log = get_logger(__name__)


def _is_pdf_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(".pdf"):
        return True
    if ".pdf?" in url.lower() or ".pdf#" in url.lower():
        return True
    return False


async def _scrape_pdf_links_from_page(page_url: str) -> list[str]:
    from ..tools.browsers.fetcher import fetch
    from ..tools.parsers.html_parser import all_links

    try:
        page = await fetch(page_url, force_render=False)
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="pdf_finder", category="scrape").inc()
        _log.debug("pdf_finder.scrape_failed", url=page_url, error=str(e))
        return []
    html = page.get("html", "")
    if not html:
        return []
    links = all_links(html, base_url=page.get("url") or page_url)
    return [canonical_url(link["href"]) for link in links if _is_pdf_url(link["href"])]


async def _targeted_search_pdf(expo_name: str, *, per_source: int = 6) -> list[str]:
    from ..tools.search.multi import search_all

    queries = [
        f'"{expo_name}" exhibitor list filetype:pdf',
        f'"{expo_name}" brochure filetype:pdf',
        f'"{expo_name}" floor plan filetype:pdf',
    ]
    found: set[str] = set()
    for q in queries:
        try:
            hits = await search_all(q, per_source_limit=per_source)
        except Exception as e:  # noqa: BLE001
            errors_total.labels(stage="pdf_finder", category="search").inc()
            _log.debug("pdf_finder.search_failed", query=q, error=str(e))
            continue
        for h in hits:
            if _is_pdf_url(h.url):
                found.add(canonical_url(h.url))
    return sorted(found)


async def _firecrawl_pdf_search(expo_name: str) -> list[str]:
    from ..tools.firecrawl.client import search as firecrawl_search

    found: set[str] = set()
    try:
        result = await firecrawl_search(f"{expo_name} exhibitor brochure PDF", limit=5)
    except Exception:  # noqa: BLE001
        return []
    if not result.success or not result.data:
        return []
    items = result.data.get("results") or result.data.get("data") or []
    for item in items:
        if isinstance(item, dict):
            url = item.get("url") or item.get("link") or ""
            if _is_pdf_url(url):
                found.add(canonical_url(url))
    return sorted(found)


async def find_pdfs_for_expo(expo: Expo) -> list[str]:
    settings = get_settings()
    if not settings.pdf_discovery_enabled:
        return []

    tasks: list = [_targeted_search_pdf(expo.name), _firecrawl_pdf_search(expo.name)]
    if expo.aggregator_url:
        tasks.append(_scrape_pdf_links_from_page(str(expo.aggregator_url)))
    if expo.official_url:
        tasks.append(_scrape_pdf_links_from_page(str(expo.official_url)))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    found: set[str] = set(expo.pdf_brochure_urls or [])
    for r in results:
        if isinstance(r, list):
            found.update(r)

    # Cap and stable sort
    capped = sorted(found)[: settings.max_pdfs_per_expo]
    if capped:
        _log.info("pdf_finder.discovered", expo_id=expo.expo_id, count=len(capped))
    return capped
