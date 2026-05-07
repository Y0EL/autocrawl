"""Enrich-pool worker loop.

Why we deliberately don't gate on a hardcoded `must-have-{email,address}`
schema:

  * Phone-only vendors (very common in Asia) get unfairly rejected by an
    "email-required" gate.
  * Wix landing pages with one stale `info@` token email pass an "email-
    required" gate even though they're formality.
  * Both are wrong on opposite ends. A schema gate doesn't capture
    "complete enough to keep" in any robust way.

Self-learning replaces it: the agent's system prompt includes 2-3 success
exemplars and 1-2 formality exemplars (rendered by `enrich_lessons`). The
agent emits a `completeness_score` (0.0-1.0) and an optional `bail_reason`
(`formality | 404 | captcha | image_only`). The worker uses these directly
— no hardcoded thresholds — and lets the operator recalibrate by editing
exemplars in `data/agentic_enrich_lessons/{success,failure}/`.

Concurrency model:
- N parallel async tasks per process (`agentic_enrich_parallel`).
- Each pulls 1 entry per loop via XREADGROUP with block_ms=5000 — no busy
  spin, no thundering herd.
- Per-task `claim()` SET-NX guards against double-delivery (e.g. when
  XAUTOCLAIM redelivers after a crash).
- `acquire_llm_slot("vision")` from Phase 2 caps simultaneous Ollama
  vision calls cluster-wide so the listing pool can't be starved.
"""

from __future__ import annotations

import asyncio
import os
import socket
from typing import Any

from crawler.observability.logger import get_logger
from crawler.observability.metrics import (
    agentic_enrich_inflight,
    agentic_enrich_outcomes_total,
)
from crawler.store.redis_queue import claim, release

from . import enrich_queue
from .config import get_agentic_settings
from .enrich_agent import run_enrich_for_task
from .enrich_lessons import invalidate_cache as _invalidate_few_shot_cache
from .enrich_queue import EnrichTask
from .lessons import archive_lesson, categorize_failure

_log = get_logger(__name__)

_SHUTDOWN = asyncio.Event()


def _consumer_id(idx: int) -> str:
    """Stable per-task consumer id so Redis can attribute PEL ownership."""
    host = socket.gethostname()[:24]
    return f"{host}-{os.getpid()}-{idx}"


async def _archive_outcome(
    task: EnrichTask,
    result: Any,
    *,
    status: str,
    failure_category: str | None = None,
    failure_detail: str | None = None,
) -> None:
    """Write the lesson + invalidate the few-shot cache so the next task
    sees fresh exemplars. `result` is an EnrichResult; archive_lesson
    treats it duck-typed (uses .exhibitors, .bail_reason_value via attr)."""
    s = get_agentic_settings()
    # archive_lesson expects `seed.url` and `seed.name`. Build a minimal
    # shim so we don't need to refactor `lessons.py`.

    class _SeedShim:
        def __init__(self, t: EnrichTask) -> None:
            self.name = t.vendor_name
            self.url = t.hint_url or ""
            self.expo_id = t.expo_id
            self.tags = ["agentic_enrich"]
            self.source_query = t.source_query

    seed_shim = _SeedShim(task)
    try:
        await archive_lesson(
            seed=seed_shim,
            agent_result=result,
            elapsed_s=getattr(result, "elapsed_s", 0.0),
            raw_steps=getattr(result, "raw_steps", []) or [],
            status=status,
            failure_category=failure_category,
            failure_detail=failure_detail,
            archive_recordings=False,  # enrich recordings live elsewhere
            lessons_dir=s.enrich_lessons_dir,
        )
    except Exception as e:  # noqa: BLE001
        _log.warning("enrich_worker.archive_failed", error=str(e)[:200])
    _invalidate_few_shot_cache()


_PREWARMED_SESSIONS: dict[int, Any] = {}


async def _persist_unresolved_fallback(task: EnrichTask, category: str) -> None:
    """When enrich agent fails (parse_failed / formality / Browser-Use bug
    / etc.) persist the listing-provided ref data anyway. Frontend gets
    the row with name + country + product hint — operator can deepen
    later via the API.
    """
    try:
        from crawler.agents import reporter as reporter_agent
        from crawler.schemas import ExhibitorRef

        # Country hint goes into short_description so it surfaces in the
        # frontend row (ExhibitorRef has no country field).
        desc_parts = [task.product_hint, task.country_hint]
        desc = " | ".join(p for p in desc_parts if p) or None
        ref = ExhibitorRef(
            expo_id=task.expo_id or "",
            name=task.vendor_name,
            raw_url=task.hint_url,
            aggregator_domain=None,
            short_description=desc,
            booth=None,
        )
        ok = await reporter_agent.persist_unresolved_vendor(
            ref, failure_category=f"enrich_{category}"
        )
        _log.info(
            "enrich_worker.fallback_unresolved_persisted",
            vendor=task.vendor_name[:80],
            category=category,
            persisted=ok,
        )
    except Exception as _e:  # noqa: BLE001
        _log.warning(
            "enrich_worker.fallback_persist_failed",
            vendor=task.vendor_name[:80],
            error=str(_e)[:200],
        )


async def _process_one(
    consumer_id: str,
    entry_id: str,
    task: EnrichTask,
    *,
    consumer_idx: int = 0,
) -> None:
    """Run one task end-to-end: claim → agent → dedup → persist → ack."""
    s = get_agentic_settings()
    # Idempotency guard. If a redelivery (XAUTOCLAIM) of an already-handled
    # task slips through, the second worker sees the claim and skips.
    if not await claim(task.task_id, ttl_seconds=3600):
        _log.info(
            "enrich_worker.task_already_claimed",
            vendor=task.vendor_name[:80], task_id=task.task_id,
        )
        try:
            await enrich_queue.ack(entry_id)
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        agentic_enrich_inflight.labels(worker_id=consumer_id).inc()
    except Exception:  # noqa: BLE001
        pass

    _log.info(
        "enrich_worker.task_started",
        vendor=task.vendor_name[:80], expo_id=task.expo_id,
        consumer=consumer_id,
    )

    try:
        prewarmed = _PREWARMED_SESSIONS.get(consumer_idx)
        result = await run_enrich_for_task(task, prewarmed_session=prewarmed)

        # Outcome routing — purely from agent self-judgment, no gate.
        if result.bail_reason and not result.vendor:
            cat = (
                "formality" if result.bail_reason == "formality"
                else result.bail_reason
            )
            await _archive_outcome(
                task, result,
                status="failure", failure_category=cat,
                failure_detail=result.error,
            )
            try:
                agentic_enrich_outcomes_total.labels(status=cat).inc()
            except Exception:  # noqa: BLE001
                pass
            # Fallback persist with what listing pool already gave us
            # (name + country + product hint). Same as the vendor=None
            # branch below — even a bailed enrich shouldn't lose the
            # listing-provided ref. Operator can manually deepen via
            # /vendors/{id}/deepen later.
            await _persist_unresolved_fallback(task, cat)
            return

        if result.vendor is None:
            # No bail but no vendor either — parse fail, schema invalid, etc.
            cat = result.bail_reason or "empty_result"
            await _archive_outcome(
                task, result,
                status="failure", failure_category=cat,
                failure_detail=result.error,
            )
            try:
                agentic_enrich_outcomes_total.labels(status="error").inc()
            except Exception:  # noqa: BLE001
                pass
            await _persist_unresolved_fallback(task, cat)
            return

        # Chroma vendor dedup before persist — same gate the deterministic
        # path runs. We synthesise a minimal VendorURL for the dedup call.
        from crawler.agents import dedup as dedup_agent
        from crawler.agents import reporter as reporter_agent
        from crawler.schemas import VendorURL

        v = result.vendor
        vurl: Any = None
        if v.domain and v.canonical_url:
            try:
                vurl = VendorURL(
                    canonical_url=str(v.canonical_url),
                    domain=v.domain,
                    expo_id=task.expo_id,
                    exhibitor_name=task.vendor_name,
                    resolved_from=task.hint_url,
                )
            except Exception as e:  # noqa: BLE001
                _log.debug("enrich_worker.vendor_url_build_failed", error=str(e)[:120])
                vurl = None

        if vurl is not None:
            try:
                is_dup = await dedup_agent.check_and_merge(vurl)
            except Exception as e:  # noqa: BLE001
                _log.debug("enrich_worker.dedup_failed", error=str(e)[:120])
                is_dup = False
            if is_dup:
                try:
                    await reporter_agent.merge_existing_with_expo(v.domain, task.expo_id)
                except Exception:  # noqa: BLE001
                    pass
                await _archive_outcome(
                    task, result,
                    status="failure", failure_category="dedup_skipped",
                    failure_detail=f"vendor {v.domain} already in store",
                )
                try:
                    agentic_enrich_outcomes_total.labels(status="dedup_skipped").inc()
                except Exception:  # noqa: BLE001
                    pass
                return

        # Phase 3.x: translate description/tagline/products EN → ID via the
        # already-loaded vision LLM. Reuses Ollama compute, no extra VRAM.
        # Idempotent + fail-soft: errors leave English text intact.
        try:
            from .translator import translate_vendor_inplace

            await translate_vendor_inplace(v)
        except Exception as _e:  # noqa: BLE001
            _log.debug("enrich_worker.translate_skipped", error=str(_e)[:120])

        try:
            persisted, reject_cat = await reporter_agent.persist_vendor(v)
        except Exception as e:  # noqa: BLE001
            _log.warning("enrich_worker.persist_failed", error=str(e)[:200])
            await _archive_outcome(
                task, result,
                status="failure", failure_category="persist_error",
                failure_detail=str(e)[:300],
            )
            try:
                agentic_enrich_outcomes_total.labels(status="error").inc()
            except Exception:  # noqa: BLE001
                pass
            return

        if persisted:
            await _archive_outcome(task, result, status="success")
            try:
                agentic_enrich_outcomes_total.labels(status="success").inc()
            except Exception:  # noqa: BLE001
                pass
            _log.info(
                "enrich_worker.task_persisted",
                vendor=task.vendor_name[:80],
                domain=v.domain,
                completeness=result.completeness_score,
            )
        else:
            cat = reject_cat or "rejected"
            await _archive_outcome(
                task, result,
                status="failure", failure_category=cat,
            )
            try:
                agentic_enrich_outcomes_total.labels(status=cat).inc()
            except Exception:  # noqa: BLE001
                pass

    except Exception as e:  # noqa: BLE001
        # Defensive — anything not caught downstream lands here so the
        # worker stays up and the entry gets ack'd (XAUTOCLAIM would
        # redeliver in 5 minutes; better to record a lesson + move on).
        _log.warning(
            "enrich_worker.task_unhandled_error",
            vendor=task.vendor_name[:80], error=str(e)[:200],
        )
        try:
            await _archive_outcome(
                task,
                _MinimalErrorResult(task, str(e)),
                status="failure",
                failure_category=categorize_failure(str(e)),
                failure_detail=str(e)[:300],
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            agentic_enrich_outcomes_total.labels(status="error").inc()
        except Exception:  # noqa: BLE001
            pass
    finally:
        try:
            agentic_enrich_inflight.labels(worker_id=consumer_id).dec()
        except Exception:  # noqa: BLE001
            pass
        # ALWAYS XACK — at-least-once is enough; we have idempotency via claim().
        try:
            await enrich_queue.ack(entry_id)
        except Exception as e:  # noqa: BLE001
            _log.debug("enrich_worker.ack_failed", error=str(e)[:120])
        # Release the per-task SET-NX claim so a fresh re-encounter (e.g.
        # next pass, different run_date) isn't blocked by yesterday's claim.
        try:
            await release(task.task_id)
        except Exception:  # noqa: BLE001
            pass


class _MinimalErrorResult:
    """Stand-in for EnrichResult when the worker itself blew up before
    `run_enrich_for_task` returned. Just enough surface for archive_lesson."""

    def __init__(self, task: EnrichTask, err: str) -> None:
        self.task = task
        self.vendor = None
        self.completeness_score = 0.0
        self.bail_reason = None
        self.elapsed_s = 0.0
        self.n_steps = None
        self.raw_steps = []
        self.final_url = None
        self.error = err
        self.exhibitors = []
        self.expo_id = task.expo_id
        self.seed_name = task.vendor_name


async def _consumer_loop(idx: int) -> None:
    """One long-running consumer task. Pulls + processes one entry at a
    time per loop iteration; the surrounding `gather` provides parallelism."""
    consumer_id = _consumer_id(idx)
    _log.info("enrich_worker.consumer_started", consumer=consumer_id, idx=idx)
    while not _SHUTDOWN.is_set():
        try:
            entries = await enrich_queue.pull(consumer_id, count=1, block_ms=5000)
        except Exception as e:  # noqa: BLE001
            _log.warning("enrich_worker.pull_failed", error=str(e)[:200])
            await asyncio.sleep(2.0)
            continue
        for entry_id, task in entries:
            if _SHUTDOWN.is_set():
                break
            await _process_one(consumer_id, entry_id, task, consumer_idx=idx)
    _log.info("enrich_worker.consumer_stopped", consumer=consumer_id)


async def _reclaim_loop() -> None:
    """Periodic XAUTOCLAIM so PEL entries from crashed workers get re-
    delivered instead of stranding forever."""
    s = get_agentic_settings()
    reclaim_consumer = _consumer_id(0)  # any consumer can claim; pick #0
    idle_ms = s.enrich_pel_reclaim_idle_seconds * 1000
    while not _SHUTDOWN.is_set():
        try:
            entries = await enrich_queue.claim_pending_idle(reclaim_consumer, idle_ms)
            for entry_id, task in entries:
                # Just process it on the reclaiming worker. Keep it simple
                # — don't re-publish; XAUTOCLAIM already moved ownership.
                await _process_one(reclaim_consumer, entry_id, task, consumer_idx=0)
        except Exception as e:  # noqa: BLE001
            _log.debug("enrich_worker.reclaim_loop_failed", error=str(e)[:160])
        try:
            await asyncio.wait_for(_SHUTDOWN.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            pass


async def _prewarm_sessions(n: int) -> None:
    """Spawn N persistent BrowserSessions at worker startup so each consumer
    has a ready Chromium to reuse across tasks. Tab stays open in noVNC
    even when queue is idle — operator gets continuous visual presence
    of the enrich pool."""
    s = get_agentic_settings()
    if s.headless:
        # No display, no point pre-warming.
        return
    if not s.agentic_enrich_prewarm:
        # Default OFF — shared session was a cascading-failure footgun.
        _log.info("enrich_worker.prewarm_disabled", reason="agentic_enrich_prewarm=false")
        return
    if not s.agentic_persistent_profiles:
        # Without persistent profiles each session uses a tmp dir; reuse
        # is still valuable for visibility but operator may prefer fresh
        # sessions. Skip pre-warm to preserve original behavior.
        return
    try:
        from .enrich_agent import build_prewarmed_session
    except Exception as e:  # noqa: BLE001
        _log.debug("enrich_worker.prewarm_import_failed", error=str(e)[:120])
        return

    for i in range(n):
        try:
            session = await build_prewarmed_session(i)
            if session is not None:
                _PREWARMED_SESSIONS[i] = session
                _log.info("enrich_worker.session_prewarmed", slot=i)
        except Exception as e:  # noqa: BLE001
            _log.warning(
                "enrich_worker.prewarm_session_failed",
                slot=i, error=str(e)[:160],
            )


async def _shutdown_prewarmed_sessions() -> None:
    for slot, session in list(_PREWARMED_SESSIONS.items()):
        try:
            if hasattr(session, "stop"):
                await session.stop()
            elif hasattr(session, "close"):
                await session.close()
        except Exception as e:  # noqa: BLE001
            _log.debug(
                "enrich_worker.session_stop_failed",
                slot=slot, error=str(e)[:120],
            )
    _PREWARMED_SESSIONS.clear()


async def run_workers_forever() -> None:
    """Entry point used by `agentic-crawl enrich-worker` and by the
    in-process spawner in `scheduler.py`. Spawns N consumer loops + 1
    reclaim loop + 1 queue-depth gauge updater, then waits for shutdown."""
    s = get_agentic_settings()
    n = max(1, int(s.agentic_enrich_parallel))
    _log.info(
        "enrich_worker.started",
        parallel=n, llm_base_url=s.llm_base_url,
        lessons_dir=str(s.enrich_lessons_dir),
    )

    # Phase 3.2: pre-warm one persistent BrowserSession per consumer so a
    # Chromium tab stays visible in noVNC across tasks. Each consumer
    # reuses its session via _PREWARMED_SESSIONS[idx].
    await _prewarm_sessions(n)

    tasks = [asyncio.create_task(_consumer_loop(i)) for i in range(n)]
    tasks.append(asyncio.create_task(_reclaim_loop()))
    tasks.append(asyncio.create_task(enrich_queue.watch_depth(30.0)))

    try:
        await _SHUTDOWN.wait()
    finally:
        await _shutdown_prewarmed_sessions()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def request_shutdown() -> None:
    _SHUTDOWN.set()
