from __future__ import annotations

from ..db.engine import get_sessionmaker
from ..db.repositories import expo_repo, run_repo, vendor_repo
from ..observability.logger import get_logger
from ..schemas import Expo, RunSummary, Vendor

_log = get_logger(__name__)


async def persist_vendor_to_db(vendor: Vendor) -> bool:
    sm = get_sessionmaker()
    try:
        async with sm() as session:
            await vendor_repo.upsert(session, vendor)
            await session.commit()
        return True
    except Exception as e:
        _log.warning("db_reporter.vendor_failed", domain=vendor.domain, error=str(e))
        return False


async def persist_expo_to_db(expo: Expo, vendor_domains: list[str] | None = None) -> bool:
    sm = get_sessionmaker()
    try:
        async with sm() as session:
            await expo_repo.upsert(session, expo, vendor_domains=vendor_domains or [])
            await session.commit()
        return True
    except Exception as e:
        _log.warning("db_reporter.expo_failed", expo_id=expo.expo_id, error=str(e))
        return False


async def append_expo_to_vendor(domain: str, expo_id: str) -> bool:
    sm = get_sessionmaker()
    try:
        async with sm() as session:
            ok = await vendor_repo.add_expo(session, domain, expo_id)
            await session.commit()
        return ok
    except Exception as e:
        _log.debug("db_reporter.merge_failed", domain=domain, error=str(e))
        return False


async def vendors_count() -> int:
    sm = get_sessionmaker()
    try:
        async with sm() as session:
            return await vendor_repo.count(session)
    except Exception:
        return 0


async def persist_run_summary(summary: RunSummary) -> bool:
    sm = get_sessionmaker()
    try:
        async with sm() as session:
            await run_repo.upsert(session, summary)
            await session.commit()
        return True
    except Exception as e:
        _log.warning("db_reporter.run_failed", run_id=summary.run_id, error=str(e))
        return False
