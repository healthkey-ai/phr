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
- **Extract structured lab values** (test name, value, unit, reference range, date) with an LLM vision model
- **Match extracted values** against a canonical catalog of tests relevant to HealthKey's oncology-focused patient population
- **Normalise units** so every saved value is in the same unit as every other measurement of that test
- **Show provenance + confidence** on every lab value so the patient can trust (or correct) it
- **Feed existing components**: extracted values populate `LabValueCard`, `LabTrendChart`, and the Records tab automatically
- **Work end-to-end without FHIR**: a patient who cannot connect their EHR can still build a longitudinal lab record by snapping photos of paper reports

### Non-goals (explicitly deferred)

- **No editing of the canonical catalog by users.** The test list is seed data, changes via migration
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

## 3. Canonical Lab Test Catalog

### 3.1 Philosophy

The catalog is the **single source of truth** for what HealthKey can track. Every extracted value must match a row here or it's marked `unmatched` and shown in the manual-tagging section. Adding a test requires a migration, not an API call.

This narrow list is intentional. The patient population is oncology-focused (per PRD), so the catalog prioritises:
- Complete Blood Count + differentials (chemo neutropenia monitoring)
- Renal function (for platinum-based therapy eligibility)
- Liver function (hepatotoxicity monitoring)
- Disease-specific markers for Multiple Myeloma, Breast Cancer, FL, CLL (the four V1 disease profiles)
- Cardiac baselines (for anthracycline and HER2-targeted therapy)
- Infection screen (clinical trial eligibility)

Values outside this catalog aren't rejected; they're stored as `unmatched` so the patient sees them and we can add them in a future migration.

### 3.2 Seed catalog (initial migration)

Every row is a `LabTestType` record. Aliases seeded from LOINC `RELATEDNAMES2` plus common abbreviations.

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

**Total seed catalog: ~35 tests.** Enough to cover the requirements doc comprehensively. Expansion (e.g., Follicular Lymphoma FLIPI inputs, CLL cytogenetics) lands in a follow-up migration when we actually build those disease profile pages.

### 3.3 Catalog seed file

`backend/apps/labs/fixtures/lab_catalog.json` — committed, loaded via `loaddata` on first deploy and in the `/labs/` app's `ready()` hook for development convenience.

---

## 4. Data Model

### 4.1 Django app layout

New app: **`apps/labs/`**. Sits alongside `patient_profile`, `records`, `documents` in the existing project structure.

```
backend/apps/labs/
├── __init__.py
├── apps.py
├── admin.py
├── fixtures/
│   └── lab_catalog.json             # 35 LabTestType rows
├── migrations/
├── models.py                        # LabTestType, LabUpload, LabUploadFile, LabResult
├── serializers.py
├── views.py                         # LabUploadViewSet, LabResultViewSet
├── urls.py
├── tasks.py                         # Celery: process_lab_upload, extract_and_match
├── parsers/
│   ├── __init__.py
│   ├── llm_parser.py                # Claude vision + OpenAI vision abstract
│   ├── pdf_rasteriser.py            # PyMuPDF page-by-page JPEG
│   └── prompts/
│       └── lab_extraction.txt       # The actual prompt
├── matching.py                      # Tiered matching logic
├── unit_converter.py                # pint-based unit normalisation
└── tests/
    ├── test_models.py
    ├── test_matching.py
    ├── test_unit_converter.py
    ├── test_extraction.py           # Fixture-based, no live LLM calls
    └── test_api.py
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
    """Canonical test definition. Seeded, never user-edited."""
    category = models.ForeignKey(LabCategory, on_delete=models.PROTECT, related_name="tests")
    abbreviation = models.CharField(max_length=32, unique=True)     # "hgb"
    name = models.CharField(max_length=128)                         # "Hemoglobin"
    loinc_code = models.CharField(max_length=16, db_index=True, blank=True, default="")
    default_unit = models.CharField(max_length=32)                  # "g/dL"
    aliases = models.JSONField(default=list)                        # ["HGB", "Hb", "haemoglobin"]
    reference_ranges = models.JSONField(default=dict)               # { "default": [12.0, 15.5] }
    value_type = models.CharField(
        max_length=16,
        choices=[("numeric", "Numeric"), ("qualitative", "Qualitative"), ("ratio", "Ratio")],
        default="numeric",
    )
    display_order = models.PositiveSmallIntegerField(default=100)


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
      { "index": 0, "value": 12.5, "unit": "g/dL", "matched_test_id": 2, "measured_at": "2026-03-15" },
      ...
    ],
    "rejected": [1, 3]    // indices in parsed_results to drop entirely
  }
→ 200
{
  "saved_count": 7,
  "results": [ /* newly created LabResult objects */ ]
}
```

The patient's review decisions drive which parsed results become `LabResult` rows. The backend trusts the client's edits (they're the patient's data). Every accepted row is validated against the `LabTestType.value_type` + unit convertibility before saving.

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
    "confidence": <0.0..1.0>
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

### 6.3 LLM provider abstraction

```python
# parsers/llm_parser.py

class LabLLMParser(Protocol):
    def extract(self, images: list[bytes], catalog_hint: str) -> list[ParsedLabResult]: ...

class ClaudeLabParser: ...       # Uses anthropic.Anthropic SDK, claude-sonnet-4-6
class OpenAILabParser: ...       # Uses openai, gpt-4o-mini

def get_parser() -> LabLLMParser:
    if settings.LAB_LLM_PROVIDER == "openai":
        return OpenAILabParser()
    return ClaudeLabParser()      # default
```

Provider chosen via `LAB_LLM_PROVIDER` env var. Default is Claude per CLAUDE.md guidance to use latest Anthropic models for AI work. Fallback path on the primary's failure retries once with the other provider before marking the upload `failed`.

---

## 7. Tiered Matching

The matcher takes a raw `test_name` from the LLM and returns a `LabTestType` row or `None`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      MATCH_TEST TIERED STRATEGY                              │
│                                                                              │
│  Input: raw_name, value, unit, ref_min, ref_max                              │
│                                                                              │
│  Tier 0 — LOINC code direct lookup                                           │
│    If the LLM returned a loinc_code (rare but possible), query that          │
│    → If hit: return the LabTestType, match_method = "loinc"                  │
│                                                                              │
│  Tier 1 — Exact-insensitive match                                            │
│    Normalise raw_name: lowercase, strip punctuation, collapse whitespace     │
│    Compare against (abbreviation, name, every alias) for all LabTestTypes    │
│    → If exactly one hit: return it, match_method = "exact_alias"             │
│    → If multiple hits (ambiguous): fall through to disambiguation            │
│                                                                              │
│  Tier 2 — Fuzzy token_set_ratio >= 85                                        │
│    RapidFuzz `token_set_ratio` across (name + aliases) for every test       │
│    → Single winner with score >= 85: return it, match_method = "fuzzy"       │
│    → Multiple >= 85 within 3 points: disambiguation                          │
│    → No match >= 85: return None, match_method = "unmatched"                 │
│                                                                              │
│  Disambiguation (Tier 1 or Tier 2 multi-hit)                                 │
│    Apply known rules:                                                        │
│    - "calcium" + unit == "mg/dL" and value in [8..11] → total calcium        │
│    - "bilirubin" alone (no "direct"/"indirect") → total bilirubin            │
│    - "AST" vs "ALT" resolved by exact letters                                │
│    → If no rule fires, return None (manual matching path)                    │
│                                                                              │
│  Output: (LabTestType | None, match_method, disambiguation_reason | None)    │
└──────────────────────────────────────────────────────────────────────────────┘
```

Implementation lives in `apps/labs/matching.py` as pure functions, fully unit-testable without a database.

**Disambiguation rules** are hardcoded in a small dict keyed by normalised raw name. Adding a rule is a 3-line code change + test. We resist the temptation to make this data-driven until we have 10+ rules.

### 7.1 Manual matching fallback

Any result where `match_method == "unmatched"` is shown in the review UI's amber "Help us match these" section. The patient picks a `LabTestType` from a dropdown (filtered to the relevant category if the LLM returned one). The commit endpoint records the manual match on the resulting `LabResult`.

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

### 9.4 Access control

- All endpoints `IsAuthenticated` + `IsOwner` (checks `upload.user == request.user`)
- Celery tasks always look up `LabUpload` by ID and never trust a user field in the task payload
- Presigned S3 URLs issued for reading uploaded files (short-lived, 5-minute expiry)
- LLM calls **do not** include the user's HealthKey ID, name, or any PII from `PatientInfo` — only the document images. Per the existing architecture doc's BAA requirement, the LLM vendor must have a signed BAA before this ships to prod

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
| LLM returns malformed JSON | Retry once with primary provider; on second failure fall back to OpenAI |
| LLM timeout (>60s) | Mark upload failed with `error_message="Reading took too long — try a clearer scan"` |
| Celery soft timeout (>270s) | Same as above — message explains how to recover |
| LLM returns empty array | Upload marked `completed` with empty `parsed_results`; review UI shows empty state with "We couldn't find any lab values. Enter them manually?" |
| Image too low-resolution | No special handling. The LLM's own confidence scores will be low; review UI surfaces them |

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

Primary (Claude) down → automatic fallback to OpenAI on the task's first retry. If both down, the upload goes to `failed` with:

> "We're having trouble reading reports right now. Your file is saved — try again in a few minutes."

The Celery task is not auto-retried in this case; the patient taps "Retry extraction" which hits `POST /extract/`.

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

- [ ] `parsers/pdf_rasteriser.py` (PyMuPDF integration)
- [ ] `parsers/llm_parser.py` with Claude + OpenAI abstractions
- [ ] `prompts/lab_extraction.txt` + catalog-hint injection
- [ ] `matching.py` with tiered strategy + disambiguation rules
- [ ] Celery task `process_lab_upload`
- [ ] Fixture-based extraction tests (no live LLM calls in CI)
- [ ] BAA confirmation with LLM vendor before prod deploy

**Launch gate:** fixture-based extraction tests covering 20 real (anonymised) lab PDFs.

### Phase 2d — Review UI + commit (3 days)

- [ ] `LabUploadReview` component with category grouping
- [ ] `LabResultRow` editable
- [ ] Manual-match dropdown for unmatched rows
- [ ] `POST /commit/` endpoint
- [ ] Duplicate detection (against existing results)
- [ ] Success path navigates to Records

**Launch gate:** E2E: upload a fixture PDF → extraction completes → review → save → lab shows in Records tab.

---

## 14. Open Questions

Decisions deferred or needing stakeholder input:

1. **LLM provider BAA**: which vendor (Anthropic vs OpenAI) currently offers a BAA that covers vision API calls? Needs legal confirmation before Phase 2c can ship to prod. Until then, the feature runs behind a feature flag for staff accounts only.

2. **Reference-range source of truth**: the report on paper is one reference range. `LabTestType.reference_ranges["default"]` is another. When they disagree, which wins?
   - **Proposed:** the report's range wins for the specific `LabResult` (stored on the row), the catalog default is the fallback. Edge case: age- and sex-specific ranges (e.g., hemoglobin) — keep the catalog default as unisex until Phase 3 adds demographic-aware ranges.

3. **File retention policy**: do we keep the uploaded PDFs forever or purge after N months? HIPAA is 6 years for the record but the original uploaded doc isn't legally required.
   - **Proposed:** keep forever by default (cheap S3 storage); patient can delete via the upload history UI.

4. **Trend chart on low data**: two measurements form a line. One measurement is just a dot. What does `LabTrendChart` do with a single measurement?
   - **Proposed:** render the single value as a dot + reference band, no connecting line. Copy: "Not enough data for a trend yet." Already specified in design doc §6 (partial state).

5. **Mobile camera capture quality**: should the upload dialog enforce a minimum resolution on camera-captured images?
   - **Proposed:** no hard minimum. The LLM confidence flag surfaces low-quality images organically. A pre-upload warning ("This image looks small — try again?") can land in a follow-up.

6. **Date disambiguation**: US lab reports use MM/DD/YYYY, EU uses DD/MM/YYYY. When both digits are ≤12, the LLM can't tell without context.
   - **Proposed:** pass the patient's `country` from `PatientInfo` as an additional prompt hint. Falls back to the upload's `lab_date` field (which the patient can set) when still ambiguous.

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
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | pending |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | pending |
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |

**VERDICT:** DRAFT — recommend `/plan-eng-review` on this document before implementation begins, especially on the LLM provider abstraction, matching edge cases, and the BAA question in §14.
