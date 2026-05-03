"""Reporter — persist Expo / Vendor records and update the master manifest.

Also handles the merge-into-existing case for the dedup hit (adds new
expo_id to a vendor we've already enriched).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import get_settings
from ..observability.logger import get_logger
from ..observability.metrics import phase_2_progress, vendors_enriched_total
from ..schemas import Expo, Vendor
from ..store.db_reporter import (
    append_expo_to_vendor,
    persist_expo_to_db,
    persist_vendor_to_db,
    vendors_count as db_vendors_count,
)
from ..store.json_reporter import (
    manifest_vendor_count,
    update_manifest,
    write_expo,
    write_vendor,
)
from ..store.vector_store import add_vendor as add_vector
from ..tools.url_utils import canonical_domain
from .scope_classifier import is_in_scope
from .validator import validate

_log = get_logger(__name__)


def _vendor_path(domain: str) -> Path:
    settings = get_settings()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in domain.lower())
    return settings.data_dir / "reports" / "vendors" / f"{safe}.json"


async def persist_vendor(vendor: Vendor) -> bool:
    is_valid, completeness, issues = validate(vendor)
    vendor.confidence_score = max(vendor.confidence_score, completeness)
    if not is_valid:
        _log.info("reporter.vendor_rejected_validation", domain=vendor.domain, issues=issues)
        return False

    # Industry scope gate: reject hotels, news media, academic, event platforms.
    in_scope, scope_meta = await is_in_scope(vendor)
    vendor.raw_extracts["scope"] = scope_meta
    if not in_scope:
        _log.info(
            "reporter.vendor_rejected_out_of_scope",
            domain=vendor.domain,
            industry=scope_meta.get("industry_tag"),
            reason=scope_meta.get("scope_reason", "")[:200],
        )
        return False

    if scope_meta.get("industry_tag") and scope_meta["industry_tag"] != "other":
        if scope_meta["industry_tag"] not in vendor.industries:
            vendor.industries = [scope_meta["industry_tag"], *vendor.industries]

    await write_vendor(vendor)
    await update_manifest(vendor=vendor)
    await persist_vendor_to_db(vendor)
    await add_vector(
        vendor_id=vendor.domain,
        name=vendor.company_name,
        domain=vendor.domain,
        tagline=vendor.tagline,
        payload={"url": str(vendor.canonical_url), "industry": scope_meta.get("industry_tag", "")},
    )
    await _maybe_emit_phase_2_unlock()
    _log.info(
        "reporter.vendor_persisted",
        domain=vendor.domain,
        completeness=completeness,
        industry=scope_meta.get("industry_tag"),
    )
    return True


async def merge_existing_with_expo(domain: str, expo_id: str) -> bool:
    """Add `expo_id` to an existing vendor record (dedup-hit path)."""
    await append_expo_to_vendor(domain, expo_id)
    path = _vendor_path(domain)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    expos = list(data.get("expos_seen") or [])
    if expo_id in expos:
        return False
    expos.append(expo_id)
    data["expos_seen"] = expos
    try:
        from datetime import datetime, timezone

        data["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        _log.info("reporter.merged_expo_into_existing", domain=domain, expo_id=expo_id)
        return True
    except Exception as e:  # noqa: BLE001
        _log.warning("reporter.merge_failed", domain=domain, error=str(e))
        return False


async def persist_expo(expo: Expo, vendor_domains: list[str]) -> None:
    canonicalized = sorted({canonical_domain(d) for d in vendor_domains if d})
    await write_expo(expo, vendor_domains=canonicalized)
    await update_manifest(expo=expo)
    await persist_expo_to_db(expo, vendor_domains=canonicalized)


async def db_vendor_count_with_fallback() -> int:
    count = await db_vendors_count()
    if count == 0:
        count = await manifest_vendor_count()
    return count


async def _maybe_emit_phase_2_unlock() -> None:
    settings = get_settings()
    count = await manifest_vendor_count()
    if settings.phase_2_vendor_threshold > 0:
        ratio = count / settings.phase_2_vendor_threshold
        phase_2_progress.set(ratio)
    if count == settings.phase_2_vendor_threshold:
        _log.warning(
            "phase_2_unlock_eligible",
            vendors=count,
            message="Phase 1 exit gate reached. Time to consider paid enrichment tier.",
        )


__all__ = [
    "persist_vendor",
    "persist_expo",
    "merge_existing_with_expo",
    "vendors_enriched_total",  # re-exported for graph builder
]
