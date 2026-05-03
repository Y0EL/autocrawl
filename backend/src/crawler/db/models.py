from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


JsonType = JSONB().with_variant(JSON(), "sqlite")


class VendorORM(Base):
    __tablename__ = "vendors"

    domain: Mapped[str] = mapped_column(String(253), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tagline: Mapped[str | None] = mapped_column(Text)

    industries: Mapped[list[str]] = mapped_column(JsonType, default=list)
    products: Mapped[list[str]] = mapped_column(JsonType, default=list)
    expos_seen: Mapped[list[str]] = mapped_column(JsonType, default=list)
    tech_stack: Mapped[list[str]] = mapped_column(JsonType, default=list)
    enrichment_gap: Mapped[list[str]] = mapped_column(JsonType, default=list)
    source_tags: Mapped[list[str]] = mapped_column(JsonType, default=list)

    address: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    socials: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    funding: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    contacts: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    source_trail: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    raw_extracts: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    employee_count: Mapped[int | None] = mapped_column(Integer)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    domain_age_days: Mapped[int | None] = mapped_column(Integer)
    registrar: Mapped[str | None] = mapped_column(String(200))
    registrar_country: Mapped[str | None] = mapped_column(String(10))
    first_seen_wayback: Mapped[date | None] = mapped_column(Date)
    logo_url: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    language_code: Mapped[str] = mapped_column(String(2), default="en", server_default="en", nullable=False)
    description_original: Mapped[str | None] = mapped_column(Text)
    tagline_original: Mapped[str | None] = mapped_column(Text)
    products_original: Mapped[list[str]] = mapped_column(JsonType, default=list)
    industries_original: Mapped[list[str]] = mapped_column(JsonType, default=list)
    translation_method: Mapped[str | None] = mapped_column(String(60))
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    first_enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    last_enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_vendors_country", "registrar_country"),
        Index("ix_vendors_confidence_desc", "confidence_score"),
    )


class ExpoORM(Base):
    __tablename__ = "expos"

    expo_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="unknown")
    aggregator_url: Mapped[str | None] = mapped_column(Text)
    official_url: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(500))
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    start_date: Mapped[date | None] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date)
    topics: Mapped[list[str]] = mapped_column(JsonType, default=list)
    discovery_query: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False, index=True
    )
    pdf_brochure_urls: Mapped[list[str]] = mapped_column(JsonType, default=list)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    vendor_links: Mapped[list[ExpoVendorORM]] = relationship(
        back_populates="expo", cascade="all, delete-orphan"
    )


class ExpoVendorORM(Base):
    __tablename__ = "expo_vendors"

    expo_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("expos.expo_id", ondelete="CASCADE"), primary_key=True
    )
    vendor_domain: Mapped[str] = mapped_column(
        String(253), ForeignKey("vendors.domain", ondelete="CASCADE"), primary_key=True
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )

    expo: Mapped[ExpoORM] = relationship(back_populates="vendor_links")


class PdfORM(Base):
    __tablename__ = "pdfs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    expo_id: Mapped[str | None] = mapped_column(
        String(200), ForeignKey("expos.expo_id", ondelete="SET NULL"), index=True
    )
    sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    vendors_found: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False, index=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class RunORM(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(20), default="normal")
    expos_discovered: Mapped[int] = mapped_column(Integer, default=0)
    exhibitors_extracted: Mapped[int] = mapped_column(Integer, default=0)
    vendors_resolved: Mapped[int] = mapped_column(Integer, default=0)
    vendors_enriched: Mapped[int] = mapped_column(Integer, default=0)
    vendors_dedup_skipped: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    firecrawl_credits_used: Mapped[int] = mapped_column(Integer, default=0)
    openai_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
