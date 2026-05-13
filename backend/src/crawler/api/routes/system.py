"""System health endpoints — beyond `/api/health`'s reachability checks.

These routes surface live operational state the operator wants on glance:
- LLM concurrency queue depth per tier (Redis-backed counter)
- Ollama loaded-model VRAM footprint (proxy to remote `/api/ps`)
- Agentic Browser-Use session locks (per-hostname active run state)

Per the user's "no synthesized prose" rule, all data here is real — what
Redis/Ollama returns, parsed and forwarded. No mock fallbacks; gracefully
degraded responses on backend failures, callers handle null values.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter

from ...config import get_settings
from ...observability.logger import get_logger
from ...store.redis_queue import get_redis

router = APIRouter(prefix="/system", tags=["system"])
_log = get_logger(__name__)

_TIERS: tuple[str, ...] = ("vision", "heavy", "light", "tiny")


@router.get("/llm-queue")
async def llm_queue() -> dict[str, Any]:
    """Inflight slot counts vs cap per LLM tier.

    Reads `llm:concurrency:{tier}` counter keys that `tools/llm/queue.py`
    increments per acquire. Caps come from settings (`LLM_QUEUE_*_CONCURRENCY`
    env vars). When `LLM_QUEUE_ENABLED=false` the inflight counters still
    exist but the queue is bypassed — `enabled` flag tells the UI to
    de-emphasize the values.
    """
    s = get_settings()
    caps = {
        "vision": s.llm_queue_vision_concurrency,
        "heavy": s.llm_queue_heavy_concurrency,
        "light": s.llm_queue_light_concurrency,
        "tiny": s.llm_queue_tiny_concurrency,
    }
    tiers: dict[str, dict[str, int]] = {
        tier: {"cap": cap, "inflight": 0} for tier, cap in caps.items()
    }
    out: dict[str, Any] = {
        "enabled": s.llm_queue_enabled,
        "acquire_timeout_s": s.llm_queue_acquire_timeout_s,
        "tiers": tiers,
    }

    try:
        client = await get_redis()
        if client is None:
            out["source"] = "no_redis"
            return out
        for tier in _TIERS:
            try:
                val = await client.get(f"llm:concurrency:{tier}")
                if val is None:
                    continue
                tiers[tier]["inflight"] = max(0, int(val))
            except Exception as exc:  # noqa: BLE001
                _log.debug("system.llm_queue.tier_read_failed", tier=tier, error=str(exc)[:120])
        out["source"] = "redis"
    except Exception as exc:  # noqa: BLE001
        out["source"] = "error"
        out["error"] = str(exc)[:200]

    return out


@router.get("/ollama-ps")
async def ollama_ps() -> dict[str, Any]:
    """Proxy Ollama's `/api/ps` to expose loaded model VRAM footprint.

    Returns `{models: [{name, size_vram, size, expires_at, ...}]}` per Ollama
    schema. When provider is not Ollama or the daemon is unreachable, returns
    an empty `models` list with `status` set accordingly.

    NOTE: Ollama's `size_vram` field is bytes. Frontend divides by 1024**3 for GB.
    """
    s = get_settings()
    if s.llm_provider != "ollama":
        return {
            "status": "unavailable",
            "provider": s.llm_provider,
            "models": [],
            "host": None,
        }

    base = s.llm_base_url or "http://host.docker.internal:11434"
    url = f"{base.rstrip('/')}/api/ps"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "code": resp.status_code,
                    "models": [],
                    "host": base,
                }
            data = resp.json()
            models = data.get("models", [])
            total_vram = sum(int(m.get("size_vram", 0) or 0) for m in models)
            return {
                "status": "ok",
                "host": base,
                "models": models,
                "loaded_count": len(models),
                "total_vram_bytes": total_vram,
            }
    except httpx.TimeoutException:
        return {"status": "timeout", "host": base, "models": []}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "host": base,
            "error": str(exc)[:200],
            "models": [],
        }


@router.get("/agentic-sessions")
async def agentic_sessions() -> dict[str, Any]:
    """Live agentic Browser-Use sessions per container.

    Each agentic container (`agentic-a`, `agentic-b`) holds its own hostname-scoped
    Redis lock `autocrawl:agentic_active_run:<host>` while running a seed batch.
    The lock value is JSON `{"started_at": iso}` set by `scheduler._try_acquire_lock`.

    Returns one entry per active lock plus the global stop-requested flag.
    """
    out: dict[str, Any] = {
        "sessions": [],
        "stop_requested": False,
        "source": "redis",
    }
    try:
        client = await get_redis()
        if client is None:
            out["source"] = "no_redis"
            return out

        keys: list[str] = []
        try:
            async for key in client.scan_iter(match="autocrawl:agentic_active_run:*"):
                keys.append(key)
        except Exception as exc:  # noqa: BLE001
            _log.debug("system.agentic.scan_failed", error=str(exc)[:120])

        for key in keys:
            try:
                raw = await client.get(key)
                host = key.rsplit(":", 1)[-1]
                started_at: str | None = None
                if raw:
                    try:
                        payload = json.loads(raw)
                        started_at = payload.get("started_at")
                    except json.JSONDecodeError:
                        pass
                ttl_raw = await client.ttl(key)
                try:
                    ttl = int(ttl_raw) if ttl_raw is not None else None
                except (TypeError, ValueError):
                    ttl = None
                out["sessions"].append({
                    "host": host,
                    "started_at": started_at,
                    "lock_ttl_seconds": ttl,
                })
            except Exception as exc:  # noqa: BLE001
                _log.debug("system.agentic.read_failed", key=key, error=str(exc)[:120])

        try:
            stop = await client.get("autocrawl:agentic_stop_requested")
            out["stop_requested"] = bool(stop)
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        out["source"] = "error"
        out["error"] = str(exc)[:200]

    return out
