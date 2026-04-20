"""
Celery tasks for the labs app.

Phase 2c pipeline:

  1. Load LabUpload + its files
  2. For each file: rasterise (PDF → pages, image → passthrough)
  3. Concatenate all page images preserving file order
  4. llm_parser.extract(pages) — handles paged-merge and refusal internally
  5. For each ParsedLabResult: resolve test identity (LOINC or name_fallback),
     build the parsed_results entry including matched_test_id
  6. Save parsed_results onto the LabUpload row + flip status to completed

Phase 2d layers the review/commit step on top (patient decides which rows
become real LabResult objects). This task writes to `parsed_results` only —
it does NOT create LabResult rows.
"""
import logging
from datetime import datetime

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .models import LabUpload

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.labs.process_lab_upload",
    soft_time_limit=270,
    time_limit=300,
    acks_late=True,
)
def process_lab_upload(self, upload_id: int) -> dict:
    """Extract structured lab values from an uploaded report.

    Idempotent. Re-running on an already-completed upload overwrites
    `parsed_results` — used by the retry endpoint in 2d.

    Returns a compact observability dict (consumed by Flower / logs).
    """
    try:
        upload = LabUpload.objects.prefetch_related("files").get(pk=upload_id)
    except LabUpload.DoesNotExist:
        logger.warning("process_lab_upload: upload %s disappeared before task ran", upload_id)
        return {"upload_id": upload_id, "status": "missing"}

    logger.info(
        "process_lab_upload starting",
        extra={"upload_id": upload_id, "file_count": upload.files.count()},
    )

    try:
        upload.mark_processing()
        parsed = _run_extraction_pipeline(upload)
        # Stamp which provider actually produced this extraction. Matches the
        # llm_parser._resolve_provider() result so downstream analytics can
        # slice accuracy by provider without a second env-var read.
        from .parsers.llm_parser import _resolve_provider
        upload.provider = _resolve_provider()
        upload.mark_completed(parsed_results=parsed)
        upload.save(update_fields=["provider"])
        logger.info(
            "process_lab_upload completed",
            extra={
                "upload_id": upload_id,
                "result_count": len(parsed),
                "match_rate": _match_rate(parsed),
            },
        )
        return {
            "upload_id": upload_id,
            "status": "completed",
            "result_count": len(parsed),
        }

    except SoftTimeLimitExceeded:
        upload.mark_failed("Reading took too long — try a clearer scan.")
        logger.warning("process_lab_upload soft timeout", extra={"upload_id": upload_id})
        return {"upload_id": upload_id, "status": "failed", "reason": "soft_timeout"}

    except Exception as exc:
        # Branch on our own error hierarchy for user-facing copy; fall through
        # to a generic message for unknown failures. Imports are local so the
        # task module loads even if anthropic isn't installed (tests).
        from .parsers.llm_parser import (
            ExtractionError,
            ParseError,
            RefusalError,
            TimeoutError as LlmTimeoutError,
        )
        from .parsers.pdf_rasteriser import PdfTooLargeError

        if isinstance(exc, RefusalError):
            msg = "Our AI couldn't process this report. Please enter the values manually or try a different scan."
            reason = "refusal"
        elif isinstance(exc, LlmTimeoutError):
            msg = "Reading took too long — try a clearer scan."
            reason = "llm_timeout"
        elif isinstance(exc, ParseError):
            msg = "We couldn't read the values from this report. Try a clearer scan or enter them manually."
            reason = "parse_error"
        elif isinstance(exc, PdfTooLargeError):
            msg = str(exc)
            reason = "pdf_too_large"
        elif isinstance(exc, ExtractionError):
            msg = "Our AI is having trouble reading reports right now. Your file is saved — try again in a few minutes."
            reason = "llm_error"
        else:
            msg = "Something went wrong reading your report. Please try again."
            reason = "unexpected"

        upload.mark_failed(msg)
        logger.exception(
            "process_lab_upload failed",
            extra={"upload_id": upload_id, "reason": reason, "error": str(exc)},
        )
        return {"upload_id": upload_id, "status": "failed", "reason": reason}


# ── Pipeline body ────────────────────────────────────────────────────────────

def _run_extraction_pipeline(upload: LabUpload) -> list[dict]:
    """Orchestration: rasterise → extract → resolve identity.

    Returns the parsed_results JSON payload (list of dicts) for storage on
    LabUpload.parsed_results. Each dict is the shape the review UI consumes
    and the commit endpoint (Phase 2d) turns into LabResult rows.
    """
    # Imports are local so this module can load without anthropic installed.
    from .matching import resolve_test_identity
    from .parsers.llm_parser import ParsedLabResult, extract
    from .parsers.pdf_rasteriser import PageImage, rasterise

    # ── 1–3. Rasterise all files into a single page list ─────────────────
    all_pages: list[PageImage] = []
    for file_row in upload.files.order_by("file_order"):
        with file_row.file.open("rb") as fp:
            file_bytes = fp.read()
        file_pages = rasterise(file_bytes, file_row.mime_type)
        # Re-number page_index so it's unique across files in this upload.
        # The original index is kept as file_row.file_order offset.
        base = len(all_pages)
        for p in file_pages:
            all_pages.append(PageImage(page_index=base + p.page_index, image_bytes=p.image_bytes))

    if not all_pages:
        return []

    # ── 4. LLM extraction (handles paged-merge + refusal + retry) ────────
    rows: list[ParsedLabResult] = extract(all_pages)
    if not rows:
        return []

    # ── 5. Resolve test identity for every row ──────────────────────────
    enriched: list[dict] = []
    for idx, row in enumerate(rows):
        test_type, match_method = resolve_test_identity(
            raw_name=row["test_name"],
            raw_loinc=row.get("loinc_code"),
            raw_unit=row.get("unit"),
            raw_value=row.get("value"),
        )
        enriched.append({
            # LLM-extracted fields (verbatim for audit)
            "raw_name": row["test_name"],
            "raw_loinc_code": row.get("loinc_code", ""),
            "raw_unit": row.get("unit", ""),
            "value": row["value"],
            "unit": row.get("unit", ""),
            "reference_min": row.get("reference_min"),
            "reference_max": row.get("reference_max"),
            "measured_date": _parse_measured_date(row.get("measured_date"), upload.lab_date),
            "page": row.get("page", 0),
            "confidence": row.get("confidence", 0.0),
            # Matched test identity (always populated after 2c pivot —
            # resolve_test_identity never returns None)
            "matched_test_id": test_type.pk,
            "matched_test_abbreviation": test_type.abbreviation,
            "matched_test_name": test_type.name,
            "match_method": match_method,
            # Review-state (populated in Phase 2d commit)
            "accepted": None,
            "source_index": idx,  # stable handle for the commit endpoint
        })
    return enriched


def _parse_measured_date(raw: str | None, upload_lab_date) -> str | None:
    """Return a YYYY-MM-DD string or None.

    Precedence: LLM's measured_date > upload.lab_date > None.
    The LLM's date is trusted when well-formed; malformed dates fall back to
    the patient-supplied lab_date (design §12.3).
    """
    if raw:
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            pass
    if upload_lab_date:
        return upload_lab_date.isoformat()
    return None


def _match_rate(parsed: list[dict]) -> float:
    """Fraction of parsed rows that matched via LOINC (not name fallback).
    Pushed to observability — feeds `lab_upload.match_rate_percent` metric."""
    if not parsed:
        return 0.0
    loinc_hits = sum(1 for r in parsed if r.get("match_method") == "loinc")
    return round(loinc_hits / len(parsed), 3)
