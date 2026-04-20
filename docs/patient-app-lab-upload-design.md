# Patient App — Lab Results Upload Design

**Branch:** patient-app
**Status:** Design, pre-implementation
**Date:** April 2026
**References:** `docs/patient-app-requirements.md` §2.5.1 + §2.6 + §3.2, `docs/patient-app-architecture.md` §2, `docs/patient-app-design.md` §4 + §5

> This document is the implementation plan for **uploading lab reports (PDF / JPEG / PNG), extracting structured lab values, matching them against a canonical test catalog, and storing normalised results**. It deliberately scopes down the first build to what HealthKey actually needs. No FHIR sync here (that's Phase 2 §3.1). No discharge-summary parsing (different semantics, different prompt).

---

## Contents

1. [Goals & Non-Goals](#1-goals--non-goals)
2. [User Journey](#2-user-journey)
3. [Canonical Lab Test Catalog](#3-canonical-lab-test-catalog)
4. [Data Model](#4-data-model)
5. [API Contract](#5-api-contract)
6. [Extraction Pipeline](#6-extraction-pipeline)
7. [Tiered Matching](#7-tiered-matching)
8. [Unit Normalisation](#8-unit-normalisation)
9. [Storage & Security](#9-storage--security)
10. [Frontend — Screens & Components](#10-frontend--screens--components)
11. [Interaction State Coverage](#11-interaction-state-coverage)
12. [Error Handling & Edge Cases](#12-error-handling--edge-cases)
13. [Implementation Phases](#13-implementation-phases)
14. [Open Questions](#14-open-questions)
15. [Rollout & Observability](#15-rollout--observability)

---

## 1. Goals & Non-Goals

### Goals

- **Upload 1+ lab report files** (PDF, JPEG, PNG, HEIC) from any screen in the Records tab or onboarding Labs step
- **Extract structured lab values** (test name, value, unit, reference range, date, LOINC code) with an LLM vision model
- **Identify tests by LOINC code.** Two results with the same LOINC are the same test — that is the trendability contract. The LLM returns a LOINC per row; we validate against `loinc_common.json` (§3.4). No curated alias catalog, no fuzzy name matching — LOINC is the identity.
- **Normalise units** so every saved value is in the same unit as every other measurement of that test
- **Show provenance + confidence** on every lab value so the patient can trust (or correct) it
- **Feed existing components**: extracted values populate `LabValueCard`, `LabTrendChart`, and the Records tab automatically
- **Work end-to-end without FHIR**: a patient who cannot connect their EHR can still build a longitudinal lab record by snapping photos of paper reports

### Non-goals (explicitly deferred)

- **No curated alias / abbreviation table.** The previous design's `LabTestType.aliases` and `abbreviation` fields are removed. Matching is LOINC-first; if the LLM can't find a LOINC, we fall back to normalized-name grouping (§7). We are not maintaining a synonym dictionary.
- **No fuzzy / token-set matching.** Deleted along with aliases. A result either has a validated LOINC (matches an existing `LabTestType` or auto-creates one) or falls back to normalized-name grouping. No RapidFuzz, no disambiguation rules, no `match_method="fuzzy"`.
- **No pathology report parsing.** Different document type, belongs in a separate pipeline
- **No image annotation / bounding-box highlighting.** Nice-to-have; adds engineering cost without clear Phase 2 value
- **No automatic conflict resolution with FHIR data.** Lab conflicts surface in the existing `records.ConflictRecord` UI when FHIR sync lands in Phase 2
- **No real-time OCR preview while uploading.** Extraction is fully async
- **No non-English lab reports.** Prompt targets English lab reports only; Spanish/other languages deferred to Phase 3
- **No structured HL7/v2 or CCDA parsing.** PDF/image only

---

## 2. User Journey

### 2.1 Happy path — patient uploads a single lab PDF

```
Sarah gets a paper lab report from her oncologist.

1. Opens HealthKey → Records tab
2. Taps "Add lab results" (appears in the Labs section)
3. Picks "Upload a document" mode
4. Selects the PDF from her phone (file picker)
5. Sees progress: "Uploading…" → "Reading your report…" → "Found 7 lab values"
6. Review screen: list of 7 extracted values, each with:
   - Test name (matched to catalog, e.g. "Hemoglobin")
   - Value + unit ("12.5 g/dL")
   - Reference range ("12.0–15.5")
   - Confidence chip ("High", "Medium", "Low")
   - Pencil icon to edit
   - Toggle to exclude from save
7. Any unmatched values shown in an amber "Help us match these" section
   - For each, Sarah picks from a dropdown of catalog tests
8. Taps "Save 7 results"
9. Lands back on Records → Labs section with new values visible
```

Total taps, happy path: **4** (Add → Upload → Select file → Save).

### 2.2 Edge journey — photo of a crumpled paper report

```
1. Records → Add lab results → Use camera
2. Snap photo (iOS/Android native camera capture intent)
3. Same flow as above; extraction may return lower confidence
4. Low-confidence values are marked, user confirms or edits
5. Unmatched values surface for manual tagging
```

### 2.3 Edge journey — multi-page PDF

```
1. Patient uploads a 12-page CBC + CMP + hormone panel PDF
2. Backend rasterises page-by-page to bounded-memory JPEG
3. Single LLM call passes all page images in one vision request
4. Extraction returns deduplicated results across pages
5. Review screen groups by category (CBC / CMP / other)
```

### 2.4 Emotional arc

| Step | Feeling | Design supports it |
|---|---|---|
| Tap "Add lab results" | Curious, slight friction | Calm modal, no spinner immediately |
| Upload in progress | Patience strained | "Reading your report…" beats "Processing…"; progress bar (not indeterminate spinner) |
| First glance at review | Surprise + scrutiny | Matched values look confident; low-confidence flagged obviously |
| Save | Small sense of accomplishment | "7 results saved" toast, timeline updated |

No celebration animations. Patient is building a medical record, not winning a game.

---

## 3. Lab Test Identity — LOINC + Fixture

### 3.1 Philosophy

**LOINC is the test identity.** Two `LabResult` rows with the same validated `loinc_code` are the same test — trendable, comparable, chartable. No curated catalog gates what HealthKey can track.

`LabTestType` exists as a thin, **auto-populated** display-metadata table: one row per unique LOINC (or per unique normalized name for the no-LOINC fallback). On first sight of a LOINC, we `get_or_create` a `LabTestType` hydrated from `loinc_common.json` (§3.4). No migration is required to support a new common test — it appears organically the first time a patient uploads a report mentioning it.

This is a deliberate reversal of the earlier "single source of truth" catalog framing. The old model paid for curation (aliases, abbreviations, fuzzy matching, disambiguation rules, migrations to add a test) without a proportional payoff: LLMs now reliably return LOINC codes, and LOINC is already the industry-standard identity. Maintaining a second identity layer on top of that is redundant.

The patient population is still oncology-focused (per PRD), but that now influences only which entries in `loinc_common.json` we **preload** as `LabTestType` rows for a friendlier fresh-install UX (§3.2). Anything else in the fixture is one patient upload away from existing in the DB.

### 3.2 Preloaded tests (fresh-install seed)

Two fixtures cooperate:

- `fixtures/lab_catalog.json` — ~37 `LabTestType` rows loaded via Django `loaddata` on first deploy. Rich curation: category, display_order, reference_ranges, alternative_units, sample_values, molecular_weight. These are the oncology-relevant tests the patient sees in autocomplete and in the Records tab out of the box.
- `data/loinc_common.json` — ~110 LOINC codes (§3.4) used by `matching.py` to validate LLM claims. A superset of `lab_catalog.json` codes; entries NOT in `lab_catalog.json` remain validation-only until a patient upload triggers auto-creation.

Preload coverage prioritises:
- Complete Blood Count + differentials (chemo neutropenia monitoring)
- Renal function (for platinum-based therapy eligibility)
- Liver function (hepatotoxicity monitoring)
- Disease-specific markers for Multiple Myeloma, Breast Cancer, FL, CLL (the four V1 disease profiles)
- Cardiac baselines (for anthracycline and HER2-targeted therapy)
- Infection screen (clinical trial eligibility)

Values outside the preload list aren't rejected or marked special — they auto-create a `LabTestType` on first sight (LOINC path) or land in a normalized-name fallback row (no-LOINC path). Neither case requires engineering work.

The tables below are illustrative of what the preload fixture entries contain. They are **not** a closed list of supported tests; they are the subset we hand-curate ranges + display metadata for. Aliases and abbreviation columns are retained below only as historical reference — they are **no longer stored** on `LabTestType` (§1 Non-goals).

#### CBC & haematology (§2.6.1)

| Abbrev | Name | LOINC | Default unit | Aliases |
|---|---|---|---|---|
| `wbc` | White blood cell count | 6690-2 | `10^3/uL` | WBC, leukocytes, leucocytes, white blood cells |
| `hgb` | Hemoglobin | 718-7 | `g/dL` | HGB, Hb, haemoglobin |
| `plt` | Platelet count | 777-3 | `10^3/uL` | PLT, platelets, thrombocytes |
| `anc` | Absolute neutrophil count | 751-8 | `10^3/uL` | ANC, neutrophils (abs), segs |
| `alc` | Absolute lymphocyte count | 731-0 | `10^3/uL` | ALC, lymphocytes (abs) |
| `hct` | Hematocrit | 4544-3 | `%` | HCT, Hct, packed cell volume |
| `mcv` | Mean corpuscular volume | 787-2 | `fL` | MCV |

#### Renal function (§2.6.2)

| Abbrev | Name | LOINC | Default unit | Aliases |
|---|---|---|---|---|
| `creatinine` | Serum creatinine | 2160-0 | `mg/dL` | Cr, creat, SCr |
| `egfr` | Estimated GFR (CKD-EPI) | 62238-1 | `mL/min/1.73m2` | eGFR, estimated GFR |
| `crcl` | Creatinine clearance | 2164-2 | `mL/min` | CrCl, CCr |
| `calcium` | Serum calcium | 17861-6 | `mg/dL` | Ca, calcium total |
| `bun` | Blood urea nitrogen | 3094-0 | `mg/dL` | BUN, urea |

#### Liver function (§2.6.3)

| Abbrev | Name | LOINC | Default unit | Aliases |
|---|---|---|---|---|
| `ast` | Aspartate aminotransferase | 1920-8 | `U/L` | AST, SGOT |
| `alt` | Alanine aminotransferase | 1742-6 | `U/L` | ALT, SGPT |
| `alp` | Alkaline phosphatase | 6768-6 | `U/L` | ALP, alk phos |
| `bili_total` | Total bilirubin | 1975-2 | `mg/dL` | TBili, total bilirubin, bilirubin total |
| `bili_direct` | Direct bilirubin | 1968-7 | `mg/dL` | DBili, conjugated bilirubin |
| `albumin` | Serum albumin | 1751-7 | `g/dL` | Alb |
| `ldh` | Lactate dehydrogenase | 2532-0 | `U/L` | LDH |

#### Disease markers — Multiple Myeloma (§2.5.1 + §2.6)

| Abbrev | Name | LOINC | Default unit | Aliases |
|---|---|---|---|---|
| `mspike_serum` | Monoclonal protein, serum | 33358-3 | `g/dL` | M-spike, M-protein, monoclonal immunoglobulin |
| `mspike_urine` | Monoclonal protein, urine 24h | 34366-5 | `mg/24h` | Bence Jones protein |
| `flc_kappa` | Kappa free light chain | 36916-5 | `mg/L` | κFLC, kappa FLC |
| `flc_lambda` | Lambda free light chain | 33944-0 | `mg/L` | λFLC, lambda FLC |
| `flc_ratio` | Kappa/Lambda FLC ratio | 48378-4 | (ratio) | K/L ratio, FLC ratio |
| `bmpc` | Bone marrow plasma cells | 26450-7 | `%` | BMPC, plasma cells % |
| `b2m` | Serum beta-2 microglobulin | 1952-1 | `mg/L` | β2M, beta-2 M |

#### Disease markers — Breast Cancer (§2.5.2)

| Abbrev | Name | LOINC | Default unit | Notes |
|---|---|---|---|---|
| `ca_15_3` | CA 15-3 | 6875-9 | `U/mL` | Tumour marker |
| `ca_27_29` | CA 27-29 | 17842-6 | `U/mL` | Tumour marker |
| `ki67` | Ki-67 proliferation index | 85337-4 | `%` | IHC-derived |

#### Cardiac & endocrine (§2.6.4, §2.6.7)

| Abbrev | Name | LOINC | Default unit | Aliases |
|---|---|---|---|---|
| `lvef` | Left ventricular ejection fraction | 10230-1 | `%` | EF, LVEF |
| `troponin` | Troponin I | 10839-9 | `ng/mL` | TnI, cardiac troponin |
| `bnp` | B-type natriuretic peptide | 30934-4 | `pg/mL` | BNP |
| `hba1c` | Hemoglobin A1c | 4548-4 | `%` | A1C, glycohemoglobin |
| `ldl` | LDL cholesterol | 13457-7 | `mg/dL` | LDL-C |
| `hdl` | HDL cholesterol | 2085-9 | `mg/dL` | HDL-C |
| `tsh` | Thyroid-stimulating hormone | 3016-3 | `mIU/L` | TSH |

#### Infection screen (§2.6.6)

| Abbrev | Name | LOINC | Default unit | Notes |
|---|---|---|---|---|
| `hiv_ab` | HIV 1/2 antibody | 75622-1 | (qualitative) | Stored as `reactive` / `non-reactive` |
| `hbsag` | Hepatitis B surface antigen | 5195-3 | (qualitative) | |
| `hcv_ab` | Hepatitis C antibody | 16128-1 | (qualitative) | |

**Total preloaded tests: ~37.** The preload exists to give a fresh-install patient something in their autocomplete + Records tab without having to upload a report first. It does **not** limit what HealthKey can track — novel tests auto-create `LabTestType` rows on first sight (§7).

### 3.3 Preload fixture

`backend/apps/labs/fixtures/lab_catalog.json` — committed, loaded via `loaddata` on first deploy. One `LabTestType` row per entry with full curation (category, display_order, reference_ranges, alternative_units, sample_values, molecular_weight where applicable). Phase 2c dropped `aliases` from the schema — matching is LOINC-first, no synonym table.

### 3.4 LOINC validation dictionary (`loinc_common.json`)

**`backend/apps/labs/data/loinc_common.json`** is a plain JSON file loaded by `apps/labs/matching.py` at module import. Ships with ~110 common serum/plasma/whole-blood analytes. Its job is singular: validate `loinc_code` claims the LLM returns.

Shape (loaded into a `dict[str, LoincEntry]` keyed by canonical code):

```json
{
  "_meta": { "description": "...", "source": "LOINC 2.77 Top-2000 subset" },
  "codes": [
    {
      "loinc_code": "718-7",
      "loinc_short_name": "Hemoglobin",
      "loinc_default_unit": "g/dL",
      "value_type": "numeric"
    },
    {
      "loinc_code": "75622-1",
      "loinc_short_name": "HIV 1/2 antibody",
      "loinc_default_unit": "",
      "value_type": "qualitative"
    }
  ]
}
```

**Why a dictionary, not a DB table?** ~110 entries, read-only, mostly static across releases. Loading at module import + O(1) dict lookup is the right tool. A DB table would be overengineered.

**Hard startup invariant:** `matching.py` raises `RuntimeError` at import if the fixture is missing or empty. Silent Tier 0a degradation is an unacceptable failure mode — we'd rather fail-loud at deploy than silently halve match quality in prod.

**Fixture refresh:** `backend/scripts/refresh_loinc_fixture.py` regenerates from LOINC's latest release (deferred to a follow-up; TODO-017 captures the ~twice-a-year reminder).

---

## 4. Data Model

### 4.1 Django app layout

New app: **`apps/labs/`**. Sits alongside `patient_profile`, `records`, `documents` in the existing project structure.

```
backend/apps/labs/
├── __init__.py
├── apps.py
├── admin.py
├── data/
│   └── loinc_common.json            # LOINC validation dict (§3.4)
├── fixtures/
│   └── lab_catalog.json             # ~37 preloaded LabTestType rows
├── migrations/
├── models.py                        # LabCategory, LabTestType, LabResult, LabUpload, LabUploadFile
├── serializers.py
├── views.py                         # LabUploadViewSet, LabResultViewSet
├── urls.py
├── tasks.py                         # Celery: process_lab_upload
├── parsers/
│   ├── __init__.py
│   ├── llm_parser.py                # Claude vision — ParsedLabResult, refusal, paged merge
│   ├── pdf_rasteriser.py            # PyMuPDF page-by-page JPEG + batch_pages()
│   └── prompts/
│       └── lab_extraction.txt       # The actual prompt (with {CATALOG_HINT})
├── matching.py                      # normalize_loinc, normalize_name, resolve_test_identity, LOINC_COMMON
├── unit_converter.py                # pint-based unit normalisation
└── tests/
    ├── test_api.py                  # Phase 2a endpoints
    ├── test_llm_parser.py           # Mocked Claude, refusal + parse + merge
    ├── test_matching.py             # LOINC + name fallback identity resolution
    ├── test_pipeline.py             # End-to-end upload → extraction (mocked LLM)
    ├── test_rasteriser.py           # PyMuPDF + paged batching
    ├── test_unit_converter.py       # Unit conversion
    └── test_uploads_api.py          # Upload API (Phase 2b)
```

### 4.2 Core models

```python
# apps/labs/models.py

class LabCategory(models.Model):
    """Groups tests for display. Seeded, never user-edited."""
    key = models.CharField(max_length=32, unique=True)      # "cbc" / "liver" / "myeloma"
    name = models.CharField(max_length=64)                  # "Complete Blood Count"
    display_order = models.PositiveSmallIntegerField()


class LabTestType(models.Model):
    """Test identity + display metadata.

    Phase 2c pivot: thin, AUTO-POPULATED table. Preloaded rows live in
    lab_catalog.json for Records-tab UX; any novel test seen in an upload
    auto-creates a row via matching.resolve_test_identity.
    """
    category = models.ForeignKey(LabCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="tests")
    abbreviation = models.CharField(max_length=64, unique=True)     # "hgb"; auto-slug'd from name for novel rows
    name = models.CharField(max_length=128)                         # "Hemoglobin"
    name_normalized = models.CharField(max_length=128, db_index=True, blank=True, default="")
    # Primary identity key. Partial-unique when non-empty (multiple no-LOINC
    # rows coexist, keyed by name_normalized instead):
    #   UniqueConstraint(fields=["loinc_code"], condition=Q(loinc_code__gt=""))
    loinc_code = models.CharField(max_length=16, db_index=True, blank=True, default="")
    default_unit = models.CharField(max_length=32)                  # "g/dL"
    alternative_units = models.JSONField(default=list, blank=True)
    sample_values = models.JSONField(default=dict, blank=True)
    reference_ranges = models.JSONField(default=dict, blank=True)   # { "default": [12.0, 15.5] }
    value_type = models.CharField(
        max_length=16,
        choices=[("numeric", "Numeric"), ("qualitative", "Qualitative"), ("ratio", "Ratio")],
        default="numeric",
    )
    molecular_weight = models.FloatField(null=True, blank=True)     # For molar↔mass (§8.2)
    display_order = models.PositiveSmallIntegerField(default=100)

    # NOTE: `aliases` was dropped in Phase 2c. Matching is LOINC-first; no
    # synonym table maintained. See §1 non-goals.


class LabUpload(models.Model):
    """One upload session. Can contain multiple files."""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lab_uploads")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)

    # Which LLM produced the extraction. Phase 2c is Claude-only (§6.3), but
    # recording the provider per-upload means any future Gemini/OpenAI adapter
    # doesn't need a backfill — old rows stay "claude", new rows stamp themselves.
    provider = models.CharField(max_length=32, default="claude")

    # Patient-supplied context
    lab_date = models.DateField(null=True, blank=True)              # Date shown on the report
    notes = models.TextField(blank=True, default="")                # Optional patient note

    # Extraction output (pre-match, raw LLM result)
    parsed_results = models.JSONField(default=list, blank=True)

    # Job tracking
    celery_task_id = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)


class LabUploadFile(models.Model):
    """One file within a LabUpload. Ordered for multi-page PDF processing."""
    upload = models.ForeignKey(LabUpload, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="lab-uploads/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    file_order = models.PositiveSmallIntegerField(default=0)
    sha256 = models.CharField(max_length=64, db_index=True)         # Dedupe identical uploads


class MatchMethod(models.TextChoices):
    """Canonical list — single source of truth for matching strategies.
    Referenced by LabResult, parsed_results JSON, API responses, and tests."""
    LOINC = "loinc", "LOINC direct"
    EXACT_ALIAS = "exact_alias", "Exact alias match"
    FUZZY = "fuzzy", "Fuzzy match"
    DISAMBIGUATION = "disambiguation", "Disambiguation rule"
    MANUAL = "manual", "Patient manually matched"
    UNMATCHED = "unmatched", "Unmatched"


class LabResult(models.Model):
    """Single numeric (or qualitative) lab value, normalised to default_unit.

    USER DELETION POLICY (per eng review §A2):
    - on_delete=CASCADE wipes LabResult when the user deletes their account.
    - Audit log entries referencing the deleted rows are pseudonymised via a
      post_delete signal: actor_id → NULL, resource_id → NULL.
    - No soft-delete, no de-identified retention for analytics.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lab_results")
    test_type = models.ForeignKey(LabTestType, on_delete=models.PROTECT, related_name="results")
    upload = models.ForeignKey(LabUpload, on_delete=models.SET_NULL, null=True, blank=True, related_name="results")

    value = models.FloatField(null=True, blank=True)                # Normalised to test_type.default_unit
    value_qualitative = models.CharField(max_length=32, blank=True, default="")  # For qualitative tests
    unit = models.CharField(max_length=32)                          # Always == test_type.default_unit after save
    source_text = models.CharField(max_length=64)                   # Verbatim original from the source (audit trail)
    source_unit = models.CharField(max_length=32)                   # Verbatim unit from the source

    # LLM-reported LOINC code — the ONLY LOINC field we persist from the LLM.
    # The model also returns loinc_name + loinc_default_unit (§6.1) but we
    # intentionally do NOT store them: the LLM can hallucinate a plausible code
    # paired with a wrong name, and the fixture (§3.4) is authoritative for name
    # and default unit anyway. Matcher (§7 Tier 0a) validates this code against
    # loinc_common.json before trusting it. Empty for manual entries and for
    # rows where the LLM returned no LOINC.
    raw_loinc_code = models.CharField(max_length=16, blank=True, default="")

    reference_min = models.FloatField(null=True, blank=True)        # Normalised
    reference_max = models.FloatField(null=True, blank=True)        # Normalised
    reference_source = models.CharField(
        max_length=8,
        choices=[("report", "From report"), ("catalog", "Catalog default"), ("none", "No range")],
        default="none",
    )                                                                # Provenance for UI "from report" vs "default"

    match_method = models.CharField(max_length=16, choices=MatchMethod.choices, default=MatchMethod.MANUAL)

    measured_at = models.DateField(null=True, blank=True)           # From the report
    source = models.CharField(
        max_length=32,
        choices=[
            ("manual", "Manual entry"),
            ("document_extraction", "Document extraction"),
            ("fhir", "FHIR sync"),
        ],
    )
    confidence = models.FloatField(default=1.0)                     # 0..1 from LLM (manual = 1.0)
    status = models.CharField(
        max_length=16,
        choices=[
            ("in_range", "In range"),
            ("below", "Below"),
            ("above", "Above"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["user", "test_type", "-measured_at"]),
        ]
```

**Unmatched results** — when the LLM returns a value the matcher can't tie to a `LabTestType`, it stays in `LabUpload.parsed_results` as a JSON entry until the patient manually picks a test from the catalog. It does **not** become a `LabResult` until matched.

**Reference range precedence** (resolved per eng review §CQ2): when both the report and the catalog provide reference ranges, **the report wins**. `LabResult.reference_source` records which was used. Rationale: the patient's own lab chose those ranges for their instrument; the catalog default is a fallback for reports that omit ranges entirely.

### 4.3 Relationships

```
User ──< LabUpload ──< LabUploadFile
User ──< LabResult >── LabTestType >── LabCategory
                   ╲
                    LabUpload (source)
```

---

## 5. API Contract

All endpoints under `/api/v1/labs/`, JWT-authenticated, scoped to `request.user`.

### 5.1 Catalog (read-only)

```
GET /api/v1/labs/catalog/
→ 200
{
  "categories": [
    { "key": "cbc", "name": "Complete Blood Count", "display_order": 10 },
    ...
  ],
  "tests": [
    {
      "id": 1, "abbreviation": "hgb", "name": "Hemoglobin",
      "loinc_code": "718-7", "default_unit": "g/dL",
      "category": "cbc", "reference_ranges": { "default": [12.0, 15.5] },
      "value_type": "numeric", "display_order": 20
    },
    ...
  ]
}
```

Heavily cached on the frontend (`staleTime: 24h`). Versioned by a `catalog_version` header sourced from a simple counter that bumps on any catalog-changing migration.

### 5.2 Upload & extraction

```
POST /api/v1/labs/uploads/
  multipart/form-data:
    files: File[]        (1-10 files)
    lab_date: YYYY-MM-DD (optional)
    notes: string        (optional)
→ 202
{
  "id": 42,
  "status": "pending",
  "celery_task_id": "abc123…",
  "files": [{ "original_filename": "cbc.pdf", "size_bytes": 128456 }]
}
```

`POST` enqueues Celery task immediately. Does not wait for extraction. Max total payload 20 MB.

```
POST /api/v1/labs/uploads/{id}/extract/
→ 202  (idempotent; re-running extraction is allowed)
{ "celery_task_id": "abc124…" }
```

Used when the patient retries a failed extraction. Separated from upload so we don't need to re-upload the file.

```
GET /api/v1/labs/uploads/{id}/
→ 200
{
  "id": 42,
  "status": "completed",
  "lab_date": "2026-03-15",
  "parsed_results": [
    {
      "raw_name": "Hemoglobin",
      "matched_test_id": 2,             // null if unmatched
      "value": 12.5,
      "unit": "g/dL",
      "reference_min": 12.0,
      "reference_max": 15.5,
      "confidence": 0.94,
      "measured_at": "2026-03-15",
      "match_method": "exact_alias",    // "loinc" | "exact_alias" | "fuzzy" | "unmatched"
      "accepted": null                   // true = saved, false = rejected, null = pending review
    },
    ...
  ],
  "error_message": ""
}
```

Frontend polls this endpoint every 2 seconds until `status` is `completed` or `failed`. No WebSockets in Phase 2; poll is fine for a ~20-second job.

```
POST /api/v1/labs/uploads/{id}/commit/
  {
    "accepted": [
      {
        "source_index": 0,
        "test_type_id": 2,
        "value": 12.5,
        "unit": "g/dL",
        "measured_at": "2026-03-15",
        "reference_min": 12.0,
        "reference_max": 15.5
      },
      ...
    ]
  }
→ 200
{
  "saved_count": 5,
  "skipped_count": 1,        // rows that matched an existing LabResult (same test+date, value ±1%)
  "results": [ /* newly created LabResult objects */ ]
}
```

Phase 2d behavior:
- Upload must be `status=completed` — otherwise 400.
- Anything not in `accepted` is rejected (no explicit `rejected` array needed).
- `source_index` is the stable handle into `parsed_results`; provenance (`match_method`, `confidence`) comes from the parsed row at that index. Client's edits to `value` / `unit` / `measured_at` / `reference_*` / `test_type_id` override the LLM output.
- Server-side dup detection: a row matching an existing `LabResult` on (user, test_type, measured_at) with numeric value within 1% (or exact qualitative match) is skipped silently. The frontend shows this client-side too.
- All-or-nothing transaction: any row that fails validation rolls back the entire commit.

### 5.3 Lab results (read / manual entry)

```
GET /api/v1/labs/results/
  ?test=hgb          (filter by abbreviation)
  &from=2024-01-01
  &to=2026-04-01
→ 200 [LabResult, ...]
```

Used by `LabTrendChart` and the Records tab.

```
POST /api/v1/labs/results/
  { "test_type_id": 2, "value": 12.5, "unit": "g/dL", "measured_at": "2026-03-15" }
→ 201 LabResult
```

Manual entry path — skips the upload flow entirely. Patient can type a single value. Unit converted and normalised server-side.

```
DELETE /api/v1/labs/results/{id}/
→ 204
```

---

## 6. Extraction Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     LAB UPLOAD → EXTRACTED RESULTS                           │
│                                                                              │
│  [Patient] ── POST /labs/uploads/ ── files + lab_date + notes                │
│       │                                                                      │
│       ▼                                                                      │
│  [Django]  ─ creates LabUpload (status=pending) + LabUploadFile rows         │
│       │    ─ deduplicates by sha256 (same file already uploaded? reject)     │
│       │    ─ enqueues process_lab_upload.delay(upload_id)                    │
│       │    ─ returns 202 immediately                                         │
│       ▼                                                                      │
│  [Celery worker — process_lab_upload]                                        │
│       │                                                                      │
│       ├─ LabUpload.status = "processing"                                     │
│       │                                                                      │
│       ├─ For each file:                                                      │
│       │    ├─ If PDF:                                                        │
│       │    │    └─ PyMuPDF: rasterise each page → 150 DPI JPEG              │
│       │    │       Yielded one page at a time to bound memory               │
│       │    ├─ If HEIC: pyheif → JPEG                                        │
│       │    └─ If JPEG/PNG: pass through                                     │
│       │                                                                      │
│       ├─ Build image parts list (all pages from all files in order)         │
│       │                                                                      │
│       ├─ llm_parser.extract(image_parts, catalog_hint)                       │
│       │    │                                                                 │
│       │    ├─ Provider: Claude 3.5 Sonnet Vision (primary)                   │
│       │    │            OpenAI gpt-4o-mini (fallback on Claude error)        │
│       │    │                                                                 │
│       │    ├─ Prompt: lab_extraction.txt                                     │
│       │    │    "You are a medical document extractor. Return JSON only…"    │
│       │    │    Includes compact catalog hint (abbreviation + aliases)       │
│       │    │    so the model knows which tests to care about                 │
│       │    │                                                                 │
│       │    └─ Returns: [{test_name, value, unit, ref_min, ref_max,           │
│       │                 measured_date, confidence}, ...]                     │
│       │                                                                      │
│       ├─ For each raw result:                                                │
│       │    ├─ matching.match_test(raw_name, value, unit) → LabTestType|None │
│       │    │    (see §7 for tiered strategy)                                 │
│       │    ├─ unit_converter.normalise(value, raw_unit, target_unit)         │
│       │    └─ Append enriched entry to parsed_results                        │
│       │                                                                      │
│       ├─ LabUpload.parsed_results = [...]                                    │
│       ├─ LabUpload.status = "completed"                                      │
│       └─ LabUpload.completed_at = now()                                      │
│                                                                              │
│  [Frontend polls GET /uploads/{id}/ every 2s]                                │
│       │                                                                      │
│       ▼                                                                      │
│  [Review UI]                                                                 │
│       ├─ Matched rows shown with confidence chip                             │
│       ├─ Unmatched rows in "Help us match" section                           │
│       └─ Patient taps Save → POST /commit/                                   │
│                                                                              │
│  [Django]  ─ creates LabResult rows from accepted entries                    │
│            ─ returns 200                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 LLM prompt (`prompts/lab_extraction.txt`)

Plain-text file so it's reviewable in git without syntax noise. Compiled at task-start, cached per worker:

```
You are a medical lab report extractor. You will receive images of lab report
pages and must return a JSON array of every numeric or qualitative lab test
result you can confidently identify.

RETURN FORMAT (strict JSON, no prose):
[
  {
    "test_name": "<name exactly as it appears on the page>",
    "value": "<the numeric or qualitative value>",
    "unit": "<unit exactly as it appears, empty string if none>",
    "reference_min": <number or null>,
    "reference_max": <number or null>,
    "measured_date": "<YYYY-MM-DD or null>",
    "page": <page index, 0-based>,
    "confidence": <0.0..1.0>,
    "loinc_code": "<canonical LOINC code for this test, or empty string>",
    "loinc_name": "<official LOINC long name, or empty string>",
    "loinc_default_unit": "<LOINC example unit, or empty string>"
  }
]

RULES:
- Only include results you can read with high confidence. Skip rows where the
  value is obscured, crossed out, or ambiguous.
- Return the value as the user would read it — do NOT convert units.
- `confidence` is your honest estimate of how sure you are this extraction is
  correct. If you have any doubt about the value or the unit, set it below 0.7.
- If the report has multiple dates (e.g., historical trend), use the most
  recent measured_date for each row.
- Qualitative results (e.g., HIV screen): return "reactive" or "non-reactive"
  as value, empty unit.
- DO NOT invent reference ranges. If the page does not show a range, return
  null for both reference_min and reference_max.
- DO NOT include narrative interpretation ("Patient appears healthy", etc.).
- LOINC fields: return the canonical LOINC code you are confident identifies
  this test (e.g. "718-7" for Hemoglobin in blood). If you are not sure which
  LOINC applies, return empty strings for all three LOINC fields — do NOT
  guess. The system validates every LOINC you return against an authoritative
  list and discards claims that don't match.

CONTEXT — HealthKey tracks these tests (partial list for your reference):
{CATALOG_HINT}
```

`{CATALOG_HINT}` is injected at runtime as a compact list:
```
- Hemoglobin (HGB, Hb, g/dL)
- White blood cell count (WBC, 10^3/uL)
- Alanine aminotransferase (ALT, SGPT, U/L)
- …
```

This is a **hint** only — the prompt explicitly tells the model not to restrict output to this list. The catalog hint exists so the model uses our preferred names when possible, which makes matching (§7) easier.

### 6.2 Why a single-shot multi-image call

Sending all pages in one prompt has three benefits:
- **Cross-page context**: values on page 2 (references) get tied to the test name on page 1
- **Deduplication**: a CBC repeated on multiple pages is recognised as one test
- **Cost**: one request beats N requests for token accounting and rate limiting

Trade-off: the input token count can be large on 20-page PDFs. Mitigations:
- PDF rasterisation at 150 DPI (readable, not HD)
- JPEG quality 85 (small files, still legible)
- Hard page cap of 30 per upload; reject anything larger with a clear error
- If input exceeds model context window, split into batches of 10 pages and merge

### 6.3 LLM provider — Claude + OpenAI, swappable via env

Phase 2c shipped Claude-only. **Phase 2c.1 added OpenAI as a selectable alternate** — neither is a fallback; `LAB_LLM_PROVIDER` (env var) picks which one runs. Swapping requires only the env flip + the corresponding API key.

- `LAB_LLM_PROVIDER=claude` (default) → `anthropic.Anthropic`, model `claude-sonnet-4-6`
- `LAB_LLM_PROVIDER=openai`          → `openai.OpenAI`, model `settings.LAB_OPENAI_MODEL` (default `gpt-4o`)

Both providers share `ParsedLabResult`, `_parse_response_json`, `detect_refusal`, `merge_results`, and the prompt template. Only the API call + image-encoding block differ. Refusal regex covers both "I apologize" (Claude) and "I'm sorry, but I cannot" (OpenAI). BAA gate remains per-provider — `LAB_UPLOAD_ENABLED` stays off in prod until the chosen provider's BAA is signed.

```python
# parsers/llm_parser.py

class ParsedLabResult(TypedDict):
    test_name: str
    value: str | None
    unit: str
    reference_min: float | None
    reference_max: float | None
    measured_date: str | None
    page: int
    confidence: float
    batch_index: int   # Which extraction batch this came from (0 for single-shot)


class ClaudeLabParser:
    """Uses anthropic.Anthropic SDK with claude-sonnet-4-6.

    Failure modes handled:
      - Malformed JSON      → ParseError, retry once, then fail
      - Timeout (>60s)      → TimeoutError, fail fast
      - Rate limit          → RateLimitError with exponential backoff (3 retries)
      - Empty array         → return [] (upload completes with empty results)
      - Refusal detected    → RefusalError (see §12.2)
      - Token limit hit     → trigger paged extraction (§6.4)
    """
    def extract(self, images: list[bytes], catalog_hint: str) -> list[ParsedLabResult]: ...
```

The `ParsedLabResult` TypedDict is the contract every downstream consumer (matching, serializers, tests) relies on. If OpenAI support is ever added, its parser must return the same shape; the adapter work is a known cost that's deferred until we actually need it.

### 6.4 Paged extraction for large PDFs (per eng review §A1)

Phase 2c implements proper paged merge, not a hard cap. The catalog hint stays; the merge logic lives in `llm_parser.py`:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      PAGED EXTRACTION MERGE LOGIC                            │
│                                                                              │
│  Input: N rendered page images, total_pages                                  │
│                                                                              │
│  if total_pages <= 10:                                                       │
│      # Single-shot: one Claude call with all pages                           │
│      return claude.extract(images, catalog_hint, batch_index=0)              │
│                                                                              │
│  else:                                                                       │
│      # Paged: split into batches of 10                                       │
│      batches = [images[i:i+10] for i in range(0, total_pages, 10)]           │
│      all_results = []                                                        │
│      for idx, batch in enumerate(batches):                                   │
│          batch_results = claude.extract(                                     │
│              batch,                                                          │
│              catalog_hint,                                                   │
│              batch_index=idx,                                                │
│              system_hint=f"This is batch {idx+1}/{len(batches)} "            │
│                          f"of a larger report.",                             │
│          )                                                                   │
│          all_results.extend(batch_results)                                   │
│                                                                              │
│      return deduplicate(all_results)                                         │
│                                                                              │
│  dedupe key: (normalized_test_name, value, unit, measured_date)              │
│  when two results have the same key, keep the one with higher confidence;    │
│  when confidences are equal, keep the earlier batch_index (preserves order). │
│                                                                              │
│  KNOWN LIMITATION: a test whose NAME is on page 10 and VALUE is on page 11   │
│  (straddling a batch boundary) may be missed. The pdf_rasteriser adds a      │
│  2-page overlap between batches (pages 9+10 appear in both batches) to       │
│  mitigate. Overlap results are deduped by the standard key.                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Overlap strategy:** batches overlap by 2 pages. Batch 0 has pages 0..9, batch 1 has pages 8..17, batch 2 has pages 16..25. A test whose name is on page 9 and value is on page 10 is visible to both batch 0 (sees page 9+10) and batch 1 (sees page 8+9+10). Dedup by key resolves the duplicate. Cost is ~20% more image tokens per large PDF, acceptable for correctness.

**Hard upper bound:** 60 pages total. Beyond that, the upload is rejected at ingress with a clear error. Rationale: 60 pages = 7 batches = 7 Claude calls = acceptable latency (< 90s), still clearly useful. Anything larger is "split your report and upload separately."

---

## 7. Test Identity Resolution

Phase 2c pivot collapsed the previous 3-tier (exact alias → fuzzy → disambiguation) matching into a single function. LOINC is the identity; if the LLM can't produce a usable LOINC we fall back to normalized-name grouping. No aliases, no fuzzy, no disambiguation rules.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                   resolve_test_identity(raw_name, raw_loinc, raw_unit)       │
│                                                                              │
│   Input:  raw_name, raw_loinc (may be None/empty/garbage), raw_unit          │
│   Output: (LabTestType, match_method)  — NEVER (None, ...)                   │
│                                                                              │
│   STEP 1 — Normalize LOINC                                                   │
│     normalize_loinc(raw_loinc):                                              │
│       - strip whitespace                                                     │
│       - map Unicode en-dash/em-dash → ASCII hyphen                           │
│       - regex extract (\d{1,5}-\d)                                           │
│       "LOINC:718-7"  → "718-7"                                              │
│       "718–7" (U+2013) → "718-7"                                             │
│       "718" (no checksum) → ""                                               │
│                                                                              │
│   STEP 2 — Validated LOINC path (if normalized code ∈ LOINC_COMMON)          │
│     LabTestType.objects.get_or_create(                                       │
│         loinc_code=<code>,                                                   │
│         defaults={                                                           │
│             name = fixture.loinc_short_name,                                 │
│             default_unit = fixture.loinc_default_unit or raw_unit,           │
│             value_type = fixture.value_type,                                 │
│             abbreviation = slug_with_collision_suffix(slug_from_name(...)),  │
│         },                                                                   │
│     )                                                                        │
│     return (test_type, "loinc")                                              │
│                                                                              │
│   STEP 3 — Name fallback (LOINC absent or not in fixture)                    │
│     normalized = normalize_name(raw_name)                                    │
│     existing = LabTestType.filter(name_normalized=normalized).first()        │
│     if existing:                                                             │
│         return (existing, "name_fallback")                                   │
│     # Create no-LOINC row                                                    │
│     test_type = LabTestType.create(                                          │
│         loinc_code="", name=raw_name, abbreviation=slug_with_collision(...), │
│         default_unit=raw_unit, value_type="numeric",                         │
│     )                                                                        │
│     return (test_type, "name_fallback")                                      │
│                                                                              │
│   No row ever returns None. Pathological input (empty name + empty LOINC)    │
│   parks under a shared "unknown test" row the patient can rename on review.  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Implementation:** `apps/labs/matching.py`, ~150 lines total. The LOINC fixture loads at module import into `LOINC_COMMON: dict[str, LoincEntry]` — O(1) membership + O(1) name/unit lookup. Fixture-missing at import is a hard startup failure.

**Name normalisation (§CQ5):** NFKD + casefold + punctuation-strip.

```python
def normalize_name(raw: str) -> str:
    s = unicodedata.normalize("NFKD", raw).casefold()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())
```

**Known trade-off:** `"HGB"` (slug 'hgb', normalized 'hgb') and `"Hemoglobin"` (slug 'hemoglobin', normalized 'hemoglobin') without LOINC would create *two* no-LOINC rows — same test, different identity. In practice this rarely fires: Claude almost always returns the LOINC for common analytes (path 2 fires, both reports merge). The fallback is the escape hatch for novel / non-English / low-quality reports. Phase 2d's review UI lets the patient manually merge fragmented rows by selecting a different LabTestType before commit.

**Match method** is the same `MatchMethod` `TextChoices` enum — single source of truth shared with the frontend types. New code produces one of: `loinc`, `name_fallback`, `manual`. Legacy values (`exact_alias`, `fuzzy`, `disambiguation`) are kept for backwards compatibility with any pre-2c rows but never produced by new code.

### 7.1 Manual test selection (review UI)

The review UI (Phase 2d) always ties a parsed row to a `LabTestType` — resolution never returns None. Patients can override the auto-resolution before commit by picking a different `LabTestType` from an autocomplete backed by existing rows + the LOINC fixture. This corrects rare cases where the fallback fragmented what should have been one test, or where the LLM picked the wrong LOINC.

---

## 8. Unit Normalisation

### 8.1 Strategy

Every `LabTestType` has a `default_unit`. Every `LabResult` stores `value` + `unit` where `unit == test_type.default_unit`. The conversion happens on save, using `pint` (the standard Python units library).

```python
# apps/labs/unit_converter.py

import pint

_ureg = pint.UnitRegistry()
_ureg.define("10^3/uL = 1000/uL = K/uL = kilo_per_uL")
_ureg.define("IU = 1 * dimensionless")
# …plus a small map of common lab unit aliases to pint-friendly forms

UNIT_ALIASES = {
    "ug": "microgram",
    "µg": "microgram",
    "pg/ml": "pg/mL",
    "K/uL": "10^3/uL",
    "10^9/L": "10^3/uL",          # Identical quantity, SI notation
    "mmol/L": "mmol/liter",
    ...
}

def normalise(value: float, from_unit: str, to_unit: str,
              molecular_weight: float | None = None) -> float | None:
    """Convert value from from_unit to to_unit. Returns None on failure."""
    try:
        src = _ureg.Quantity(value, _canonicalise(from_unit))
        return src.to(_canonicalise(to_unit)).magnitude
    except (pint.errors.DimensionalityError, pint.errors.UndefinedUnitError):
        # Molar ↔ mass conversion requires molecular weight
        if molecular_weight is not None:
            return _molar_mass_convert(value, from_unit, to_unit, molecular_weight)
        return None
```

### 8.2 Molar ↔ mass conversions

Some tests report in either mass (mg/dL) or molar (mmol/L) units. Conversion requires the analyte's molecular weight. For HealthKey's seed catalog this matters for:
- Calcium (mg/dL ↔ mmol/L, MW 40.08)
- Creatinine (mg/dL ↔ µmol/L, MW 113.12)
- Bilirubin (mg/dL ↔ µmol/L, MW 584.66)

`LabTestType` gets an optional `molecular_weight` field (null for tests where the conversion doesn't apply, e.g., LVEF).

### 8.3 Graceful failure

If normalisation fails (unknown unit, dimensionality mismatch without molecular weight), the parsed result is still shown in the review UI but the value is **not** pre-accepted — the patient must correct the unit before committing. No silent data corruption.

---

## 9. Storage & Security

### 9.1 Storage

- **Local dev:** `MEDIA_ROOT/lab-uploads/YYYY/MM/` via Django's default `FileSystemStorage`
- **Production:** S3 via `django-storages`, private bucket, SSE-KMS encryption
- **Max file size:** 10 MB per file, 20 MB per upload total
- **Max pages per PDF:** 30 (enforced client-side + server-side)
- **Accepted MIME types:** `application/pdf`, `image/jpeg`, `image/png`, `image/heic`

### 9.2 Deduplication

Each `LabUploadFile` stores `sha256(file_bytes)`. If the same user uploads the same file twice:
- Existing `LabUpload` with the same hash is returned (idempotent)
- The Celery task is not re-enqueued unless the previous upload's status is `failed`

### 9.3 Retention

- **Uploaded files:** retained indefinitely as source-of-truth for extracted values. Deleted when user deletes the upload or deletes their account. Mirrors the PHR architecture doc's "raw FHIR bundles are the source of truth" principle applied to uploaded documents.
- **Pre-match `parsed_results` JSON:** kept on `LabUpload` for audit/debugging. Included in the patient's data export.

### 9.4 Access control + PHI in LLM calls

- All endpoints `IsAuthenticated` + `IsOwner` (checks `upload.user == request.user`)
- Celery tasks always look up `LabUpload` by ID and never trust a user field in the task payload
- Presigned S3 URLs issued for reading uploaded files (short-lived, 5-minute expiry)

**PHI transmitted to the LLM vendor — honest description:**

Full lab reports (including patient name, DOB, MRN, provider name, provider address, and every clinical value on the page) are transmitted to the LLM vendor as image data. **This is PHI.** There is no attempt to redact or minimise the image content before sending — doing so reliably at scale would require its own OCR pipeline, defeating the purpose.

**No PII from our database is appended** to the request. We do not send the user's HealthKey account ID, email, internal patient_id, or any `PatientInfo` field. The only user-identifying data in the vendor's hands is whatever was printed on the lab report the patient chose to upload.

**Mandatory before prod deploy:**
1. Signed BAA with the LLM vendor covering vision API calls
2. Vendor contractual commitment that images are not retained or used for training
3. TODO-001 resolution confirming which vendor's BAA we have

Feature flag `LAB_UPLOAD_ENABLED` (§15.1) stays `False` in prod until all three land.

### 9.5 Deletion propagation

Per eng review §A2, user deletion cascades through labs:

```
User.delete()
    │
    ├─ CASCADE → LabUpload.delete()   (FK on_delete=CASCADE)
    │              │
    │              ├─ CASCADE → LabUploadFile.delete()
    │              │              └─ post_delete signal → remove file from S3
    │              │
    │              └─ CASCADE → LabResult.delete()
    │                              └─ post_delete signal → pseudonymise
    │                                 audit entries (actor_id→NULL,
    │                                 resource_id→NULL), keep the row
    │                                 for 6-year HIPAA audit retention
    │
    └─ "Delete my uploads but keep my account" is a separate flow:
       DELETE /api/v1/labs/uploads/{id}/ cascades the same way but leaves
       User intact. Patient-initiated, single-upload scope.
```

Audit log rows are **never** cascade-deleted. They are pseudonymised in place so the compliance timeline stays intact even after the referenced data is gone.

### 9.5 PHI in logs

The LLM extraction task logs the `upload_id`, `file_count`, `total_pages`, `extraction_duration_ms`, and per-result `match_method` + `confidence`. It does **not** log raw test names, values, or extracted JSON. Observability without PHI leaks.

---

## 10. Frontend — Screens & Components

### 10.1 Component inventory (new or extended)

| Component | File | Notes |
|---|---|---|
| `LabUploadDialog` | `components/labs/LabUploadDialog.tsx` | New. Modal (or bottom sheet on mobile) with file picker + camera + submit |
| `LabUploadReview` | `components/labs/LabUploadReview.tsx` | New. Review extracted values, per-row confidence chip + edit |
| `LabResultRow` | `components/labs/LabResultRow.tsx` | New. Editable row: test name, value, unit, reference range, source badge |
| `LabMatchDropdown` | `components/labs/LabMatchDropdown.tsx` | New. shadcn `Select` filtered by category for unmatched-row manual pick |
| `LabCatalogProvider` | `features/labs/useCatalog.ts` | New. React Query hook, 24h cache |
| `LabValueCard` | existing in design doc §4.2 | Now populated by real data |
| `LabTrendChart` | existing in design doc §4.2 | Now populated by real data |
| `DataSourceBadge` | existing | `source="document"` with optional confidence |

### 10.2 Upload dialog (mobile wireframe)

```
┌─────────────────────────────────────┐
│  ← Add lab results              ✕   │
├─────────────────────────────────────┤
│                                     │
│   How would you like to add this?   │
│                                     │
│   ┌───────┐  ┌───────┐  ┌───────┐   │
│   │ ✏      │  │ 📄    │  │ 🔗    │   │
│   │Type   │  │Upload │  │EHR    │   │
│   │one in │  │file   │  │(soon) │   │
│   └───────┘  └───────┘  └───────┘   │
│                                     │
│   Report date (optional)            │
│   [ 2026-03-15            ]          │
│                                     │
│   Notes (optional)                  │
│   [                       ]          │
│   [                       ]          │
│                                     │
│   ┌─────────────────────────────┐   │
│   │ 📎 cbc-results.pdf   24 KB  │   │
│   └─────────────────────────────┘   │
│                                     │
│   [  Add another file  ]            │
│                                     │
│  ─────────────────────────────────  │
│   [ Cancel ]     [ Upload & read ]  │
└─────────────────────────────────────┘
```

Reuses `OnboardingStepShell`'s pattern of three-mode input (Type / Upload / EHR) for consistency with onboarding.

### 10.3 Processing screen

```
┌─────────────────────────────────────┐
│  Reading your report…               │
│                                     │
│  [████████░░░░░░░] 45%              │
│                                     │
│  This usually takes 10–30 seconds.  │
│                                     │
│  You can leave this screen —        │
│  we'll notify you when it's ready.  │
└─────────────────────────────────────┘
```

Progress bar estimate is visual only (2% per second, capped at 95% until the backend reports complete). The "you can leave" line points to a toast notification on completion.

### 10.4 Review screen (the heart of the feature)

```
┌──────────────────────────────────────────────────────────┐
│  ← Review extracted results                              │
│                                                          │
│  We found 9 values in your report.                       │
│  Review, edit, then save what you want to keep.          │
│                                                          │
│  ▸ Complete Blood Count                                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │ ☑ Hemoglobin       12.5  g/dL   Normal  ●High   │    │
│  │                    ref 12.0–15.5            ✏   │    │
│  ├──────────────────────────────────────────────────┤    │
│  │ ☑ Platelets        145   K/µL   Low     ●High   │    │
│  │                    ref 150–400               ✏   │    │
│  ├──────────────────────────────────────────────────┤    │
│  │ ☑ WBC              4.8   10³/µL Normal  ●High   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ▸ Liver function                                        │
│  ┌──────────────────────────────────────────────────┐    │
│  │ ☑ ALT               28   U/L    Normal  ●Med    │    │
│  │ ☑ AST               31   U/L    Normal  ●High   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ⚠ Help us match these (2)                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │ "Beta-2-Microgl"   2.1   mg/L                    │    │
│  │ [ Pick test type ▾ ]                             │    │
│  ├──────────────────────────────────────────────────┤    │
│  │ "Kappa FLC Ratio"  1.2                           │    │
│  │ [ Pick test type ▾ ]                             │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ──────────────────────────────────────────────────────  │
│              [ Cancel ]     [ Save 7 results ]           │
└──────────────────────────────────────────────────────────┘
```

**Colour semantics:**
- `●High` — confidence ≥ 0.85 (healthkey brand-700 dot)
- `●Med` — 0.6 ≤ confidence < 0.85 (warning-700 dot)
- `●Low` — confidence < 0.6 (error-700 dot, auto-unchecked, patient must confirm)
- `Normal / Low / High` — in-range status based on reference

Every row is editable: tap the pencil to change value, unit, or reference range. Edits mark the row as manually verified and bump its confidence to 1.0.

The save button label counts **checked** rows, not all rows, so the patient sees the consequence.

### 10.5 State-level integration

- Upload dialog lives under `/dashboard/records` as a route-modal
- After successful `POST /commit/`, React Query invalidates `["lab-results"]` and `["timeline"]` so the Records tab re-renders
- Newly saved lab results flow into `LabValueCard` in the Home tab automatically
- The upload shows as a timeline entry (`TimelineEntry` component in design doc §4.2)

---

## 11. Interaction State Coverage

Every state the UI must render, per design doc §6.

| Feature | Loading | Empty | Error | Success | Partial |
|---|---|---|---|---|---|
| **Upload dialog file list** | — | "Drop or pick a file to start." | "Couldn't read that file. Try another." | File chip shown | Multi-file supported |
| **Upload POST** | Button spinner | — | Inline: "Couldn't upload. Check your connection." | Navigate to processing screen | — |
| **Extraction (Celery)** | Animated progress bar + "Reading your report…" | — | "We couldn't read this report. Try again or enter values manually." | → Review screen | "Got 3 of 9 values. Some pages were unclear — review carefully." |
| **Review — matched rows** | Skeleton rows | "We couldn't find any lab values." CTA: manual entry | — | Full list | Low-confidence rows auto-unchecked |
| **Review — unmatched rows** | — | Section hidden when empty | — | "Help us match these (N)" | — |
| **Commit POST** | Button spinner, disabled form | — | Inline: "Couldn't save. Nothing was lost — try again." | Navigate to Records tab, toast: "N results saved" | — |
| **Lab results list** | Skeleton cards | "No lab values yet. Upload a report or connect your provider." | "Couldn't load some results" + retry | Cards + trend charts | Mixed sources (manual + extracted) |

### Empty-state copy guidelines (from design doc §10)

- "No lab values yet. Upload a report or connect your provider." — warm, primary action, context
- **Not** "No data found."

---

## 12. Error Handling & Edge Cases

### 12.1 Upload errors

| Cause | UI | Backend |
|---|---|---|
| File > 10 MB | "This file is too big (max 10 MB). Try a lower-quality scan." | `413 Payload Too Large` |
| Wrong MIME type | "We can read PDF, JPEG, PNG, and HEIC. This file isn't supported." | `415 Unsupported Media Type` |
| > 30 pages | "This PDF has {N} pages. We can handle up to 30. Split and re-upload." | `400` with detail |
| Hash collision w/ prior upload | "You've already uploaded this file. Let's take you to the existing review." | Returns the existing upload |

### 12.2 Extraction errors

| Cause | Behaviour |
|---|---|
| LLM returns malformed JSON | Retry once; on second failure mark upload failed with `error_message="We couldn't read the values from this report. Try a clearer scan or enter them manually."` |
| **LLM refusal** (per eng review §3.4) | Detect common refusal phrases (`"i cannot"`, `"i am unable"`, `"i can't process"`, `"as an ai"`) via regex before JSON parsing. Distinct `RefusalError`. User message: `"Our AI couldn't process this report. Please enter the values manually or try a different scan."` Do NOT retry — retrying won't change the model's answer |
| LLM timeout (>60s) | Mark upload failed: `"Reading took too long — try a clearer scan"` |
| LLM rate limit | Exponential backoff 1s/2s/4s, 3 attempts. On final failure: `"Our AI is busy right now. Try again in a minute."` — keep upload in a retryable state |
| Celery soft timeout (>270s) | Same message as LLM timeout; triggered when the full pipeline (rasterise + extract + match) runs over budget |
| LLM returns empty array | Upload marked `completed` with empty `parsed_results`; review UI shows empty state with "We couldn't find any lab values. Enter them manually?" |
| Image too low-resolution | No special handling. The LLM's own confidence scores will be low; review UI surfaces them |
| Paged extraction: one batch fails | Mark the batch failed in `parsed_results` metadata; merge the successful batches; show a warning in the review UI: "We couldn't read all the pages. Some values may be missing." |

### 12.3 Extraction quality issues

- **Hallucinated tests** (LLM invents values): manual review catches these before save
- **Wrong unit detected**: normalisation fails gracefully, row auto-unchecked, patient fixes
- **Ambiguous test name** (e.g., "Calcium" without "total"/"ionised"): disambiguation rule fires; on miss, shown in unmatched section
- **Date on report is unclear**: `measured_at` falls back to `LabUpload.lab_date` if provided, otherwise to upload creation date. The review UI always shows the date as editable
- **Multiple values for the same test** (e.g., baseline + follow-up on the same report): all returned as separate rows; patient picks which to save

### 12.4 Commit edge cases

- **Patient edits an extracted value beyond sanity** (e.g., hemoglobin = 500 g/dL): accepted. Sanity range warnings shown pre-save ("That seems high. Double-check?") but never blocking. Patient sovereignty
- **Duplicate within the upload**: detected pre-save and shown in review as a single row
- **Duplicate against existing LabResult** (same test, same date, same value ±1%): shown as "Already saved — Mar 15 · 12.5" with a greyed-out checkbox

### 12.5 LLM provider outage

Per eng review §A3, Phase 2c ships with Claude only — no automatic fallback. If Anthropic is down, the upload goes to `failed` with:

> "We're having trouble reading reports right now. Your file is saved — try again in a few minutes."

The Celery task is not auto-retried on infrastructure errors; the patient taps "Retry extraction" which hits `POST /extract/`. This is a deliberate trade-off: building a working OpenAI adapter costs ~2 days (different image format, different JSON schema, different refusal patterns) and only pays off during real Anthropic outages, which are rare. When we have our first real outage, that data justifies the adapter landing.

---

## 13. Implementation Phases

This feature is Phase 2 of the overall patient app plan (see architecture doc §9). Within Phase 2, split into four landings:

### Phase 2a — Catalog + manual entry (1 week)

- [ ] `apps/labs/` Django app scaffolding
- [ ] `LabCategory`, `LabTestType`, `LabResult` models + migrations
- [ ] `lab_catalog.json` fixture (35 tests)
- [ ] `GET /catalog/`, `POST /results/`, `GET /results/`, `DELETE /results/{id}/`
- [ ] `unit_converter.py` + full pytest coverage
- [ ] Frontend `useCatalog()` hook
- [ ] Manual entry form on Records tab
- [ ] `LabValueCard` wired to real data
- [ ] `LabTrendChart` wired to real data

**Launch gate:** unit-converter edge-case tests passing, manual entry E2E.

### Phase 2b — Upload + storage (3 days)

- [ ] `LabUpload`, `LabUploadFile` models
- [ ] `POST /uploads/`, `GET /uploads/{id}/`
- [ ] File storage config (local dev + S3 plan)
- [ ] SHA256 deduplication
- [ ] Frontend upload dialog with file picker + multi-file support
- [ ] Processing screen with polling

**Launch gate:** upload test covering multi-file, SHA dedupe, size/MIME limits.

### Phase 2c — LLM extraction + matching (1 week)

- [ ] `parsers/pdf_rasteriser.py` (PyMuPDF, generator-based, 2-page overlap for paged mode)
- [ ] `parsers/llm_parser.py` — **Claude only** (no OpenAI adapter in Phase 2c)
- [ ] `ParsedLabResult` TypedDict as the matching contract (includes `loinc_code`, `loinc_name`, `loinc_default_unit`)
- [ ] Paged extraction merge logic (`§6.4`) for PDFs >10 pages, cap at 60
- [ ] `prompts/lab_extraction.txt` + catalog-hint injection + LOINC output fields (§6.1) + cache invalidation on catalog version bump
- [ ] `fixtures/loinc_common.json` (~500 common analytes, §3.4) + `scripts/refresh_loinc_fixture.py`
- [ ] `LabUpload.provider` field + `LabResult.raw_loinc_code` migration (name + unit pulled from fixture, not persisted)
- [ ] `matching.py` — **Tier 0a validated-LOINC** + tiered strategy + `MatchMethod` enum + `DISAMBIGUATION_RULES` dict + Unicode-folding `normalize_name`
- [ ] Refusal detection in `llm_parser.py` before JSON parsing
- [ ] Celery task `process_lab_upload` + refusal/timeout/rate-limit handling
- [ ] Fixture-based extraction eval suite (no live LLM calls on every CI run)
- [ ] BAA confirmation with Anthropic before `LAB_UPLOAD_ENABLED` goes true in prod

**Launch gate (all must pass before shipping 2c):**
1. Unit tests for `unit_converter`, `matching`, `pdf_rasteriser` — 100% branch coverage
2. Integration tests for `tasks.process_lab_upload` with Celery eager mode — happy + 4 failure modes
3. Extraction eval suite on 20 anonymised fixture PDFs meets baseline: **recall ≥ 0.90, precision ≥ 0.95, unit-match rate ≥ 0.95** (per eng review test decision)
4. Eval baseline locked in `backend/apps/labs/tests/fixtures/baseline_metrics.json`; CI fails if any metric drops >3% vs baseline
5. Eval marked `pytest -m eval` — runs only on changes to `prompts/lab_extraction.txt` or `llm_parser.py`, not on every test invocation
6. BAA signed with Anthropic, filed with TODO-001

### Phase 2d — Review UI + commit ✅ (landed 2026-04-20)

- [x] `LabUploadReview` component (flat list, category grouping deferred)
- [x] Per-row toggle + inline edit (value, unit, measured_at, reference range)
- [x] `POST /uploads/{id}/commit/` endpoint with all-or-nothing transaction
- [x] Duplicate detection (server + client, same test + date + value ±1%)
- [x] `POST /uploads/{id}/extract/` retry endpoint for failed uploads
- [x] Success path: commit → invalidate `["labs", "results"]` → Records tab re-renders
- [x] 17 new API tests (commit happy / edits / override / dup / error paths / retry)

Deferred (follow-up):
- Category grouping on the review screen (flat list works for ~10-row typical case)
- Test-type override in-dialog via autocomplete (patient can edit post-commit via manual dialog)
- Pencil-icon edit-mode polish (current inline form is functional, not polished)

**Launch gate (met):** upload a fixture PDF → extraction (mocked) → review → save → lab shows in Records tab. Full pipeline covered by `test_pipeline.py` + `test_commit_api.py`.

---

## 14. Open Questions

Decisions resolved during eng review (2026-04-09) are marked ✅. Open items are still pending.

1. ✅ **LLM provider** — Anthropic Claude only for Phase 2c. OpenAI adapter deferred to its own landing if/when a real Anthropic outage justifies the ~2 days of adapter work. Still requires BAA with Anthropic before `LAB_UPLOAD_ENABLED` flips true in prod. Tracked as TODO-001.

2. ✅ **Reference-range precedence** — report wins when present, catalog default is the fallback. `LabResult.reference_source` records which was used. Demographic-aware ranges (age/sex-specific) deferred to Phase 3.

3. ✅ **PDF page cap** — soft cap at 10 pages for single-shot extraction, hard cap at 60 pages total. Pages 11–60 trigger paged extraction (§6.4) with 2-page batch overlap. Pages 61+ rejected at ingress.

4. ✅ **User deletion** — hard delete. `on_delete=CASCADE` wipes `LabUpload` + `LabUploadFile` + `LabResult`. Audit log references pseudonymised, not deleted, to preserve HIPAA 6-year audit retention.

5. **File retention after upload deletion**: do we keep orphaned S3 files after the LabUpload row is deleted? Current plan: `post_delete` signal removes the file. Still worth a review with legal on whether to retain for 30 days as a recoverable "trash" bucket.
   - **Proposed:** hard delete from S3 on upload deletion, no trash. Aligns with GDPR right-to-erasure mental model.

6. **Trend chart on low data**: one measurement renders as a dot, no line. Copy: "Not enough data for a trend yet." Already covered in design doc §6 (partial state).
   - **No action needed — use the existing empty-state pattern.**

7. **Mobile camera capture quality**: no hard minimum in Phase 2c. LLM confidence flags low-quality scans. A follow-up can add pre-upload warning.
   - **Deferred to Phase 3 polish.**

8. **Date disambiguation** (MM/DD vs DD/MM): pass patient's `country` from `PatientInfo` as a prompt hint. Falls back to upload's `lab_date` field. Ambiguous dates with no hint land on the review screen for patient correction.
   - **Actionable in Phase 2c prompt.**

9. ✅ **LOINC ground-truth** — resolved. Ship `backend/apps/labs/fixtures/loinc_common.json` (~500 most-common analyte LOINCs, §3.4) as the validator for LLM-reported LOINC codes. Matcher Tier 0a (§7) rejects LOINCs not in the fixture before trusting them. `LabResult.raw_loinc_code/name/default_unit` audit fields preserve the LLM's claim even when matching falls back to name-based tiers.

10. **Auto-create LabTestType from uploaded tests** — deferred to **Phase 3**. When an extraction returns a LOINC that's in `loinc_common.json` but no `LabTestType` row exists for it, Phase 3 can auto-create the catalog row using the fixture's canonical `loinc_name` + `loinc_default_unit` (authoritative — **not** the LLM's name/unit, which we intentionally do not persist per §4.2). Flow: show the uploaded row in the unmatched section pre-creation, let the patient accept/name-tweak the fixture-derived name, then commit the new `LabTestType` row. Out of scope for Phase 2c: for now these rows land in the unmatched section for manual selection from the existing ~35-test catalog.
   - **Deferred — Phase 3.**

---

## 15. Rollout & Observability

### 15.1 Feature flag

New flag in `Settings.FEATURE_FLAGS` (simple dict): `LAB_UPLOAD_ENABLED` (default `True` in dev, `False` in prod until BAA is confirmed). The frontend reads this via `/api/v1/feature-flags/` and hides the upload button when disabled.

### 15.2 Metrics to track

| Metric | Where | Purpose |
|---|---|---|
| `lab_upload.created` | Django logging | Volume |
| `lab_upload.extraction_duration_ms` | Celery task metric | p50/p95 latency |
| `lab_upload.match_rate_percent` | Per-upload average of matched / total | Catalog coverage |
| `lab_upload.confidence_avg` | Mean LLM confidence per upload | Quality trend |
| `lab_upload.manual_match_rate` | % rows requiring manual match | Matching-algorithm quality |
| `lab_upload.committed_vs_extracted` | Saved count / extracted count | User trust signal |
| `lab_upload.failed_rate` | Failed / total | Pipeline health |
| `llm_provider.errors` | Grouped by error type | Vendor reliability |

No patient-identifying data in any of these. Upload ID is pseudonymous at the metric level.

### 15.3 On-call playbook

| Symptom | First check | Fix |
|---|---|---|
| Extraction failures spiking | LLM provider status page | Switch `LAB_LLM_PROVIDER` env var to fallback |
| Celery queue backing up | Worker count + soft timeout rate | Scale workers, raise soft timeout if genuinely slower |
| Match rate dropping | Recent catalog changes | Rollback catalog migration |
| Upload size errors spiking | User reports | Consider raising limits |

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 12 issues, all resolved; 1 critical gap (LLM refusal) resolved |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | deferred, UI reuses existing components from `patient-app-design.md` §4 |
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |

**ENG REVIEW RESOLUTIONS (2026-04-09):**
- **A1** paged merge implemented with 2-page overlap (§6.4), hard cap 60 pages
- **A2** hard delete + audit pseudonymisation (§4.2, §9.5)
- **A3** Claude only for Phase 2c, OpenAI deferred (§6.3, §12.5)
- **A4** honest PHI wording (§9.4)
- **CQ1** `raw_value` → `source_text` (§4.2)
- **CQ2** reference precedence: report wins, `reference_source` field added (§4.2)
- **CQ3** `MatchMethod` enum as single source of truth (§4.2, §7)
- **CQ5** Unicode NFKD + casefold in `normalize_name` (§7)
- **Critical gap** LLM refusal detection + distinct error (§12.2)
- **Eval** strict thresholds: recall ≥0.90, precision ≥0.95, unit match ≥0.95; baseline locked (§13 Phase 2c)

**VERDICT:** ENG CLEAR — ready to implement. Start Phase 2a (catalog + manual entry + unit converter). Phase 2c blocked on TODO-001 (Anthropic BAA) — feature flag stays `False` in prod until BAA lands.
