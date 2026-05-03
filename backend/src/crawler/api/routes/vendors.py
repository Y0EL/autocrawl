from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.repositories import vendor_repo
from ..deps import get_db

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("")
async def list_vendors(
    industry: str | None = None,
    country: str | None = None,
    search: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("last_enriched_at:desc"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await vendor_repo.list_paginated(
        session,
        industry=industry,
        country=country,
        search=search,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    return {
        "items": [vendor_repo.orm_to_dict(v) for v in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{domain}")
async def get_vendor(domain: str, session: AsyncSession = Depends(get_db)) -> dict:
    orm = await vendor_repo.get_by_domain(session, domain)
    if orm is None:
        raise HTTPException(status_code=404, detail=f"Vendor {domain} not found")
    return vendor_repo.orm_to_dict(orm)
