"""CRUD buat FusionORM dan FusionEmailDraftORM, plus helper kandidat vendor."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FusionEmailDraftORM, FusionORM, VendorORM


async def create(
    session: AsyncSession,
    *,
    fusion: FusionORM,
    drafts: list[FusionEmailDraftORM],
) -> FusionORM:
    session.add(fusion)
    for d in drafts:
        d.fusion_id = fusion.fusion_id
        session.add(d)
    await session.flush()
    await session.refresh(fusion)
    return fusion


async def get_by_id(session: AsyncSession, fusion_id: str) -> FusionORM | None:
    res = await session.execute(select(FusionORM).where(FusionORM.fusion_id == fusion_id))
    return res.scalar_one_or_none()


async def list_paginated(
    session: AsyncSession, *, limit: int = 20, offset: int = 0
) -> list[FusionORM]:
    res = await session.execute(
        select(FusionORM).order_by(desc(FusionORM.created_at)).limit(limit).offset(offset)
    )
    return list(res.scalars().all())


async def mark_email_copied(session: AsyncSession, email_id: int) -> bool:
    existing = await session.get(FusionEmailDraftORM, email_id)
    if existing is None:
        return False
    existing.copied_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def vendors_with_verified_email(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> list[VendorORM]:
    """Filter vendor yang punya minimal 1 contact dengan type='email' dan verified=true.

    Pake JSONB containment di Postgres. Buat SQLite (test fixture), pake fallback
    yang ngambil semua row terus filter di Python (slow tapi ok buat test).
    """
    dialect = session.get_bind().dialect.name if session.get_bind() else "postgresql"

    if dialect == "postgresql":
        stmt = select(VendorORM).where(
            text("contacts @> '[{\"type\": \"email\", \"verified\": true}]'::jsonb")
        )
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(VendorORM.company_name.ilike(like))
        stmt = stmt.order_by(desc(VendorORM.confidence_score)).limit(limit).offset(offset)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    # SQLite fallback (test only): ambil semua, filter di Python.
    stmt = select(VendorORM)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(VendorORM.company_name.ilike(like))
    stmt = stmt.order_by(desc(VendorORM.confidence_score))
    res = await session.execute(stmt)
    rows = list(res.scalars().all())
    filtered = [
        v for v in rows
        if any(
            isinstance(c, dict) and c.get("type") == "email" and c.get("verified")
            for c in (v.contacts or [])
        )
    ]
    return filtered[offset:offset + limit]
