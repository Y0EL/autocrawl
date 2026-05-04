from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.repositories import vendor_repo
from ...observability.logger import get_logger
from ..deps import get_db

_log = get_logger(__name__)
router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("")
async def list_vendors(
    industry: str | None = None,
    country: str | None = None,
    search: str | None = None,
    status: str | None = None,
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
        status=status,
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


@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str, session: AsyncSession = Depends(get_db)) -> dict:
    """Lookup by vendor_id UUID first, fall back to domain for backwards compat."""
    orm = await vendor_repo.get_by_vendor_id(session, vendor_id)
    if orm is None:
        orm = await vendor_repo.get_by_domain(session, vendor_id)
    if orm is None:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    return vendor_repo.orm_to_dict(orm)


@router.post("/{vendor_id}/deepen", status_code=202)
async def deepen_vendor(vendor_id: str, session: AsyncSession = Depends(get_db)) -> dict:
    """Trigger a single-vendor re-enrichment in the background.

    Picks up from current state: if domain is set, re-runs enricher to refresh
    description, tagline, contacts, completeness. If domain is null (unresolved),
    re-runs name resolver first, then enricher. Persists in-place.
    """
    orm = await vendor_repo.get_by_vendor_id(session, vendor_id)
    if orm is None:
        orm = await vendor_repo.get_by_domain(session, vendor_id)
    if orm is None:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")

    snapshot = vendor_repo.orm_to_dict(orm)
    asyncio.create_task(_deepen_task(snapshot))
    return {
        "status": "scheduled",
        "vendor_id": snapshot.get("vendor_id"),
        "domain": snapshot.get("domain"),
        "current_status": snapshot.get("status"),
        "current_score": snapshot.get("confidence_score"),
    }


async def _deepen_task(snapshot: dict) -> None:
    """Run resolve (if needed) + enrich + persist for one vendor row."""
    try:
        from ...agents import enricher as enricher_agent
        from ...agents import name_resolver as name_resolver_agent
        from ...agents import reporter as reporter_agent
        from ...schemas import VendorURL

        domain = snapshot.get("domain")
        canonical = snapshot.get("canonical_url")
        company = snapshot.get("company_name") or ""
        expos_seen = snapshot.get("expos_seen") or []
        first_expo = expos_seen[0] if expos_seen else ""

        if not domain or not canonical:
            resolved = await name_resolver_agent.resolve_from_name(
                company,
                expo_id=first_expo or "",
                context_snippet=snapshot.get("description") or None,
            )
            if resolved is None:
                _log.info("vendors.deepen_unresolved", vendor_id=snapshot.get("vendor_id"))
                return
            vurl = resolved
        else:
            vurl = VendorURL(
                domain=domain,
                canonical_url=canonical,
                resolved_from=None,
                expo_id=first_expo or "",
                exhibitor_name=company,
                resolution_method="manual",
                confidence=1.0,
            )

        vendor = await enricher_agent.enrich_vendor(vurl)
        if vendor is None:
            _log.info("vendors.deepen_enrich_none", domain=vurl.domain)
            return

        # Preserve identity + lineage from the existing row
        vendor.vendor_id = snapshot.get("vendor_id") or vendor.vendor_id
        merged_expos = list(dict.fromkeys((expos_seen or []) + (vendor.expos_seen or [])))
        vendor.expos_seen = merged_expos
        vendor.status = "enriched"

        persisted, reason = await reporter_agent.persist_vendor(vendor)
        _log.info(
            "vendors.deepen_done",
            vendor_id=snapshot.get("vendor_id"),
            domain=vendor.domain,
            persisted=persisted,
            reason=reason,
            score=vendor.confidence_score,
        )
    except Exception as e:  # noqa: BLE001
        _log.warning("vendors.deepen_failed", vendor_id=snapshot.get("vendor_id"), error=str(e)[:200])
