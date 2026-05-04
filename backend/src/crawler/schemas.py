"""Pydantic models for the AutoCrawler domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CrawlMode(str, Enum):
    DEV = "dev"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


class FailureRecord(BaseModel):
    where: str
    error: str
    url: str | None = None
    occurred_at: datetime = Field(default_factory=_utcnow)
    retryable: bool = True


class ExpoSource(str, Enum):
    TENTIMES = "10times"
    EVENTBRITE = "eventbrite"
    TRADEFAIRDATES = "tradefairdates"
    CONFERENCEINDEX = "conferenceindex"
    ALLCONFERENCES = "allconferences"
    NEVENTS = "nevents"
    EXPOPROMOTER = "expopromoter"
    EVENTSEYE = "eventseye"
    FIRECRAWL_SEARCH = "firecrawl_search"
    DDG = "duckduckgo"
    WIKIPEDIA = "wikipedia"
    GOOGLE_NEWS = "google_news"
    UNKNOWN = "unknown"


class Expo(BaseModel):
    """A discovered expo / trade-show."""

    expo_id: str  # canonical slug, e.g. "isc-west-2026"
    name: str
    source: ExpoSource = ExpoSource.UNKNOWN
    aggregator_url: AnyHttpUrl | None = None
    official_url: AnyHttpUrl | None = None
    location: str | None = None
    country: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    topics: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=_utcnow)
    discovery_query: str | None = None
    raw_metadata: dict = Field(default_factory=dict)
    pdf_brochure_urls: list[str] = Field(default_factory=list)

    @field_validator("expo_id")
    @classmethod
    def _normalize_id(cls, v: str) -> str:
        return v.strip().lower()


class SourceProvenance(BaseModel):
    """Where a piece of data came from. Attached to ExhibitorRef and Vendor.source_trail.

    For aggregator-sourced refs: type=aggregator, url=aggregator page URL.
    For PDF-sourced refs: type=pdf, url=PDF URL, plus pdf_filename, pdf_sha256,
    page (1-indexed), position (1-indexed within page), extraction_method.
    For search-resolved vendors: type=search, url=search hit URL.
    """

    type: Literal["aggregator", "pdf", "search", "manual"]
    url: AnyHttpUrl | None = None
    pdf_filename: str | None = None
    pdf_sha256: str | None = None
    page: int | None = None
    position: int | None = None  # nth vendor on the page
    extraction_method: str | None = None  # "pymupdf" | "pdfplumber_table" | "surya_ocr" | "search_llm_tiebreak"
    confidence: float | None = None
    context_snippet: str | None = None
    discovered_at: datetime = Field(default_factory=_utcnow)


class ExhibitorRef(BaseModel):
    """Reference to an exhibitor as found on an aggregator page or PDF brochure.

    For aggregator-sourced refs, `raw_url` points to the aggregator page (e.g.
    10times.com/...) — the resolver derives the vendor's real domain from there.
    For PDF-sourced refs, `raw_url` is None and `provenance` carries page/position.
    """

    expo_id: str
    name: str
    raw_url: AnyHttpUrl | None = None
    aggregator_domain: str | None = None
    booth: str | None = None
    short_description: str | None = None
    discovered_at: datetime = Field(default_factory=_utcnow)
    provenance: list[SourceProvenance] = Field(default_factory=list)


class VendorURL(BaseModel):
    """A canonical vendor URL after resolution. Domain MUST NOT be an aggregator."""

    domain: str  # canonical, lowercase, no scheme
    canonical_url: AnyHttpUrl
    resolved_from: AnyHttpUrl | None = None  # source URL (aggregator) or None for PDF/name origin
    expo_id: str
    exhibitor_name: str
    resolution_method: Literal[
        "schema_org",
        "visit_website_button",
        "outbound_link",
        "llm_tiebreak",
        "search_llm_tiebreak",  # NEW: from name-only resolver
        "manual",
    ]
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    resolved_at: datetime = Field(default_factory=_utcnow)
    provenance: list[SourceProvenance] = Field(default_factory=list)


class ContactPoint(BaseModel):
    type: Literal["email", "phone", "fax", "form", "other"] = "email"
    value: str
    label: str | None = None
    verified: bool | None = None
    verification_score: float | None = None
    verification_signals: dict | None = None


class Address(BaseModel):
    street: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    postal_code: str | None = None
    raw: str | None = None


class SocialLinks(BaseModel):
    linkedin: AnyHttpUrl | None = None
    twitter: AnyHttpUrl | None = None
    facebook: AnyHttpUrl | None = None
    youtube: AnyHttpUrl | None = None
    instagram: AnyHttpUrl | None = None
    github: AnyHttpUrl | None = None
    other: list[AnyHttpUrl] = Field(default_factory=list)


class FundingInfo(BaseModel):
    """Phase 1: usually empty (free tools can't reliably get this).
    Filled in Phase 2 with paid Crunchbase/Apollo."""

    total_raised_usd: float | None = None
    last_round: str | None = None
    last_round_at: date | None = None
    investors: list[str] = Field(default_factory=list)


VendorStatus = Literal[
    "enriched",
    "unresolved",
    "enrich_failed",
    "scope_rejected",
    "validation_rejected",
]


class Vendor(BaseModel):
    """Enriched vendor profile. Final output unit.

    Stage 4 schema: `vendor_id` UUID is the primary key. `domain` and
    `canonical_url` may be null when status != "enriched" (e.g. unresolved
    refs that failed to find a domain still get persisted with their PDF
    provenance for audit).
    """

    vendor_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: VendorStatus = "enriched"
    domain: str | None = None
    company_name: str
    canonical_url: AnyHttpUrl | None = None
    description: str | None = None
    tagline: str | None = None
    products: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)

    expos_seen: list[str] = Field(default_factory=list)  # expo_id list

    address: Address | None = None
    contacts: list[ContactPoint] = Field(default_factory=list)
    socials: SocialLinks = Field(default_factory=SocialLinks)

    funding: FundingInfo = Field(default_factory=FundingInfo)
    employee_count: int | None = None
    founded_year: int | None = None

    domain_age_days: int | None = None
    registrar: str | None = None
    registrar_country: str | None = None
    first_seen_wayback: date | None = None

    logo_url: AnyHttpUrl | None = None
    tech_stack: list[str] = Field(default_factory=list)

    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    enrichment_gap: list[str] = Field(default_factory=list)
    source_trail: list[SourceProvenance] = Field(default_factory=list)
    source_tags: list[str] = Field(default_factory=list)  # legacy free-form tags ("whois", "dns", ...)

    first_enriched_at: datetime = Field(default_factory=_utcnow)
    last_enriched_at: datetime = Field(default_factory=_utcnow)

    raw_extracts: dict = Field(default_factory=dict)

    # Localization: translated content lives on the main fields when language_code != "en".
    # Originals (English) are mirrored to *_original for audit and toggling in the UI.
    language_code: Literal["en", "id"] = "en"
    description_original: str | None = None
    tagline_original: str | None = None
    products_original: list[str] = Field(default_factory=list)
    industries_original: list[str] = Field(default_factory=list)
    translation_method: str | None = None
    translated_at: datetime | None = None


class RunSummary(BaseModel):
    """Daily/run-level rollup written by the reporter."""

    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    mode: CrawlMode = CrawlMode.NORMAL
    expos_discovered: int = 0
    exhibitors_extracted: int = 0
    vendors_resolved: int = 0
    vendors_enriched: int = 0
    vendors_dedup_skipped: int = 0
    failures: int = 0
    firecrawl_credits_used: int = 0
    openai_tokens_used: int = 0
    exhibitors_resolve_failed: int = 0
    exhibitors_enrich_failed: int = 0
    exhibitors_validation_rejected: int = 0
    exhibitors_scope_rejected: int = 0
    notes: str | None = None
