# LOINC Data Pipeline — Implementation Plan

How `Loinc.csv` from loinc.org becomes searchable `LoincEntry` rows and
~192k `LoincAlias` entries that power the v2 matcher.

**Bundle**: `loinc-codes-aliases.zip` (ships `Loinc.csv` + `curated_loinc_aliases.json`)
**Models**: `LoincEntry`, `LoincAlias` (defined in `apps/labs/models.py`)

---

## Current State

| What | Status |
|---|---|
| `LoincEntry` model | Defined, table exists (empty) |
| `LoincAlias` model | Defined, table exists (empty) |
| `loinc-codes-aliases.zip` | Exists in project root (LOINC 2.82, 192k aliases) |
| `Loinc_2.82.zip` | Exists in project root (official LOINC download, 81 MB) |
| `loinc_common.json` | 111-code fixture powering Tier 0a only |
| Management commands | None |
| Tier 1 matching | Not implemented |

### What's in `loinc-codes-aliases.zip` today

```
loinc-codes-aliases.zip          12 MB
├── Loinc.csv                    82 MB uncompressed, ~100k rows
├── curated_loinc_aliases.json   37 MB, 192,275 aliases across 60k codes
├── curate_report.json           Stats (60,009 codes, 36,370 ambiguous dropped)
└── VERSION                      "2.82"
```

Alias breakdown by source:
- `LONG_COMMON_NAME`: 59,377
- `SHORTNAME`: 59,102
- `DisplayName`: 46,459
- `COMPONENT`: 15,823
- `RELATEDNAMES2`: 11,150
- `curated_audit`: 335
- `rule:egfr`: 29

---

## Pipeline Overview

```
loinc.org quarterly release → Loinc_x.yy.zip
    │
    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  curate_loinc_aliases --source Loinc.csv                            │
│    Phase 1: CSV field extraction → candidates                       │
│    Phase 2: Alias rules (egfr etc.) → more candidates               │
│    Phase 3: Ambiguity filter → drop multi-code aliases               │
│    Output: curated_loinc_aliases.json + curate_report.json           │
│                                                                      │
│  /curate-loinc-aliases (Claude skill, optional)                      │
│    Batch-audit top 2000 codes → additions_NNN.json                   │
│    prepare_alias_audit --merge → updated curated_loinc_aliases.json  │
│                                                                      │
│  pack_loinc_bundle                                                   │
│    Loinc.csv + curated_loinc_aliases.json → loinc-codes-aliases.zip  │
└──────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  loinc_reset --bundle loinc-codes-aliases.zip                        │
│                                                                      │
│  [wipe]  DELETE LoincAlias → NULL LabValue.loinc_entry               │
│          → DELETE LoincEntry                                         │
│                                                                      │
│  [1/3]  sync_loinc_csv      Loinc.csv → LoincEntry table            │
│  [2/3]  load_aliases        curated_loinc_aliases.json → LoincAlias  │
│  [3/3]  link_test_entries   Wire LabTestEntry.loinc_entry FKs        │
│                                                                      │
│  Result: ~60k LoincEntry rows, ~192k LoincAlias rows                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Normalization module

**File**: `apps/labs/normalize.py` (extract from `matching.py`)

The normalize function is shared between the curation pipeline (runs
offline / in management commands) and the runtime matcher. Extract into
its own module so management commands don't import Django models at
module level.

```python
def normalize(raw: str) -> str:
    """Produce the lookup key used by both fixture builder and Tier-1 index.

    Pipeline:
      1. Unicode NFKC
      2. Lowercase
      3. Strip trailing parenthesized content: "Hemoglobin A1c (HbA1c)" → "Hemoglobin A1c"
      4. Strip leading parenthesized content: "(Serum) Albumin" → "Albumin"
      5. Collapse whitespace
      6. Strip boundary punctuation (keep + - / . inside tokens)
      7. Clamp to 100 chars
    """

def normalize_loinc(raw: str | None) -> str:
    """Canonical NNNNN-N format or empty string."""
```

Keep `normalize_name()` in `matching.py` as a thin wrapper that calls
`normalize()` — or deprecate in favor of `normalize()` if the semantics
are identical.

**Migration note**: `LoincAlias.text_normalized` uses this function.
The existing `curated_loinc_aliases.json` was generated with a prior
version of normalize. The `load_aliases` step must re-normalize all
entries through the current function to guarantee consistency.

---

### Step 2: Alias rules package

**Directory**: `apps/labs/alias_rules/`

```
alias_rules/
├── __init__.py      # discover_rules() — scan *.py, import, collect ALIAS_RULES
├── egfr.py          # eGFR race/formula aliases (source: rule:egfr)
└── ... (future)     # Additional rules as needed
```

**Rule interface**:
```python
# Each module exports ALIAS_RULES: list of callables
# Each callable: (row: dict) -> list[tuple[str, str]]  # (alias_text, source_tag)

def egfr_race_aliases(row: dict) -> list[tuple[str, str]]:
    """Detect eGFR codes via COMPONENT, generate race-qualified aliases."""
    ...

ALIAS_RULES = [egfr_race_aliases, egfr_formula_aliases]
```

**Discovery** (`__init__.py`):
```python
def discover_rules() -> list[Callable]:
    """Import all alias_rules/*.py, collect ALIAS_RULES lists."""
```

---

### Step 3: `curate_loinc_aliases` management command

**File**: `apps/labs/management/commands/curate_loinc_aliases.py`

Extracts aliases from Loinc.csv and alias rules, resolves ambiguity,
writes the fixture file.

**Arguments**:
- `--source PATH` — path to Loinc.csv (required for extraction)
- `--output PATH` — where to write `curated_loinc_aliases.json`
  (default: `./curated_loinc_aliases.json`)
- `--report PATH` — where to write `curate_report.json`
  (default: next to `--output`)
- `--status STATUS [STATUS ...]` — LOINC statuses to include
  (default: `ACTIVE TRIAL`)

**Phases**:

#### Phase 1: CSV field extraction

For each qualifying row (`STATUS` in allowed set, `CLASSTYPE == "1"`):

```
Fields scanned:
  COMPONENT, LONG_COMMON_NAME, SHORTNAME, CONSUMER_NAME,
  DisplayName, RELATEDNAMES2

RELATEDNAMES2: split on ";" → extract each part separately.
All others: single entry per field.
```

Each extracted string is normalized via `normalize()`, then added as a
candidate `(normalized_alias, loinc_num, raw_alias, source_field)`.

Skip if the same normalized form was already seen for this code.

#### Phase 2: Alias rules

Run `discover_rules()` → apply each rule to each CSV row → add
candidates with the rule's source tag.

#### Phase 3: Ambiguity filter

```python
by_alias: dict[str, set[str]] = defaultdict(set)
for norm, loinc_num, _raw, _field in candidates:
    by_alias[norm].add(loinc_num)

ambiguous = {norm for norm, codes in by_alias.items() if len(codes) > 1}
kept = [c for c in candidates if c[0] not in ambiguous]
```

Any normalized alias that maps to more than one LOINC code is dropped.
This is the core safety mechanism.

#### Output

JSON array sorted by `(loinc_num, alias_normalized)`:
```json
[
  {
    "loinc_num": "2345-7",
    "alias": "Glucose [Mass/Vol]",
    "alias_normalized": "glucose [mass/vol",
    "source_field": "LONG_COMMON_NAME"
  }
]
```

Plus `curate_report.json`:
```json
{
  "total_qualifying_codes": 60009,
  "total_aliases_kept": 191940,
  "codes_with_aliases": 60006,
  "coverage_pct": 100.0,
  "ambiguous_aliases_dropped": 36370,
  "ambiguous_examples": { ... }
}
```

---

### Step 4: `prepare_alias_audit` management command

**File**: `apps/labs/management/commands/prepare_alias_audit.py`

Supports the `/curate-aliases` skill workflow.

**Subcommands**:

#### `--prepare`

```bash
python manage.py prepare_alias_audit --prepare \
  --source Loinc.csv \
  --fixture curated_loinc_aliases.json
```

1. Read Loinc.csv, rank codes by clinical importance (COMMON_TEST_RANK
   or ordered by alias count as proxy)
2. Take top 2000 codes
3. Split into 20 batches of 100
4. Write `build/alias_audit/batch_NNN.json`:
   ```json
   [
     {
       "loinc_num": "2345-7",
       "component": "Glucose",
       "short_name": "Glucose SerPl-mCnc",
       "long_common_name": "Glucose [Mass/volume] in Serum or Plasma",
       "system": "Ser/Plas",
       "existing_aliases": ["glucose", "glucose serpl-mcnc", ...],
       "existing_alias_count": 5
     }
   ]
   ```
5. Write `build/alias_audit/summary.json`:
   ```json
   {"batch_count": 20, "codes_per_batch": 100, "total_codes": 2000}
   ```

#### `--merge`

```bash
python manage.py prepare_alias_audit --merge \
  --fixture curated_loinc_aliases.json
```

1. Read all `build/alias_audit/additions_NNN.json` files
2. Re-normalize each alias through `normalize()`
3. Drop additions whose normalized form already exists for a different
   code in the fixture (preserves existing aliases)
4. Drop additions that are ambiguous among themselves
5. Append surviving additions to the fixture
6. Re-sort by `(loinc_num, alias_normalized)`
7. Write updated `curated_loinc_aliases.json`

---

### Step 5: `sync_loinc_csv` management command

**File**: `apps/labs/management/commands/sync_loinc_csv.py`

Parses `Loinc.csv` and upserts rows into the `LoincEntry` table.

**Arguments**:
- `--csv PATH` — path to Loinc.csv
- `--status STATUS [STATUS ...]` — (default: `ACTIVE TRIAL`)
- `--batch-size N` — rows per bulk_create (default: 1000)

**CSV → LoincEntry column mapping**:

| CSV column | LoincEntry field |
|---|---|
| `LOINC_NUM` | `code` |
| `COMPONENT` | `component` |
| `SHORTNAME` | `short_name` |
| `LONG_COMMON_NAME` | `long_name` |
| `SYSTEM` | `system` |
| `EXAMPLE_UCUM_UNITS` | `default_unit` (first semicolon-delimited entry) |
| `STATUS` | `status` |
| `PROPERTY` | → infer `unit_family` (see mapping below) |
| `CLASS` | `category` (truncated to 64 chars) |

**PROPERTY → unit_family mapping**:

| PROPERTY | unit_family |
|---|---|
| MCnc | mass_per_volume |
| SCnc | molar_per_volume |
| CCnc | enzymatic_activity |
| NCnc | cells_per_volume |
| NFr, MFr, AFr, VFr, CFr, SFr (+ .DF) | percent |
| VRat, ArVRat | volume_rate |
| MRat | mass_per_time |
| SRto, MRto, NRto, CRto, VRto, TRto, LnRto, RelRto, Ratio | ratio |

**value_type inference**:
- `SCALE_TYP` == "Qn" → `numeric`
- `SCALE_TYP` == "Ord" or "Nom" → `qualitative`
- else → `numeric`

**Upsert strategy**:
- Batched `bulk_create(..., update_conflicts=True, unique_fields=["code"], update_fields=[...])`
- Each batch in its own transaction
- After all batches: delete LoincEntry rows not in the incoming set
  (handles retired codes between LOINC releases)

**Row filtering**:
- Skip empty `LOINC_NUM`
- `STATUS` must be in allowed set
- `CLASSTYPE` must be `"1"` (lab/clinical, not survey/claim)

---

### Step 6: `loinc_reset` management command

**File**: `apps/labs/management/commands/loinc_reset.py`

Orchestrator that wipes and reloads all LOINC data.

**Arguments**:
- `--bundle PATH` — path to `loinc-codes-aliases.zip`
  (extracts `Loinc.csv` + `curated_loinc_aliases.json` to temp dir)
- `--csv PATH` — direct path to Loinc.csv (alternative to `--bundle`)
- `--aliases PATH` — direct path to curated_loinc_aliases.json
- `--yes` — skip confirmation prompt

**Pipeline**:

```
[wipe]
  1. DELETE all LoincAlias rows
  2. SET NULL on LabValue.loinc_entry and LabTestEntry.loinc_entry
  3. DELETE all LoincEntry rows

[1/3] sync_loinc_csv
  Loinc.csv → LoincEntry table (~60k rows)

[2/3] load_aliases
  curated_loinc_aliases.json → LoincAlias table (~192k rows)
  - Skip aliases whose loinc_num doesn't match any LoincEntry.code
  - Re-normalize text_normalized through current normalize()
  - Bulk create with batch_size=2000, ignore_conflicts=True

[3/3] link_test_entries
  For each LabTestEntry with a non-empty abbreviation:
    - Try to match against LoincEntry via the loinc_common.json
      fixture (code lookup) or by name_normalized matching
    - Set LabTestEntry.loinc_entry FK if a unique match is found
  For each LabValue with test_entry.loinc_entry set:
    - Copy loinc_entry FK to LabValue.loinc_entry for direct queries
```

**Timing estimate** (local dev, SQLite):
- Wipe: <1s
- sync_loinc_csv: ~30s (60k rows, batched)
- load_aliases: ~20s (192k rows, batched)
- link_test_entries: <5s
- **Total: ~1 minute**

---

### Step 7: `pack_loinc_bundle` management command

**File**: `apps/labs/management/commands/pack_loinc_bundle.py`

Creates or updates `loinc-codes-aliases.zip`.

**Arguments**:
- `--csv PATH` — path to Loinc.csv
- `--aliases PATH` — path to curated_loinc_aliases.json
- `--report PATH` — path to curate_report.json (optional)
- `--version STR` — LOINC version string (default: auto-detect from CSV)
- `--output PATH` — output zip path
  (default: `../loinc-codes-aliases.zip` relative to manage.py)

**Bundle contents**:
```
loinc-codes-aliases.zip
├── Loinc.csv                      # Raw CSV (needed by sync_loinc_csv)
├── curated_loinc_aliases.json     # Pre-built alias fixture
├── curate_report.json             # Curation statistics (optional)
└── VERSION                        # LOINC version string
```

---

### Step 8: Update `matching.py` for Tier 1

Once LoincEntry + LoincAlias tables are populated, update
`resolve_test_identity()` to use them:

```
Current flow (Tier 0a only):
  normalize_loinc → lookup in loinc_common.json fixture → LabTestEntry

New flow:
  Tier 0: normalize_loinc → LoincEntry.objects.get(code=...) → LabTestEntry
  Tier 1: normalize(raw_name) → LoincAlias.objects.filter(text_normalized=...) 
           → if exactly 1 LoincEntry → LabTestEntry (match_method=ALIAS_EXACT)
  Stub:   name-normalized grouping (unchanged)
```

**Tier 0 change**: Replace `LOINC_COMMON` fixture dict with a DB query:
```python
loinc = LoincEntry.objects.filter(code=code).first()
if loinc:
    test_entry = LabTestEntry.objects.get_or_create(loinc_entry=loinc, ...)
    return test_entry, MatchMethod.LOINC
```

**Tier 1 (new)**: Bag-of-words alias lookup:
```python
normalized = normalize(raw_name)
aliases = LoincAlias.objects.filter(text_normalized=normalized).select_related("loinc_entry")
loinc_ids = {a.loinc_entry_id for a in aliases}
if len(loinc_ids) == 1:
    loinc = aliases[0].loinc_entry
    test_entry = LabTestEntry.objects.get_or_create(loinc_entry=loinc, ...)
    return test_entry, MatchMethod.ALIAS_EXACT
```

**Backward compatibility**: Keep `loinc_common.json` as a fallback for
environments where the DB hasn't been populated yet. Check
`LoincEntry.objects.exists()` at import time to decide which path to use.

---

### Step 9: Update `lab_catalog.json` fixture

The existing fixture references old model names (`LabTestType`,
`LabCategory`) and the `loinc_code` string field. Two options:

**Option A** (recommended): Delete the fixture entirely. Preloaded
test entries are auto-created by `resolve_test_identity()` on first
encounter. The `link_test_entries` step in `loinc_reset` wires them to
LoincEntry rows.

**Option B**: Rewrite the fixture to use `LabTestEntry` with `loinc_entry`
FK. Requires LoincEntry rows to exist first (fixture ordering).

---

### Step 10: `/curate-loinc-aliases` skill integration

The skill (defined in the conversation) batch-audits alias coverage for
top 2000 LOINC codes. It depends on:

1. `prepare_alias_audit --prepare` (Step 4) — generates batch files
2. LLM-driven audit of each batch — writes `additions_NNN.json`
3. `prepare_alias_audit --merge` — merges additions into fixture
4. `pack_loinc_bundle` — updates the zip

The skill is invoked by the user (`/curate-loinc-aliases`) and processes
20 batches of 100 codes each. After every 1M tokens it pauses for
user confirmation. Checks if loinc-codes-aliases.zip and update or create it.

---

## Implementation Order

```
Phase A — Foundation (no model changes)
  ├── A1. normalize.py — extract normalize() and normalize_loinc()
  ├── A2. alias_rules/ — rule package with egfr rules
  └── A3. curate_loinc_aliases — CSV extraction + ambiguity filter + fixture output

Phase B — Bundle creation
  ├── B1. prepare_alias_audit — --prepare and --merge subcommands
  ├── B2. pack_loinc_bundle — zip creator
  └── B3. Run /curate-aliases skill if coverage gaps found

Phase C — Database loading
  ├── C1. sync_loinc_csv — Loinc.csv → LoincEntry
  ├── C2. loinc_reset — orchestrator (wipe + sync + load + link)
  └── C3. Tests for all management commands

Phase D — Matcher upgrade
  ├── D1. Update resolve_test_identity() for Tier 0 (DB) + Tier 1 (alias)
  ├── D2. Retire loinc_common.json (or keep as fallback)
  ├── D3. Delete or rewrite lab_catalog.json fixture
  └── D4. Update matching tests
```

---

## Quarterly Update Workflow

When LOINC releases a new version (e.g. 2.83):

```bash
# 1. Download new Loinc_2.83.zip from loinc.org
# 2. Extract Loinc.csv
unzip -o Loinc_2.83.zip "Loinc_2.83/LoincTable/Loinc.csv" -d /tmp/loinc_work
mv /tmp/loinc_work/Loinc_2.83/LoincTable/Loinc.csv /tmp/loinc_work/Loinc.csv

# 3. Re-generate aliases from the new CSV
python manage.py curate_loinc_aliases \
  --source /tmp/loinc_work/Loinc.csv \
  --output /tmp/loinc_work/curated_loinc_aliases.json

# 4. (Optional) Run /curate-aliases to audit coverage of new codes

# 5. Pack the bundle
python manage.py pack_loinc_bundle \
  --csv /tmp/loinc_work/Loinc.csv \
  --aliases /tmp/loinc_work/curated_loinc_aliases.json \
  --version 2.83

# 6. Load into database
python manage.py loinc_reset --bundle ../loinc-codes-aliases.zip --yes

# 7. Verify
python manage.py shell -c "
from apps.labs.models import LoincEntry, LoincAlias
print(f'LoincEntry: {LoincEntry.objects.count()}')
print(f'LoincAlias: {LoincAlias.objects.count()}')
"
```

---

## File Inventory (to be created)

| File | Phase | Purpose |
|---|---|---|
| `apps/labs/normalize.py` | A1 | `normalize()`, `normalize_loinc()` |
| `apps/labs/alias_rules/__init__.py` | A2 | Rule discovery |
| `apps/labs/alias_rules/egfr.py` | A2 | eGFR alias rules |
| `apps/labs/management/__init__.py` | A3 | Package init |
| `apps/labs/management/commands/__init__.py` | A3 | Package init |
| `apps/labs/management/commands/curate_loinc_aliases.py` | A3 | Fixture generator |
| `apps/labs/management/commands/prepare_alias_audit.py` | B1 | Audit batch prep/merge |
| `apps/labs/management/commands/pack_loinc_bundle.py` | B2 | Zip creator |
| `apps/labs/management/commands/sync_loinc_csv.py` | C1 | CSV → LoincEntry loader |
| `apps/labs/management/commands/loinc_reset.py` | C2 | Full pipeline orchestrator |

---

## Key Design Decisions

1. **Single normalize function** shared between curation and runtime.
   The fixture stores `alias_normalized` but `loinc_reset` re-normalizes
   on load — this means updating the normalize function automatically
   fixes all aliases on next load without regenerating the fixture.

2. **Ambiguity = drop, not disambiguate**. If "albumin" maps to both
   serum-albumin and urine-albumin LOINC codes, neither gets it. Safe
   default; the `/curate-aliases` skill can add qualified aliases
   ("serum albumin", "urine albumin") that are unambiguous.

3. **Bundle is the deployment artifact**, not the raw CSV. Production
   never runs the extraction pipeline — it loads the pre-built fixture
   via `loinc_reset --bundle`. The pipeline runs on dev machines and CI
   when updating to a new LOINC version.

4. **LoincEntry.category from CLASS column** (e.g. "CHEM", "HEM/BC",
   "COAG"). Mapped to human-readable names in the frontend, not stored
   as a separate model.

5. **loinc_common.json kept as fallback**. Environments without the full
   LOINC DB (e.g. unit tests, fresh dev setups) still get Tier 0a matching
   for the 111 most common codes. Once LoincEntry is populated, the DB
   path takes priority.
