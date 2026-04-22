"""
LLM vision parser for lab report extraction.

Design doc §6.1, §6.3, §6.4, §12.2. Phase 2c shipped Claude-only; the
OpenAI adapter was added as a follow-up so LAB_LLM_PROVIDER can switch
between the two without touching the task, matcher, or pipeline. Both
providers return the same `ParsedLabResult` shape — everything downstream
is provider-agnostic.

Provider routing (settings.LAB_LLM_PROVIDER):
  - "claude" (default) → anthropic.Anthropic, model settings.LAB_CLAUDE_MODEL
                         (default "claude-sonnet-4-6")
  - "openai"           → openai.OpenAI, model settings.LAB_OPENAI_MODEL
                         (default "gpt-4o")

Shared across providers:
  - Single extract() call per PageBatch; merge_results dedups across batches
  - Refusal detection BEFORE JSON parsing — never retry a refusal
  - Strict JSON output, single retry on parse failure
  - 60s per-call timeout; rate-limit backoff handled by the caller

Tests mock the provider clients, so CI runs fully offline.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from django.conf import settings

from .pdf_rasteriser import PageBatch, PageImage

logger = logging.getLogger(__name__)

# Model IDs are runtime-configurable via LAB_CLAUDE_MODEL / LAB_OPENAI_MODEL.
# Defaults are pinned so behavior doesn't drift mid-deploy when env is unset.
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o"

# Conservative output caps. Claude Sonnet handles 32k out comfortably;
# gpt-4o caps at 16k. Both are well above our typical ~20k-token report
# extraction ceiling.
CLAUDE_MAX_OUTPUT_TOKENS = 32_000
OPENAI_MAX_OUTPUT_TOKENS = 16_000

# LLM call timeout (seconds). Celery task's soft time limit is 270s — keep
# per-call timeout well below so we get multiple retries before the task dies.
REQUEST_TIMEOUT = 60

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "lab_extraction.txt"


class ParsedLabResult(TypedDict):
    """Single extracted lab row. Contract for the matching layer + serializers.

    Shape locked in design doc §6.3 + the §6.1 prompt. Phase 2c fills `loinc_code`
    + `loinc_name` + `loinc_default_unit` from the LLM; matching.resolve_test_identity
    validates the code against loinc_common.json before trusting it.
    """

    test_name: str
    value: str | None
    unit: str
    reference_min: float | None
    reference_max: float | None
    measured_date: str | None
    page: int
    confidence: float
    loinc_code: str
    loinc_name: str
    loinc_default_unit: str
    batch_index: int   # Which extraction batch produced this row


# ── Errors ────────────────────────────────────────────────────────────────────

class ExtractionError(Exception):
    """Base for all parser-level failures."""


class RefusalError(ExtractionError):
    """The LLM refused to process the image (likely a privacy/safety trip).

    Per design doc §12.2: do NOT retry — the model won't change its answer.
    Task fails the upload with a user-facing 'please enter values manually'
    message.
    """


class ParseError(ExtractionError):
    """The LLM returned non-JSON output. Retriable once."""


class TimeoutError(ExtractionError):
    """The LLM call exceeded REQUEST_TIMEOUT. Retriable with backoff."""


# ── Refusal detection ────────────────────────────────────────────────────────

# Case-insensitive patterns. Matches the LLM's most common decline phrases
# before we attempt JSON parsing. Kept reasonably narrow — but expanded to
# cover OpenAI's "I'm sorry, but I cannot..." phrasing as well as Claude's
# "I apologize" variant. The head-anchored bits avoid false positives from
# legitimate extractions that happen to include the word "cannot" in a long
# narrative string.
_REFUSAL_PATTERNS = re.compile(
    r"""
    (?:
      ^\s*i\s+(?:can(?:not|'t)|am\s+unable|won't)\b     |  # "I cannot", "I am unable"
      ^\s*i\s+apologize                                 |  # "I apologize"
      ^\s*i'?m\s+sorry\b                                |  # "I'm sorry, but..." (OpenAI)
      ^\s*i'?m\s+unable\b                               |  # "I'm unable to..."
      (?:^|[\n\s])as\s+an\s+ai\b                        |  # "as an AI"
      (?:^|[\n\s])i'?m\s+not\s+able\s+to\s+process      |  # "I'm not able to process"
      (?:^|[\n\s])this\s+appears\s+to\s+contain\s+
         (?:personal|private|sensitive)\s+information   |
      (?:^|[\n\s])i\s+can(?:not|'t)\s+(?:extract|process|help|assist)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def detect_refusal(response_text: str) -> bool:
    """Scan the first 500 chars of response for refusal phrases.

    Why first 500: the LLM usually leads with the refusal. Scanning the whole
    response risks false positives if a later data row contains e.g. the
    phrase 'as an AI' inside a test name on an edge-case report.
    """
    if not response_text:
        return False
    head = response_text[:500]
    return bool(_REFUSAL_PATTERNS.search(head))


# ── Catalog hint (injected into prompt) ──────────────────────────────────────

def _build_catalog_hint() -> str:
    """Produce a compact test list from loinc_common.json for the prompt's
    {CATALOG_HINT} placeholder. Helps the model prefer our canonical LOINCs
    and names, without restricting extraction.
    """
    from ..matching import LOINC_COMMON
    lines: list[str] = []
    # Cap the hint at ~80 lines so it doesn't dominate the prompt.
    for i, (code, entry) in enumerate(LOINC_COMMON.items()):
        if i >= 80:
            break
        name = entry["loinc_short_name"]
        unit = entry["loinc_default_unit"] or "qualitative"
        lines.append(f"- {name} (LOINC {code}, {unit})")
    return "\n".join(lines)


def _compile_prompt() -> str:
    """Load prompt.txt and inject the catalog hint. Cached per worker process.

    Recompile on every call is fine — the file read is O(1) KB. If we hit
    perf issues, cache via module-level dict keyed by catalog hash.
    """
    template = PROMPT_PATH.read_text()
    return template.replace("{CATALOG_HINT}", _build_catalog_hint())


# ── JSON recovery ────────────────────────────────────────────────────────────

_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]", re.MULTILINE)


def _parse_response_json(raw: str) -> list[dict]:
    """Parse the LLM's response text into a list of row dicts.

    Tolerates:
      - markdown code fences around JSON (strips ``` and ```json)
      - leading/trailing prose (extracts the first [...] block)
      - single-line or multi-line arrays

    Raises ParseError if no valid JSON array is recoverable.
    """
    if not raw or not raw.strip():
        return []

    # Strip common code-fence wrappings
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence up to the first newline
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: extract the first top-level [...] block
    match = _JSON_ARRAY_RE.search(raw)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError as exc:
            raise ParseError(f"LLM output contained a JSON block but it didn't parse: {exc}") from exc

    raise ParseError(f"LLM output did not contain a recognizable JSON array: {raw[:200]!r}")


# ── Provider dispatch ────────────────────────────────────────────────────────

def _resolve_provider() -> str:
    """Return the normalised provider name for this extraction.

    Reads settings.LAB_LLM_PROVIDER, lowercases, validates. Unknown values
    fall back to "claude" with a warning — we never silently disable
    extraction on a typo.
    """
    raw = (getattr(settings, "LAB_LLM_PROVIDER", "") or "claude").strip().lower()
    if raw in ("claude", "openai"):
        return raw
    logger.warning("Unknown LAB_LLM_PROVIDER=%r; defaulting to 'claude'", raw)
    return "claude"


# ── Claude client + call ─────────────────────────────────────────────────────

def _get_anthropic_client():
    """Lazily construct the anthropic.Anthropic client. Centralized so tests
    can monkeypatch this single function to inject a mock."""
    import anthropic
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        raise ExtractionError(
            "ANTHROPIC_API_KEY is not configured. Set it in the Render dashboard."
        )
    return anthropic.Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT)


def _encode_image_claude(page: PageImage) -> dict:
    """Claude vision image content block: base64 source object."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": page.mime_type,
            "data": base64.b64encode(page.image_bytes).decode("ascii"),
        },
    }


def _call_claude(batch: PageBatch, system_prompt: str) -> str:
    """Issue one Claude Messages API call. Returns the raw response text.

    Timeout → TimeoutError. Other failures → ExtractionError. Caller handles
    refusal detection and JSON parsing so those paths are provider-agnostic.
    """
    client = _get_anthropic_client()
    content_blocks = [_encode_image_claude(p) for p in batch.pages]
    model = getattr(settings, "LAB_CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL) or DEFAULT_CLAUDE_MODEL

    try:
        response = client.messages.create(
            model=model,
            max_tokens=CLAUDE_MAX_OUTPUT_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
        )
    except Exception as exc:
        # anthropic.APITimeoutError subclasses APIConnectionError in some SDK
        # versions — keep the check duck-typed so a minor bump doesn't break.
        name = type(exc).__name__
        if "Timeout" in name:
            raise TimeoutError(f"Claude timed out: {exc}") from exc
        raise ExtractionError(f"Claude API error ({name}): {exc}") from exc

    text_parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return "".join(text_parts)


# ── OpenAI client + call ─────────────────────────────────────────────────────

def _get_openai_client():
    """Lazily construct the openai.OpenAI client. Centralised for test
    monkeypatching, same pattern as _get_anthropic_client."""
    from openai import OpenAI
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        raise ExtractionError(
            "OPENAI_API_KEY is not configured. Set it in the Render dashboard."
        )
    return OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT)


def _encode_image_openai(page: PageImage) -> dict:
    """OpenAI chat.completions image_url content block. Uses the data-URL
    form; `detail: high` gives us full-resolution vision (critical for small
    printed lab values). That's more tokens than "low" or "auto", but the
    150-DPI JPEGs we render are already modest size."""
    data_url = f"data:{page.mime_type};base64,{base64.b64encode(page.image_bytes).decode('ascii')}"
    return {
        "type": "image_url",
        "image_url": {"url": data_url, "detail": "high"},
    }


def _call_openai(batch: PageBatch, system_prompt: str) -> str:
    """Issue one OpenAI chat.completions call with vision. Returns the raw
    response text. Mirrors _call_claude's error surface.

    Empty content is treated as an ExtractionError rather than an empty
    extraction — a successful 200 with no text usually means an OpenAI-side
    moderation filter, a reasoning-model `refusal` field, or a finish_reason
    of "length" (completion tokens exhausted before any text was produced).
    Returning "" silently would make those look identical to a clean report
    with no labs, which confuses debugging.
    """
    client = _get_openai_client()
    model = getattr(settings, "LAB_OPENAI_MODEL", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL
    content_blocks = [_encode_image_openai(p) for p in batch.pages]

    logger.info(
        "OpenAI extract_batch call",
        extra={
            "model": model,
            "batch_index": batch.batch_index,
            "page_count": len(batch.pages),
        },
    )

    try:
        response = client.chat.completions.create(
            model=model,
            # OpenAI deprecated `max_tokens` in favor of `max_completion_tokens`
            # for newer models (GPT-5 family, o1, etc.). The new name works on
            # older models too, so it's the forward-compatible choice.
            max_completion_tokens=OPENAI_MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_blocks},
            ],
        )
    except Exception as exc:
        name = type(exc).__name__
        if "Timeout" in name:
            raise TimeoutError(f"OpenAI timed out: {exc}") from exc
        # Include the actual SDK error message — otherwise "OpenAI API error
        # (NotFoundError): Error code: 404 ..." stays hidden behind ExtractionError
        # and the task-level copy.
        logger.error("OpenAI API raised %s: %s", name, exc)
        raise ExtractionError(f"OpenAI API error ({name}): {exc}") from exc

    if not response.choices:
        raise ExtractionError(
            "OpenAI returned a response with no choices — usually a signal that "
            "the content was blocked or the model name is invalid. Check the "
            "API key, model, and org/project settings."
        )

    choice = response.choices[0]
    finish_reason = getattr(choice, "finish_reason", None)
    content = choice.message.content or ""
    refusal = getattr(choice.message, "refusal", None)

    if refusal:
        # Structured refusal field (newer SDKs / reasoning models).
        raise RefusalError(f"OpenAI refusal: {refusal}")

    if not content:
        # Log enough detail to diagnose why. Most common causes at this point:
        # - finish_reason="length" → max_completion_tokens exhausted before text emerged
        # - finish_reason="content_filter" → moderation blocked the image
        logger.warning(
            "OpenAI returned empty content",
            extra={
                "finish_reason": finish_reason,
                "model": model,
                "batch_index": batch.batch_index,
            },
        )
        raise ExtractionError(
            f"OpenAI returned no text (finish_reason={finish_reason!r}). "
            "Check the model name, API key quota, and that the request isn't "
            "tripping the content filter."
        )

    logger.info(
        "OpenAI returned %d chars (finish_reason=%s)",
        len(content),
        finish_reason,
    )
    return content


# ── Top-level batch extraction (provider-agnostic) ───────────────────────────

def extract_batch(
    batch: PageBatch,
    *,
    total_batches: int,
    prompt: str | None = None,
) -> list[ParsedLabResult]:
    """Run one LLM extraction call on a single PageBatch.

    Routes to the configured provider via settings.LAB_LLM_PROVIDER.
    `total_batches` injects 'This is batch N of M' context into the system
    prompt when paged mode is active (N > 1).
    """
    provider = _resolve_provider()
    prompt_text = prompt or _compile_prompt()

    system_parts = [prompt_text]
    if total_batches > 1:
        system_parts.append(
            f"This is batch {batch.batch_index + 1} of {total_batches} from a larger report."
        )
    system_prompt = "\n\n".join(system_parts)

    if provider == "openai":
        raw_text = _call_openai(batch, system_prompt)
    else:
        raw_text = _call_claude(batch, system_prompt)

    # Refusal check BEFORE parsing — design doc §12.2. Shared across providers
    # because both families use the same polite-decline phrasing.
    if detect_refusal(raw_text):
        raise RefusalError(
            f"{provider.title()} declined to process the image. "
            "Patient must enter values manually."
        )

    raw_rows = _parse_response_json(raw_text)

    results: list[ParsedLabResult] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        results.append(_coerce_row(row, batch_index=batch.batch_index))
    return results


def _coerce_row(row: dict, *, batch_index: int) -> ParsedLabResult:
    """Force an LLM-returned dict into the ParsedLabResult TypedDict shape.

    Missing fields get sensible defaults; wrong types get coerced or nulled.
    We're permissive here because the LLM sometimes returns `value` as a
    number when the prompt asks for a string — that's fine, str() it.
    """
    def _num_or_none(v):
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return ParsedLabResult(
        test_name=str(row.get("test_name") or "").strip(),
        value=None if row.get("value") is None else str(row.get("value")).strip(),
        unit=str(row.get("unit") or "").strip(),
        reference_min=_num_or_none(row.get("reference_min")),
        reference_max=_num_or_none(row.get("reference_max")),
        measured_date=(row.get("measured_date") or None),
        page=int(row.get("page") or 0),
        confidence=max(0.0, min(1.0, _num_or_none(row.get("confidence")) or 0.0)),
        loinc_code=str(row.get("loinc_code") or "").strip(),
        loinc_name=str(row.get("loinc_name") or "").strip(),
        loinc_default_unit=str(row.get("loinc_default_unit") or "").strip(),
        batch_index=batch_index,
    )


# ── Paged extraction + merge (design §6.4) ───────────────────────────────────

def extract(pages: list[PageImage]) -> list[ParsedLabResult]:
    """Top-level entry point. Rasterises, batches, extracts, merges.

    Caller passes the fully-rasterised page list (from pdf_rasteriser.rasterise).
    We handle the ≤10-page single-shot case and the >10-page paged-merge case
    with 2-page overlap. Dedup across batches is the caller's contract.

    Raises:
      RefusalError: Claude declined (any batch)
      ParseError: Claude returned non-JSON (after one retry per batch)
      TimeoutError: any batch timed out
      ExtractionError: other API errors
    """
    from .pdf_rasteriser import batch_pages

    batches = batch_pages(pages)
    total = len(batches)
    all_results: list[ParsedLabResult] = []
    prompt = _compile_prompt()

    for batch in batches:
        try:
            batch_results = extract_batch(batch, total_batches=total, prompt=prompt)
        except ParseError:
            # One retry on parse failure (§6.3). Refusal + timeout NOT retried
            # here — those propagate to the task, which decides the UX.
            logger.warning("JSON parse failed on batch %s; retrying once", batch.batch_index)
            batch_results = extract_batch(batch, total_batches=total, prompt=prompt)
        all_results.extend(batch_results)

    return merge_results(all_results)


def merge_results(rows: list[ParsedLabResult]) -> list[ParsedLabResult]:
    """Dedup rows produced by paged extraction.

    Dedup key: (normalize_name(test_name), value_str, unit, measured_date)

    When duplicates collide:
      - Keep the higher-confidence row
      - On tie, keep the earlier batch_index (preserves source order)

    Empty input returns [].
    """
    from ..matching import normalize_name

    if not rows:
        return []

    best: dict[tuple, ParsedLabResult] = {}
    for row in rows:
        key = (
            normalize_name(row["test_name"]),
            (row["value"] or "").strip(),
            (row["unit"] or "").strip(),
            row["measured_date"] or "",
        )
        existing = best.get(key)
        if existing is None:
            best[key] = row
            continue
        # Tie-break: higher confidence wins; on tie, earlier batch_index wins.
        if row["confidence"] > existing["confidence"]:
            best[key] = row
        elif row["confidence"] == existing["confidence"] and row["batch_index"] < existing["batch_index"]:
            best[key] = row
    return list(best.values())
