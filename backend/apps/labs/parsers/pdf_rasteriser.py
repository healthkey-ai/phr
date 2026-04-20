"""
PDF + image rasterisation for LLM vision extraction.

Design doc §6 / §6.4:
  - PDF pages rendered at 150 DPI, JPEG quality 85 (readable, compact)
  - Generator-based: one page in memory at a time
  - Hard caps: 60 pages per PDF (§6.4), 10 MB per file (§5.2)
  - Paged extraction mode: batches of 10 pages with a 2-page overlap so a
    test whose name and value straddle page boundaries gets seen by both
    batches (and dedup'd later by llm_parser.merge_results)
"""
import io
import logging
from dataclasses import dataclass

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Rasterisation parameters — tuned in the design doc §6.2.
TARGET_DPI = 150
JPEG_QUALITY = 85

# Paged extraction — design §6.4.
BATCH_SIZE = 10            # pages per LLM call
BATCH_OVERLAP = 2          # pages shared between adjacent batches
MAX_PAGES = 60             # hard reject beyond this


@dataclass
class PageImage:
    """One rendered page, ready to hand to the LLM."""

    page_index: int        # 0-based within the source document
    image_bytes: bytes     # JPEG payload
    mime_type: str = "image/jpeg"


class PdfTooLargeError(Exception):
    """Raised when a PDF exceeds MAX_PAGES. The view translates this to a
    user-facing 'split your report and upload separately' error."""


def rasterise(file_bytes: bytes, content_type: str) -> list[PageImage]:
    """Convert an uploaded file into a list of PageImage objects.

    PDF: each page rendered to JPEG at TARGET_DPI.
    Image (JPEG/PNG/HEIC): single-page passthrough (re-encoded to JPEG if
      the source isn't already JPEG, for uniform LLM input).

    Raises:
      PdfTooLargeError: PDF has more than MAX_PAGES
      RuntimeError: PyMuPDF fails to open the file

    The caller (llm_parser.extract) batches these into groups for paged
    extraction; see batch_pages() below.
    """
    if content_type == "application/pdf":
        return list(_rasterise_pdf(file_bytes))

    if content_type == "image/jpeg":
        # Already JPEG — pass through
        return [PageImage(page_index=0, image_bytes=file_bytes)]

    if content_type in ("image/png", "image/heic"):
        # Re-encode to JPEG via PyMuPDF (it handles both natively).
        # Single-page image → single PageImage.
        with fitz.open(stream=file_bytes, filetype=_filetype_for(content_type)) as doc:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=TARGET_DPI)
            buf = io.BytesIO()
            # Use the legacy pnmtojpeg writer; PyMuPDF handles JPEG via Pixmap
            jpeg_bytes = pix.tobytes("jpeg", jpg_quality=JPEG_QUALITY)
            return [PageImage(page_index=0, image_bytes=jpeg_bytes)]

    raise ValueError(f"Unsupported content_type for rasterisation: {content_type}")


def _rasterise_pdf(pdf_bytes: bytes):
    """Yield PageImage per page. Bounded memory: one page at a time."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page_count = doc.page_count
        if page_count > MAX_PAGES:
            raise PdfTooLargeError(
                f"PDF has {page_count} pages (max {MAX_PAGES}). Split and re-upload."
            )
        for idx in range(page_count):
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=TARGET_DPI)
            jpeg_bytes = pix.tobytes("jpeg", jpg_quality=JPEG_QUALITY)
            yield PageImage(page_index=idx, image_bytes=jpeg_bytes)


def _filetype_for(content_type: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/heic": "heic",
        "application/pdf": "pdf",
    }[content_type]


# ── Paged extraction batching (design §6.4) ─────────────────────────────────

@dataclass
class PageBatch:
    """One batch of pages passed to a single LLM call."""

    batch_index: int
    pages: list[PageImage]

    @property
    def page_indices(self) -> list[int]:
        return [p.page_index for p in self.pages]


def batch_pages(pages: list[PageImage]) -> list[PageBatch]:
    """Split page list into batches of BATCH_SIZE with BATCH_OVERLAP overlap.

    ≤ BATCH_SIZE pages: returns a single batch (no overlap applies).

    For N > BATCH_SIZE:
      batch 0: pages 0..(BATCH_SIZE-1)
      batch 1: pages (BATCH_SIZE-BATCH_OVERLAP)..(2*BATCH_SIZE-BATCH_OVERLAP-1)
      batch 2: pages (2*BATCH_SIZE-2*BATCH_OVERLAP)..(3*BATCH_SIZE-2*BATCH_OVERLAP-1)
      ...

    The overlap costs ~20% more image tokens but catches rows whose name sits
    on the last page of one batch and value on the first page of the next.
    Dedup in llm_parser.merge_results removes the duplicates.
    """
    if len(pages) <= BATCH_SIZE:
        return [PageBatch(batch_index=0, pages=list(pages))]

    batches: list[PageBatch] = []
    step = BATCH_SIZE - BATCH_OVERLAP
    batch_idx = 0
    start = 0
    while start < len(pages):
        end = min(start + BATCH_SIZE, len(pages))
        batches.append(PageBatch(batch_index=batch_idx, pages=pages[start:end]))
        if end == len(pages):
            break
        start += step
        batch_idx += 1
    return batches
