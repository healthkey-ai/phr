"""
PDF rasteriser + paged batching tests.

Uses PyMuPDF to build synthetic PDFs in-memory — no fixture files needed.
"""
import fitz
import pytest

from apps.labs.parsers.pdf_rasteriser import (
    BATCH_OVERLAP,
    BATCH_SIZE,
    MAX_PAGES,
    PageBatch,
    PageImage,
    PdfTooLargeError,
    batch_pages,
    rasterise,
)


def _make_pdf(page_count: int) -> bytes:
    """Build an N-page PDF in memory with minimal text content per page."""
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} — test content")
    buf = doc.write()
    doc.close()
    return buf


def _make_png() -> bytes:
    """Build a small test PNG in memory via PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    page.insert_text((50, 150), "test image")
    pix = page.get_pixmap()
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


# ── rasterise() ──────────────────────────────────────────────────────────────

class TestRasterise:
    def test_single_page_pdf(self):
        pdf = _make_pdf(1)
        pages = rasterise(pdf, "application/pdf")
        assert len(pages) == 1
        assert pages[0].page_index == 0
        assert pages[0].mime_type == "image/jpeg"
        # JPEG magic bytes
        assert pages[0].image_bytes[:3] == b"\xff\xd8\xff"

    def test_multi_page_pdf_preserves_order(self):
        pdf = _make_pdf(5)
        pages = rasterise(pdf, "application/pdf")
        assert len(pages) == 5
        assert [p.page_index for p in pages] == [0, 1, 2, 3, 4]

    def test_rejects_pdf_over_max_pages(self):
        pdf = _make_pdf(MAX_PAGES + 1)
        with pytest.raises(PdfTooLargeError) as exc:
            rasterise(pdf, "application/pdf")
        assert str(MAX_PAGES) in str(exc.value)

    def test_accepts_pdf_at_max_pages(self):
        pdf = _make_pdf(MAX_PAGES)
        pages = rasterise(pdf, "application/pdf")
        assert len(pages) == MAX_PAGES

    def test_jpeg_passthrough(self):
        # Fake JPEG magic bytes + padding — passthrough doesn't parse the file
        raw = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        pages = rasterise(raw, "image/jpeg")
        assert len(pages) == 1
        assert pages[0].image_bytes == raw

    def test_png_reencoded_to_jpeg(self):
        png = _make_png()
        pages = rasterise(png, "image/png")
        assert len(pages) == 1
        # Output is JPEG even though input was PNG
        assert pages[0].image_bytes[:3] == b"\xff\xd8\xff"

    def test_unsupported_mime_raises(self):
        with pytest.raises(ValueError):
            rasterise(b"anything", "application/octet-stream")


# ── batch_pages() paged mode (§6.4) ──────────────────────────────────────────

class TestBatchPages:
    def _pages(self, n: int) -> list[PageImage]:
        return [PageImage(page_index=i, image_bytes=b"") for i in range(n)]

    def test_empty_input_returns_single_empty_batch(self):
        batches = batch_pages([])
        assert len(batches) == 1
        assert batches[0].pages == []

    def test_single_batch_when_under_size(self):
        batches = batch_pages(self._pages(5))
        assert len(batches) == 1
        assert batches[0].batch_index == 0
        assert batches[0].page_indices == [0, 1, 2, 3, 4]

    def test_single_batch_at_exact_size(self):
        batches = batch_pages(self._pages(BATCH_SIZE))
        assert len(batches) == 1
        assert len(batches[0].pages) == BATCH_SIZE

    def test_two_batches_with_overlap(self):
        """12 pages, BATCH_SIZE=10, OVERLAP=2 →
        batch 0: 0..9, batch 1: 8..11 (pages 8, 9 appear in both)."""
        batches = batch_pages(self._pages(12))
        assert len(batches) == 2
        assert batches[0].page_indices == list(range(0, 10))
        assert batches[1].page_indices == [8, 9, 10, 11]

    def test_overlap_pages_appear_in_both(self):
        """Pages BATCH_SIZE-OVERLAP..(BATCH_SIZE-1) belong to both batches."""
        batches = batch_pages(self._pages(20))
        overlap_range = set(range(BATCH_SIZE - BATCH_OVERLAP, BATCH_SIZE))
        b0_indices = set(batches[0].page_indices)
        b1_indices = set(batches[1].page_indices)
        assert overlap_range.issubset(b0_indices)
        assert overlap_range.issubset(b1_indices)

    def test_60_pages_produces_expected_batch_count(self):
        """60 pages / step=8 (10-2 overlap) = 7.5, rounded up → 8 batches
        but the actual stride means: 0-9, 8-17, 16-25, 24-33, 32-41, 40-49,
        48-57, 56-59 = 8 batches."""
        batches = batch_pages(self._pages(60))
        # Each batch size = min(BATCH_SIZE, remaining)
        assert len(batches) >= 6
        assert batches[0].batch_index == 0
        # Every page (0..59) appears in at least one batch
        seen: set[int] = set()
        for b in batches:
            seen.update(b.page_indices)
        assert seen == set(range(60))

    def test_batch_indices_are_sequential(self):
        batches = batch_pages(self._pages(25))
        for i, b in enumerate(batches):
            assert b.batch_index == i
