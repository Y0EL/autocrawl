from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import Vendor
from ..models import VendorORM


def _to_orm_dict(v: Vendor) -> dict[str, Any]:
    return {
        "domain": v.domain,
        "company_name": v.company_name,
        "canonical_url": str(v.canonical_url),
        "description": v.description,
        "tagline": v.tagline,
        "industries": list(v.industries or []),
        "products": list(v.products or []),
        "expos_seen": list(v.expos_seen or []),
        "tech_stack": list(v.tech_stack or []),
        "enrichment_gap": list(v.enrichment_gap or []),
        "source_tags": list(v.source_tags or []),
        "address": v.address.model_dump(mode="json") if v.address else None,
        "socials": v.socials.model_dump(mode="json") if v.socials else {},
        "funding": v.funding.model_dump(mode="json") if v.funding else {},
        "contacts": [c.model_dump(mode="json") for c in (v.contacts or [])],
        "source_trail": [s.model_dump(mode="json") for s in (v.source_trail or [])],
        "raw_extracts": dict(v.raw_extracts or {}),
        "employee_count": v.employee_count,
        "founded_year": v.founded_year,
        "domain_age_days": v.domain_age_days,
        "registrar": v.registrar,
        "registrar_country": v.registrar_country,
        "first_seen_wayback": v.first_seen_wayback,
        "logo_url": str(v.logo_url) if v.logo_url else None,
        "confidence_score": v.confidence_score,
        "first_enriched_at": v.first_enriched_at,
        "last_enriched_at": v.last_enriched_at,
        "language_code": v.language_code,
        "description_original": v.description_original,
        "tagline_original": v.tagline_original,
        "products_original": list(v.products_original or []),
        "industries_original": list(v.industries_original or []),
        "translation_method": v.translation_method,
        "translated_at": v.translated_at,
    }


def orm_to_dict(orm: VendorORM) -> dict[str, Any]:
    return {
        "domain": orm.domain,
        "company_name": orm.company_name,
        "canonical_url": orm.canonical_url,
        "description": orm.description,
        "tagline": orm.tagline,
        "industries": orm.industries or [],
        "products": orm.products or [],
        "expos_seen": orm.expos_seen or [],
        "tech_stack": orm.tech_stack or [],
        "enrichment_gap": orm.enrichment_gap or [],
        "source_tags": orm.source_tags or [],
        "address": orm.address,
        "socials": orm.socials or {},
        "funding": orm.funding or {},
        "contacts": orm.contacts or [],
        "source_trail": orm.source_trail or [],
        "raw_extracts": orm.raw_extracts or {},
        "employee_count": orm.employee_count,
        "founded_year": orm.founded_year,
        "domain_age_days": orm.domain_age_days,
        "registrar": orm.registrar,
        "registrar_country": orm.registrar_country,
        "first_seen_wayback": orm.first_seen_wayback.isoformat() if orm.first_seen_wayback else None,
        "logo_url": orm.logo_url,
        "confidence_score": orm.confidence_score,
        "first_enriched_at": orm.first_enriched_at.isoformat() if orm.first_enriched_at else None,
        "last_enriched_at": orm.last_enriched_at.isoformat() if orm.last_enriched_at else None,
        "language_code": orm.language_code or "en",
        "description_original": orm.description_original,
        "tagline_original": orm.tagline_original,
        "products_original": orm.products_original or [],
        "industries_original": orm.industries_original or [],
        "translation_method": orm.translation_method,
        "translated_at": orm.translated_at.isoformat() if orm.translated_at else None,
    }


async def upsert(session: AsyncSession, vendor: Vendor) -> VendorORM:
    payload = _to_orm_dict(vendor)
    existing = await session.get(VendorORM, vendor.domain)
    if existing is None:
        existing = VendorORM(**payload)
        session.add(existing)
    else:
        for key, value in payload.items():
            if key == "first_enriched_at":
                continue
            setattr(existing, key, value)
        merged_expos = list(dict.fromkeys((existing.expos_seen or []) + (payload["expos_seen"] or [])))
        existing.expos_seen = merged_expos
    await session.flush()
    return existing


async def get_by_domain(session: AsyncSession, domain: str) -> VendorORM | None:
    return await session.get(VendorORM, domain)


async def add_expo(session: AsyncSession, domain: str, expo_id: str) -> bool:
    orm = await session.get(VendorORM, domain)
    if orm is None:
        return False
    if expo_id in (orm.expos_seen or []):
        return False
    orm.expos_seen = list(orm.expos_seen or []) + [expo_id]
    orm.last_enriched_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def list_paginated(
    session: AsyncSession,
    *,
    industry: str | None = None,
    country: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "last_enriched_at:desc",
) -> tuple[list[VendorORM], int]:
    stmt = select(VendorORM)
    count_stmt = select(func.count()).select_from(VendorORM)

    if search:
        like = f"%{search.lower()}%"
        cond = func.lower(VendorORM.domain).like(like) | func.lower(VendorORM.company_name).like(like)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    if industry:
        cond = VendorORM.industries.contains([industry])  # JSONB contains
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    if country:
        cond = VendorORM.registrar_country == country
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    field, _, direction = sort.partition(":")
    column = getattr(VendorORM, field, VendorORM.last_enriched_at)
    stmt = stmt.order_by(desc(column) if direction != "asc" else asc(column))
    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    items = list(result.scalars().all())
    total = (await session.execute(count_stmt)).scalar_one()
    return items, int(total)


async def count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(VendorORM))
    return int(result.scalar_one())


async def industry_breakdown(session: AsyncSession) -> list[dict[str, Any]]:
    rows = (await session.execute(select(VendorORM.industries))).scalars().all()
    counts: dict[str, int] = {}
    for arr in rows:
        for tag in arr or []:
            counts[tag] = counts.get(tag, 0) + 1
    return [{"tag": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


async def country_breakdown(session: AsyncSession, *, limit: int = 10) -> list[dict[str, Any]]:
    stmt = (
        select(VendorORM.registrar_country, func.count())
        .where(VendorORM.registrar_country.isnot(None))
        .group_by(VendorORM.registrar_country)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [{"country": r[0], "count": int(r[1])} for r in rows]


async def source_type_breakdown(session: AsyncSession) -> list[dict[str, Any]]:
    rows = (await session.execute(select(VendorORM.source_trail))).scalars().all()
    counts: dict[str, int] = {}
    for trail in rows:
        types = {entry.get("type") for entry in (trail or []) if isinstance(entry, dict)}
        for t in types:
            if t:
                counts[t] = counts.get(t, 0) + 1
    return [{"type": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


async def timeline(session: AsyncSession, *, days: int = 30) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            func.date(VendorORM.first_enriched_at).label("d"),
            func.count().label("c"),
        )
        .where(VendorORM.first_enriched_at >= cutoff)
        .group_by(func.date(VendorORM.first_enriched_at))
        .order_by(func.date(VendorORM.first_enriched_at))
    )
    rows = (await session.execute(stmt)).all()
    return [{"date": r[0].isoformat() if r[0] else None, "vendors_added": int(r[1])} for r in rows]
