"""Typer CLI for AutoCrawler.

Commands:
  crawl run        — single end-to-end run
  crawl schedule   — start the 24/7 scheduler (foreground)
  crawl report     — print summary stats
  crawl health     — quick connectivity check
  crawl backfill   — re-process a specific topic
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .observability.logger import configure_logging, get_logger
from .schemas import CrawlMode

app = typer.Typer(help="AutoCrawler — 24/7 expo → vendor enrichment.")
console = Console()
_log = get_logger(__name__)


def _resolve_mode(mode: str | None) -> CrawlMode:
    if not mode:
        return get_settings().mode
    try:
        return CrawlMode(mode)
    except ValueError:
        typer.echo(f"Unknown mode: {mode}. Use one of: dev, normal, aggressive.", err=True)
        raise typer.Exit(1) from None


@app.command()
def run(
    mode: str = typer.Option(None, help="dev | normal | aggressive (overrides .env)"),
    metrics_port: int = typer.Option(0, help="If > 0, expose /metrics on this port for the run"),
) -> None:
    """One-shot end-to-end run."""
    configure_logging()
    selected = _resolve_mode(mode)
    if metrics_port > 0:
        from .observability.metrics import start_metrics_server

        start_metrics_server(metrics_port)

    from .graph import run_once

    summary = asyncio.run(run_once(mode=selected))
    table = Table(title=f"Run {summary.run_id}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for k, v in summary.model_dump(mode="json").items():
        table.add_row(str(k), str(v))
    console.print(table)


@app.command()
def schedule(
    metrics_port: int = typer.Option(8080, help="Prometheus /metrics port"),
) -> None:
    """Start the 24/7 scheduler (foreground)."""
    from .scheduler import main_async

    asyncio.run(main_async(metrics_port=metrics_port))


@app.command()
def report() -> None:
    """Print a summary of vendors collected so far."""
    settings = get_settings()
    manifest_path: Path = settings.data_dir / "reports" / "master_manifest.json"
    if not manifest_path.exists():
        console.print("[yellow]No manifest yet. Run `crawl run` first.[/yellow]")
        raise typer.Exit(0)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    n_vendors = len(data.get("vendors", {}))
    n_expos = len(data.get("expos", {}))
    threshold = settings.phase_2_vendor_threshold
    pct = (n_vendors / threshold * 100) if threshold else 0.0

    table = Table(title="AutoCrawler Status")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Vendors enriched (manifest)", str(n_vendors))
    table.add_row("Expos discovered (manifest)", str(n_expos))
    table.add_row("Phase 2 threshold", str(threshold))
    table.add_row("Phase 2 progress", f"{pct:.1f} %")
    table.add_row("Phase 2 unlocked", str(n_vendors >= threshold))
    table.add_row("Updated at", data.get("updated_at", "—"))
    console.print(table)


@app.command()
def health() -> None:
    """Quick connectivity check on dependencies."""

    async def _run() -> dict:
        out: dict[str, str] = {}
        # Redis
        try:
            from .store.redis_queue import get_redis

            r = await get_redis()
            out["redis"] = "ok" if r is not None else "unavailable"
        except Exception as e:  # noqa: BLE001
            out["redis"] = f"error: {e}"
        # Chroma
        try:
            from .store.vector_store import _get_collection

            await _get_collection()
            out["chroma"] = "ok"
        except Exception as e:  # noqa: BLE001
            out["chroma"] = f"error: {e}"
        # OpenAI
        try:
            from .tools.llm.openai_client import embed_one

            v = await embed_one("ping")
            out["openai"] = f"ok (vec dim {len(v)})"
        except Exception as e:  # noqa: BLE001
            out["openai"] = f"error: {e}"
        # Firecrawl
        try:
            from .tools.firecrawl.client import budget_low

            low = await budget_low()
            out["firecrawl"] = f"ok (budget_low={low})"
        except Exception as e:  # noqa: BLE001
            out["firecrawl"] = f"error: {e}"
        return out

    configure_logging()
    res = asyncio.run(_run())
    table = Table(title="Health Check")
    table.add_column("Service")
    table.add_column("Status")
    for k, v in res.items():
        table.add_row(k, v)
    console.print(table)


@app.command()
def backfill(
    topic: str = typer.Argument(..., help="Topic name from config/seed_topics.yaml"),
    mode: str = typer.Option("normal", help="dev | normal | aggressive"),
) -> None:
    """Re-run discovery for a single topic."""
    configure_logging()
    selected = _resolve_mode(mode)
    console.print(f"[cyan]Backfilling topic[/cyan] {topic!r} in mode {selected.value}")
    from .graph import run_once

    summary = asyncio.run(run_once(mode=selected))
    console.print(json.dumps(summary.model_dump(mode="json"), indent=2))


@app.command(name="pdf-test")
def pdf_test(
    pdf_url: str = typer.Argument(..., help="Direct URL to a PDF brochure"),
    expo_id: str = typer.Option("manual-test", help="Expo ID slug for storage layout"),
) -> None:
    """Download a PDF, extract vendor names, print results. No graph execution."""
    configure_logging()

    async def _run() -> None:
        from .tools.scrapers.pdf_extractor import list_exhibitors

        refs = await list_exhibitors(pdf_url, expo_id)
        if not refs:
            console.print("[yellow]No vendors extracted.[/yellow]")
            return

        table = Table(title=f"Vendors extracted from {pdf_url}")
        table.add_column("#", justify="right")
        table.add_column("Page", justify="right")
        table.add_column("Pos", justify="right")
        table.add_column("Method")
        table.add_column("Name")
        table.add_column("Context", overflow="fold")
        for i, r in enumerate(refs, start=1):
            p = r.provenance[0] if r.provenance else None
            table.add_row(
                str(i),
                str(p.page) if p and p.page else "-",
                str(p.position) if p and p.position else "-",
                p.extraction_method if p else "-",
                r.name,
                (r.short_description or "")[:80],
            )
        console.print(table)
        console.print(f"[green]Total:[/green] {len(refs)} vendor refs")

    asyncio.run(_run())


db_app = typer.Typer(help="Database commands.")
app.add_typer(db_app, name="db")


@db_app.command("migrate")
def db_migrate() -> None:
    """Create database tables (idempotent, uses Base.metadata.create_all)."""
    configure_logging()
    from .db.engine import init_db

    asyncio.run(init_db())
    console.print("[green]Database migration completed.[/green]")


@db_app.command("import-json")
def db_import_json() -> None:
    """Import existing JSON reports into Postgres."""
    configure_logging()
    from datetime import datetime, timezone

    from .db.engine import get_sessionmaker, init_db
    from .db.repositories import expo_repo, run_repo, vendor_repo
    from .schemas import Expo, RunSummary, Vendor

    settings = get_settings()
    reports = settings.data_dir / "reports"

    async def _run() -> None:
        await init_db()
        sm = get_sessionmaker()
        imported = {"vendors": 0, "expos": 0, "runs": 0, "errors": 0}

        for path in (reports / "vendors").glob("*.json"):
            async with sm() as session:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    trail = data.get("source_trail") or []
                    legacy_tags: list[str] = []
                    structured_trail: list[dict] = []
                    for entry in trail:
                        if isinstance(entry, str):
                            legacy_tags.append(entry)
                        elif isinstance(entry, dict):
                            structured_trail.append(entry)
                    if legacy_tags:
                        existing_tags = list(data.get("source_tags") or [])
                        merged = existing_tags + [t for t in legacy_tags if t not in existing_tags]
                        data["source_tags"] = merged
                    data["source_trail"] = structured_trail
                    vendor = Vendor.model_validate(data)
                    await vendor_repo.upsert(session, vendor)
                    await session.commit()
                    imported["vendors"] += 1
                except Exception as exc:
                    await session.rollback()
                    imported["errors"] += 1
                    console.print(f"[red]vendor failed[/red] {path.name}: {str(exc)[:120]}")

        for path in (reports / "expos").glob("*.json"):
            async with sm() as session:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    vendor_domains = data.pop("vendors", []) or []
                    if "vendor_domains" in data:
                        vendor_domains = data.pop("vendor_domains") or vendor_domains
                    expo = Expo.model_validate(data)
                    await expo_repo.upsert(session, expo, vendor_domains=vendor_domains)
                    await session.commit()
                    imported["expos"] += 1
                except Exception as exc:
                    await session.rollback()
                    imported["errors"] += 1
                    console.print(f"[red]expo failed[/red] {path.name}: {str(exc)[:120]}")

        for path in (reports / "runs").glob("*.json"):
            async with sm() as session:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    started = data.get("started_at")
                    if isinstance(started, str):
                        data["started_at"] = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    finished = data.get("finished_at")
                    if isinstance(finished, str):
                        data["finished_at"] = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                    if data.get("started_at") is None:
                        data["started_at"] = datetime.now(timezone.utc)
                    summary = RunSummary.model_validate(data)
                    await run_repo.upsert(session, summary)
                    await session.commit()
                    imported["runs"] += 1
                except Exception as exc:
                    await session.rollback()
                    imported["errors"] += 1
                    console.print(f"[red]run failed[/red] {path.name}: {str(exc)[:120]}")

        table = Table(title="Import results")
        table.add_column("Kind")
        table.add_column("Count", justify="right")
        for k, v in imported.items():
            table.add_row(k, str(v))
        console.print(table)

    asyncio.run(_run())


@app.command(name="translate-vendors")
def translate_vendors_cmd(
    limit: int = typer.Option(0, help="Max vendors to translate (0 = all)"),
    force: bool = typer.Option(False, help="Re-translate even if already at target language"),
    dry_run: bool = typer.Option(False, help="Print what would change without writing"),
) -> None:
    """Translate vendor text fields in Postgres to the configured TARGET_LANGUAGE."""
    configure_logging()
    from sqlalchemy import select

    from .db.engine import get_sessionmaker, init_db
    from .db.models import VendorORM
    from .db.repositories import vendor_repo
    from .schemas import Vendor
    from .tools.llm.translator import translate_vendor_fields

    settings = get_settings()
    if not settings.translation_enabled:
        console.print("[yellow]TRANSLATION_ENABLED=false. Set it true and retry.[/yellow]")
        raise typer.Exit(1)

    target = settings.target_language.lower()

    async def _run() -> None:
        await init_db()
        sm = get_sessionmaker()
        async with sm() as session:
            stmt = select(VendorORM)
            if not force:
                stmt = stmt.where((VendorORM.language_code != target) | (VendorORM.language_code.is_(None)))
            if limit > 0:
                stmt = stmt.limit(limit)
            rows = list((await session.execute(stmt)).scalars().all())

        console.print(f"[cyan]Found {len(rows)} vendor(s) needing translation → {target}[/cyan]")
        ok, fail, skipped = 0, 0, 0
        for orm in rows:
            try:
                payload = vendor_repo.orm_to_dict(orm)
                payload.pop("first_seen_wayback", None)
                payload.pop("first_enriched_at", None)
                payload.pop("last_enriched_at", None)
                payload.pop("translated_at", None)
                vendor = Vendor.model_validate(payload)
                before = vendor.description
                await translate_vendor_fields(vendor)
                if vendor.description == before and vendor.language_code != target:
                    skipped += 1
                    continue
                if dry_run:
                    console.print(
                        f"  [dim]{vendor.domain}[/dim] desc:"
                        f" {(vendor.description or '')[:80]!r}"
                    )
                    ok += 1
                    continue
                async with sm() as ses2:
                    await vendor_repo.upsert(ses2, vendor)
                    await ses2.commit()
                ok += 1
                console.print(f"  [green]✓[/green] {vendor.domain}")
            except Exception as exc:  # noqa: BLE001
                fail += 1
                console.print(f"  [red]✗[/red] {orm.domain}: {str(exc)[:120]}")

        table = Table(title="Translation results")
        table.add_column("Metric")
        table.add_column("Count", justify="right")
        table.add_row("translated", str(ok))
        table.add_row("skipped", str(skipped))
        table.add_row("failed", str(fail))
        console.print(table)

    asyncio.run(_run())


@app.command(name="wiki-test")
def wiki_test_cmd(
    wiki_url: str = typer.Argument(..., help="Wikipedia article URL (e.g. en.wikipedia.org/wiki/2026_Bilderberg_Conference)"),
    expo_id: str = typer.Option("wiki-test", help="Expo ID slug for tagging"),
) -> None:
    """Test the Wikipedia scraper on a single article URL. No DB writes."""
    configure_logging()

    async def _run() -> None:
        from .tools.scrapers.wikipedia import list_exhibitors

        refs = await list_exhibitors(wiki_url, expo_id)
        if not refs:
            console.print("[yellow]No organizations / companies extracted.[/yellow]")
            return

        table = Table(title=f"Organizations from {wiki_url}")
        table.add_column("#", justify="right")
        table.add_column("Name")
        table.add_column("Wikipedia URL", overflow="fold")
        table.add_column("Method")
        table.add_column("Confidence", justify="right")
        for i, r in enumerate(refs, start=1):
            p = r.provenance[0] if r.provenance else None
            table.add_row(
                str(i),
                r.name,
                str(r.raw_url) if r.raw_url else "-",
                p.extraction_method if p else "-",
                f"{p.confidence:.2f}" if p and p.confidence is not None else "-",
            )
        console.print(table)
        console.print(f"[green]Total:[/green] {len(refs)} refs")

    asyncio.run(_run())


@app.command(name="api-serve")
def api_serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8081, help="Bind port"),
    reload: bool = typer.Option(False, help="Auto reload"),
) -> None:
    """Run the FastAPI service."""
    import uvicorn

    uvicorn.run("crawler.api:app", host=host, port=port, reload=reload, proxy_headers=True)


if __name__ == "__main__":
    app()
