---
name: curate-loinc-aliases
description: |
  Audit and fill alias coverage gaps for top LOINC codes by COMMON_TEST_RANK.
  Batch-audits alias coverage for top 2000 LOINC codes and adds missing
  common lab report names. 20 batches of 100 codes, progress after each.
triggers:
  - curate-loinc-aliases
  - curate aliases
  - audit alias coverage
  - fill alias gaps
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Agent
  - AskUserQuestion
---

# Curate LOINC Aliases — Coverage Audit

Batch-audit alias coverage for top 2000 LOINC codes and add missing
common lab report names. 20 batches of 100 codes, progress after each.

## Step 0: Resolve LOINC version and extract files

Find the latest LOINC version available in the project root:

```bash
ls ../Loinc_*.zip ../loinc-codes-aliases*.zip 2>/dev/null
```

Pick the highest `x.yy` version from `Loinc_x.yy.zip` files.

### Path A — `loinc-codes-aliases.zip` exists

The bundle already has `Loinc.csv`, `LoincClass.csv`, and `curated_loinc_aliases.json` inside.
Extract what we need:

```bash
unzip -o ../loinc-codes-aliases.zip Loinc.csv LoincClass.csv curated_loinc_aliases.json VERSION -d /tmp/eq_loinc_work
```

Use `--source /tmp/eq_loinc_work/Loinc.csv` and
`--fixture /tmp/eq_loinc_work/curated_loinc_aliases.json` for later steps.

### Path B — only `Loinc_x.yy.zip` exists (no `loinc-codes-aliases.zip`)

Extract `Loinc.csv` and `LoincClass.csv` from the official archive:

```bash
unzip -o ../Loinc_x.yy.zip "Loinc_x.yy/LoincTable/Loinc.csv" "Loinc_x.yy/AccessoryFiles/ClassificationRules/LoincClass.csv" -d /tmp/eq_loinc_work
mv /tmp/eq_loinc_work/Loinc_x.yy/LoincTable/Loinc.csv /tmp/eq_loinc_work/Loinc.csv
mv /tmp/eq_loinc_work/Loinc_x.yy/AccessoryFiles/ClassificationRules/LoincClass.csv /tmp/eq_loinc_work/LoincClass.csv
echo "x.yy" > /tmp/eq_loinc_work/VERSION
```

Build the initial curated fixture from scratch:

```bash
python manage.py curate_loinc_aliases --source /tmp/eq_loinc_work/Loinc.csv \
  --output /tmp/eq_loinc_work/curated_loinc_aliases.json
```

## Step 1: Prepare

```bash
cd backend && python manage.py prepare_alias_audit --prepare \
  --source /tmp/eq_loinc_work/Loinc.csv \
  --fixture /tmp/eq_loinc_work/curated_loinc_aliases.json
```

Creates `build/alias_audit/batch_*.json`.

## Step 2: Process batches

Read `build/alias_audit/summary.json` for batch count.

For **each** batch file `batch_NNN.json`:

1. Read the batch (100 codes with fields + existing aliases).
2. For each code, decide if important aliases are missing.
3. Write additions to `build/alias_audit/additions_NNN.json`:
   ```json
   [{"loinc_num": "2345-7", "alias": "Blood Sugar", "source_field": "curated_audit"}]
   ```
   (`alias_normalized` is computed by the merge step — omit it or include it,
   either way the merge re-normalizes.)
4. Print: **Batch X/N — added Y aliases**
5. If a batch has no gaps, write an empty `[]` and move on fast.

### What to add

- Standard abbreviations actually used on lab reports: TSH, HbA1c, CRP,
  BUN, AST, ALT, LDH, GGT, ALP, PSA, AFP, BNP, ESR, PT, INR, aPTT, etc.
- Common report names: "Total Cholesterol", "Free T4", "Uric Acid",
  "Blood Urea Nitrogen", "Sed Rate".
- Quest / LabCorp / hospital-system names you've seen in real PDFs.
- Clinician shorthand that uniquely identifies the test.
- Bare short forms commonly used on reports: "Glucose", "Bilirubin",
  "Protein", "Ketones", "Nitrite", "Color", "Appearance" — but ONLY
  when these unambiguously map to one LOINC code (e.g. urinalysis context).
  If a bare name is ambiguous across specimens (serum glucose vs urine
  glucose), skip it.

### What to skip

- Aliases already in `existing_aliases` for that code.
- Generic terms that match many codes: "blood test", "chemistry", "panel",
  "serum", "level".
- Patient-facing informal names: "the thyroid test".
- When unsure if an alias is ambiguous across codes — skip it.
  The merge step filters ambiguous additions anyway, but skipping
  reduces noise in the additions files.

### Pacing

- Don't analyze every field of every code in detail — scan for obvious gaps.
  Most codes with 5+ existing aliases are probably fine.
- Codes with 0-2 existing aliases deserve more attention.
- Spend ~10-20 seconds of thought per batch, not minutes.

### Budget control

Track cumulative token usage across batches. After each batch, report:

> Batch X/N — added Y aliases — ~Z tokens this batch, ~T total

After every **1M cumulative tokens**, **stop and ask the user** whether to
continue. Do not proceed to the next batch until the user confirms.
Use `ccusage .` or check the conversation stats to get actual token counts.
If exact counts are unavailable, estimate from context size x batches processed.

## Step 3: Merge

```bash
cd backend && python manage.py prepare_alias_audit --merge \
  --fixture /tmp/eq_loinc_work/curated_loinc_aliases.json
```

The merge step:
- Re-normalizes all `alias` values through `normalize()`.
- Drops additions whose normalized form conflicts with an existing alias
  on a different code (preserves existing aliases).
- Drops additions that are ambiguous among themselves.
- Writes the updated `curated_loinc_aliases.json` fixture.

## Step 4: Verify

Copy the merged fixture into the app so tests can find it, then run:

```bash
cp /tmp/eq_loinc_work/curated_loinc_aliases.json backend/apps/fixtures/curated_loinc_aliases.json
cd backend && python -m pytest apps/health/tests/test_curate_loinc_aliases.py -v --tb=short
```

## Step 5: Pack into zip

After tests pass, update (or create) the zip bundle.
Use the project root path detected in Step 0 (e.g. `../loinc-codes-aliases.zip`).

### Path A — `loinc-codes-aliases.zip` existed

Update the fixture inside it:

```bash
cd /tmp/eq_loinc_work && zip <project_root>/loinc-codes-aliases.zip curated_loinc_aliases.json VERSION
```

### Path B — creating `loinc-codes-aliases.zip` from scratch

```bash
cd /tmp/eq_loinc_work && zip <project_root>/loinc-codes-aliases.zip \
  Loinc.csv LoincClass.csv curated_loinc_aliases.json VERSION
```

(Add `curate_report.json` and `VERSION` if they were generated.)

## Cleanup

```bash
rm -rf /tmp/eq_loinc_work
```
