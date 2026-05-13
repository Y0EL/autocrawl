from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import Vendor
from ..models import VendorORM

# Maps common short codes / alternate spellings → canonical country name.
# Applied in country_breakdown() so the frontend sees consistent strings.
_COUNTRY_ALIASES: dict[str, str] = {
    "IN": "India", "IND": "India",
    "US": "United States", "USA": "United States",
    "UK": "United Kingdom", "GB": "United Kingdom", "GBR": "United Kingdom",
    "TR": "Turkey", "TUR": "Turkey", "Türkiye": "Turkey",
    "DE": "Germany", "DEU": "Germany",
    "FR": "France", "FRA": "France",
    "CN": "China", "CHN": "China",
    "JP": "Japan", "JPN": "Japan",
    "KR": "South Korea", "KOR": "South Korea",
    "AE": "United Arab Emirates", "ARE": "United Arab Emirates", "UAE": "United Arab Emirates",
    "IL": "Israel", "ISR": "Israel",
    "RU": "Russia", "RUS": "Russia", "Russian Federation": "Russia",
    "AU": "Australia", "AUS": "Australia",
    "CA": "Canada", "CAN": "Canada",
    "SG": "Singapore", "SGP": "Singapore",
    "QA": "Qatar", "QAT": "Qatar",
    "IT": "Italy", "ITA": "Italy",
    "ES": "Spain", "ESP": "Spain",
    "BR": "Brazil", "BRA": "Brazil",
    "PK": "Pakistan", "PAK": "Pakistan",
    "PL": "Poland", "POL": "Poland",
    "NL": "Netherlands", "NLD": "Netherlands",
    "SE": "Sweden", "SWE": "Sweden",
    "NO": "Norway", "NOR": "Norway",
    "FI": "Finland", "FIN": "Finland",
    "CH": "Switzerland", "CHE": "Switzerland",
    "AT": "Austria", "AUT": "Austria",
    "BE": "Belgium", "BEL": "Belgium",
    "PT": "Portugal", "PRT": "Portugal",
    "GR": "Greece", "GRC": "Greece",
    "SA": "Saudi Arabia", "SAU": "Saudi Arabia",
    "ZA": "South Africa", "ZAF": "South Africa",
    "EG": "Egypt", "EGY": "Egypt",
    "MY": "Malaysia", "MYS": "Malaysia",
    "TH": "Thailand", "THA": "Thailand",
    "ID": "Indonesia", "IDN": "Indonesia",
    "PH": "Philippines", "PHL": "Philippines",
    "TW": "Taiwan", "TWN": "Taiwan",
    "UA": "Ukraine", "UKR": "Ukraine",
    "CZ": "Czech Republic", "CZE": "Czech Republic",
    "HU": "Hungary", "HUN": "Hungary",
    "RO": "Romania", "ROU": "Romania",
    "BG": "Bulgaria", "BGR": "Bulgaria",
    "HR": "Croatia", "HRV": "Croatia",
    "SK": "Slovakia", "SVK": "Slovakia",
    "DK": "Denmark", "DNK": "Denmark",
    "IE": "Ireland", "IRL": "Ireland",
    "NZ": "New Zealand", "NZL": "New Zealand",
    "MX": "Mexico", "MEX": "Mexico",
    "AR": "Argentina", "ARG": "Argentina",
    "CO": "Colombia", "COL": "Colombia",
    "CL": "Chile", "CHL": "Chile",
    "NG": "Nigeria", "NGA": "Nigeria",
    "KE": "Kenya", "KEN": "Kenya",
    "JO": "Jordan", "JOR": "Jordan",
    "KW": "Kuwait", "KWT": "Kuwait",
    "BH": "Bahrain", "BHR": "Bahrain",
    "OM": "Oman", "OMN": "Oman",
}


def _to_orm_dict(v: Vendor) -> dict[str, Any]:
    return {
        "vendor_id": v.vendor_id,
        "status": v.status,
        "domain": v.domain,
        "company_name": v.company_name,
        "canonical_url": str(v.canonical_url) if v.canonical_url else None,
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
        "vendor_id": getattr(orm, "vendor_id", None),
        "status": getattr(orm, "status", "enriched") or "enriched",
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
        # Phase 5 — Product catalog + DOI scoring
        "products_detailed": getattr(orm, "products_detailed", None) or [],
        "overall_scope_score": getattr(orm, "overall_scope_score", 0.0) or 0.0,
        "focus_summary": getattr(orm, "focus_summary", None),
        "domain_of_interest": getattr(orm, "domain_of_interest", None) or [],
    }


async def upsert(session: AsyncSession, vendor: Vendor) -> VendorORM:
    """Upsert a vendor.

    Dual-key behavior:
    - If vendor.domain is set, dedup by domain (UPDATE if exists, else INSERT).
    - If vendor.domain is None (status=unresolved), always INSERT a new row
      keyed by vendor_id. Multiple unresolved candidates with the same name
      can coexist until a resolver run later promotes one of them.
    """
    payload = _to_orm_dict(vendor)
    existing: VendorORM | None = None
    if vendor.domain:
        stmt = select(VendorORM).where(VendorORM.domain == vendor.domain)
        existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        existing = VendorORM(**payload)
        session.add(existing)
    else:
        for key, value in payload.items():
            if key in ("first_enriched_at", "vendor_id"):
                continue
            setattr(existing, key, value)
        merged_expos = list(dict.fromkeys((existing.expos_seen or []) + (payload["expos_seen"] or [])))
        existing.expos_seen = merged_expos
    await session.flush()

    # Create expo_vendors links for any expos_seen entry that has a matching ExpoORM record.
    if existing.domain and existing.expos_seen:
        from ..models import ExpoORM, ExpoVendorORM
        for expo_id in existing.expos_seen:
            expo_orm = await session.get(ExpoORM, expo_id)
            if expo_orm is None:
                continue
            link = await session.get(ExpoVendorORM, (expo_id, existing.domain))
            if link is None:
                session.add(ExpoVendorORM(expo_id=expo_id, vendor_domain=existing.domain))
        await session.flush()

    return existing


async def get_by_domain(session: AsyncSession, domain: str) -> VendorORM | None:
    stmt = select(VendorORM).where(VendorORM.domain == domain).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_vendor_id(session: AsyncSession, vendor_id: str) -> VendorORM | None:
    return await session.get(VendorORM, vendor_id)


async def update_product_catalog(
    session: AsyncSession,
    vendor_id: str,
    *,
    products_detailed: list[dict[str, Any]],
    overall_scope_score: float,
    focus_summary: str | None,
    domain_of_interest: list[str],
) -> bool:
    """Phase 5 — replace the product catalog + scope fields on one vendor.
    Returns True if a row was updated. Idempotent — full replace, no merge."""
    orm = await session.get(VendorORM, vendor_id)
    if orm is None:
        return False
    orm.products_detailed = products_detailed
    orm.overall_scope_score = float(overall_scope_score)
    orm.focus_summary = focus_summary
    orm.domain_of_interest = list(domain_of_interest)
    orm.last_enriched_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def add_expo(session: AsyncSession, domain: str, expo_id: str) -> bool:
    stmt = select(VendorORM).where(VendorORM.domain == domain).limit(1)
    orm = (await session.execute(stmt)).scalar_one_or_none()
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
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "last_enriched_at:desc",
) -> tuple[list[VendorORM], int]:
    stmt = select(VendorORM)
    count_stmt = select(func.count()).select_from(VendorORM)

    if status:
        cond = VendorORM.status == status
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    if search:
        like = f"%{search.lower()}%"
        cond = func.lower(func.coalesce(VendorORM.domain, "")).like(like) | func.lower(VendorORM.company_name).like(like)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    if industry:
        cond = VendorORM.industries.contains([industry])  # JSONB contains
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    if country:
        from sqlalchemy import or_, cast, String
        # address->>'country' is the richest source; registrar_country is whois fallback.
        address_country = cast(VendorORM.address["country"], String)
        cond = or_(
            address_country == country,
            VendorORM.registrar_country == country,
        )
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
    """Vendor count grouped by country.

    Uses COALESCE(address->>'country', registrar_country) so the richer
    address.country JSONB field is preferred (populated by the enricher for
    most vendors) with whois registrar_country as fallback. The expo_vendors
    path was removed because that join table is only populated when the
    deterministic crawler runs; the agentic crawler writes expos_seen but
    does not create expo_vendors rows.
    """
    from sqlalchemy import text
    # Pull raw country strings — limit is generous to capture aliases before dedup
    sql = text("""
        SELECT country, COUNT(*) AS cnt
        FROM (
            SELECT COALESCE(address->>'country', registrar_country) AS country
            FROM vendors
            WHERE COALESCE(address->>'country', registrar_country) IS NOT NULL
              AND COALESCE(address->>'country', registrar_country) != ''
              AND LOWER(COALESCE(address->>'country', registrar_country)) NOT IN
                  ('unknown', 'na', 'n/a', 'none', '-', 'other', 'worldwide', 'global', 'international')
        ) sub
        GROUP BY country
        ORDER BY cnt DESC
        LIMIT :lim
    """)
    rows = (await session.execute(sql, {"lim": limit * 4})).all()
    # Normalize aliases → canonical names, then re-aggregate
    merged: dict[str, int] = {}
    for country, cnt in rows:
        canonical = _COUNTRY_ALIASES.get(country, country)
        merged[canonical] = merged.get(canonical, 0) + int(cnt)
    sorted_items = sorted(merged.items(), key=lambda kv: -kv[1])
    return [{"country": k, "count": v} for k, v in sorted_items[:limit]]


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
