"""
Test identity resolution.

Phase 2c pivot (design doc §7): LOINC is the identity. No more curated alias
catalog, no tiered exact/fuzzy matching, no disambiguation rules. The matcher
collapses to a single function that, given an LLM-extracted row, returns the
LabTestType row it belongs to — creating one on the fly when needed.

Pipeline:
  1. normalize_loinc(raw_loinc_code) → canonical NNNNN-N or ""
  2. If normalized code is in loinc_common.json (§3.4):
       → LabTestType.objects.get_or_create(loinc_code=<code>, ...)
         hydrated from the fixture on first sight
       → match_method = "loinc"
  3. Else fall back to normalized name:
       → lookup by name_normalized among no-LOINC rows; create if missing
       → match_method = "name_fallback"

This file's public surface:
  - normalize_loinc(raw) -> str
  - normalize_name(raw) -> str
  - resolve_test_identity(raw_name, raw_loinc, raw_unit) -> (LabTestType, match_method)
  - LOINC_COMMON (read-only dict) for tests and frontend serialization
"""
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import TypedDict

from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_FIXTURE_PATH = _DATA_DIR / "loinc_common.json"


class LoincEntry(TypedDict):
    loinc_code: str
    loinc_short_name: str
    loinc_default_unit: str
    value_type: str  # numeric | qualitative | ratio


def _load_loinc_fixture() -> dict[str, LoincEntry]:
    """Load loinc_common.json into an immutable dict keyed by normalized code.

    Fails loud at import time if the fixture is missing or malformed — silent
    Tier 0a degradation in prod is an unacceptable failure mode per eng review
    (see docs/patient-app-lab-upload-design.md §7 closing paragraph).
    """
    if not _FIXTURE_PATH.exists():
        raise RuntimeError(
            f"LOINC validation fixture missing: {_FIXTURE_PATH}. "
            "Tier 0a cannot function — refusing to start."
        )
    with _FIXTURE_PATH.open() as f:
        data = json.load(f)

    result: dict[str, LoincEntry] = {}
    for row in data.get("codes", []):
        code = normalize_loinc(row.get("loinc_code", ""))
        if not code:
            continue  # skip malformed rows rather than crash
        result[code] = {
            "loinc_code": code,
            "loinc_short_name": row["loinc_short_name"],
            "loinc_default_unit": row.get("loinc_default_unit", ""),
            "value_type": row["value_type"],
        }
    if not result:
        raise RuntimeError(
            f"LOINC validation fixture at {_FIXTURE_PATH} has no usable entries."
        )
    logger.info("loaded LOINC validation fixture with %d entries", len(result))
    return result


# ── LOINC code normalization ─────────────────────────────────────────────────

_LOINC_RE = re.compile(r"(\d{1,5}-\d)")


def normalize_loinc(raw: str | None) -> str:
    """Return the canonical NNNNN-N LOINC code, or "" if no match.

    Handles common junk the LLM emits: "LOINC:718-7", "718–7" (en-dash),
    "  718-7 ", "LOINC 718-7". Empty / missing checksum-dash returns "".
    """
    if not raw:
        return ""
    # Unicode dashes → ASCII hyphen
    s = raw.replace("\u2013", "-").replace("\u2014", "-").strip()
    m = _LOINC_RE.search(s)
    return m.group(1) if m else ""


# ── Name normalization (shared with LabTestType.save) ────────────────────────

def normalize_name(raw: str | None) -> str:
    """Fold a test name for indexing: NFKD + casefold + strip non-alphanumerics.

    Examples:
      "Hemoglobin A1c"    → "hemoglobin a1c"
      "HGB"               → "hgb"
      "CA 15-3"           → "ca 15 3"
      "κFLC (kappa)"      → "κflc kappa"  (NFKD doesn't decompose Greek, but
                                           casefold still normalizes case)
      "µg/dL"             → "μg dl"       (NFKD maps U+00B5 → U+03BC)

    Why NFKD + casefold: catches Unicode compatibility variants (µ vs u, ﬁ vs fi,
    ß vs ss) that a naive .lower() + strip would miss. Matches the §7 design.
    """
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw)).casefold()
    # Replace anything that isn't a letter or digit with a space, then collapse
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())


# ── Abbreviation slug (for auto-created LabTestType rows) ────────────────────

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug_from_name(raw: str) -> str:
    """Produce a short url-friendly slug from a test name. Used as the
    `abbreviation` for auto-created LabTestType rows where we don't have a
    curated one. Trimmed to 60 chars to fit the model's max_length=64 with
    room for a "-N" disambiguation suffix.
    """
    ascii_form = unicodedata.normalize("NFKD", raw or "").encode("ascii", "ignore").decode("ascii")
    s = _SLUG_NON_ALNUM.sub("-", ascii_form.lower()).strip("-")
    return (s or "test")[:60]


# ── Fixture load (at import) ─────────────────────────────────────────────────

LOINC_COMMON: dict[str, LoincEntry] = _load_loinc_fixture()


# ── Identity resolution ──────────────────────────────────────────────────────

def _infer_value_type(raw_value: str | None, raw_unit: str | None) -> str:
    """Infer value_type from the LLM's first sighting of this test.

    We default to numeric for anything parseable as a float; otherwise
    qualitative. An empty value with an empty unit falls back to numeric
    (most reports have no value only for rows we skipped, and numeric is
    a safer default for trending).

    Examples:
      ("12.5", "g/dL")      → numeric
      ("Not Detected", "")  → qualitative
      ("Positive", "")      → qualitative
      ("",  "")             → numeric (fallback)
    """
    if raw_value is None:
        return "numeric"
    s = str(raw_value).strip()
    if not s:
        return "numeric"
    try:
        float(s)
        return "numeric"
    except (ValueError, TypeError):
        return "qualitative"


def resolve_test_identity(
    raw_name: str,
    raw_loinc: str | None,
    raw_unit: str | None,
    raw_value: str | None = None,
):
    """Return (LabTestType, match_method) for an extracted lab row.

    Never returns None — every call yields a row the extracted result can link
    to. Phase 2c reduced Tier 0 through Tier 2 of the old design down to this
    one function (see design doc §7).

    `match_method` is one of:
      - "loinc"          validated LOINC matched an existing or newly-created
                         LabTestType row
      - "name_fallback"  no usable LOINC, matched or created a row keyed by
                         name_normalized

    Args:
      raw_name: the LLM's test name as printed on the report, verbatim
      raw_loinc: the LLM's LOINC claim (may be None, empty, or garbage)
      raw_unit: the LLM's unit string (used only when auto-creating)
      raw_value: the LLM's value (used to infer value_type on auto-create —
                 a non-numeric string like "Not Detected" produces a
                 qualitative row; a parseable number produces numeric)
    """
    # Lazy import to break the models ↔ matching circular dep (models.save
    # calls normalize_name, so models imports matching — but resolve_test_identity
    # needs models. Both files only end up loaded after Django app init, so
    # this is safe at call time.)
    from .models import LabTestType, MatchMethod

    code = normalize_loinc(raw_loinc)

    # Tier 0a — validated LOINC lookup
    if code and code in LOINC_COMMON:
        fixture_entry = LOINC_COMMON[code]
        defaults = {
            "name": fixture_entry["loinc_short_name"],
            "default_unit": fixture_entry["loinc_default_unit"] or (raw_unit or ""),
            "value_type": fixture_entry["value_type"],
            "abbreviation": _slug_with_collision_suffix(
                _slug_from_name(fixture_entry["loinc_short_name"]),
            ),
        }
        try:
            with transaction.atomic():
                test_type, _created = LabTestType.objects.get_or_create(
                    loinc_code=code,
                    defaults=defaults,
                )
        except IntegrityError:
            # Concurrent auto-create lost a race; re-fetch the winner.
            test_type = LabTestType.objects.get(loinc_code=code)
        return test_type, MatchMethod.LOINC

    # Tier fallback — name-normalized grouping
    normalized = normalize_name(raw_name)
    if not normalized:
        # Truly nothing to match on. Park it under an "unknown" catch-all so
        # the row still lands in the DB and the patient can rename it in review.
        normalized = "unknown test"

    existing = (
        LabTestType.objects
        .filter(name_normalized=normalized)
        .order_by("id")  # prefer the oldest matching row (first-write-wins)
        .first()
    )
    if existing is not None:
        return existing, MatchMethod.NAME_FALLBACK

    # Create a no-LOINC row with a slug'd abbreviation
    slug = _slug_with_collision_suffix(_slug_from_name(raw_name or "test"))
    try:
        with transaction.atomic():
            test_type = LabTestType.objects.create(
                loinc_code="",
                name=raw_name or "Unknown test",
                abbreviation=slug,
                default_unit=(raw_unit or "").strip(),
                value_type=_infer_value_type(raw_value, raw_unit),
            )
    except IntegrityError:
        # Concurrent create by another worker — re-fetch by normalized name.
        test_type = (
            LabTestType.objects
            .filter(name_normalized=normalized)
            .order_by("id")
            .first()
        )
        if test_type is None:
            raise
    return test_type, MatchMethod.NAME_FALLBACK


def _slug_with_collision_suffix(base: str) -> str:
    """Find an unused abbreviation starting from `base`, appending -2, -3, …
    on collision. Called at create time to avoid duplicate-key IntegrityErrors.

    Limited to 50 attempts — beyond that, we append a 4-char random hex. At
    that point we've clearly got a pathological input; best to fail the row
    rather than spin forever.
    """
    import secrets
    from .models import LabTestType

    candidate = base
    for n in range(1, 51):
        if not LabTestType.objects.filter(abbreviation=candidate).exists():
            return candidate
        candidate = f"{base}-{n + 1}"
    return f"{base}-{secrets.token_hex(2)}"
