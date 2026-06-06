"""Turn raw PDF bytes into plain text, with OCR for scanned pages.

Real leases arrive as free-text PDFs, scans, or a mix. We try the native text
layer first (pdfplumber). Any page with no text layer is almost certainly a
scan, so we rasterise just that page and run OCR (Tesseract) to recover its
text, then hand the merged result downstream exactly as if it had been digital
all along — classify, extract, and validate never know the difference.

OCR is optional and degrades gracefully: if Tesseract or its Python/Poppler
bindings aren't installed, scanned pages simply yield no text and the
gate-check flags the document as needing OCR. So the app still runs with just
``pip install``; OCR turns on when the system dependencies are present
(``brew install tesseract poppler`` / ``apt-get install tesseract-ocr poppler-utils``).
"""

from __future__ import annotations

import io
import logging

import pdfplumber

log = logging.getLogger(__name__)

OCR_DPI = 300  # rasterisation resolution for scanned pages


class PdfTextResult:
    def __init__(self, text: str, page_count: int, scanned_pages: int, ocr_pages: int = 0):
        self.text = text
        self.page_count = page_count
        self.scanned_pages = scanned_pages  # pages with no native text layer
        self.ocr_pages = ocr_pages          # scanned pages OCR actually recovered

    @property
    def needs_ocr(self) -> bool:
        """True when a page had no native text and OCR did not recover it."""
        return self.scanned_pages > self.ocr_pages

    @property
    def used_ocr(self) -> bool:
        return self.ocr_pages > 0


def _ocr_page(pdf_bytes: bytes, page_number: int) -> str:
    """Rasterise one page (1-indexed) and OCR it. Returns '' on any failure."""
    try:
        from pdf2image import convert_from_bytes  # needs Poppler
        import pytesseract                         # needs the Tesseract binary
    except ImportError:
        return ""
    try:
        images = convert_from_bytes(
            pdf_bytes, dpi=OCR_DPI, first_page=page_number, last_page=page_number
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0])
    except Exception as exc:  # noqa: BLE001 - missing binary, bad image, etc.
        log.warning("OCR failed on page %d: %s", page_number, exc)
        return ""


def extract_text(pdf_bytes: bytes) -> PdfTextResult:
    """Pull text from a PDF page by page, OCR-ing pages that have no text layer."""
    chunks: list[str] = []
    scanned = 0
    ocr_recovered = 0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            native = page.extract_text() or ""
            if native.strip():
                chunks.append(native)
                continue
            # No native text -> treat as a scan and try OCR.
            scanned += 1
            ocr_text = _ocr_page(pdf_bytes, idx + 1)
            if ocr_text.strip():
                ocr_recovered += 1
                chunks.append(ocr_text)
            else:
                chunks.append(native)
    return PdfTextResult("\n".join(chunks), page_count, scanned, ocr_recovered)
