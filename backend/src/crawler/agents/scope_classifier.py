"""Industry scope classifier.

After enrichment, ask the LLM whether the vendor is plausibly a
security / defense / cyber industry company. Hotels, news media,
universities, and event platforms that slip past the URL resolver
are caught here.

Returns (is_in_scope: bool, industry_tag: str, reason: str).
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..observability.logger import get_logger
from ..observability.metrics import errors_total
from ..schemas import Vendor
from ..tools.llm.openai_client import chat

_log = get_logger(__name__)


class _ScopeJudgment(BaseModel):
    is_in_scope: bool = Field(default=False, description="True if vendor sells security/defense/cyber/police/border products or services")
    industry_tag: str = Field(default="other", description="One of: defense, cybersecurity, law_enforcement, surveillance, border_control, critical_infra, dual_use, hotel, news_media, academia, event_platform, other")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = Field(default="")


_SYSTEM = SystemMessage(
    content=(
        "You judge whether a company belongs to the security / defense / "
        "cybersecurity / law-enforcement / surveillance / border-control / "
        "critical-infrastructure-protection industry. These are the only "
        "industries IN scope.\n\n"
        "REJECT (out of scope):\n"
        "- Hotels, hospitality, hotel chains, vacation rentals\n"
        "- News organizations, magazines, blogs, editorial publishers\n"
        "- Universities, academic institutions, research conferences\n"
        "- Generic event platforms, ticketing, conference hosts\n"
        "- General consulting firms (unless they specifically serve "
        "  defense/security clients as primary segment)\n"
        "- Banks, real estate, retail, marketing agencies\n\n"
        "ACCEPT (in scope):\n"
        "- Defense manufacturers, military equipment, weapons systems\n"
        "- Cybersecurity software / services / appliances\n"
        "- Police / law enforcement / tactical gear\n"
        "- Surveillance, ISR, drones, biometrics\n"
        "- Border control, customs, immigration tech\n"
        "- Critical-infrastructure security (SCADA, power grid, oil/gas)\n"
        "- Dual-use companies whose security/defense vertical is meaningful\n\n"
        "Be strict. When evidence is weak or the vendor looks like a "
        "tangential venue/sponsor, set is_in_scope=false."
    )
)


async def classify_vendor(vendor: Vendor) -> _ScopeJudgment:
    profile = (
        f"Domain: {vendor.domain}\n"
        f"Company: {vendor.company_name}\n"
        f"Tagline: {vendor.tagline or '(none)'}\n"
        f"Description: {(vendor.description or '')[:1500]}\n"
        f"Products: {', '.join(vendor.products[:20]) or '(none)'}\n"
        f"Industries (claimed): {', '.join(vendor.industries[:10]) or '(none)'}\n"
        f"Expos seen: {', '.join(vendor.expos_seen[:8])}\n"
    )
    user = HumanMessage(content=profile)
    try:
        result = await chat([_SYSTEM, user], use_heavy=False, response_format=_ScopeJudgment)
        return result if isinstance(result, _ScopeJudgment) else _ScopeJudgment()
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="scope", category="llm_judgment").inc()
        _log.warning("scope_classifier.failed", domain=vendor.domain, error=str(e))
        # On failure, default to in_scope=True so we don't drop legit vendors
        # due to LLM downtime. The aggregator blacklist + completeness gate
        # already provide a baseline filter.
        return _ScopeJudgment(is_in_scope=True, industry_tag="other", confidence=0.0, reason="classifier_failed")


async def is_in_scope(vendor: Vendor) -> tuple[bool, dict]:
    judgment = await classify_vendor(vendor)
    meta = {
        "industry_tag": judgment.industry_tag,
        "scope_confidence": judgment.confidence,
        "scope_reason": judgment.reason,
    }
    return judgment.is_in_scope, meta
