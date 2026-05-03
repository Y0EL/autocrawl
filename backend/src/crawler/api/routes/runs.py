from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.repositories import run_repo
from ...observability.logger import get_logger
from ...schemas import CrawlMode
from ..deps import get_db

_log = get_logger(__name__)
router = APIRouter(prefix="/runs", tags=["runs"])


_active_run: dict | None = None
_run_lock = asyncio.Lock()


class TriggerRequest(BaseModel):
    mode: str = "normal"


@router.get("")
async def list_runs(
    limit: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> dict:
    items = await run_repo.list_recent(session, limit=limit)
    payload = [run_repo.orm_to_dict(r) for r in items]
    return {"items": payload, "total": len(payload), "limit": limit, "offset": 0}


@router.get("/active")
async def get_active_run() -> dict:
    return {"active": _active_run}


async def _execute_run(mode: CrawlMode) -> None:
    global _active_run
    try:
        from ...graph import run_once

        _log.info("api.run_started", mode=mode.value)
        summary = await run_once(mode=mode)
        _log.info(
            "api.run_finished",
            run_id=summary.run_id,
            enriched=summary.vendors_enriched,
        )
    except Exception as exc:
        _log.exception("api.run_failed", error=str(exc))
    finally:
        async with _run_lock:
            _active_run = None


@router.post("/trigger", status_code=202)
async def trigger_run(payload: TriggerRequest | None = None) -> dict:
    global _active_run
    body = payload or TriggerRequest()
    try:
        mode = CrawlMode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {body.mode}") from exc

    async with _run_lock:
        if _active_run is not None:
            raise HTTPException(
                status_code=409,
                detail={"message": "A run is already active", "active": _active_run},
            )
        _active_run = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode.value,
            "status": "running",
        }

    asyncio.create_task(_execute_run(mode))

    return {"status": "accepted", "active": _active_run}
