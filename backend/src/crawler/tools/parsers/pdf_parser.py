"""Combined PDF parser: PyMuPDF (native text) + pdfplumber (tables) + Surya OCR (scanned).

Strategy:
  1. PyMuPDF.get_text("text") → fast native extraction
  2. pdfplumber.extract_tables() → structured table cells
  3. If native text is sparse (< THRESHOLD chars or text-image ratio low) → Surya OCR

Surya is imported lazily inside the OCR path so the rest of the pipeline can
run even when surya-ocr or its torch dependency are unavailable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...config import get_settings
from ...observability.logger import get_logger
from ...observability.metrics import errors_total

_log = get_logger(__name__)

# Pages with fewer native chars than this triggers OCR fallback.
_OCR_TEXT_THRESHOLD = 80


@dataclass
class PageContent:
    """Structured representation of one PDF page."""

    page_number: int
    text: str
    tables: list[list[list[str | None]]] = field(default_factory=list)
    extraction_method: str = "pymupdf"  # "pymupdf" | "pdfplumber_table" | "surya_ocr"
    char_count: int = 0
    width: float | None = None
    height: float | None = None
    layout_blocks: list[dict] = field(default_factory=list)


def _looks_like_scanned(native_text: str, page: Any) -> bool:
    if len(native_text.strip()) < _OCR_TEXT_THRESHOLD:
        return True
    return False


async def extract_pages(pdf_path: Path) -> list[PageContent]:
    """Extract all pages from a PDF. Returns one PageContent per page."""
    return await asyncio.to_thread(_extract_pages_blocking, pdf_path)


def _extract_pages_blocking(pdf_path: Path) -> list[PageContent]:
    pages: list[PageContent] = []
    settings = get_settings()
    ocr_enabled = settings.ocr_enabled

    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError as e:
            _log.warning("pdf_parser.pymupdf_unavailable", error=str(e))
            return pages

    try:
        import pdfplumber  # type: ignore
    except ImportError:
        pdfplumber = None  # type: ignore

    try:
        mu_doc = pymupdf.open(pdf_path)
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="pdf_parser", category="pymupdf_open").inc()
        _log.warning("pdf_parser.open_failed", path=str(pdf_path), error=str(e))
        return pages

    plumber_doc = None
    if pdfplumber is not None:
        try:
            plumber_doc = pdfplumber.open(pdf_path)
        except Exception as e:  # noqa: BLE001
            _log.debug("pdf_parser.pdfplumber_open_failed", error=str(e))

    try:
        for i, mu_page in enumerate(mu_doc, start=1):
            try:
                native_text = mu_page.get_text("text") or ""
            except Exception:  # noqa: BLE001
                native_text = ""

            tables: list[list[list[str | None]]] = []
            if plumber_doc is not None and i - 1 < len(plumber_doc.pages):
                try:
                    raw = plumber_doc.pages[i - 1].extract_tables() or []
                    tables = [[[c for c in row] for row in t] for t in raw]
                except Exception:  # noqa: BLE001
                    pass

            method = "pymupdf"
            text = native_text
            if ocr_enabled and _looks_like_scanned(native_text, mu_page):
                ocr_text = _surya_ocr_page_blocking(mu_page)
                if ocr_text and len(ocr_text) > len(native_text):
                    text = ocr_text
                    method = "surya_ocr"

            rect = getattr(mu_page, "rect", None)
            width = float(rect.width) if rect is not None else None
            height = float(rect.height) if rect is not None else None

            pages.append(PageContent(
                page_number=i,
                text=text,
                tables=tables,
                extraction_method=method,
                char_count=len(text),
                width=width,
                height=height,
            ))
    finally:
        with _suppress():
            mu_doc.close()
        if plumber_doc is not None:
            with _suppress():
                plumber_doc.close()

    _log.info("pdf_parser.extracted", path=str(pdf_path), pages=len(pages))
    return pages


def _surya_ocr_page_blocking(mu_page: Any) -> str:
    """Render PyMuPDF page to image and run Surya OCR. Returns plain text.

    Surya import is deferred until first call so a missing surya-ocr install
    does not break the rest of the pipeline.
    """
    settings = get_settings()
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return ""

    try:
        from surya.foundation import FoundationPredictor  # type: ignore
        from surya.recognition import RecognitionPredictor  # type: ignore
        from surya.detection import DetectionPredictor  # type: ignore
    except ImportError as e:
        _log.debug("pdf_parser.surya_unavailable", error=str(e))
        return ""

    try:
        pix = mu_page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except Exception as e:  # noqa: BLE001
        _log.debug("pdf_parser.render_failed", error=str(e))
        return ""

    try:
        global _SURYA_REC, _SURYA_DET
        if _SURYA_REC is None or _SURYA_DET is None:
            device = settings.surya_device.lower()
            kwargs: dict[str, Any] = {}
            if device in ("cpu", "cuda", "mps"):
                kwargs["device"] = device
            foundation = FoundationPredictor(**kwargs)
            _SURYA_REC = RecognitionPredictor(foundation_predictor=foundation)
            _SURYA_DET = DetectionPredictor(**kwargs)

        predictions = _SURYA_REC([img], det_predictor=_SURYA_DET)
        if not predictions:
            return ""
        page_pred = predictions[0]
        lines = getattr(page_pred, "text_lines", None) or []
        return "\n".join(getattr(line, "text", "") or "" for line in lines)
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="pdf_parser", category="surya_ocr").inc()
        _log.warning("pdf_parser.ocr_failed", error=str(e))
        return ""


_SURYA_REC: Any | None = None
_SURYA_DET: Any | None = None


class _suppress:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return True
