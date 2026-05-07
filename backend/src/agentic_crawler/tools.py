"""Custom Browser-Use actions for the agentic crawler.

Three power-tools that bypass the slow scroll-look-extract loop the small
vision model gets stuck in:

  scroll_until_loaded()
      Auto-scrolls to the bottom, polling document.body.scrollHeight after
      each step until it stops growing (or hits the iteration cap). One
      tool-call replaces 5+ LLM turns of "scroll → look → scroll → look".

  extract_by_selector(selector)
      Bulk-grabs every element matching a CSS selector via page.evaluate()
      and returns JSON {text, href} per item. The agent picks a recurring
      container class (e.g. ".exhibitor-card") and pulls the whole list in
      a single shot — no screenshot OCR, no per-row LLM parsing.

  dismiss_overlays()
      Clicks-or-removes cookie banners, GDPR walls, newsletter modals,
      chat widgets, geo-blockers, and notification prompts. Most expo /
      vendor sites throw 1-3 of these at every visit; a small vision model
      gets stuck trying to manually click around them. Selectors below
      cover the bulk of OneTrust / Cookiebot / HubSpot / Intercom / Drift
      patterns.

  search_vendor(query)
      Multi-engine search via the Phase 2 `multi.search_all` plumbing.
      Used exclusively by the enrich pool to find a vendor's official
      domain BEFORE visiting it — DON'T let the agent free-browse to
      Google/Bing UI. Returns up to 8 {title, url, snippet} hits.

  open_in_new_tab(url)
      Opens `url` in a fresh tab (vs Browser-Use's default `go_to_url`
      which replaces the current page). Keeps the previous context
      visible in noVNC — operator watching the agent can still see the
      search results page after the agent picks one and dives in.

All five register into a single `Controller` passed to
`Agent(controller=...)`. The default Browser-Use built-in actions (click,
type, scroll_by, navigate, done) remain available alongside ours.

NOTE: this module deliberately does NOT use `from __future__ import annotations`.
Browser-Use's registry inspects raw `param.annotation` and compares with `==`
to the actual `BrowserSession` class — under PEP 563 the annotation becomes a
string forward-reference and the comparison fails with a confusing
"conflicts with special argument injected" error.
"""

import asyncio
import json
from typing import Any

from crawler.observability.logger import get_logger

_log = get_logger(__name__)


def build_controller() -> Any:
    """Construct + return a Browser-Use Controller with our actions registered.

    Lazy-imports browser_use so this module is safe to import even outside
    the agentic profile (e.g. from cli.py for sanity checks). Returns None
    if browser_use isn't installed.
    """
    try:
        from browser_use import ActionResult, Controller
    except ImportError as e:
        _log.warning("agentic.tools_browser_use_missing", error=str(e))
        return None

    # BrowserSession import path drifted between 0.12.x patch releases — try
    # both. The annotation is what Controller's registry uses to inject the
    # live session into our action functions.
    BrowserSession: Any
    try:
        from browser_use.browser.session import BrowserSession  # type: ignore
    except ImportError:
        try:
            from browser_use.browser import BrowserSession  # type: ignore
        except ImportError:
            try:
                from browser_use import BrowserSession  # type: ignore
            except ImportError:
                _log.warning("agentic.tools_browser_session_unavailable")
                return None

    controller = Controller()

    @controller.action(
        "Scroll the page to the very bottom, waiting for lazy-loaded content "
        "to render. Loops until scrollHeight stops growing or 10 iterations "
        "have run. Use this ONCE per page instead of issuing multiple manual "
        "scrolls — much faster than the per-step scroll/look loop. Saves "
        "a PNG snapshot per iteration to data/agentic_recordings/scroll_*/"
        "so you can flip-book the scroll path offline for debugging."
    )
    async def scroll_until_loaded(browser_session: BrowserSession) -> Any:
        # Browser-Use 0.12.x enforces `(...args) => ...` arrow-function format
        # in page.evaluate() — raw expressions like "document.body.scrollHeight"
        # get rejected with "JavaScript code must start with (...args) => format".
        # Wrap every snippet in an arrow function.
        import os
        from datetime import datetime, timezone
        from pathlib import Path

        page = await browser_session.get_current_page()

        # Per-call screenshot directory: data/agentic_recordings/scroll_<host>_<stamp>/
        # Stamp includes microseconds so concurrent calls from different
        # listing slots never clash.
        host = os.environ.get("HOSTNAME") or "host"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
        snap_dir = Path("/app/data/agentic_recordings") / f"scroll_{host}_{stamp}"
        try:
            snap_dir.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            snap_dir = None  # type: ignore[assignment]

        async def _snap(label: str) -> None:
            if snap_dir is None:
                return
            try:
                await page.screenshot(
                    path=str(snap_dir / f"{label}.png"),
                    full_page=False,  # viewport only — full_page is slow + huge
                )
            except Exception:  # noqa: BLE001
                # Don't let screenshot failures abort the scroll.
                pass

        await _snap("00_before")

        last_height = await page.evaluate("() => document.body.scrollHeight")
        iterations = 0
        for i in range(10):
            iterations = i + 1
            await page.evaluate(
                "() => window.scrollTo(0, document.body.scrollHeight)"
            )
            # Browser-Use 0.12.x dropped Playwright's `page.wait_for_timeout`
            # in favor of CDP — use plain asyncio.sleep instead.
            await asyncio.sleep(0.7)
            new_height = await page.evaluate("() => document.body.scrollHeight")
            await _snap(f"{iterations:02d}_after_scroll_h{int(new_height)}")
            if new_height == last_height:
                break
            last_height = new_height
        msg = (
            f"Scrolled to bottom in {iterations} iteration(s). "
            f"Final scrollHeight={last_height}px. "
            f"Snapshots saved under {snap_dir.name if snap_dir else 'none'}. "
            f"Now identify the exhibitor-row CSS selector and call "
            f"extract_by_selector to bulk-pull the list."
        )
        _log.info(
            "agentic.tool.scroll_until_loaded",
            iterations=iterations,
            height=last_height,
            snapshots=str(snap_dir.name) if snap_dir else None,
        )
        return ActionResult(extracted_content=msg, include_in_memory=True)

    @controller.action(
        "Bulk-extract all elements matching a CSS selector. Returns JSON list "
        "of {text, href} per element. USE AFTER scroll_until_loaded — provide "
        "a selector targeting each exhibitor card/row, e.g. '.exhibitor-card', "
        "'div[data-exhibitor]', 'li.exhibitor-item', or 'tr.exhibitor-row'. "
        "If your first selector returns 0 or returns something wrong (text "
        "looks like nav menu, not exhibitor names), retry with a different "
        "one — don't fall back to manual scrolling."
    )
    async def extract_by_selector(
        selector: str, browser_session: BrowserSession
    ) -> Any:
        page = await browser_session.get_current_page()
        js = """
        (sel) => {
            const items = [];
            document.querySelectorAll(sel).forEach((el) => {
                const text = (el.innerText || el.textContent || '').trim();
                if (!text || text.length > 2000) return;
                const link = el.tagName === 'A' ? el : el.querySelector('a');
                items.push({
                    text: text.slice(0, 500),
                    href: link && link.href ? link.href : null,
                });
            });
            return items;
        }
        """
        try:
            items = await page.evaluate(js, selector)
        except Exception as e:  # noqa: BLE001
            return ActionResult(
                error=(
                    f"Selector '{selector}' failed to evaluate: {e}. "
                    f"Try a different CSS selector — inspect the DOM tree "
                    f"in the browser state for clues."
                )
            )
        if not items:
            return ActionResult(
                error=(
                    f"Selector '{selector}' matched 0 elements. Try another — "
                    f"common patterns: '.exhibitor', '[data-exhibitor]', "
                    f"'li.list-item', '.card-title', 'a.company-link'."
                )
            )
        # Cap payload back to LLM — large lists eat context. Agent can call
        # again with a more specific selector if it needs subset.
        preview = items[:80]
        msg = (
            f"Extracted {len(items)} items via selector '{selector}'. "
            f"Showing first {len(preview)}: "
            f"{json.dumps(preview, ensure_ascii=False)}"
        )
        _log.info(
            "agentic.tool.extract_by_selector",
            selector=selector,
            count=len(items),
        )
        return ActionResult(extracted_content=msg, include_in_memory=True)

    @controller.action(
        "Dismiss cookie banners, GDPR walls, newsletter modals, chat "
        "widgets, geo-blockers, and notification prompts blocking the "
        "page. Use this FIRST whenever you can't scroll, click, or read "
        "page content — don't waste turns clicking 'Accept' on banners "
        "manually. Returns count of overlays dismissed."
    )
    async def dismiss_overlays(browser_session: BrowserSession) -> Any:
        page = await browser_session.get_current_page()
        # The matched node is removed from the DOM (rather than clicked) so
        # we don't accidentally pick the "Accept all" button on a cookie
        # banner. For modals with explicit close icons we click those first
        # because some sites enforce dismissal via JS state. The DOM-remove
        # fallback always wins over leaving an overlay up.
        js = r"""
        () => {
            const log = [];

            // 1) Match the overlay container by common selector families.
            //    Substring + case-insensitive (`*= i`) catches many vendor
            //    naming conventions: cookieBanner, CookieConsent, etc.
            const containerSelectors = [
                // cookies / consent / GDPR
                '[id*="cookie" i]',
                '[class*="cookie" i]',
                '[id*="consent" i]',
                '[class*="consent" i]',
                '[id*="gdpr" i]',
                '[class*="gdpr" i]',
                '#onetrust-banner-sdk',
                '#onetrust-consent-sdk',
                '#CybotCookiebotDialog',
                '.qc-cmp2-container',
                '.truste_overlay',
                '.truste_box_overlay',
                '[id*="cookiebanner" i]',
                // generic modals / lightboxes
                '[role="dialog"]',
                '[class*="modal" i]',
                '[class*="lightbox" i]',
                '.fancybox-overlay',
                '[class*="popup" i]',
                '[class*="overlay" i]',
                // newsletter / subscribe
                '[class*="newsletter" i]',
                '[class*="subscribe" i]',
                '[class*="signup" i]',
                '[id*="newsletter" i]',
                // chat widgets (don't bother clicking close, just nuke)
                '#hubspot-messages-iframe-container',
                '[class*="intercom" i]',
                '[id*="intercom" i]',
                '[id*="drift" i]',
                '[class*="drift-frame" i]',
                '[class*="tawk" i]',
                '[id*="tawk" i]',
                '[class*="zendesk" i]',
                '[class*="zopim" i]',
                '[class*="livechat" i]',
                '[class*="crisp" i]',
                // geo / region picker
                '[class*="geo-block" i]',
                '[class*="region-select" i]',
                '[class*="country-picker" i]',
                '[class*="locale-modal" i]',
            ];

            // Don't ever match anything that obviously contains the
            // page's primary content — these are negative checks against
            // the matched node before we remove it.
            const protectedRoots = ['main', 'article', '[role="main"]'];

            const seen = new Set();
            const elements = [];
            for (const sel of containerSelectors) {
                let matches;
                try { matches = document.querySelectorAll(sel); }
                catch (e) { continue; }
                matches.forEach((el) => {
                    if (seen.has(el)) return;
                    // Skip if this overlay is actually wrapping <main> /
                    // <article> — we'd nuke the page itself.
                    if (protectedRoots.some(p => el.querySelector(p))) return;
                    // Skip invisible nodes (display:none, opacity:0, 0px).
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5) return;
                    const cs = window.getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden') return;
                    seen.add(el);
                    elements.push({el, sel});
                });
            }

            // 2) For each matched container, try to click an in-container
            //    close icon FIRST — purely as a courtesy to sites that
            //    re-render if you DOM-remove. If no close button found,
            //    we DOM-remove. We deliberately exclude accept/agree/ok
            //    so we don't auto-consent to anything.
            const closeSelectors = [
                '[aria-label*="close" i]',
                '[aria-label*="dismiss" i]',
                '[aria-label*="reject" i]',
                'button[class*="close" i]:not([class*="accept" i])',
                'button[class*="dismiss" i]',
                'button[class*="reject" i]',
                'button[id*="close" i]:not([id*="accept" i])',
                '[data-dismiss]',
                '.close-button',
                '.modal-close',
                '.btn-close',
            ];
            const glyphXpath = ".//*[normalize-space(text())='×' or "
                + "normalize-space(text())='✕' or "
                + "normalize-space(text())='✖']";

            for (const {el, sel} of elements) {
                let clicked = false;
                for (const cs of closeSelectors) {
                    let btn;
                    try { btn = el.querySelector(cs); }
                    catch (e) { continue; }
                    if (btn) {
                        try { btn.click(); clicked = true; break; }
                        catch (e) { /* fall through to remove */ }
                    }
                }
                if (!clicked) {
                    // Try literal × ✕ ✖ glyph match via xpath.
                    try {
                        const r = document.evaluate(
                            glyphXpath, el,
                            null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                        );
                        if (r && r.singleNodeValue) {
                            r.singleNodeValue.click();
                            clicked = true;
                        }
                    } catch (e) {}
                }
                if (clicked) {
                    log.push({selector: sel, method: 'click'});
                } else {
                    try { el.remove(); log.push({selector: sel, method: 'remove'}); }
                    catch (e) { log.push({selector: sel, method: 'failed'}); }
                }
            }

            // 3) Strip any leftover body/html locks — many overlays disable
            //    scroll on <body> via inline style or class.
            try {
                document.body.style.overflow = '';
                document.body.style.position = '';
                document.documentElement.style.overflow = '';
                document.body.classList.remove(
                    'modal-open', 'no-scroll', 'noscroll',
                    'overflow-hidden', 'lock-scroll'
                );
            } catch (e) {}

            return {dismissed: log.length, methods: log};
        }
        """
        try:
            result = await page.evaluate(js)
        except Exception as e:  # noqa: BLE001
            _log.debug("agentic.tool.dismiss_overlays_failed", error=str(e)[:160])
            return ActionResult(
                extracted_content="dismiss_overlays: page evaluate failed; "
                f"continuing without dismissal ({str(e)[:80]})",
                include_in_memory=False,
            )
        n = int(result.get("dismissed", 0)) if isinstance(result, dict) else 0
        methods = result.get("methods", []) if isinstance(result, dict) else []
        if n > 0:
            try:
                from crawler.observability.metrics import (
                    agentic_overlays_dismissed_total,
                )

                # Label by host for observability without exploding cardinality —
                # PR1 keeps this simple; future metric tweaks can refine.
                try:
                    host = page.url.split("/")[2] if "://" in page.url else "unknown"
                except Exception:  # noqa: BLE001
                    host = "unknown"
                agentic_overlays_dismissed_total.labels(site=host).inc(n)
            except Exception:  # noqa: BLE001
                # Metric is best-effort — don't fail the action over it.
                pass
        _log.info("agentic.tool.dismiss_overlays", count=n, methods=methods[:8])
        msg = (
            f"Dismissed {n} overlay(s). "
            f"Now retry the action that was blocked (scroll, click, or read)."
        )
        return ActionResult(extracted_content=msg, include_in_memory=True)

    @controller.action(
        "Open a URL in a NEW tab (don't replace the current tab). Use this "
        "for every navigation — visiting a search result, opening a vendor "
        "domain, opening a contact page — so the previous context stays "
        "visible. The new tab becomes the active tab. If you genuinely "
        "need same-tab navigation (rare), use `go_to_url` instead."
    )
    async def open_in_new_tab(
        url: str, browser_session: BrowserSession
    ) -> Any:
        # Browser-Use 0.12.x exposes the underlying Playwright BrowserContext
        # via `browser_session.browser_context`. We open a fresh page there
        # and switch focus so subsequent built-in actions (click, scroll,
        # extract_by_selector) operate on the new tab.
        try:
            ctx = getattr(browser_session, "browser_context", None)
            if ctx is None:
                return ActionResult(
                    error="open_in_new_tab: browser_context not available; "
                    "fall back to `go_to_url`."
                )
            new_page = await ctx.new_page()
            await new_page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Make Browser-Use treat this as the active page for subsequent
            # actions. The exact attribute changed across 0.12.x patches —
            # try the documented setter first, fall back to direct assign.
            try:
                if hasattr(browser_session, "set_current_page"):
                    await browser_session.set_current_page(new_page)
                elif hasattr(browser_session, "_current_page"):
                    browser_session._current_page = new_page  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                # Worst case: the new tab opens but Browser-Use's idea of
                # "current" is the old tab. Operator still sees both tabs
                # in noVNC; agent can issue `switch_tab` to recover.
                pass
            _log.info("agentic.tool.open_in_new_tab", url=url[:120])
            return ActionResult(
                extracted_content=(
                    f"Opened {url} in a new tab. The new tab is now active. "
                    f"Previous tab(s) remain open in the background — you "
                    f"can `switch_tab` back if needed."
                ),
                include_in_memory=True,
            )
        except Exception as e:  # noqa: BLE001
            return ActionResult(
                error=f"open_in_new_tab failed for {url}: {str(e)[:200]}. "
                f"Fall back to `go_to_url` (same-tab nav)."
            )

    @controller.action(
        "Search the web for a vendor and return up to 8 candidate domains. "
        "Use this FIRST when you only have a vendor NAME (no URL) — never "
        "free-browse to google.com / bing.com manually, this tool fans out "
        "to multiple engines (regional too) and returns the cleanest set "
        "of {title, url, snippet} hits. Pass a query like the vendor name "
        "plus any country / product hints you have."
    )
    async def search_vendor(query: str) -> Any:
        # Lazy import to keep this module importable when the base
        # crawler tree isn't on the path (defensive — same pattern as the
        # rest of agentic_crawler).
        try:
            from crawler.tools.search.multi import search_all
        except ImportError as e:
            return ActionResult(
                error=f"search_vendor: multi.search_all import failed: {e}"
            )
        try:
            hits = await search_all(query, per_source_limit=8)
        except Exception as e:  # noqa: BLE001
            return ActionResult(
                error=f"search_vendor: query failed ({str(e)[:120]}); "
                f"try a simpler query or fall back to navigating known "
                f"directory aggregators."
            )
        if not hits:
            return ActionResult(
                extracted_content=(
                    f"search_vendor: 0 hits for '{query}'. "
                    f"Try a different phrasing — drop quotes, remove "
                    f"trailing tokens, or add a country/product hint."
                ),
                include_in_memory=True,
            )
        # Cap to 8 results; trim snippet so payload stays compact for the
        # vision-model context.
        compact = []
        for h in hits[:8]:
            compact.append(
                {
                    "title": (getattr(h, "title", "") or "")[:120],
                    "url": getattr(h, "url", "") or "",
                    "snippet": (getattr(h, "snippet", "") or "")[:200],
                    "source": getattr(h, "source", "") or "",
                }
            )
        msg = (
            f"search_vendor returned {len(compact)} candidate(s) for "
            f"'{query}'. Pick the official vendor domain — prefer single-"
            f"word matches to the vendor name, AVOID directory aggregators "
            f"(alibaba.com, made-in-china.com, linkedin.com, indiamart.com). "
            f"Results: {json.dumps(compact, ensure_ascii=False)}"
        )
        _log.info("agentic.tool.search_vendor", query=query[:80], hits=len(compact))
        return ActionResult(extracted_content=msg, include_in_memory=True)

    return controller
