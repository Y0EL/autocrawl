"""Redis-backed task queue + idempotency dedup.

Used to fan out work between the supervisor and worker subgraphs, and to
ensure the same (vendor, run_date) pair is never enriched twice.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import date
from typing import Any

from ..config import get_settings
from ..observability.logger import get_logger

_log = get_logger(__name__)
_CLIENT: Any | None = None
_LOCK = asyncio.Lock()


async def get_redis() -> Any | None:
    global _CLIENT
    async with _LOCK:
        if _CLIENT is not None:
            return _CLIENT
        try:
            import redis.asyncio as aioredis  # type: ignore

            client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
            await client.ping()
            _CLIENT = client
            return _CLIENT
        except Exception as e:  # noqa: BLE001
            _log.warning("redis.unavailable", error=str(e))
            return None


def task_id(domain: str, kind: str = "enrich", run_date: str | None = None) -> str:
    rd = run_date or date.today().isoformat()
    raw = f"{kind}:{domain.lower()}:{rd}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


async def claim(tid: str, *, ttl_seconds: int = 86400) -> bool:
    """SET NX with TTL. Returns True if we acquired the claim."""
    client = await get_redis()
    if client is None:
        return True  # without redis, allow everything (single-process mode)
    key = f"taskclaim:{tid}"
    return bool(await client.set(key, "1", nx=True, ex=ttl_seconds))


async def release(tid: str) -> None:
    client = await get_redis()
    if client is not None:
        await client.delete(f"taskclaim:{tid}")


async def push(stream: str, payload: dict) -> str | None:
    client = await get_redis()
    if client is None:
        return None
    flat = {k: str(v) for k, v in payload.items()}
    return await client.xadd(stream, flat)


async def pull(stream: str, group: str, consumer: str, *, count: int = 10, block_ms: int = 5000) -> list[tuple[str, dict]]:
    client = await get_redis()
    if client is None:
        return []
    try:
        await client.xgroup_create(stream, group, id="$", mkstream=True)
    except Exception:  # noqa: BLE001 — group exists
        pass
    try:
        resp = await client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block_ms)
    except Exception as e:  # noqa: BLE001
        _log.warning("redis.xreadgroup_failed", stream=stream, error=str(e))
        return []
    if not resp:
        return []
    out: list[tuple[str, dict]] = []
    for _stream_name, entries in resp:
        for entry_id, fields in entries:
            out.append((entry_id, fields))
    return out


async def ack(stream: str, group: str, entry_id: str) -> None:
    client = await get_redis()
    if client is None:
        return
    await client.xack(stream, group, entry_id)


async def queue_depth(stream: str) -> int:
    client = await get_redis()
    if client is None:
        return 0
    try:
        return int(await client.xlen(stream))
    except Exception:  # noqa: BLE001
        return 0
