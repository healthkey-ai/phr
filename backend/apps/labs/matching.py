"""
Test identity resolution — v2.

Pipeline (three tiers, first match wins):
  Tier 0 — LOINC code lookup:
    normalize_loinc(raw) → LoincEntry DB row (or loinc_common.json fallback)
    → get_or_create LabTestEntry linked to that LoincEntry
    → match_method = "loinc"

  Tier 1 — Alias lookup:
    normalize(raw_name) → LoincAlias.text_normalized exact match
    → if exactly 1 LoincEntry resolves → LabTestEntry
    → match_method = "alias_exact"

  Stub — Name-normalized grouping:
    normalize_name(raw_name) → group by name_normalized, create if new
    → match_method = "name_fallback"

Public surface:
  - normalize_loinc(raw) -> str
  - normalize_name(raw) -> str
  - resolve_test_identity(raw_name, raw_loinc, raw_unit, raw_value) -> (LabTestEntry, match_method)
  - LOINC_COMMON (read-only dict) for backward compat with tests
"""
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import TypedDict

from django.db import IntegrityError, transaction

from .normalize import normalize, normalize_loinc, normalize_name  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_FIXTURE_PATH = _DATA_DIR / "loinc_common.json"


class LoincCommonEntry(TypedDict):
    loinc_code: str
    loinc_short_name: str
    loinc_default_unit: str
    value_type: str


def _load_loinc_fixture() -> dict[str, LoincCommonEntry]:
    if not _FIXTURE_PATH.exists():
        logger.warning("LOINC validation fixture missing: %s", _FIXTURE_PATH)
        return {}
    with _FIXTURE_PATH.open() as f:
        data = json.load(f)

    result: dict[str, LoincCommonEntry] = {}
    for row in data.get("codes", []):
        code = normalize_loinc(row.get("loinc_code", ""))
        if not code:
            continue
        result[code] = {
            "loinc_code": code,
            "loinc_short_name": row["loinc_short_name"],
            "loinc_default_unit": row.get("loinc_default_unit", ""),
            "value_type": row["value_type"],
        }
    logger.info("loaded LOINC validation fixture with %d entries", len(result))
    return result


def _loinc_db_populated() -> bool:
    """Check if LoincEntry table has data. Cached per process; first call logs stats."""
    global _DB_POPULATED
    if _DB_POPULATED is not None:
        return _DB_POPULATED
    try:
        from .models import LoincAlias, LoincEntry
        entry_count = LoincEntry.objects.count()
        alias_count = LoincAlias.objects.count()
        _DB_POPULATED = entry_count > 0
        if _DB_POPULATED:
            logger.info(
                "loinc_db: using DB matcher — %d LoincEntry rows, %d LoincAlias rows",
                entry_count, alias_count,
            )
        else:
            logger.info(
                "loinc_db: LoincEntry table empty — falling back to loinc_common.json fixture (%d codes)",
                len(LOINC_COMMON),
            )
    except Exception:
        _DB_POPULATED = False
        logger.warning("loinc_db: could not query LoincEntry table — using fixture fallback")
    return _DB_POPULATED


_DB_POPULATED: bool | None = None


def reset_db_cache():
    """Call after loinc_reset to re-check DB population."""
    global _DB_POPULATED
    _DB_POPULATED = None


# ── Abbreviation slug ──────────────────────────────────────────────────────

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug_from_name(raw: str) -> str:
    ascii_form = unicodedata.normalize("NFKD", raw or "").encode("ascii", "ignore").decode("ascii")
    s = _SLUG_NON_ALNUM.sub("-", ascii_form.lower()).strip("-")
    return (s or "test")[:60]


# ── Fixture load (at import) ─────────────────────────────────────────────────

LOINC_COMMON: dict[str, LoincCommonEntry] = _load_loinc_fixture()


# ── Identity resolution ──────────────────────────────────────────────────────

def _infer_value_type(raw_value: str | None, raw_unit: str | None) -> str:
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


def _get_or_create_for_loinc(loinc_entry, raw_unit: str | None):
    """Get or create a LabTestEntry linked to a LoincEntry."""
    from .models import LabTestEntry

    existing = LabTestEntry.objects.filter(loinc_entry=loinc_entry).first()
    if existing:
        return existing

    name = loinc_entry.short_name or loinc_entry.long_name or loinc_entry.component
    defaults = {
        "name": name,
        "loinc_entry": loinc_entry,
        "default_unit": loinc_entry.default_unit or (raw_unit or ""),
        "value_type": loinc_entry.value_type or "numeric",
        "abbreviation": _slug_with_collision_suffix(_slug_from_name(name)),
    }
    try:
        with transaction.atomic():
            test_entry, _created = LabTestEntry.objects.get_or_create(
                name_normalized=normalize_name(name),
                defaults=defaults,
            )
    except IntegrityError:
        test_entry = LabTestEntry.objects.filter(
            name_normalized=normalize_name(name),
        ).first()
        if test_entry is None:
            raise
    if test_entry.loinc_entry_id is None:
        test_entry.loinc_entry = loinc_entry
        test_entry.save(update_fields=["loinc_entry"])
    return test_entry


def resolve_test_identity(
    raw_name: str,
    raw_loinc: str | None,
    raw_unit: str | None,
    raw_value: str | None = None,
):
    """Return (LabTestEntry, match_method) for an extracted lab row.

    Never returns None — every call yields a row the extracted result can
    link to.
    """
    from .models import LabTestEntry, LoincAlias, LoincEntry, MatchMethod

    code = normalize_loinc(raw_loinc)
    use_db = _loinc_db_populated()

    # ── Tier 0 — LOINC code lookup ───────────────────────────────────────
    if code:
        if use_db:
            loinc = LoincEntry.objects.filter(code=code).first()
            if loinc:
                test_entry = _get_or_create_for_loinc(loinc, raw_unit)
                logger.debug(
                    "resolve: tier0_db raw_name=%r loinc=%s → entry=%s",
                    raw_name, code, test_entry.abbreviation,
                )
                return test_entry, MatchMethod.LOINC
            else:
                logger.info(
                    "resolve: tier0_miss loinc=%s not in LoincEntry — falling through (raw_name=%r)",
                    code, raw_name,
                )

        elif code in LOINC_COMMON:
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
                    test_entry, _created = LabTestEntry.objects.get_or_create(
                        name_normalized=normalize_name(fixture_entry["loinc_short_name"]),
                        defaults=defaults,
                    )
            except IntegrityError:
                test_entry = LabTestEntry.objects.filter(
                    name_normalized=normalize_name(fixture_entry["loinc_short_name"]),
                ).first()
                if test_entry is None:
                    raise
            logger.debug(
                "resolve: tier0_fixture raw_name=%r loinc=%s → entry=%s",
                raw_name, code, test_entry.abbreviation,
            )
            return test_entry, MatchMethod.LOINC

        else:
            logger.info(
                "resolve: tier0_miss loinc=%s not in fixture — falling through (raw_name=%r)",
                code, raw_name,
            )

    # ── Tier 1 — Alias lookup ────────────────────────────────────────────
    if use_db and raw_name:
        normalized_alias = normalize(raw_name)
        if normalized_alias:
            aliases = (
                LoincAlias.objects
                .filter(text_normalized=normalized_alias)
                .select_related("loinc_entry")
                .values_list("loinc_entry", flat=True)
                .distinct()
            )
            loinc_ids = list(aliases[:2])
            if len(loinc_ids) == 1:
                loinc = LoincEntry.objects.get(pk=loinc_ids[0])
                test_entry = _get_or_create_for_loinc(loinc, raw_unit)
                logger.debug(
                    "resolve: tier1_alias raw_name=%r normalized=%r → loinc=%s entry=%s",
                    raw_name, normalized_alias, loinc.code, test_entry.abbreviation,
                )
                return test_entry, MatchMethod.ALIAS_EXACT
            elif len(loinc_ids) > 1:
                logger.info(
                    "resolve: tier1_ambiguous raw_name=%r normalized=%r → %d codes — falling through",
                    raw_name, normalized_alias, len(loinc_ids),
                )
            else:
                logger.info(
                    "resolve: tier1_miss raw_name=%r normalized=%r — no alias match",
                    raw_name, normalized_alias,
                )

    # ── Stub — name-normalized grouping ──────────────────────────────────
    normalized = normalize_name(raw_name)
    if not normalized:
        normalized = "unknown test"

    existing = (
        LabTestEntry.objects
        .filter(name_normalized=normalized)
        .order_by("id")
        .first()
    )
    if existing is not None:
        logger.debug(
            "resolve: stub_existing raw_name=%r → entry=%s (id=%d)",
            raw_name, existing.abbreviation, existing.pk,
        )
        return existing, MatchMethod.NAME_FALLBACK

    slug = _slug_with_collision_suffix(_slug_from_name(raw_name or "test"))
    try:
        with transaction.atomic():
            test_entry = LabTestEntry.objects.create(
                name=raw_name or "Unknown test",
                abbreviation=slug,
                default_unit=(raw_unit or "").strip(),
                value_type=_infer_value_type(raw_value, raw_unit),
            )
    except IntegrityError:
        test_entry = (
            LabTestEntry.objects
            .filter(name_normalized=normalized)
            .order_by("id")
            .first()
        )
        if test_entry is None:
            raise
    logger.warning(
        "resolve: stub_created raw_name=%r → new entry=%s (no LOINC, no alias match)",
        raw_name, test_entry.abbreviation,
    )
    return test_entry, MatchMethod.NAME_FALLBACK


def _slug_with_collision_suffix(base: str) -> str:
    import secrets
    from .models import LabTestEntry

    candidate = base
    for n in range(1, 51):
        if not LabTestEntry.objects.filter(abbreviation=candidate).exists():
            return candidate
        candidate = f"{base}-{n + 1}"
    return f"{base}-{secrets.token_hex(2)}"
