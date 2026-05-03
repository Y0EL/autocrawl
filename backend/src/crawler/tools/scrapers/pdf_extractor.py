"""PDF Extractor — turn a PDF URL into a list of ExhibitorRef with provenance.

Pipeline:
  1. Download PDF (pdf_store with SHA256 dedup)
  2. Extract pages (pdf_parser combines PyMuPDF + pdfplumber + Surya OCR)
  3. Per-page LLM-driven vendor name extraction
  4. Build ExhibitorRef with full provenance (page, position, method, snippet)
  5. Persist .pages.jsonl audit trail

Same Protocol as `tentimes.py` and `generic.py` — returns `list[ExhibitorRef]`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ...observability.logger import get_logger
from ...observability.metrics import (
    errors_total,
    pdf_extracted_total,
    pdf_pages_processed_total,
    pdf_vendors_found_total,
)
from ...schemas import ExhibitorRef, SourceProvenance

_log = get_logger(__name__)


class _PdfVendor(BaseModel):
    name: str = Field(description="Company / organization / vendor name as it appears in the PDF")
    position: int = Field(description="1-indexed order on the page", default=1)
    context: str = Field(default="", description="Surrounding 50-100 chars of text around the name")
    table_row: int | None = Field(default=None, description="If extracted from a table, the row index (0-indexed)")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class _PdfPageVendors(BaseModel):
    vendors: list[_PdfVendor] = Field(default_factory=list)


_NOISE_PATTERNS = re.compile(
    r"^(page\s+\d+|exhibitor\s+list|table\s+of\s+contents|index|appendix|copyright|"
    r"all\s+rights\s+reserved|sponsor|booth\s+\d+|hall\s+[A-Z0-9]+)$",
    re.IGNORECASE,
)


def _is_noise(name: str) -> bool:
    name = name.strip()
    if len(name) < 3 or len(name) > 200:
        return True
    if _NOISE_PATTERNS.match(name):
        return True
    if name.replace(" ", "").isdigit():
        return True
    return False


def _vendors_from_table(table: list[list[str | None]]) -> list[_PdfVendor]:
    """Heuristic table-to-vendors extraction.

    Looks for rows where one column appears to be a company name. Skips header
    rows. Confidence is high (0.85) because tables are structured.
    """
    if not table or len(table) < 2:
        return []
    header = [str(c or "").strip().lower() for c in (table[0] or [])]
    name_col_idx: int | None = None
    for i, h in enumerate(header):
        if any(k in h for k in ("company", "exhibitor", "vendor", "organization", "organisation", "name")):
            name_col_idx = i
            break

    out: list[_PdfVendor] = []
    for row_idx, row in enumerate(table[1:], start=1):
        if not row:
            continue
        candidates: list[str] = []
        if name_col_idx is not None and name_col_idx < len(row):
            v = str(row[name_col_idx] or "").strip()
            if v:
                candidates.append(v)
        else:
            # Fallback: pick the cell with the longest alphabetical content
            longest = max(
                (str(c or "").strip() for c in row),
                key=lambda s: len(s) if any(ch.isalpha() for ch in s) else 0,
                default="",
            )
            if longest:
                candidates.append(longest)

        for cand in candidates:
            if not _is_noise(cand):
                out.append(_PdfVendor(
                    name=cand[:200],
                    position=row_idx,
                    context=" | ".join(str(c or "")[:60] for c in row),
                    table_row=row_idx,
                    confidence=0.85,
                ))
                break  # one vendor per row
    return out


async def _extract_vendors_via_llm(page_text: str, page_number: int) -> list[_PdfVendor]:
    """LLM extraction for prose-style pages where there's no clean table."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from ..llm.openai_client import chat

    if len(page_text.strip()) < 30:
        return []

    sys = SystemMessage(content=(
        "Extract company / organization / vendor names from a trade-show PDF "
        "page. Skip headers, footers, page numbers, hall labels, generic "
        "section titles. Output one entry per real exhibitor in the order "
        "they appear, with a 1-indexed position. The 'context' field should "
        "be a 50-100 character window around the name. Be conservative — "
        "skip anything that is not clearly a company or organization."
    ))
    user = HumanMessage(content=f"Page {page_number} text:\n\n{page_text[:12000]}")
    try:
        result = await chat([sys, user], use_heavy=False, response_format=_PdfPageVendors)
        if isinstance(result, _PdfPageVendors):
            cleaned: list[_PdfVendor] = []
            for v in result.vendors:
                if not _is_noise(v.name):
                    cleaned.append(v)
            return cleaned
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="pdf_extractor", category="llm_extract").inc()
        _log.warning("pdf_extractor.llm_failed", page=page_number, error=str(e))
    return []


async def list_exhibitors(pdf_url: str, expo_id: str) -> list[ExhibitorRef]:
    """Download PDF, extract vendor refs with full provenance."""
    from ...store import pdf_store
    from ..parsers.pdf_parser import extract_pages

    download_result = await pdf_store.download(pdf_url, expo_id)
    if download_result is None:
        return []
    pdf_path, sha256 = download_result

    pages = await extract_pages(pdf_path)
    if not pages:
        _log.info("pdf_extractor.no_pages", pdf=pdf_path.name, expo_id=expo_id)
        return []
    pdf_extracted_total.inc()
    for page in pages:
        pdf_pages_processed_total.labels(method=page.extraction_method).inc()

    refs: list[ExhibitorRef] = []
    for page in pages:
        vendors_table: list[_PdfVendor] = []
        for table in page.tables:
            vendors_table.extend(_vendors_from_table(table))

        seen_names: set[str] = {v.name.lower() for v in vendors_table}

        if vendors_table:
            page_vendors = vendors_table
        else:
            page_vendors = await _extract_vendors_via_llm(page.text, page.page_number)
            page_vendors = [v for v in page_vendors if v.name.lower() not in seen_names]

        for position, v in enumerate(page_vendors, start=1):
            try:
                refs.append(ExhibitorRef(
                    expo_id=expo_id,
                    name=v.name,
                    raw_url=None,
                    aggregator_domain=None,
                    short_description=v.context,
                    booth=None,
                    provenance=[SourceProvenance(
                        type="pdf",
                        url=pdf_url,
                        pdf_filename=pdf_path.name,
                        pdf_sha256=sha256,
                        page=page.page_number,
                        position=position,
                        extraction_method=page.extraction_method if not v.table_row else "pdfplumber_table",
                        confidence=v.confidence,
                        context_snippet=v.context[:300] if v.context else None,
                    )],
                ))
            except Exception as e:  # noqa: BLE001
                _log.debug("pdf_extractor.invalid_ref", error=str(e), name=v.name[:80])

    try:
        await pdf_store.write_page_extracts(expo_id, pdf_path.name, pages, refs)
    except Exception as e:  # noqa: BLE001
        _log.debug("pdf_extractor.audit_write_failed", error=str(e))

    pdf_vendors_found_total.inc(len(refs))
    _log.info(
        "pdf_extractor.vendors_found",
        expo_id=expo_id,
        pdf=pdf_path.name,
        pages=len(pages),
        vendors=len(refs),
    )
    return refs
