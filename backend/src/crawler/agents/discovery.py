"""Discovery agent.

Phase A — Dynamic Seed Generation:
  Use the LLM (gpt-4o-mini) to expand the YAML topic config into 8-15 query
  variations per topic, contextualised with the current year. Dedupe against
  recent run history (kept in Redis).

Phase B — Multi-source Search:
  Run the merged search (Firecrawl + DDG + Wikipedia + Google News RSS) on
  each query in parallel, then ask the LLM (gpt-4o) to extract candidate
  expo entries from the merged hit list. Each entry becomes an `Expo`.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..config import get_seed_topics, get_settings
from ..observability.logger import get_logger
from ..observability.metrics import errors_total, expos_discovered_total
from ..schemas import Expo, ExpoSource
from ..store.redis_queue import get_redis
from ..tools.llm.openai_client import chat
from ..tools.search.base import SearchHit
from ..tools.search.multi import search_all
from ..tools.url_utils import canonical_domain

_log = get_logger(__name__)


class _ExpandedQueries(BaseModel):
    queries: list[str] = Field(default_factory=list)


class _ExpoCandidate(BaseModel):
    name: str
    aggregator_url: str | None = None
    official_url: str | None = None
    location: str | None = None
    country: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class _ExtractedExpos(BaseModel):
    expos: list[_ExpoCandidate] = Field(default_factory=list)


def _slugify(name: str, year: int | None = None) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip().lower()
    s = re.sub(r"\s+", "-", s)
    if year:
        s = f"{year}-{s}" if str(year) not in s else s
    return s[:80]


async def expand_seeds(*, max_per_topic: int = 12) -> list[str]:
    cfg = get_seed_topics()
    topics = cfg.get("topics", [])
    anchors = cfg.get("anchor_expos", [])
    year = datetime.now(timezone.utc).year
    sys = SystemMessage(
        content=(
            "You expand crawl topics into specific search queries to discover "
            "trade-shows / conferences / expos. Output 8-12 highly varied queries "
            "per topic mixing region keywords, year context, exhibitor / floor "
            "plan / agenda terms, and known landmark events. Avoid duplicates.\n\n"
            "IMPORTANT — when the topic includes Asia / China / Japan / Korea / "
            "Russia regions, ALSO produce 2-4 queries written in the local "
            "language/script so we can hit local search engines (Baidu / Yahoo "
            "Japan / Naver / Yandex):\n"
            "  - China  → Simplified Chinese (e.g. 中国国际防务展 2026 参展商)\n"
            "  - Japan  → Japanese (e.g. 防衛装備品展示会 2026 出展者)\n"
            "  - Korea  → Korean (e.g. 서울 ADEX 2026 참가업체)\n"
            "  - Russia → Russian (e.g. Армия 2026 участники выставки)\n"
            "Mix English + local-language queries; do not output just one or "
            "the other for these regions."
        )
    )

    async def _expand_one(topic: dict) -> list[str]:
        user = HumanMessage(
            content=(
                f"Topic: {topic.get('label')}\n"
                f"Keywords: {', '.join(topic.get('keywords', []))}\n"
                f"Regions: {', '.join(topic.get('regions', []))}\n"
                f"Anchor events (positive examples): {', '.join(anchors)}\n"
                f"Year context: {year}\n"
                f"Generate up to {max_per_topic} queries."
            )
        )
        try:
            res = await chat([sys, user], use_heavy=False, response_format=_ExpandedQueries)
            return list(getattr(res, "queries", []))[:max_per_topic]
        except Exception as e:  # noqa: BLE001
            errors_total.labels(stage="discovery", category="seed_expand").inc()
            _log.warning("discovery.seed_expand_failed", topic=topic.get("name"), error=str(e))
            return []

    expansions = await asyncio.gather(*(_expand_one(t) for t in topics))
    flat: list[str] = []
    seen: set[str] = set()
    for batch in expansions:
        for q in batch:
            k = q.strip().lower()
            if k and k not in seen:
                seen.add(k)
                flat.append(q.strip())
    flat = await _filter_recent_history(flat)
    _log.info("discovery.seeds_ready", count=len(flat))
    return flat


async def _filter_recent_history(queries: list[str], *, lookback_runs: int = 30) -> list[str]:
    client = await get_redis()
    if client is None:
        return queries
    key = "discovery:recent_queries"
    try:
        recent = set(await client.smembers(key))
    except Exception:  # noqa: BLE001
        recent = set()
    new = [q for q in queries if q.lower() not in recent]
    try:
        if new:
            await client.sadd(key, *(q.lower() for q in new))
            await client.expire(key, 60 * 60 * 24 * lookback_runs)
    except Exception:  # noqa: BLE001
        pass
    return new


async def _extract_expos_from_hits(query: str, hits: list[SearchHit]) -> list[_ExpoCandidate]:
    if not hits:
        return []
    rendered = "\n".join(f"- [{h.source}] {h.title} :: {h.url}\n    {h.snippet[:240]}" for h in hits[:30])
    sys = SystemMessage(
        content=(
            "From the search snippets below, extract trade-show / conference / "
            "expo entries. Each must be a real event with a name. Set "
            "`aggregator_url` if the URL is on an event-listing site (10times, "
            "eventbrite, tradefairdates, conferenceindex, allconferences, "
            "n-events, expopromoter, eventseye). Set `official_url` if the URL "
            "looks like the event's own site. Skip generic news articles unless "
            "they clearly announce a specific event."
        )
    )
    user = HumanMessage(content=f"Search query: {query}\n\nResults:\n{rendered}")
    try:
        # gpt-4o-mini is plenty for snippet extraction and has 10x higher TPM than gpt-4o
        res = await chat([sys, user], use_heavy=False, response_format=_ExtractedExpos)
        return list(getattr(res, "expos", []))
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="discovery", category="expo_extract").inc()
        _log.warning("discovery.expo_extract_failed", query=query, error=str(e))
        return []


def _candidate_to_expo(c: _ExpoCandidate, query: str) -> Expo | None:
    name = (c.name or "").strip()
    if len(name) < 3:
        return None
    year_match = re.search(r"\b(20\d{2})\b", name) or re.search(r"\b(20\d{2})\b", c.aggregator_url or c.official_url or "")
    year = int(year_match.group(1)) if year_match else None
    expo_id = _slugify(name, year)

    source = ExpoSource.UNKNOWN
    if c.aggregator_url:
        dom = canonical_domain(c.aggregator_url)
        for member in ExpoSource:
            if member.value in dom:
                source = member
                break
        else:
            source = ExpoSource.FIRECRAWL_SEARCH if "firecrawl" in (c.aggregator_url or "") else ExpoSource.UNKNOWN

    try:
        return Expo(
            expo_id=expo_id,
            name=name,
            source=source,
            aggregator_url=c.aggregator_url,
            official_url=c.official_url,
            location=c.location,
            country=c.country,
            discovery_query=query,
        )
    except Exception as e:  # noqa: BLE001
        _log.debug("discovery.expo_construct_failed", error=str(e), name=name)
        return None


async def discover_expos() -> list[Expo]:
    settings = get_settings()
    queries = await expand_seeds()
    if not queries:
        return []

    sem = asyncio.Semaphore(settings.concurrency().expo_discovery)
    seen_ids: set[str] = set()
    out: list[Expo] = []

    async def _per_query(q: str) -> list[Expo]:
        async with sem:
            hits = await search_all(q, per_source_limit=12)
            cands = await _extract_expos_from_hits(q, hits)
            local: list[Expo] = []
            for c in cands:
                exp = _candidate_to_expo(c, q)
                if not exp:
                    continue
                if exp.expo_id in seen_ids:
                    continue
                seen_ids.add(exp.expo_id)
                local.append(exp)
            return local

    batches = await asyncio.gather(*(_per_query(q) for q in queries))
    for b in batches:
        out.extend(b)
        for e in b:
            expos_discovered_total.labels(source=e.source.value).inc()

    if len(out) > settings.max_expos_per_run:
        out = out[: settings.max_expos_per_run]
    _log.info("discovery.done", expos=len(out), queries=len(queries))
    return out
