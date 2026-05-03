from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_db)) -> dict:
    db_status = "down"
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        return {"status": "degraded", "db": "down", "error": str(exc), "version": "0.1.0"}
    return {"status": "ok", "db": db_status, "version": "0.1.0"}
