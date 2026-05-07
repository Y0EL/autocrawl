"""Typer CLI for the agentic crawler.

Commands:
  agentic-crawl run [--seed-name X] — one-shot, single seed (or all if omitted)
  agentic-crawl schedule           — 24/7 loop (foreground, used as docker CMD)
  agentic-crawl seeds              — print loaded seeds for inspection
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from crawler.observability.logger import configure_logging

from .config import get_agentic_settings
from .runner import run_seed
from .scheduler import run_forever
from .seeds import load_seeds

app = typer.Typer(help="Agentic browser crawler — AI-driven sibling to the base crawler.")
console = Console()


@app.command()
def run(
    seed_name: str = typer.Option(None, help="Run only the seed with this exact name; omit = run all"),
) -> None:
    """One-shot run (manual trigger)."""
    configure_logging()
    s = get_agentic_settings()
    seeds = load_seeds(s.seeds_yaml)
    if seed_name:
        seeds = [s for s in seeds if s.name == seed_name]
    if not seeds:
        console.print(f"[yellow]No seeds matched (yaml={s.seeds_yaml}).[/yellow]")
        raise typer.Exit(1)

    async def _run() -> None:
        totals = {"resolved": 0, "enriched": 0, "dedup_skipped": 0, "rejected": 0, "failed": 0}
        for seed in seeds:
            counts = await run_seed(seed)
            for k, v in counts.items():
                totals[k] += v

        table = Table(title=f"Agentic run — {len(seeds)} seed(s)")
        table.add_column("Stage")
        table.add_column("Count", justify="right")
        for k, v in totals.items():
            table.add_row(k, str(v))
        console.print(table)

    asyncio.run(_run())


@app.command()
def schedule() -> None:
    """Foreground 24/7 scheduler loop. Used as the docker container CMD."""
    configure_logging()
    asyncio.run(run_forever())


@app.command()
def combined() -> None:
    """Run BOTH the listing scheduler AND the enrich worker in one process.

    Used as the CMD for `agentic-a` / `agentic-b` twin containers in the
    Phase 3 deployment topology — each container hosts 2 listing workers
    plus 2 enrich workers, all rendering to the same Xvfb display so
    noVNC shows them tiled together. Two containers × 4 chromium = 8
    chromium total; per-VNC operator sees a balanced mix of both pools.

    Listing lock is now per-hostname (see scheduler._lock_key) so the
    twin container's listing scheduler runs in parallel without fighting
    for one global lock.
    """
    configure_logging()

    async def _run() -> None:
        from .enrich_worker import run_workers_forever

        # Two long-running coroutines, single event loop. Cancellation of
        # one shouldn't kill the other — wrap as separate tasks and gather
        # with return_exceptions so we get a clear shutdown trace if either
        # blows up.
        listing_task = asyncio.create_task(run_forever())
        enrich_task = asyncio.create_task(run_workers_forever())
        try:
            await asyncio.gather(
                listing_task, enrich_task, return_exceptions=True
            )
        except BaseException:
            for t in (listing_task, enrich_task):
                if not t.done():
                    t.cancel()
            await asyncio.gather(
                listing_task, enrich_task, return_exceptions=True
            )
            raise

    asyncio.run(_run())


@app.command()
def seeds() -> None:
    """Print the loaded seed list (useful to verify YAML before scheduling)."""
    configure_logging()
    s = get_agentic_settings()
    items = load_seeds(s.seeds_yaml)
    table = Table(title=f"Agentic seeds — {s.seeds_yaml}")
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Expo ID")
    table.add_column("Tags")
    for it in items:
        table.add_row(it.name, it.url, it.expo_id or "—", ",".join(it.tags) or "—")
    console.print(table)
    if not items:
        console.print("[yellow]No seeds loaded. Add entries to the YAML.[/yellow]")


@app.command()
def discover() -> None:
    """Mode C dry run — generate discovery seeds, print them, exit. No crawl.

    Operator workflow: enable AGENTIC_DISCOVERY_ENABLED=true, run this command
    to preview which URLs Mode C wants to add to the queue this pass. Adjust
    AGENTIC_DISCOVERY_URL_SCORE_THRESHOLD if the output is too noisy / sparse.
    """
    configure_logging()

    async def _run() -> None:
        from .discovery import discover_new_seeds

        seeds = await discover_new_seeds()
        table = Table(title=f"Discovery preview — {len(seeds)} seed(s)")
        table.add_column("Name", overflow="fold")
        table.add_column("URL", overflow="fold")
        table.add_column("Source query", overflow="fold")
        table.add_column("Tags")
        for seed in seeds:
            table.add_row(
                seed.name[:60],
                seed.url[:80],
                (seed.source_query or "—")[:60],
                ",".join(seed.tags) or "—",
            )
        console.print(table)
        if not seeds:
            s = get_agentic_settings()
            if not s.discovery_enabled:
                console.print(
                    "[yellow]Discovery disabled. Set AGENTIC_DISCOVERY_ENABLED=true.[/yellow]"
                )
            else:
                console.print(
                    "[yellow]Discovery returned 0 seeds — try lowering "
                    "AGENTIC_DISCOVERY_URL_SCORE_THRESHOLD or check Ollama / "
                    "search-engine connectivity.[/yellow]"
                )

    asyncio.run(_run())


enrich_app = typer.Typer(help="Phase 3 enrich-pool subcommands.")
app.add_typer(enrich_app, name="enrich")


@enrich_app.command("worker")
def enrich_worker_cmd() -> None:
    """Run the enrich-pool consumer process foreground.

    Used as the CMD for a separate `agentic-enrich-worker` docker service.
    Pulls EnrichTasks from `agentic:enrich:queue` and runs Browser-Use
    agents that search → visit → extract → persist via reporter.
    """
    configure_logging()

    async def _run() -> None:
        from .enrich_worker import run_workers_forever

        await run_workers_forever()

    asyncio.run(_run())


@enrich_app.command("enqueue")
def enrich_enqueue_cmd(
    vendor: str = typer.Option(..., help="Vendor display name."),
    hint_url: str = typer.Option(None, "--hint-url", help="Optional hint URL."),
    expo_id: str = typer.Option("manual-test", "--expo-id"),
    country: str = typer.Option(None, "--country"),
    product: str = typer.Option(None, "--product"),
) -> None:
    """Manual enqueue helper for smoke testing the queue end-to-end."""
    configure_logging()

    async def _run() -> None:
        from .enrich_queue import EnrichTask, make_task_id, publish

        task = EnrichTask(
            task_id=make_task_id(vendor, expo_id),
            vendor_name=vendor,
            hint_url=hint_url,
            expo_id=expo_id,
            country_hint=country,
            product_hint=product,
            source_query=None,
            lesson_id_of_listing=None,
        )
        entry_id = await publish(task)
        if entry_id:
            console.print(
                f"[green]enqueued[/green] vendor=[bold]{vendor}[/bold] "
                f"task_id={task.task_id} entry_id={entry_id}"
            )
        else:
            console.print("[red]enqueue failed — Redis unreachable[/red]")
            raise typer.Exit(1)

    asyncio.run(_run())


@enrich_app.command("depth")
def enrich_depth_cmd() -> None:
    """Show the current XLEN of `agentic:enrich:queue`."""
    configure_logging()

    async def _run() -> None:
        from .enrich_queue import depth

        n = await depth()
        console.print(f"agentic:enrich:queue depth = [bold]{n}[/bold]")

    asyncio.run(_run())


@app.command()
def reset(
    locks: bool = typer.Option(True, help="Clear scheduler per-host locks."),
    llm: bool = typer.Option(True, help="Reset llm:concurrency:* counters."),
    pel: bool = typer.Option(False, help="Reclaim and ack ALL pending enrich queue entries (destructive)."),
    queue: bool = typer.Option(False, help="DROP entire enrich queue (very destructive)."),
) -> None:
    """One-shot Redis cleanup helper.

    Common workflow after `docker compose restart agentic-*`:

        agentic-crawl reset

    Clears stale scheduler locks (so next pass doesn't `scheduler_locked_skip`)
    and resets LLM-queue counters (so containers that died mid-acquire don't
    leave the cap permanently wedged).

    Add --pel to also force-ack every entry sitting in the enrich-queue
    Pending Entries List (use when consumers from a previous container
    generation are gone and tasks are blocked behind XAUTOCLAIM idle).

    Add --queue to nuke the entire enrich-queue stream (rare — only when
    you want a totally fresh start).
    """
    configure_logging()

    async def _run() -> None:
        from crawler.store.redis_queue import get_redis

        client = await get_redis()
        if client is None:
            console.print("[red]Redis unreachable.[/red]")
            raise typer.Exit(1)

        cleared: dict[str, int] = {}

        if locks:
            keys = []
            async for k in client.scan_iter(match="autocrawl:agentic_active_run:*"):
                keys.append(k)
            if keys:
                await client.delete(*keys)
            cleared["locks"] = len(keys)

        if llm:
            tier_keys = [
                "llm:concurrency:vision",
                "llm:concurrency:heavy",
                "llm:concurrency:light",
                "llm:concurrency:tiny",
            ]
            for k in tier_keys:
                await client.set(k, 0)
            holder_keys = []
            async for k in client.scan_iter(match="llm:concurrency:*:holder:*"):
                holder_keys.append(k)
            if holder_keys:
                await client.delete(*holder_keys)
            cleared["llm_counters"] = len(tier_keys)
            cleared["llm_holders"] = len(holder_keys)

        if pel:
            from .enrich_queue import CONSUMER_GROUP, STREAM_NAME

            try:
                pending = await client.xpending(STREAM_NAME, CONSUMER_GROUP)
                count = pending[0] if isinstance(pending, (list, tuple)) else 0
                if count and count > 0:
                    # Pull all pending entry IDs and XACK them.
                    entries = await client.xpending_range(
                        STREAM_NAME, CONSUMER_GROUP, "-", "+", count,
                    )
                    ids = [e["message_id"] for e in entries] if entries else []
                    if ids:
                        await client.xack(STREAM_NAME, CONSUMER_GROUP, *ids)
                    cleared["pel_acked"] = len(ids)
                else:
                    cleared["pel_acked"] = 0
            except Exception as e:  # noqa: BLE001
                console.print(f"[yellow]PEL clear skipped: {e}[/yellow]")
                cleared["pel_acked"] = -1

        if queue:
            from .enrich_queue import STREAM_NAME

            try:
                length = await client.xlen(STREAM_NAME)
                await client.delete(STREAM_NAME)
                cleared["queue_dropped"] = int(length)
            except Exception as e:  # noqa: BLE001
                console.print(f"[yellow]queue drop skipped: {e}[/yellow]")
                cleared["queue_dropped"] = -1

        console.print("[green]Reset complete.[/green]")
        for k, v in cleared.items():
            console.print(f"  {k}: {v}")

    asyncio.run(_run())


@app.command()
def stop() -> None:
    """Set the remote-stop flag in Redis. The running scheduler picks it up
    between seeds (or between passes during sleep) and exits cleanly. Worst
    case latency: one in-flight Browser-Use task (~AGENTIC_TASK_TIMEOUT seconds).

    Use this when you can't reach the container directly (e.g. agent stuck on
    a runaway seed and you want to stop without `docker compose kill`).
    """
    configure_logging()

    async def _set_flag() -> None:
        from crawler.store.redis_queue import get_redis

        client = await get_redis()
        if client is None:
            console.print("[red]Redis unreachable — cannot set remote-stop flag.[/red]")
            console.print("[yellow]Use `docker compose stop agentic-crawler` instead.[/yellow]")
            raise typer.Exit(1)
        await client.set("autocrawl:agentic_stop_requested", "1", ex=600)
        console.print("[green]Remote-stop flag set.[/green] Scheduler will exit on next check (≤5 min).")

    asyncio.run(_set_flag())


if __name__ == "__main__":
    app()
