from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import Expo
from ..models import ExpoORM, ExpoVendorORM, VendorORM


def _to_orm_dict(e: Expo) -> dict[str, Any]:
    return {
        "expo_id": e.expo_id,
        "name": e.name,
        "source": e.source.value if hasattr(e.source, "value") else str(e.source),
        "aggregator_url": str(e.aggregator_url) if e.aggregator_url else None,
        "official_url": str(e.official_url) if e.official_url else None,
        "location": e.location,
        "country": e.country,
        "start_date": e.start_date,
        "end_date": e.end_date,
        "topics": list(e.topics or []),
        "discovery_query": e.discovery_query,
        "discovered_at": e.discovered_at,
        "pdf_brochure_urls": list(e.pdf_brochure_urls or []),
        "raw_metadata": dict(e.raw_metadata or {}),
    }


def orm_to_dict(orm: ExpoORM, vendor_domains: list[str] | None = None) -> dict[str, Any]:
    return {
        "expo_id": orm.expo_id,
        "name": orm.name,
        "source": orm.source,
        "aggregator_url": orm.aggregator_url,
        "official_url": orm.official_url,
        "location": orm.location,
        "country": orm.country,
        "start_date": orm.start_date.isoformat() if orm.start_date else None,
        "end_date": orm.end_date.isoformat() if orm.end_date else None,
        "topics": orm.topics or [],
        "discovery_query": orm.discovery_query,
        "discovered_at": orm.discovered_at.isoformat() if orm.discovered_at else None,
        "pdf_brochure_urls": orm.pdf_brochure_urls or [],
        "vendor_domains": vendor_domains or [],
    }


async def upsert(session: AsyncSession, expo: Expo, vendor_domains: list[str] | None = None) -> ExpoORM:
    payload = _to_orm_dict(expo)
    existing = await session.get(ExpoORM, expo.expo_id)
    if existing is None:
        existing = ExpoORM(**payload)
        session.add(existing)
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
    await session.flush()

    for domain in vendor_domains or []:
        existing_vendor = await session.get(VendorORM, domain)
        if existing_vendor is None:
            continue
        link = await session.get(ExpoVendorORM, (expo.expo_id, domain))
        if link is None:
            session.add(ExpoVendorORM(expo_id=expo.expo_id, vendor_domain=domain))
    await session.flush()
    return existing


async def get_by_id(session: AsyncSession, expo_id: str) -> ExpoORM | None:
    return await session.get(ExpoORM, expo_id)


async def get_vendor_domains(session: AsyncSession, expo_id: str) -> list[str]:
    stmt = select(ExpoVendorORM.vendor_domain).where(ExpoVendorORM.expo_id == expo_id)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


async def list_paginated(
    session: AsyncSession,
    *,
    country: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ExpoORM], int]:
    stmt = select(ExpoORM)
    count_stmt = select(func.count()).select_from(ExpoORM)
    if search:
        like = f"%{search.lower()}%"
        cond = func.lower(ExpoORM.name).like(like) | func.lower(ExpoORM.expo_id).like(like)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if country:
        stmt = stmt.where(ExpoORM.country == country)
        count_stmt = count_stmt.where(ExpoORM.country == country)
    stmt = stmt.order_by(desc(ExpoORM.discovered_at)).limit(limit).offset(offset)
    items = list((await session.execute(stmt)).scalars().all())
    total = int((await session.execute(count_stmt)).scalar_one())
    return items, total


async def count(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(ExpoORM))).scalar_one())


async def vendor_count_per_expo(session: AsyncSession) -> dict[str, int]:
    stmt = (
        select(ExpoVendorORM.expo_id, func.count())
        .group_by(ExpoVendorORM.expo_id)
    )
    rows = (await session.execute(stmt)).all()
    return {r[0]: int(r[1]) for r in rows}
