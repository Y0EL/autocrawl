"""LangGraph state-machine wiring with parallel Send fan-out.

Top-level flow:
  start → discover_expos
        → fan_out(extract_exhibitors)        [parallel up to extraction concurrency]
        → fan_out(resolve_vendor_url)        [parallel up to resolution concurrency]
        → fan_out(dedup_then_enrich_then_persist)  [parallel up to enrichment concurrency]
        → finalize_report
        → END

Each fan-out is implemented with `langgraph.types.Send` against a worker
node that processes ONE item at a time. asyncio.Semaphore inside the worker
node enforces the concurrency cap.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from .agents import dedup as dedup_agent
from .agents import discovery as discovery_agent
from .agents import enricher as enricher_agent
from .agents import extractor as extractor_agent
from .agents import name_resolver as name_resolver_agent
from .agents import pdf_finder as pdf_finder_agent
from .agents import reporter as reporter_agent
from .agents import resolver as resolver_agent
from .config import get_settings
from .observability.logger import get_logger
from .observability.metrics import (
    active_workers,
    errors_total,
)
from .schemas import (
    CrawlMode,
    ExhibitorRef,
    Expo,
    FailureRecord,
    RunSummary,
    Vendor,
    VendorURL,
)
from .state import (
    CrawlState,
    WorkerExhibitorState,
    WorkerExpoState,
    WorkerVendorState,
)
from .store.json_reporter import write_run_summary

_log = get_logger(__name__)


# =====================================================================
# Sub-agent worker nodes (process ONE item, return partial state)
# =====================================================================


async def _worker_extract(state: WorkerExpoState) -> dict:
    settings = get_settings()
    sem = _stage_sem("extraction", settings.concurrency().exhibitor_extraction)
    expo: Expo = state["expo"]
    active_workers.labels(stage="extraction").inc()
    try:
        async with sem:
            refs = await extractor_agent.extract_exhibitors(expo)
            return {"pending_exhibitors": refs}
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="extraction", category=type(e).__name__).inc()
        _log.warning("worker_extract.error", expo_id=expo.expo_id, error=str(e))
        return {
            "failures": [FailureRecord(where="extraction", error=str(e), url=str(expo.aggregator_url))]
        }
    finally:
        active_workers.labels(stage="extraction").dec()


async def _worker_resolve(state: WorkerExhibitorState) -> dict:
    settings = get_settings()
    sem = _stage_sem("resolution", settings.concurrency().vendor_resolution)
    ref: ExhibitorRef = state["exhibitor"]
    active_workers.labels(stage="resolution").inc()
    try:
        async with sem:
            if ref.raw_url:
                v = await resolver_agent.resolve_vendor_url(ref)
            else:
                # PDF-sourced ref: name-only resolver
                v = await name_resolver_agent.resolve_from_name(
                    ref.name,
                    expo_id=ref.expo_id,
                    context_snippet=ref.short_description,
                )
            if v is None:
                return {}
            # Carry PDF (or aggregator) provenance forward into the VendorURL
            if ref.provenance:
                v.provenance = list(ref.provenance) + list(v.provenance or [])
            return {"resolved_vendors": [v]}
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="resolution", category=type(e).__name__).inc()
        _log.warning("worker_resolve.error", exhibitor=ref.name, error=str(e))
        return {"failures": [FailureRecord(where="resolution", error=str(e), url=str(ref.raw_url) if ref.raw_url else None)]}
    finally:
        active_workers.labels(stage="resolution").dec()


async def _worker_pdf_extract(state: WorkerExpoState) -> dict:
    """Per-expo PDF discovery + extraction. Runs in parallel to _worker_extract."""
    settings = get_settings()
    if not settings.pdf_discovery_enabled:
        return {}
    sem = _stage_sem("pdf_extraction", settings.pdf_extraction_concurrency)
    expo: Expo = state["expo"]
    active_workers.labels(stage="pdf_extraction").inc()
    try:
        async with sem:
            from .tools.scrapers import pdf_extractor as pdf_extractor_mod

            pdf_urls = await pdf_finder_agent.find_pdfs_for_expo(expo)
            if not pdf_urls:
                return {}
            expo.pdf_brochure_urls = pdf_urls

            refs: list[ExhibitorRef] = []
            for pdf_url in pdf_urls:
                try:
                    refs.extend(await pdf_extractor_mod.list_exhibitors(pdf_url, expo.expo_id))
                except Exception as e:  # noqa: BLE001
                    errors_total.labels(stage="pdf_extraction", category=type(e).__name__).inc()
                    _log.warning("worker_pdf_extract.pdf_failed", expo_id=expo.expo_id, pdf=pdf_url, error=str(e))
            return {"pending_exhibitors": refs}
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="pdf_extraction", category=type(e).__name__).inc()
        _log.warning("worker_pdf_extract.error", expo_id=expo.expo_id, error=str(e))
        return {"failures": [FailureRecord(where="pdf_extraction", error=str(e))]}
    finally:
        active_workers.labels(stage="pdf_extraction").dec()


async def _worker_enrich(state: WorkerVendorState) -> dict:
    settings = get_settings()
    sem = _stage_sem("enrichment", settings.concurrency().enrichment)
    vurl: VendorURL = state["vendor_url"]
    active_workers.labels(stage="enrichment").inc()
    try:
        async with sem:
            is_dup = await dedup_agent.check_and_merge(vurl)
            if is_dup:
                await reporter_agent.merge_existing_with_expo(vurl.domain, vurl.expo_id)
                return {"dedup_skipped_count": 1}
            v: Vendor | None = await enricher_agent.enrich_vendor(vurl)
            if v is None:
                return {"failures": [FailureRecord(where="enrichment", error="no_profile", url=str(vurl.canonical_url))]}
            persisted = await reporter_agent.persist_vendor(v)
            if persisted:
                return {"enriched_vendors": [v]}
            return {"failures": [FailureRecord(where="reporter", error="rejected_by_validator", url=str(vurl.canonical_url))]}
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="enrichment", category=type(e).__name__).inc()
        _log.warning("worker_enrich.error", domain=vurl.domain, error=str(e))
        return {"failures": [FailureRecord(where="enrichment", error=str(e), url=str(vurl.canonical_url))]}
    finally:
        active_workers.labels(stage="enrichment").dec()


# =====================================================================
# Supervisor nodes (sequential, fan-out to workers)
# =====================================================================


async def _node_discover(state: CrawlState) -> dict:
    expos = await discovery_agent.discover_expos()
    _log.info("graph.discover_done", count=len(expos))
    return {"discovered_expos": expos, "expos_count": len(expos)}


def _route_to_extract(state: CrawlState) -> list[Send]:
    """Fan out per expo to BOTH aggregator scraper and PDF extractor."""
    settings = get_settings()
    expos = state.get("discovered_expos") or []
    sends: list[Send] = []
    for e in expos:
        sends.append(Send("worker_extract", {"run_id": state["run_id"], "expo": e}))
        if settings.pdf_discovery_enabled:
            sends.append(Send("worker_pdf_extract", {"run_id": state["run_id"], "expo": e}))
    return sends


def _route_to_resolve(state: CrawlState) -> list[Send]:
    pending = state.get("pending_exhibitors") or []
    return [
        Send("worker_resolve", {"run_id": state["run_id"], "exhibitor": ref})
        for ref in pending
    ]


def _route_to_enrich(state: CrawlState) -> list[Send]:
    settings = get_settings()
    vendors = state.get("resolved_vendors") or []
    if len(vendors) > settings.max_vendors_per_run:
        vendors = vendors[: settings.max_vendors_per_run]
    return [
        Send("worker_enrich", {"run_id": state["run_id"], "vendor_url": v})
        for v in vendors
    ]


async def _node_finalize(state: CrawlState) -> dict:
    run_id = state["run_id"]
    expos = state.get("discovered_expos") or []
    enriched: list[Vendor] = state.get("enriched_vendors") or []

    # group enriched vendor domains by expo
    by_expo: dict[str, list[str]] = {}
    for v in enriched:
        for ex in v.expos_seen or []:
            by_expo.setdefault(ex, []).append(v.domain)

    for e in expos:
        await reporter_agent.persist_expo(e, by_expo.get(e.expo_id, []))

    summary = RunSummary(
        run_id=run_id,
        started_at=state.get("__started_at__") or datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        mode=state.get("mode") or CrawlMode.NORMAL,
        expos_discovered=state.get("expos_count") or 0,
        exhibitors_extracted=len(state.get("pending_exhibitors") or []),
        vendors_resolved=len(state.get("resolved_vendors") or []),
        vendors_enriched=len(enriched),
        vendors_dedup_skipped=state.get("dedup_skipped_count") or 0,
        failures=len(state.get("failures") or []),
    )
    await write_run_summary(summary)
    _log.info(
        "graph.finalize",
        run_id=run_id,
        expos=summary.expos_discovered,
        exhibitors=summary.exhibitors_extracted,
        resolved=summary.vendors_resolved,
        enriched=summary.vendors_enriched,
        dedup_skipped=summary.vendors_dedup_skipped,
        failures=summary.failures,
    )
    return {}


# =====================================================================
# Concurrency caps (singletons per stage)
# =====================================================================

_SEMS: dict[str, asyncio.Semaphore] = {}


def _stage_sem(stage: str, cap: int) -> asyncio.Semaphore:
    sem = _SEMS.get(stage)
    if sem is None:
        sem = asyncio.Semaphore(cap)
        _SEMS[stage] = sem
    return sem


# =====================================================================
# Graph builder
# =====================================================================


def build_graph():
    g = StateGraph(CrawlState)

    g.add_node("discover", _node_discover)
    g.add_node("worker_extract", _worker_extract)
    g.add_node("worker_pdf_extract", _worker_pdf_extract)
    g.add_node("worker_resolve", _worker_resolve)
    g.add_node("worker_enrich", _worker_enrich)
    g.add_node("finalize", _node_finalize)

    g.set_entry_point("discover")
    g.add_conditional_edges("discover", _route_to_extract, ["worker_extract", "worker_pdf_extract"])
    g.add_conditional_edges("worker_extract", _route_to_resolve, ["worker_resolve"])
    g.add_conditional_edges("worker_pdf_extract", _route_to_resolve, ["worker_resolve"])
    g.add_conditional_edges("worker_resolve", _route_to_enrich, ["worker_enrich"])
    g.add_edge("worker_enrich", "finalize")
    g.add_edge("finalize", END)

    return g


async def run_once(*, mode: CrawlMode | None = None) -> RunSummary:
    """Single end-to-end run. Returns the run summary."""
    settings = get_settings()
    selected_mode = mode or settings.mode
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

    # Pre-warm the LLM (no-op for OpenAI; loads Ollama models into VRAM).
    from .tools.llm.openai_client import warmup as llm_warmup

    try:
        await llm_warmup()
    except Exception as e:  # noqa: BLE001
        _log.warning("graph.warmup_failed", error=str(e))

    init_state: CrawlState = {
        "run_id": run_id,
        "mode": selected_mode,
        "seed_queries": [],
        "discovered_expos": [],
        "pending_exhibitors": [],
        "resolved_vendors": [],
        "enriched_vendors": [],
        "failures": [],
        "expos_count": 0,
        "exhibitors_count": 0,
        "vendors_resolved_count": 0,
        "vendors_enriched_count": 0,
        "dedup_skipped_count": 0,
        "firecrawl_budget_low": False,
        "phase_2_unlocked": False,
    }

    graph = build_graph()
    # No checkpointer: Pydantic state isn't msgpack-serializable, and we
    # don't need crash-resume mid-run (JSON reports give us persistence).
    compiled = graph.compile()

    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 200}
    result = await compiled.ainvoke(init_state, config=config)

    return RunSummary(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        mode=selected_mode,
        expos_discovered=len(result.get("discovered_expos") or []),
        exhibitors_extracted=len(result.get("pending_exhibitors") or []),
        vendors_resolved=len(result.get("resolved_vendors") or []),
        vendors_enriched=len(result.get("enriched_vendors") or []),
        vendors_dedup_skipped=result.get("dedup_skipped_count") or 0,
        failures=len(result.get("failures") or []),
    )
