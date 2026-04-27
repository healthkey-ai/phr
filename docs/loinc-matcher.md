# LOINC Matching Algorithm (v2)

How an extracted lab test name becomes a LOINC code. This is the
matching engine that runs after the LLM extracts structured results
from a lab report PDF/image.

**Source**: `backend/apps/labs/matcher.py`

---

## Overview

```
LLM extraction (parsers/llm_parser.py) produces per-test ParsedLabResult:
  test_name, abbreviation, aliases[], loinc_code, value, unit, specimen, method, confidence

                    ┌──────────────────────────┐
                    │   Tier 0: LOINC verify    │  LLM gave a code?
                    │   Direct DB lookup        │  Verify it exists + unit-compatible
                    └──────────┬───────────────┘
                               │ miss
                    ┌──────────▼───────────────┐
                    │   Tier 1: Bag-of-words   │  Abbreviation index +
                    │   exact match            │  word-set match against LoincAlias rows
                    └──────────┬───────────────┘
                               │ miss
                    ┌──────────▼───────────────┐
                    │   Stub fallback           │  Create/reuse a stub LabTestEntry
                    │   (in tasks.py)           │  grouped by LOINC code or name+unit
                    └───────────────────────────┘
```

Three possible outcomes from the matcher:
- **matched** — single LOINC code survived all gates → `LabValue.loinc_entry` set to the matched `LoincEntry`
- **no_match** — no tier found anything → falls through to stub `LabTestEntry`
- **ambiguous** — multiple distinct analytes survived → `LabValue.loinc_entry=NULL`, candidates stored

---

## Models

### LoincEntry

Canonical LOINC code reference. One row per LOINC code (~60k for
ACTIVE, CLASSTYPE=1). Loaded from LOINC CSV via `loinc_reset`
management command.

```python
class LoincEntry(models.Model):
    code          = CharField(max_length=16, unique=True, db_index=True)  # "718-7"
    component     = CharField(max_length=128)   # "Hemoglobin"
    short_name    = CharField(max_length=128)   # "Hemoglobin [Mass/Vol]"
    long_name     = CharField(max_length=256)   # "Hemoglobin [Mass/volume] in Blood"
    system        = CharField(max_length=64)    # "Bld" — specimen type
    default_unit  = CharField(max_length=32)    # "g/dL"
    unit_family   = CharField(max_length=32)    # "mass_per_volume" — canonical family
    category      = CharField(max_length=64)    # "CBC" / "CHEM" — from LOINC CLASS
    status        = CharField(max_length=16)    # "ACTIVE" / "DEPRECATED"
    value_type    = CharField(max_length=16)    # "numeric" / "qualitative" / "ratio"
```

### LoincAlias

Many-to-one with `LoincEntry`. Powers the Tier 1 bag-of-words index.

```python
class LoincAlias(models.Model):
    loinc_entry      = ForeignKey(LoincEntry, CASCADE, related_name="aliases")
    text             = CharField(max_length=256)   # "Hemoglobin A1c"
    text_normalized  = CharField(max_length=256)   # "hemoglobin a1c"
    source           = CharField(max_length=32)    # "csv_extraction" / "alias_rule" / "curated"
```

### LabTestEntry

Test identity + display metadata. Rows are either preloaded from the
fixture or auto-created on first sight by the matcher.

```python
class LabTestEntry(models.Model):
    loinc_entry      = ForeignKey(LoincEntry, SET_NULL, null=True, blank=True)
    abbreviation     = CharField(max_length=64, unique=True)   # "hgb"
    name             = CharField(max_length=128)               # "Hemoglobin"
    name_normalized  = CharField(max_length=128, db_index=True)
    default_unit     = CharField(max_length=32)                # "g/dL"
    alternative_units = JSONField(default=list)
    sample_values    = JSONField(default=dict)
    value_type       = CharField(max_length=16)                # "numeric" / "qualitative"
    molecular_weight = FloatField(null=True)
    display_order    = PositiveSmallIntegerField(default=100)
```

**Key change**: `loinc_code` string field replaced by FK to
`LoincEntry`. Category comes from `LoincEntry.category` (no more
`LabCategory` model). Reference ranges removed from the model — they
come exclusively from user-supplied data (uploaded reports or manual
entry) stored on `LabValue`.

### LabValue

Single numeric or qualitative lab measurement.

```python
class LabValue(models.Model):
    user             = ForeignKey(AUTH_USER_MODEL, CASCADE)
    test_entry       = ForeignKey(LabTestEntry, PROTECT)
    loinc_entry      = ForeignKey(LoincEntry, SET_NULL, null=True)  # direct link for queries
    upload           = ForeignKey(UploadJob, SET_NULL, null=True)
    value            = FloatField(null=True)
    value_qualitative = CharField(max_length=32)
    unit             = CharField(max_length=32)
    source_text      = CharField(max_length=64)
    source_unit      = CharField(max_length=32)
    reference_min    = FloatField(null=True)     # from report or user, never hardcoded
    reference_max    = FloatField(null=True)     # from report or user, never hardcoded
    reference_source = CharField(max_length=8)   # "report" / "none" (no more "catalog")
    match_method     = CharField(max_length=16)
    source           = CharField(max_length=32)
    confidence       = FloatField(default=1.0)
    status           = CharField(max_length=16)
    measured_at      = DateField(null=True)
    created_at       = DateTimeField()
```

**Key change**: `reference_source` no longer supports `"catalog"`. Ref
ranges come only from the report (LLM-extracted) or from user manual
entry. No hardcoded defaults.

### UploadJob

```python
class UploadStatus(TextChoices):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"

class UploadJob(models.Model):
    user             = ForeignKey(AUTH_USER_MODEL, CASCADE)
    status           = CharField(choices=UploadStatus.choices)
    provider         = CharField(max_length=32)
    lab_date         = DateField(null=True)
    notes            = TextField()
    parsed_results   = JSONField(default=list)
    celery_task_id   = CharField(max_length=64)
    error_message    = TextField()
    created_at       = DateTimeField()
    completed_at     = DateTimeField(null=True)
```

### UploadFile

```python
class UploadFile(models.Model):
    upload           = ForeignKey(UploadJob, CASCADE, related_name="files")
    file             = FileField()
    original_filename = CharField(max_length=255)
    mime_type        = CharField(max_length=64)
    size_bytes       = PositiveIntegerField()
    file_order       = PositiveSmallIntegerField(default=0)
    sha256           = CharField(max_length=64, db_index=True)
    created_at       = DateTimeField()
```

---

## The Alias Index

Built once per Celery worker lifetime, cached in module-level
`_INDEX_CACHE`. Streams all `LoincAlias` rows from the database
using `iterator(chunk_size=50_000)` to avoid loading everything at once.

### Data source

`LoincAlias` rows come from three sources:

1. **Phase 1 — Deterministic extraction** (`curate_loinc_aliases` command):
   Extracts aliases from LOINC's own CSV fields (COMPONENT,
   LONG_COMMON_NAME, SHORTNAME, CONSUMER_NAME, DisplayName,
   RELATEDNAMES2). Normalizes them, drops ambiguous aliases (same
   normalized string maps to multiple LOINC codes). Produces ~192k
   aliases for ~60k qualifying LOINC rows (ACTIVE, CLASSTYPE=1).

2. **Phase 2 — Alias rules** (`alias_rules/` package): Hand-written
   Python functions (e.g., eGFR formula/race aliases) that emit
   domain-specific synonyms based on row attributes like METHOD_TYP.
   Auto-discovered by `discover_rules()`.

3. **Curated audit additions**: ~335 LLM-produced aliases for
   top-2000 LOINC codes by COMMON_TEST_RANK, covering standard lab
   abbreviations (TSH, BMP, CMP, etc.) and clinician shorthand.

All three are merged into a fixture JSON, shipped inside a versioned
zip, and loaded into the `LoincAlias` table via `loinc_reset`.

### Index structure

Two lookup dictionaries:

```python
{
    "by_wordset": {
        frozenset({"tsh"}): [LightLoincEntry(pk=42, code="3016-3", ...)],
        frozenset({"hemoglobin", "a1c"}): [LightLoincEntry(pk=99, code="4548-4", ...)],
        ...
    },
    "by_abbrev": {
        "tsh": [LightLoincEntry(pk=42, code="3016-3", ...)],
        ...
    }
}
```

- **by_wordset**: keyed by `frozenset` of words from the normalized
  alias. Allows order-independent matching ("Glucose Fasting" matches
  "Fasting Glucose").
- **by_abbrev**: keyed by lowercased `LabTestEntry.abbreviation`. Checked
  first as the highest-signal match.

### Memory optimization

`LightLoincEntry` uses `__slots__` to store only the 5 fields needed
for Tier-1 matching. Maps to a lightweight projection of `LoincEntry`:

| Slot | Source field |
|---|---|
| `pk` | `LoincEntry.pk` |
| `code` | `LoincEntry.code` |
| `unit_family` | `LoincEntry.unit_family` |
| `system` | `LoincEntry.system` |
| `component` | `LoincEntry.component` |

Repeated string values (unit_family, system) are `sys.intern`ed. The
full index is ~165 MB for 192k aliases across 60k codes.

---

## Tier 0 — Direct LOINC Verification

**Input**: `ParsedLabResult["loinc_code"]` from LLM extraction

**Logic**:
1. Normalize the code using `normalize_loinc()`
2. Look up `LoincEntry.objects.filter(code=loinc_code, status="ACTIVE")`
3. If found, check `units_compatible(incoming_unit_family, loinc_entry.unit_family)`
4. If compatible → **matched** (match_method=`MatchMethod.LOINC`, score=1.0)
5. If code not found or unit-incompatible → fall through to Tier 1

**Why**: The LLM sometimes confidently identifies the LOINC code from
the report. When it's right, this is the strongest possible signal — a
direct code lookup with no ambiguity. Unit-family check catches cases
where the LLM confuses codes with similar names but different analyte
types.

---

## Tier 1 — Bag-of-Words Exact Match

**Input**: `ParsedLabResult["test_name"]`, aliases, abbreviation, unit

### Step 1: Abbreviation lookup

Check `by_abbrev` for the abbreviation. Filter hits by unit-family
compatibility. Collect into `all_compatible` dict keyed by LOINC code.

### Step 2: Word-set matching with unique-alias short-circuit

For each name in `[test_name, *aliases]`:

1. **Normalize**: Unicode NFKC → lowercase → strip leading/trailing
   parenthetical qualifiers → collapse whitespace → strip boundary
   punctuation (keeping `+ - / .` inside tokens).
2. **Tokenize**: Strip boundary punctuation (commas, semicolons, parens,
   colons, slashes) → split into word set → `frozenset`.
3. **Lookup**: `by_wordset.get(word_set)` → list of `LightLoincEntry`.
4. **Unit gate**: Filter to codes whose `unit_family` is compatible with
   the incoming unit (see Unit-Family Gate below).
5. **Short-circuit**: If exactly 1 compatible code survives for this
   single name/alias → return immediately as **matched**. This prevents
   broad aliases from diluting a specific match. Example: "TSH" uniquely
   resolves, so even if a later alias like "Thyroid" would be ambiguous,
   we never check it.

### Step 3: Collision resolution

If no single name short-circuited but we accumulated compatible codes
across all names:

- **1 unique code** → **matched**
- **Multiple codes** → `_pick_best_collision()` selects the best one:
  1. Prefer codes with specimen system in `_PREFERRED_SYSTEMS`
     (Ser/Plas > Ser/Plas/Bld > Ser > Plas > Bld > RBC/WBC > Bld.dot)
  2. If incoming unit family is known, prefer exact family match
  3. Sort by system priority, then by PK (deterministic tiebreak)
  4. Return the first → **matched**

### Normalization examples

| Input | Normalized | Word set |
|---|---|---|
| `"Hemoglobin A1c (HbA1c)"` | `"hemoglobin a1c"` | `{"hemoglobin", "a1c"}` |
| `"25-OH Vitamin D"` | `"25-oh vitamin d"` | `{"25-oh", "vitamin", "d"}` |
| `"TSH"` | `"tsh"` | `{"tsh"}` |
| `"C-Reactive Protein"` | `"c-reactive protein"` | `{"c-reactive", "protein"}` |
| `"Glucose, Fasting"` | `"glucose fasting"` | `{"glucose", "fasting"}` |

---

## Unit-Family Gate

Runs at every tier. Classifies both the incoming result's unit and each
candidate `LoincEntry`'s `unit_family` into one of 13 canonical families.

Builds on `unit_converter.py` which already handles canonicalization via
`UNIT_ALIASES` (60+ lab unit notations) and dimensional analysis via
`pint`. The `classify_unit_family()` function extends this with explicit
family categorization:

| Family | Example units |
|---|---|
| `mass_per_volume` | mg/dL, ng/mL, pg/mL, g/L |
| `molar_per_volume` | mmol/L, nmol/L, pmol/L, mEq/L |
| `cells_per_volume` | /uL, K/uL, x10^9/L |
| `percent` | %, % of total |
| `ratio` | ratio |
| `enzymatic_activity` | U/L, IU/L |
| `hormone_activity` | mIU/L, IU/mL |
| `hematology_derived` | fL, pg |
| `pressure` | mmHg, kPa |
| `volume_rate` | mL/min/1.73m2 |
| `mass_per_time` | mg/24h, g/24h |
| `sed_rate` | mm/h |
| `unknown` | anything unrecognized |

**Compatibility rules**:
- Same family → compatible
- `unknown` on either side → compatible (permissive bias)
- `mass_per_volume` ↔ `molar_per_volume` → compatible (convertible
  with molecular weight via `unit_converter._molar_mass_convert()`)
- All other cross-family → **incompatible** (blocks the match)

---

## Stub Fallback

When both tiers fail, `get_or_create_stub()` in `tasks.py` creates
or reuses a `LabTestEntry` with `loinc_entry=NULL`.

Grouping key (in priority order):
1. LOINC code if present → one stub per code
2. `(name_normalized, unit_family)` → so "Eosinophils" in cells/uL and
   "Eosinophils" in % create separate stubs (clinically distinct tests)
3. Fresh stub otherwise

The `MatchMethod` enum tracks which tier produced the match:

| Value | Meaning |
|---|---|
| `MatchMethod.LOINC` | Tier 0 — direct LOINC verification |
| `MatchMethod.ALIAS_EXACT` | Tier 1 — bag-of-words alias match |
| `MatchMethod.NAME_FALLBACK` | Stub fallback — name-normalized grouping |
| `MatchMethod.MANUAL` | Patient manually matched/entered |
| `MatchMethod.UNMATCHED` | No match attempted |

---

## Reference Ranges

**v2 design change**: reference ranges are NOT stored on `LabTestEntry`
or `LoincEntry`. They come exclusively from:

1. **Report-extracted ranges**: The LLM reads the reference range printed
   on the lab report alongside each value. Stored on `LabValue.reference_min`
   / `LabValue.reference_max` with `reference_source="report"`.

2. **User-entered ranges**: The patient can enter or edit reference
   ranges manually via the review UI or the edit dialog.

3. **No range**: When neither source provides a range, `reference_source="none"`
   and the UI shows "No range".

This eliminates the `ReferenceSource.CATALOG` option and the
`LabTestEntry.reference_ranges` field. The benefit: no stale hardcoded
ranges that drift from what labs actually print, and each measurement
carries its own range from the specific lab that produced it.

The UI adapts by showing "No range" for values where the report didn't
include one and the patient hasn't entered one. The trend chart draws
reference lines only when the latest measurement has a range.

---

## System Priority for Collision Resolution

When multiple `LoincEntry` rows match (same alias maps to codes
differing only in specimen type), `_pick_best_collision` picks the most
clinically common specimen:

| Priority | System | Meaning |
|---|---|---|
| 0 | Ser/Plas | Serum or Plasma |
| 1 | Ser/Plas/Bld | Serum, Plasma, or Blood |
| 2 | Ser | Serum only |
| 3 | Plas | Plasma only |
| 4 | Bld | Blood |
| 5 | RBC, WBC | Red/White blood cells |
| 6 | Bld.dot | Blood spot |
| 99 | (other) | Urine, CSF, etc. |

This means "Glucose" (which exists for serum, urine, CSF, etc.) will
default to the serum/plasma code when the lab report doesn't specify.

---

## Data Flow Summary

```
loinc.org Loinc.csv
    │
    ▼
curate_loinc_aliases (management command)
    │ (Phase 1: CSV field extraction)
    │ (Phase 2: alias rules)
    │ (Curated audit additions)
    │
    ▼
Fixture JSON ──► versioned zip
    │
    ▼
loinc_reset (management command)
    │
    ├──► LoincEntry table (~60k rows)
    │    code, component, short_name, system,
    │    default_unit, unit_family, category, status
    │
    └──► LoincAlias table (~192k rows)
         text, text_normalized, source
    │
    ▼
build_index() ──► in-memory dict (~165 MB)
    │               by_wordset: 191k frozenset keys
    │               by_abbrev: abbreviation keys
    │
    ▼
match(ParsedLabResult) per extracted test
    │
    │  ParsedLabResult comes from parsers/llm_parser.py
    │  Fields: test_name, loinc_code, unit, value, confidence
    │
    ├── Tier 0: LoincEntry.objects.get(code=X)      ──► matched
    │
    ├── Tier 1: index["by_wordset"][word_set]        ──► matched
    │
    └── Stub fallback                                ──► LabTestEntry(loinc_entry=NULL)

Results stored as:
    LabValue.test_entry   → FK to LabTestEntry
    LabValue.loinc_entry  → FK to LoincEntry (direct, for queries)
    LabValue.match_method → MatchMethod enum value
    LabValue.confidence   → 0..1 score
    LabValue.reference_min/max → from report only (never hardcoded)
```

---

## Configuration

| Setting | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for LLM extraction (same key used by `llm_parser.py`) |

---

## Performance

- **Index build**: ~1.3s for 192k aliases (streamed in 50k chunks)
- **Index memory**: ~165 MB
- **Per-item matching**: sub-millisecond for Tier 0/1 (dict lookups)
- **Index lifetime**: cached for the worker process lifetime; invalidated after `LoincAlias` changes

---

## Key Files

| File | Role |
|---|---|
| `models.py` | `LoincEntry`, `LoincAlias`, `LabTestEntry`, `LabValue`, `UploadJob`, `UploadFile`, `MatchMethod` |
| `matcher.py` | Tier 0/1 matching engine, alias index builder |
| `matching.py` | `normalize_loinc()`, `normalize_name()` — shared normalization utilities |
| `unit_converter.py` | Unit classification, compatibility, and conversion |
| `unit_family.py` | `classify_unit_family()` — the 13-family gate |
| `tasks.py` | Celery task integration, stub fallback |
| `serializers.py` | DRF serializers for all models |
| `views.py` | API endpoints |
| `parsers/llm_parser.py` | LLM extraction, `ParsedLabResult` TypedDict |
| `management/commands/curate_loinc_aliases.py` | Phase 1+2 fixture generation from Loinc.csv |
| `alias_rules/` | Package for Phase 2 alias rule functions |
