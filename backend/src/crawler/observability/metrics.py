"""Prometheus metrics. Imported by tools/agents to record observations.

Exposed via an HTTP endpoint started in `start_metrics_server()`. Grafana
scrapes from there.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

REGISTRY = CollectorRegistry(auto_describe=True)

# === Discovery & extraction ===
expos_discovered_total = Counter(
    "crawl_expos_discovered_total",
    "Total expos discovered across all runs.",
    ["source"],
    registry=REGISTRY,
)
exhibitors_extracted_total = Counter(
    "crawl_exhibitors_extracted_total",
    "Total exhibitor refs extracted from aggregator pages.",
    ["aggregator"],
    registry=REGISTRY,
)
vendors_resolved_total = Counter(
    "crawl_vendors_resolved_total",
    "Total vendor URLs successfully resolved (aggregator → real vendor domain).",
    ["resolution_method"],
    registry=REGISTRY,
)
vendors_enriched_total = Counter(
    "crawl_vendors_enriched_total",
    "Total vendors enriched (Phase 1 exit gate at 100).",
    registry=REGISTRY,
)

# === PDF extraction ===
pdf_extracted_total = Counter(
    "crawl_pdf_extracted_total",
    "Total PDFs successfully downloaded and parsed.",
    registry=REGISTRY,
)
pdf_pages_processed_total = Counter(
    "crawl_pdf_pages_processed_total",
    "Total PDF pages processed (text or OCR).",
    ["method"],
    registry=REGISTRY,
)
pdf_vendors_found_total = Counter(
    "crawl_pdf_vendors_found_total",
    "Total vendor refs extracted from PDFs.",
    registry=REGISTRY,
)
email_verified_total = Counter(
    "crawl_email_verified_total",
    "Email verifications bucketed by score (low<0.4, mid<0.7, high>=0.7).",
    ["bucket"],
    registry=REGISTRY,
)
dedup_hits_total = Counter(
    "crawl_dedup_hits_total",
    "Vendors skipped because they were already in the vector store.",
    registry=REGISTRY,
)

# === Errors ===
errors_total = Counter(
    "crawl_errors_total",
    "Errors per stage and category.",
    ["stage", "category"],
    registry=REGISTRY,
)

# === Latency ===
request_duration_seconds = Histogram(
    "crawl_request_duration_seconds",
    "HTTP / browser request latency.",
    ["tool"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60, 120),
    registry=REGISTRY,
)
llm_call_duration_seconds = Histogram(
    "crawl_llm_call_duration_seconds",
    "OpenAI call latency.",
    ["model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
    registry=REGISTRY,
)

# === Quotas ===
firecrawl_credits_used_total = Counter(
    "crawl_firecrawl_credits_used_total",
    "Firecrawl credits consumed (estimated).",
    ["operation"],
    registry=REGISTRY,
)
openai_tokens_total = Counter(
    "crawl_openai_tokens_total",
    "OpenAI tokens consumed.",
    ["model", "kind"],  # kind = prompt | completion
    registry=REGISTRY,
)

# === Live state ===
active_workers = Gauge(
    "crawl_active_workers",
    "Currently active sub-agent workers.",
    ["stage"],
    registry=REGISTRY,
)
queue_depth = Gauge(
    "crawl_queue_depth",
    "Redis stream pending work-items.",
    ["queue"],
    registry=REGISTRY,
)
phase_2_progress = Gauge(
    "crawl_phase_2_progress_ratio",
    "vendors_enriched_total / phase_2_threshold (0..1+).",
    registry=REGISTRY,
)


def start_metrics_server(port: int = 8080) -> None:
    """Start the /metrics HTTP endpoint."""
    start_http_server(port, registry=REGISTRY)
