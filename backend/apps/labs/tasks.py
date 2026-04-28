"""
Celery tasks for the labs app — v2.

Pipeline:
  1. Load UploadJob + its files
  2. For each file: rasterise (PDF → pages, image → passthrough)
  3. Concatenate all page images preserving file order
  4. llm_parser.extract(pages)
  5. For each ParsedLabResult: resolve test identity (LOINC or name_fallback)
  6. Save parsed_results onto the UploadJob row + flip status to completed
"""
import logging
import resource
import sys
import time
from datetime import datetime

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .models import UploadJob

logger = logging.getLogger(__name__)



@shared_task(
    bind=True,
    name="apps.labs.process_lab_upload",
    soft_time_limit=270,
    time_limit=300,
    acks_late=True,
)
def process_lab_upload(self, upload_id: int) -> dict:
    try:
        upload = UploadJob.objects.prefetch_related("files").get(pk=upload_id)
    except UploadJob.DoesNotExist:
        logger.warning("process_lab_upload: upload %s disappeared before task ran", upload_id)
        return {"upload_id": upload_id, "status": "missing"}

    file_count = upload.files.count()
    total_bytes = sum(f.size_bytes for f in upload.files.all())
    t0 = time.monotonic()
    mem0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    logger.info(
        "upload_start: id=%d files=%d size=%.1fKB",
        upload_id, file_count, total_bytes / 1024,
    )

    try:
        upload.mark_processing()
        parsed = _run_extraction_pipeline(upload)
        from .parsers.llm_parser import _resolve_provider
        upload.provider = _resolve_provider()
        upload.mark_completed(parsed_results=parsed)
        upload.save(update_fields=["provider"])

        elapsed = time.monotonic() - t0
        mem1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # ru_maxrss: bytes on macOS, KB on Linux
        _rss_scale = 1024 * 1024 if sys.platform == "darwin" else 1024
        mem_delta_mb = (mem1 - mem0) / _rss_scale
        logger.info(
            "upload_done: id=%d results=%d match_rate=%.1f%% "
            "elapsed=%.1fs mem_delta=%.1fMB",
            upload_id, len(parsed), _match_rate(parsed) * 100,
            elapsed, mem_delta_mb,
        )
        return {
            "upload_id": upload_id,
            "status": "completed",
            "result_count": len(parsed),
        }

    except SoftTimeLimitExceeded:
        upload.mark_failed("Reading took too long — try a clearer scan.")
        logger.warning("upload_fail: id=%d reason=soft_timeout elapsed=%.1fs",
                        upload_id, time.monotonic() - t0)
        return {"upload_id": upload_id, "status": "failed", "reason": "soft_timeout"}

    except Exception as exc:
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
        elapsed = time.monotonic() - t0
        logger.exception(
            "upload_fail: id=%d reason=%s elapsed=%.1fs error=%s",
            upload_id, reason, elapsed, exc,
        )
        return {"upload_id": upload_id, "status": "failed", "reason": reason}


def _run_extraction_pipeline(upload: UploadJob) -> list[dict]:
    from .matching import resolve_test_identity
    from .parsers.llm_parser import ParsedLabResult, extract
    from .parsers.pdf_rasteriser import PageImage, rasterise

    all_pages: list[PageImage] = []
    for file_row in upload.files.order_by("file_order"):
        with file_row.file.open("rb") as fp:
            file_bytes = fp.read()
        file_pages = rasterise(file_bytes, file_row.mime_type)
        base = len(all_pages)
        for p in file_pages:
            all_pages.append(PageImage(page_index=base + p.page_index, image_bytes=p.image_bytes))

    if not all_pages:
        return []

    rows: list[ParsedLabResult] = extract(all_pages)
    logger.info("llm_extract: upload=%d returned %d rows", upload.pk, len(rows))
    logger.debug("llm_raw: upload=%d rows=%s", upload.pk, [dict(r) for r in rows])
    upload.raw_llm_response = [dict(r) for r in rows]
    upload.save(update_fields=["raw_llm_response"])
    if not rows:
        return []

    enriched: list[dict] = []
    for idx, row in enumerate(rows):
        test_entry, match_method = resolve_test_identity(
            raw_name=row["test_name"],
            raw_loinc=row.get("loinc_code"),
            raw_unit=row.get("unit"),
            raw_value=row.get("value"),
        )
        enriched.append({
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
            "matched_test_id": test_entry.pk,
            "matched_test_abbreviation": test_entry.abbreviation,
            "matched_test_name": test_entry.name,
            "reference_text": row.get("reference_text", ""),
            "match_method": match_method,
            "accepted": None,
            "source_index": idx,
        })
    return enriched


def _parse_measured_date(raw: str | None, upload_lab_date) -> str | None:
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
    if not parsed:
        return 0.0
    loinc_hits = sum(1 for r in parsed if r.get("match_method") == "loinc")
    return round(loinc_hits / len(parsed), 3)
