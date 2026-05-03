from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.repositories import expo_repo
from ..deps import get_db

router = APIRouter(prefix="/expos", tags=["expos"])


@router.get("")
async def list_expos(
    country: str | None = None,
    search: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await expo_repo.list_paginated(
        session, country=country, search=search, limit=limit, offset=offset
    )
    counts = await expo_repo.vendor_count_per_expo(session)
    payload = []
    for orm in items:
        d = expo_repo.orm_to_dict(orm)
        d["vendor_count"] = counts.get(orm.expo_id, 0)
        payload.append(d)
    return {"items": payload, "total": total, "limit": limit, "offset": offset}


@router.get("/{expo_id}")
async def get_expo(expo_id: str, session: AsyncSession = Depends(get_db)) -> dict:
    orm = await expo_repo.get_by_id(session, expo_id)
    if orm is None:
        raise HTTPException(status_code=404, detail=f"Expo {expo_id} not found")
    domains = await expo_repo.get_vendor_domains(session, expo_id)
    return expo_repo.orm_to_dict(orm, vendor_domains=domains)
