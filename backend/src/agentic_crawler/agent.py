"""Browser-Use Agent wrapper.

Drives a real Chromium via Playwright. The vision-capable LLM (qwen3.6:27b)
sees the screen, decides next action (click / scroll / type), reads results.
Output is normalized to a list of `_Exhibitor` records that downstream
reporter/resolver/enricher can consume in the same way they consume output
from the deterministic crawler.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from crawler.observability.logger import get_logger
from crawler.observability.metrics import errors_total

from .config import get_agentic_settings
from .seeds import AgenticSeed

_log = get_logger(__name__)


class _StepCaptureHandler(logging.Handler):
    """Per-run log handler — buffers Browser-Use's per-step Eval/Memory/Goal
    lines so the lesson archive can dump them as the agent's raw thinking.

    Browser-Use's `save_conversation_path` was empirically empty in 0.12.x
    deployments (likely API drift), so we route around it by intercepting the
    logs the agent already emits to stdout. Filter is a name-prefix check on
    `browser_use.Agent` so minor renames in 0.13 don't break us.
    """

    def __init__(self, capacity: int = 500) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[dict[str, Any]] = []
        self._capacity = capacity

    def emit(self, record: logging.LogRecord) -> None:
        # Filter to only Browser-Use Agent messages — anything else is noise
        # for our purposes. Drop excess records (sliding window) so a runaway
        # agent doesn't OOM us.
        if not record.name.startswith("browser_use"):
            return
        if len(self.records) >= self._capacity:
            self.records.pop(0)
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            msg = str(record.msg)
        self.records.append(
            {
                "step": len(self.records) + 1,
                "ts": datetime.now(timezone.utc).isoformat(),
                "logger": record.name,
                "level": record.levelname,
                "message": msg,
            }
        )

# Path where Dockerfile.agentic extracts the Buster CAPTCHA-solver extension.
# Loaded into Browser-Use's Chromium via --load-extension when present.
_BUSTER_PATH = Path("/opt/buster")


class _Exhibitor(BaseModel):
    """One exhibitor row extracted by the agent. Same shape as the
    `_ExpoCandidate` from `crawler.agents.discovery` so downstream stages
    (resolver, enricher) accept it without translation."""

    name: str
    booth: str | None = None
    url: str | None = None
    description: str | None = None
    country: str | None = None


class AgentResult(BaseModel):
    seed_name: str
    expo_id: str | None
    exhibitors: list[_Exhibitor] = Field(default_factory=list)
    raw_output: str | None = None
    error: str | None = None
    # The page the agent ended on. For search-then-extract seeds this is the
    # actual exhibitor list URL (not the Bing SERP) — what the knowledge
    # store should remember as the "successful URL" for warm-start replay.
    final_url: str | None = None
    # Set by the agent when it bails out of an unworkable page. One of:
    # '404' | 'image_only' | 'captcha' | 'paywall' | '403'. Lets the lesson
    # archiver record a category instead of a generic 'empty_result'.
    bail_reason: str | None = None
    # Recordings dir for this run (when AGENTIC_RECORD_SCREENSHOTS=true).
    # The lesson archiver moves/copies it into the lesson dir post-run.
    recordings_dir: Path | None = None
    # Captured Browser-Use Agent log records — the agent's per-step thinking
    # (Eval / Memory / Next goal). Lesson archive dumps these as raw thoughts.
    raw_steps: list[dict] = Field(default_factory=list)
    # Number of agent steps executed (n_steps from Browser-Use's history).
    n_steps: int | None = None


async def run_agent_for_seed(seed: AgenticSeed) -> AgentResult:
    """Run Browser-Use Agent against one seed URL with the seed's task prompt.

    Wraps the call in a hard timeout (`AGENTIC_TASK_TIMEOUT`) so a runaway
    agent can't block the scheduler. Failures are caught and recorded so the
    scheduler can move on to the next seed without crashing.
    """
    s = get_agentic_settings()
    try:
        from browser_use import Agent  # lazy import — pkg only present in agentic profile
        # Browser-Use 0.12.x ships its own LLM wrappers (with `.provider` and
        # native `ainvoke`) replacing the langchain layer. We use the queue-
        # wrapped factory so every `ainvoke()` acquires `llm:concurrency:vision`
        # in Redis (or a process-local semaphore fallback) before hitting
        # Ollama — keeps 4 parallel seeds from collapsing the daemon's queue.
        from crawler.tools.llm.queue import QueuedChatOllama as ChatOllama
    except ImportError as e:
        _log.warning("agentic.import_failed", error=str(e))
        return AgentResult(
            seed_name=seed.name,
            expo_id=seed.expo_id,
            error=f"browser-use not installed: {e}",
        )

    # Note: browser_use's ChatOllama uses `host` (not `base_url`) and routes
    # via the `ollama` Python client rather than langchain's HTTP layer.
    # `timeout` here is the per-call HTTP timeout — defaults to 75s upstream
    # which is too tight for a 27B vision model processing a Bing SERP
    # screenshot (~100K tokens of context). 300s gives headroom for slower
    # GPU hosts; bump higher if your Ollama box is on CPU-fallback.
    llm = ChatOllama(
        model=s.vision_model,
        host=s.llm_base_url.rstrip("/"),
        timeout=300.0,
        _llm_queue_tier="vision",
    )

    instruction = (
        f"Open: {seed.url}\n\n"
        f"Steps:\n"
        f"1. dismiss_overlays  (only if banner/popup blocks scroll)\n"
        f"2. scroll_until_loaded\n"
        f"3. extract_by_selector('<recurring-row-selector>')\n"
        f"   Common: '.exhibitor-card', '[data-exhibitor]', "
        f"'li.list-item', 'tr.exhibitor'.\n"
        f"   If 0 hits, try a different selector — don't manually scroll.\n"
        f"4. emit done with JSON.\n\n"
        f"OUTPUT (JSON only, no prose, no fences):\n"
        f'{{"exhibitors": [{{"name": "...", "booth": "...", "url": "...", '
        f'"country": "..."}}]}}\n'
        f"booth/url/country optional → null if unknown.\n\n"
        f"Bail (404 / captcha / paywall / 403 / image_only): emit done with "
        f'{{"exhibitors": [], "bail_reason": "<cat>"}}.\n'
        f"Anti-loop: max 2 same Next-goal in a row, then switch tactic or done."
    )

    # Per-task recording dir (timestamped) so concurrent / sequential runs of
    # the same seed don't overwrite each other. Operator inspects after the fact.
    from datetime import datetime, timezone

    task_slug = "".join(c if c.isalnum() else "_" for c in seed.name)[:60]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rec_dir = s.recordings_dir / f"{stamp}-{task_slug}"
    if s.record_screenshots or s.record_conversation:
        rec_dir.mkdir(parents=True, exist_ok=True)

    agent_kwargs: dict[str, Any] = {
        "task": instruction,
        "llm": llm,
        "use_vision": s.use_vision,
        # Lower than the default 10 — small vision models tend to bundle
        # stale navigate/click actions that all reference the previous DOM
        # snapshot. With 3 actions per turn it observes state more often
        # and breaks out of the "click same link 5x" loop we saw in logs.
        "max_actions_per_step": 3,
        # Browser-Use ships these defaults that BLOAT the LLM context per
        # step — keys why the 300s llm_timeout was getting hit despite a
        # dedicated GPU. With qwen3-vl:8b prefill scales with input length,
        # so trimming context = exponentially faster vision generation.
        # Defaults: max_history_items=None, max_clickable_elements_length=40000.
        "max_history_items": 6,         # Browser-Use min is 6 (validator)
        "max_clickable_elements_length": 8000,  # 5× smaller DOM digest
        # Browser-Use defaults `llm_timeout` to 75s for unknown models —
        # qwen3-vl:8b on shared Ollama with big context can need 5-10 min.
        "llm_timeout": 600,
        "step_timeout": 720,
    }

    # Register custom power-tools (`scroll_until_loaded`, `extract_by_selector`)
    # alongside Browser-Use's built-in actions. These bypass the slow
    # screenshot-LLM-scroll loop for sites with long exhibitor lists.
    from .tools import build_controller

    controller = build_controller()
    if controller is not None:
        agent_kwargs["controller"] = controller

    # Browser-Use 0.12.x uses `BrowserProfile` (Pydantic model) for browser
    # config — not the legacy `BrowserConfig`. Pass it via Agent's
    # `browser_profile` kwarg. Setting headless=False makes Chromium attach
    # to the Xvfb display (DISPLAY=:99 from the entrypoint), which noVNC
    # then streams to http://localhost:7900/vnc.html.
    chromium_args: list[str] = []
    if _BUSTER_PATH.is_dir() and not s.headless:
        # Buster needs a real (non-headless) browser to access the Web Speech
        # API for audio-based reCAPTCHA solving. With Xvfb in place via the
        # entrypoint, Chromium runs "headed" against a virtual display.
        chromium_args.extend([
            f"--load-extension={_BUSTER_PATH}",
            f"--disable-extensions-except={_BUSTER_PATH}",
        ])
        _log.info("agentic.buster_loaded", path=str(_BUSTER_PATH))

    # Phase 2: route Chromium through the same proxy our httpx clients use.
    # Without this the agentic browser would egress on the host IP while the
    # search modules egress through Gluetun, mixing two distinct identities
    # and defeating the whole point of the VPN.
    try:
        from crawler.config import get_settings as _get_base_settings

        _base = _get_base_settings()
        if _base.vpn_enabled and _base.proxy_url:
            chromium_args.append(f"--proxy-server={_base.proxy_url}")
            _log.info("agentic.chromium_proxy", url=_base.proxy_url)
    except Exception as e:  # noqa: BLE001
        _log.debug("agentic.chromium_proxy_skip", error=str(e)[:120])

    # Phase 3: deny notification / geolocation / camera permission prompts
    # before the page can ask. Sites that gate scroll behind a "Allow
    # notifications?" popup get auto-rejected; the agent never sees the
    # prompt UI. Complements `dismiss_overlays` (which handles in-page
    # overlays) — these flags handle the browser-chrome-level prompts.
    chromium_args.extend([
        "--deny-permission-prompts",
        "--use-fake-ui-for-media-stream",
        "--disable-notifications",
    ])

    # Phase 3.1: persistent Chromium profile per worker slot. Cookies +
    # history + cache survive across runs, so the browser looks like a
    # returning visitor (less captcha, less "we don't recognize you" gates)
    # and HTTP cache hits speed up repeat visits. Each parallel listing
    # worker takes a stable slot dir so concurrent workers don't fight
    # over Chromium's SQLite locks.
    profile_slot_path: Path | None = None
    profile_slot_handle = None
    if s.agentic_persistent_profiles:
        try:
            from .profile_slots import acquire_listing_slot

            profile_slot_handle = acquire_listing_slot()
            slot_idx, profile_slot_path = await profile_slot_handle.__aenter__()
            _log.info(
                "agentic.persistent_profile",
                role="listing",
                slot=slot_idx,
                path=str(profile_slot_path),
            )
        except Exception as e:  # noqa: BLE001
            _log.warning("agentic.profile_slot_acquire_failed", error=str(e)[:160])
            profile_slot_handle = None
            profile_slot_path = None

    try:
        from browser_use.browser.profile import BrowserProfile  # type: ignore[attr-defined]

        profile_kwargs: dict[str, Any] = {"headless": s.headless}
        # Disable Browser-Use's three auto-installed extensions (uBlock,
        # ICDontCare cookies, Force Background Tab). They slow down session
        # boot AND have been observed to cause `BrowserStateRequestEvent`
        # to return empty {} during early agent steps → "5 consecutive
        # failures" stop. Our `dismiss_overlays` controller action handles
        # the cookie-banner case anyway.
        profile_kwargs["enable_default_extensions"] = False
        if chromium_args:
            profile_kwargs["args"] = chromium_args
        if profile_slot_path is not None:
            # Browser-Use 0.12.x maps `user_data_dir` to Chromium's
            # `--user-data-dir` arg. Persistent context = same cookies
            # next run, same downloaded resources cached.
            profile_kwargs["user_data_dir"] = str(profile_slot_path)
        # When running headed (for noVNC visibility), force the FULL Chromium
        # binary — Playwright's default `chromium` install is the lightweight
        # `headless_shell` which is inherently headless and ignores both the
        # `headless=False` profile flag and any `--headless` arg stripping.
        # Pin to the headed binary so Xvfb actually has a window to render.
        if not s.headless:
            from pathlib import Path as _Path

            for candidate in (
                "/ms-playwright/chromium-1161/chrome-linux/chrome",
                "/ms-playwright/chromium-1148/chrome-linux/chrome",
            ):
                if _Path(candidate).exists():
                    profile_kwargs["executable_path"] = candidate
                    _log.info("agentic.chromium_headed_binary", path=candidate)
                    break
        # `ignore_default_args` lets us strip Playwright/Browser-Use's auto-
        # injected `--headless=new --ozone-platform=headless` so Chromium
        # actually attaches to our Xvfb display. Without this, even with
        # headless=False, Browser-Use forces Chromium into a sandboxed
        # headless surface and the VNC stream stays empty.
        if not s.headless:
            profile_kwargs["ignore_default_args"] = [
                "--headless=new",
                "--headless",
                "--ozone-platform=headless",
            ]
        agent_kwargs["browser_profile"] = BrowserProfile(**profile_kwargs)
    except ImportError as e:
        _log.warning("agentic.browser_profile_unavailable", error=str(e))

    if s.record_conversation:
        # Browser-Use writes per-step prompt + response here.
        agent_kwargs["save_conversation_path"] = str(rec_dir / "conversation")
    if s.record_screenshots:
        # Browser-Use saves a screenshot.png per step here.
        agent_kwargs["save_recording_path"] = str(rec_dir)

    capture = _StepCaptureHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(capture)
    try:
        try:
            agent: Any = Agent(**agent_kwargs)
            # Phase 3 — best-effort fluxbox workspace assignment so the
            # listing pool's chromiums tile on workspace 1, the enrich
            # pool's on workspace 2. Fire-and-forget; no-ops gracefully
            # when wmctrl is missing or the window hasn't mapped yet.
            try:
                from .workspace import assign_after_spawn

                browser_session = getattr(agent, "browser_session", None)
                if browser_session is not None:
                    asyncio.create_task(
                        assign_after_spawn(
                            browser_session, s.listing_workspace_id
                        )
                    )
            except Exception as _e:  # noqa: BLE001
                _log.debug("agentic.workspace_helper_skip", error=str(_e)[:120])
            # Browser-Use exposes max_steps via .run(); cap it to budget.
            result = await asyncio.wait_for(
                agent.run(max_steps=s.max_actions),
                timeout=s.task_timeout_seconds,
            )
        except asyncio.TimeoutError:
            errors_total.labels(stage="agentic", category="timeout").inc()
            _log.warning("agentic.timeout", seed=seed.name, timeout=s.task_timeout_seconds)
            return AgentResult(
                seed_name=seed.name,
                expo_id=seed.expo_id,
                error="timeout",
                raw_steps=list(capture.records),
                recordings_dir=rec_dir if (s.record_screenshots or s.record_conversation) else None,
            )
        except Exception as e:  # noqa: BLE001
            errors_total.labels(stage="agentic", category=type(e).__name__).inc()
            _log.warning("agentic.run_failed", seed=seed.name, error=str(e)[:200])
            return AgentResult(
                seed_name=seed.name,
                expo_id=seed.expo_id,
                error=str(e)[:200],
                raw_steps=list(capture.records),
                recordings_dir=rec_dir if (s.record_screenshots or s.record_conversation) else None,
            )
    finally:
        root_logger.removeHandler(capture)
        # Release persistent profile slot back to the pool so the next
        # parallel listing worker can pick it up. Slot index → same dir
        # next run = sticky cookies + history.
        if profile_slot_handle is not None:
            try:
                await profile_slot_handle.__aexit__(None, None, None)
            except Exception as _e:  # noqa: BLE001
                _log.debug("agentic.profile_slot_release_failed", error=str(_e)[:120])

    # Browser-Use returns an AgentHistoryList; .final_result() is the answer
    # the agent emitted at the "done" action.
    raw = ""
    try:
        raw = result.final_result() if hasattr(result, "final_result") else str(result)
    except Exception:  # noqa: BLE001
        raw = str(result)

    exhibitors, bail_reason = _parse_exhibitors_json(raw)

    # Capture the last URL the agent actually landed on. Browser-Use's
    # AgentHistoryList exposes `.urls()` (list[str]) — last element is the
    # final URL. Fallback chain handles older / variant API surfaces.
    final_url: str | None = None
    try:
        if hasattr(result, "urls"):
            url_list = result.urls() if callable(result.urls) else result.urls
            if url_list:
                final_url = next((u for u in reversed(list(url_list)) if u), None)
    except Exception:  # noqa: BLE001
        final_url = None

    _log.info(
        "agentic.run_done",
        seed=seed.name,
        exhibitors=len(exhibitors),
        actions_used=getattr(result, "n_steps", None),
        final_url=final_url,
        bail_reason=bail_reason,
    )
    return AgentResult(
        seed_name=seed.name,
        expo_id=seed.expo_id,
        exhibitors=exhibitors,
        raw_output=raw[:2000] if raw else None,
        final_url=final_url,
        bail_reason=bail_reason,
        recordings_dir=rec_dir if (s.record_screenshots or s.record_conversation) else None,
        raw_steps=list(capture.records),
        n_steps=getattr(result, "n_steps", None),
    )


def _parse_exhibitors_json(text: str) -> tuple[list[_Exhibitor], str | None]:
    """Salvage JSON from agent output. Reuses the same balanced-brace scan
    as the base crawler's LLM client so behavior is consistent.

    Returns (exhibitors, bail_reason). `bail_reason` is one of the canonical
    bail-out categories ('404', 'image_only', 'captcha', 'paywall', '403') or
    None if the agent didn't bail.
    """
    if not text:
        return [], None
    from crawler.tools.llm.openai_client import _extract_json

    try:
        payload = _extract_json(text)
    except Exception as e:  # noqa: BLE001
        _log.warning("agentic.parse_failed", error=str(e), preview=text[:200])
        return [], None
    if not isinstance(payload, dict):
        return [], None
    items = payload.get("exhibitors") or []
    out: list[_Exhibitor] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            out.append(_Exhibitor(**it))
        except Exception:  # noqa: BLE001
            continue
    bail_raw = payload.get("bail_reason")
    bail = None
    if isinstance(bail_raw, str) and bail_raw.strip():
        # Trust agent-supplied category as long as it's a known one — anything
        # else gets bucketed as 'empty_result' by the failure categorizer.
        clean = bail_raw.strip().lower()
        if clean in {"404", "403", "captcha", "image_only", "paywall"}:
            bail = clean
        else:
            bail = clean[:40]  # archive what the agent said anyway
    return out, bail
