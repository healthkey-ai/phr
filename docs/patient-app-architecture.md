# HealthKey Patient App — Architecture

**Branch:** patient-app  
**Stack:** Django 5.x + Django REST Framework (backend) · Vite + React 18 + shadcn/ui + Tailwind CSS 3 + React Query v5 (frontend)  
**Date:** April 2026  
**References:** `docs/patient-app-requirements.md`, `docs/Architecture.md`, `docs/PRD.md`

---

## Contents

1. [System Context](#1-system-context)
2. [Backend Architecture](#2-backend-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Data Architecture](#4-data-architecture)
5. [Security Architecture](#5-security-architecture)
6. [Integration Architecture](#6-integration-architecture)
7. [API Design](#7-api-design)
8. [Deployment Architecture](#8-deployment-architecture)
9. [Implementation Phases](#9-implementation-phases)
10. [Design Decisions & Trade-offs](#10-design-decisions--trade-offs)

---

## 1. System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL ACTORS                                    │
│                                                                             │
│  Patient (Web/Mobile)     Clinician (Provider View)     Researcher API     │
│         │                          │                          │            │
└─────────┼──────────────────────────┼──────────────────────────┼────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HEALTHKEY PATIENT APP                              │
│                                                                             │
│  ┌───────────────────┐    ┌──────────────────┐    ┌─────────────────────┐  │
│  │   React SPA        │    │  Django API       │    │  Celery Workers     │  │
│  │ (Vite/shadcn/TW)  │───▶│  (DRF / REST)    │───▶│  (async tasks)      │  │
│  └───────────────────┘    └──────────────────┘    └─────────────────────┘  │
│                                    │                          │             │
│                           ┌────────┼──────────────────────────┘             │
│                           ▼        ▼                                        │
│                    ┌──────────┐  ┌──────────────────────────────────────┐  │
│                    │ Redis    │  │  PostgreSQL                           │  │
│                    │ (cache   │  │  ├── healthkey_operational schema     │  │
│                    │  + queue)│  │  └── omop schema (analytics, R/O)    │  │
│                    └──────────┘  └──────────────────────────────────────┘  │
│                                                                             │
│                    ┌──────────────────────────────────────────────────────┐ │
│                    │  S3-compatible object store                          │ │
│                    │  ├── encrypted FHIR bundles (source of truth)        │ │
│                    │  └── encrypted document uploads (PDFs, images)       │ │
│                    └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
┌────────────────────┐   ┌────────────────────┐   ┌───────────────────────────┐
│  EHR Systems        │   │  CMS/USCDI Network  │   │  Trial Matching API       │
│  Epic / Cerner /    │   │  (IAL2-gated FHIR  │   │  (cancerbot/trial-engine) │
│  Athena / MEDITECH  │   │   + payer claims)   │   └───────────────────────────┘
└────────────────────┘   └────────────────────┘
```

### Data flow summary

```
Patient browser ──HTTPS──▶ Django API ──▶ PostgreSQL (operational)
                                      ──▶ S3 (FHIR bundles, docs)
                                      ──▶ Redis (cache)
                                      ──▶ Celery ──▶ FHIR sync worker
                                                ──▶ Doc processing worker
                                                ──▶ OMOP ETL worker
                                                ──▶ Trial matching worker
```

---

## 2. Backend Architecture

### 2.1 Django Project Structure

```
backend/
├── config/                     # Project-level Django settings
│   ├── settings/
│   │   ├── base.py             # Common settings
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py                 # Top-level URL routing
│   └── celery.py               # Celery app init
│
├── apps/
│   ├── accounts/               # Auth, identity verification, MFA, passkeys
│   ├── patient_profile/        # PatientInfo form, demographics, disease profile
│   ├── records/                # Health record vault, longitudinal timeline
│   ├── fhir_sync/              # FHIR R4 integration, EHR connections
│   ├── documents/              # Upload, storage, AI extraction pipeline
│   ├── sharing/                # Access grants, SMART Health Links, QR codes
│   ├── trials/                 # Trial matching, CDS recommendations
│   ├── notifications/          # Push + email notifications
│   └── audit/                  # Immutable audit log
│
├── core/                       # Shared utilities, base models, encryption
│   ├── encryption.py           # AES-256-GCM field-level encryption helpers
│   ├── fhir_mapper.py          # FHIR R4 resource ↔ internal model mapping
│   ├── omop_etl.py             # FHIR bundle → OMOP CDM transform pipeline
│   └── pagination.py
│
└── tests/                      # Integration tests (pytest + pytest-django)
    ├── accounts/
    ├── patient_profile/
    ├── fhir_sync/
    ├── sharing/
    └── e2e/                    # Full API flow tests
```

### 2.2 Django Apps — Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DJANGO APPS DEPENDENCY GRAPH                        │
│                                                                             │
│  accounts ◄──── patient_profile ◄──── records ◄──── sharing                │
│     │                  │                │                │                  │
│     │                  ▼                ▼                ▼                  │
│     │           fhir_sync ──────── documents ─────── trials                │
│     │                  │                                                    │
│     ▼                  ▼                                                    │
│  audit ◄──────── notifications                                              │
│                                                                             │
│  core/ (shared utilities — imported by all apps, no circular deps)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### `accounts`
- Custom `User` model (email-based, extends `AbstractBaseUser`)
- MFA via TOTP (django-otp or custom)
- Passkey/WebAuthn (AAL2) — planned via `django-passkeys` or direct FIDO2 library
- Identity verification states: `UNVERIFIED → MFA_ENROLLED → IAL1 → IAL2`
- Caregiver delegation: `CaregiverGrant` model (user, patient, permission_level, expires_at)
- Social auth: Apple + Google via `django-allauth`

#### `patient_profile`
- `PatientInfo` model — flat denormalized table (matches `cancerbot/ui.v2` schema)
- `PatientInfoVersion` — immutable audit trail for every field change
- Calculated field triggers: eGFR, TNBC status, CRAB/SLIM criteria (computed server-side on save)
- `FormSettings` — dropdown option configuration per field
- `ProfileCompleteness` — cached completeness score per category

#### `records`
- `HealthRecord` — structured longitudinal record entry (links to OMOP concepts)
- `TimelineEvent` — denormalized patient-facing event view (condition, lab, procedure, med)
- `ConflictRecord` — detected data conflicts with resolution state
- `LabValue` — time-series lab values with units + reference ranges
- Views: record list, timeline, lab trends, conflict resolution

#### `fhir_sync`
- `EHRConnection` — stored OAuth credentials per EHR system (encrypted at rest)
- `FHIRBundle` — S3 pointer + metadata for raw stored FHIR bundles
- `SyncJob` — Celery task record: status, source, records affected, errors
- FHIR R4 parser: converts FHIR resources to `PatientInfo` + `TimelineEvent` updates

#### `documents`
- `Document` — S3 pointer, MIME type, source, linked patient record
- `ExtractionJob` — async AI extraction task: status, confidence scores
- `ExtractedField` — proposed PatientInfo updates from document extraction
- Pre-extraction: client-side AES-256 encryption before upload (key never sent to server)

#### `sharing`
- `AccessGrant` — scoped time-limited share: scopes, duration, token, revoked_at
- `SMARTHealthLink` — SHL metadata (encrypted FHIR bundle pointer, expiry, passcode)
- `AuditEntry` — who accessed what, when (immutable, append-only)
- QR code generation: `qrcode` library, HealthKey-branded output
- SMART Health Card generation (SHC static snapshots)

#### `trials`
- `TrialMatch` — cached matching result per patient per trial (NCT number, eligibility)
- `MatchingJob` — Celery task: triggers when `PatientInfo` changes
- Integration with cancerbot trial engine via internal API call
- `StandardOfCareResult` — NCCN/guideline recommendations cached per patient

#### `audit`
- `AuditLog` — immutable append-only log: `actor_id`, `action`, `resource_type`, `resource_id`, `scopes`, `timestamp`
- Django signal hooks on every `PatientInfo` change, `AccessGrant` create/revoke, `EHRConnection` sync
- HIPAA 6-year retention requirement: no hard deletes

### 2.3 Key Models

```python
# accounts/models.py
class User(AbstractBaseUser, PermissionsMixin):
    email           = EmailField(unique=True)
    identity_level  = CharField(choices=["unverified", "ial1", "ial2"])
    mfa_enabled     = BooleanField(default=False)
    encryption_key_hash = CharField(max_length=64)  # server side hash of key derived from password; never stores plaintext key
    created_at      = DateTimeField(auto_now_add=True)

class CaregiverGrant(Model):
    patient         = ForeignKey(User, related_name="caregiver_grants")
    caregiver       = ForeignKey(User, related_name="caregiver_access")
    permission_level = CharField(choices=["view", "view_add"])
    expires_at      = DateTimeField(null=True)
    revoked_at      = DateTimeField(null=True)

# patient_profile/models.py
class PatientInfo(Model):
    user            = OneToOneField(User)
    # --- Demographics ---
    first_name      = EncryptedCharField()
    last_name       = EncryptedCharField()
    dob             = EncryptedDateField()
    gender          = CharField(max_length=32)
    ethnicity       = ArrayField(CharField())
    height_cm       = FloatField(null=True)
    weight_kg       = FloatField(null=True)
    bmi             = FloatField(null=True)          # computed
    country         = CharField(max_length=3)        # ISO 3166-1 alpha-3
    postal_code     = CharField(max_length=16)
    geo_lat         = FloatField(null=True)          # derived from postal_code
    geo_long        = FloatField(null=True)
    # --- Clinical (disease-specific fields stored as JSONB) ---
    details         = JSONField(default=dict)        # all clinical fields
    disease         = CharField(max_length=64, null=True)
    # --- Completeness ---
    completeness_score = FloatField(default=0.0)
    completeness_by_category = JSONField(default=dict)
    updated_at      = DateTimeField(auto_now=True)

class PatientInfoVersion(Model):
    patient_info    = ForeignKey(PatientInfo)
    changed_fields  = JSONField()
    changed_by      = ForeignKey(User)
    source          = CharField(choices=["manual", "fhir", "document_extraction", "caregiver"])
    timestamp       = DateTimeField(auto_now_add=True)

# sharing/models.py
class AccessGrant(Model):
    patient         = ForeignKey(User)
    token           = CharField(max_length=64, unique=True, db_index=True)
    scopes          = ArrayField(CharField())        # ["identity", "conditions", "labs", ...]
    duration_hours  = IntegerField()
    expires_at      = DateTimeField()
    revoked_at      = DateTimeField(null=True)
    access_count    = IntegerField(default=0)
    created_at      = DateTimeField(auto_now_add=True)

# fhir_sync/models.py
class EHRConnection(Model):
    patient         = ForeignKey(User)
    ehr_system      = CharField()                    # "epic", "cerner", "athena", ...
    fhir_base_url   = CharField()
    access_token    = EncryptedTextField()           # encrypted OAuth token
    refresh_token   = EncryptedTextField()
    last_synced_at  = DateTimeField(null=True)
    sync_status     = CharField(choices=["active", "error", "revoked"])
    error_message   = TextField(null=True)
```

> **Note on `details` JSONB:** All disease-specific clinical fields live in `PatientInfo.details` as a JSONB column. This avoids a migration per new field and matches the `cancerbot/ui.v2` schema directly. A JSON Schema validator enforces structure on write. Disease-gated fields are activated/hidden based on `PatientInfo.disease`.

### 2.4 Async Tasks (Celery)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           CELERY TASK FLOWS                                  │
│                                                                              │
│  FHIR Sync (scheduled + on-demand)                                           │
│  ─────────────────────────────────                                           │
│  EHRConnection.refresh_token ──▶ fhir_sync.tasks.sync_ehr_connection         │
│       │                                                                      │
│       ├──▶ Fetch FHIR R4 resources (Patient, Condition, Obs, Med...)         │
│       ├──▶ Store raw bundle in S3 (encrypted)                                │
│       ├──▶ Map FHIR → PatientInfo fields (core/fhir_mapper.py)               │
│       ├──▶ Detect conflicts vs existing data                                 │
│       ├──▶ Queue OMOP ETL job                                                │
│       └──▶ Notify patient (new data available)                               │
│                                                                              │
│  Document Processing                                                         │
│  ────────────────────                                                        │
│  Document.uploaded ──▶ documents.tasks.process_document                      │
│       │                                                                      │
│       ├──▶ Decrypt document (client encrypted key sent as session param)     │
│       ├──▶ Extract text (pdfminer / OCR)                                     │
│       ├──▶ Call AI extraction service (structured field extraction)          │
│       ├──▶ Store ExtractedField proposals (confidence scores included)       │
│       └──▶ Notify patient for review                                         │
│                                                                              │
│  OMOP ETL (triggered after PatientInfo change)                               │
│  ─────────────────────────────────────────────                               │
│  PatientInfo.save() ──▶ audit.tasks.omop_etl_job                             │
│       │                                                                      │
│       ├──▶ Map operational tables → OMOP CDM domains                         │
│       ├──▶ Update omop.condition_occurrence, measurement, drug_exposure...   │
│       └──▶ Rebuild PatientInfo denormalized analytics row                    │
│                                                                              │
│  Trial Matching (triggered by PatientInfo change)                            │
│  ─────────────────────────────────────────────────                           │
│  PatientInfo.save() ──▶ trials.tasks.run_trial_matching                      │
│       │                                                                      │
│       ├──▶ Call cancerbot trial engine API with current PatientInfo          │
│       ├──▶ Store TrialMatch results                                          │
│       └──▶ Notify if new trials matched                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Queue configuration:**
| Queue | Workers | Priority | Timeout |
|---|---|---|---|
| `fhir_sync` | 2 | High | 120s |
| `documents` | 2 | Medium | 300s |
| `omop_etl` | 1 | Low | 600s |
| `trial_matching` | 1 | Medium | 30s |
| `notifications` | 1 | High | 10s |

---

## 3. Frontend Architecture

### 3.1 Vite/React Project Structure

```
frontend/
├── src/
│   ├── main.tsx                    # App entry point
│   ├── App.tsx                     # Root with router + providers
│   │
│   ├── pages/                      # Route-level page components
│   │   ├── auth/
│   │   │   ├── SignUp.tsx
│   │   │   ├── SignIn.tsx
│   │   │   └── MFA.tsx
│   │   ├── onboarding/
│   │   │   ├── OnboardingShell.tsx  # Progress bar + step routing
│   │   │   ├── steps/
│   │   │   │   ├── Welcome.tsx
│   │   │   │   ├── Identity.tsx    # IAL2 identity verification
│   │   │   │   ├── Demographics.tsx
│   │   │   │   ├── Conditions.tsx
│   │   │   │   ├── DiseaseProfile.tsx  # conditional: cancer only
│   │   │   │   ├── Lifestyle.tsx
│   │   │   │   ├── FamilyHistory.tsx
│   │   │   │   └── Summary.tsx
│   │   │   └── EHRConnect.tsx
│   │   ├── dashboard/
│   │   │   ├── DashboardShell.tsx   # Tab layout (Home/Records/Share/Profile)
│   │   │   ├── Home.tsx
│   │   │   ├── Records.tsx
│   │   │   ├── Share.tsx
│   │   │   └── Profile.tsx
│   │   ├── provider-view/
│   │   │   └── ProviderView.tsx     # Read-only scoped record view
│   │   └── NotFound.tsx
│   │
│   ├── features/                   # Feature-specific logic + components
│   │   ├── patient-profile/
│   │   │   ├── api.ts              # React Query hooks (usePatientInfo, useUpdatePatientInfo)
│   │   │   ├── forms/              # Form sections per onboarding step
│   │   │   └── components/         # ProfileCard, CompletenessIndicator, etc.
│   │   ├── records/
│   │   │   ├── api.ts
│   │   │   ├── LabTrendChart.tsx   # Recharts time-series + reference ranges
│   │   │   ├── TimelineView.tsx
│   │   │   └── ConflictResolution.tsx
│   │   ├── sharing/
│   │   │   ├── api.ts
│   │   │   ├── AccessGrantCard.tsx
│   │   │   ├── QRCodeModal.tsx
│   │   │   └── ScopeSelector.tsx
│   │   ├── fhir/
│   │   │   ├── api.ts
│   │   │   ├── EHRConnectionCard.tsx
│   │   │   └── ConnectEHRModal.tsx
│   │   ├── documents/
│   │   │   ├── api.ts
│   │   │   ├── DocumentUpload.tsx  # Camera / file picker / scan
│   │   │   └── ExtractionReview.tsx  # AI-extracted field review
│   │   └── trials/
│   │       ├── api.ts
│   │       ├── TrialMatchList.tsx
│   │       └── TrialDetailView.tsx
│   │
│   ├── components/                 # Shared UI components
│   │   ├── ui/                     # shadcn/ui re-exports (Button, Input, etc.)
│   │   ├── layout/                 # PageShell, Sidebar, TabBar
│   │   ├── forms/                  # TagInput, MultiSelectChips, LabValueInput
│   │   └── feedback/               # Toast, LoadingSpinner, EmptyState
│   │
│   ├── lib/
│   │   ├── queryClient.ts          # React Query client config
│   │   ├── api.ts                  # Axios instance + interceptors
│   │   ├── encryption.ts           # Client-side AES-256-GCM (Web Crypto API)
│   │   └── validators.ts           # Zod schemas for all form inputs
│   │
│   └── types/                      # TypeScript interfaces (PatientInfo, AccessGrant, etc.)
│
├── vite.config.ts
└── tailwind.config.ts              # Extends cancerbot/ui.v2 design tokens
```

### 3.2 Page Routing

```
/                           → redirect to /dashboard or /auth/sign-in
/auth/sign-up               → SignUp
/auth/sign-in               → SignIn
/auth/mfa                   → MFA challenge
/onboarding                 → OnboardingShell (step 0: Welcome)
/onboarding/:step           → OnboardingShell (step n)
/dashboard                  → DashboardShell / Home tab
/dashboard/records          → Records tab
/dashboard/share            → Share tab
/dashboard/profile          → Profile tab
/r/:token                   → ProviderView (public, token-gated)
```

### 3.3 State Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND STATE LAYERS                               │
│                                                                             │
│  Server State (React Query)                                                 │
│  ─────────────────────────                                                  │
│  usePatientInfo()          → GET /api/v1/patient-info/user/                 │
│  useUpdatePatientInfo()    → PATCH /api/v1/patient-info/user/              │
│  useProfileCompleteness()  → GET /api/v1/patient-info/profile-completeness/ │
│  useFormSettings()         → GET /api/v1/form-settings/                     │
│  useEHRConnections()       → GET /api/v1/fhir/connections/                  │
│  useAccessGrants()         → GET /api/v1/sharing/grants/                   │
│  useTrialMatches()         → GET /api/v1/trials/matches/                    │
│  useTimelineEvents()       → GET /api/v1/records/timeline/                  │
│                                                                             │
│  Client State (React Context / Zustand — minimal)                           │
│  ──────────────────────────────────────────────────                         │
│  AuthContext               → current user, JWT token, identity level        │
│  OnboardingContext         → current step, step validity, skip flags        │
│                                                                             │
│  Form State (React Hook Form + Zod)                                         │
│  ─────────────────────────────────                                          │
│  All form pages use useForm() with Zod schema validation                    │
│  PATCH on blur (debounced 500ms) — no explicit Save button on most steps    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Key UI Patterns

**Onboarding wizard state machine:**
```
                    ┌─────────┐
                    │ Welcome │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  Auth   │  email/password + MFA setup
                    └────┬────┘
                         │
                    ┌────▼────────┐
                    │  Identity   │  phased: MFA first, IAL2 only before data import
                    └────┬────────┘
                         │
          ┌──────────────┼───────────────────────────┐
          ▼              ▼              ▼             ▼
    ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐
    │Conditions│   │ Lifestyle│  │  Family  │  │  Labs    │  (each: Manual / Upload / EHR)
    └─────┬────┘   └────┬─────┘  └────┬─────┘  └────┬─────┘
          │             │             │              │
          └─────────────┴─────────────┴──────────────┘
                               │
                               ▼
                   ┌──────────────────────┐
                   │  Disease Profile      │  shown only if cancer selected
                   │  (MM / Breast / FL /  │
                   │   CLL / Lung etc.)    │
                   └──────────┬───────────┘
                              │
                         ┌────▼─────┐
                         │ Summary  │  completeness % + next actions
                         └──────────┘
```

**Three-mode data input (all data steps):**
```
┌─────────────────┬─────────────────┬─────────────────┐
│  Manual Entry   │  Upload Docs    │  Connect EHR    │
│  (form fields)  │  (PDF/image AI) │  (SMART/FHIR)   │
└─────────────────┴─────────────────┴─────────────────┘
```

**Lab trend chart (Recharts):**
```
Lab value (e.g. Hemoglobin)
    12.5 ┤                            ●
    11.0 ┤              ●         ╱
     9.5 ┤                   ●───
     8.0 ┤  ●───────●     ↑ out of range
         └────────────────────────────── time
         Jan    Mar    May    Jul   [reference range shaded]
```

---

## 4. Data Architecture

### 4.1 PostgreSQL Schema Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        POSTGRESQL SCHEMAS                                   │
│                                                                             │
│  healthkey (operational — Django ORM manages)                               │
│  ──────────────────────────────────────────                                 │
│  ├── accounts_user                  (auth.User extension)                   │
│  ├── accounts_caregivergrant                                                │
│  ├── patient_profile_patientinfo    (flat denorm + details JSONB)           │
│  ├── patient_profile_patientinfoversion  (change audit trail)               │
│  ├── records_healthrecord           (structured records)                    │
│  ├── records_timelineevent          (denorm patient-facing timeline)        │
│  ├── records_labvalue               (time-series labs)                      │
│  ├── records_conflictrecord                                                 │
│  ├── fhir_sync_ehrconnection        (EHR OAuth credentials, encrypted)      │
│  ├── fhir_sync_fhirbundle           (S3 pointer + metadata)                 │
│  ├── fhir_sync_syncjob                                                      │
│  ├── documents_document                                                     │
│  ├── documents_extractionjob                                                │
│  ├── documents_extractedfield                                               │
│  ├── sharing_accessgrant                                                    │
│  ├── sharing_smarthealthlink                                                │
│  ├── audit_auditlog                 (append-only, no updates/deletes)       │
│  ├── trials_trialmatch                                                      │
│  └── notifications_notification                                             │
│                                                                             │
│  omop (analytics — managed via migration scripts, NOT Django ORM)           │
│  ──────────────────────────────────────────────────────────────────         │
│  ├── person                         (linked by healthkey_patient_id)        │
│  ├── condition_occurrence                                                   │
│  ├── drug_exposure                                                          │
│  ├── measurement                    (labs, vitals)                          │
│  ├── observation                    (wearables, performance status)         │
│  ├── procedure_occurrence                                                   │
│  ├── visit_occurrence                                                       │
│  ├── death                                                                  │
│  └── [OMOP Oncology Extension tables]                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Sovereignty: FHIR as Source of Truth

> **Prior learning applied:** `omop-patient-facing` (confidence: 8/10) — OMOP is a research analytics tool, not a patient-facing operational database. Raw FHIR bundles are the source of truth.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATA LAYERS & SOURCE OF TRUTH                           │
│                                                                             │
│  Source of Truth (append-only, immutable)                                   │
│  ─────────────────────────────────────────                                  │
│  S3: encrypted FHIR R4 bundles                                              │
│      └── re-parseable at any time (ETL re-runs don't need re-import)        │
│                                                                             │
│  Operational Store (mutable, Django ORM)                                    │
│  ──────────────────────────────────────                                     │
│  PostgreSQL: healthkey schema                                                │
│      ├── patient_profile_patientinfo  (read/write, patient-facing)          │
│      ├── records_timelineevent        (denorm from FHIR + manual)           │
│      └── records_labvalue            (time-series, queryable)               │
│                                                                             │
│  Analytics Layer (derived, read-only from application)                      │
│  ─────────────────────────────────────────────────────                      │
│  PostgreSQL: omop schema                                                     │
│      ├── Rebuilt by ETL job on PatientInfo change                           │
│      └── Used for: trial matching, CDS, researcher queries                  │
│                                                                             │
│  GDPR Erasure Path (critical — must be designed before schema creation)     │
│  ─────────────────────────────────────────────────────────────────────      │
│  accounts_user.is_deleted = True + pseudonymize person_id in OMOP           │
│  patient_profile_patientinfo → wipe all PHI fields                          │
│  S3 FHIR bundles → delete                                                   │
│  documents → delete                                                         │
│  audit_auditlog → RETAIN for 6 years (HIPAA) but pseudonymize actor/patient │
└─────────────────────────────────────────────────────────────────────────────┘
```

> **Prior learning applied:** `omop-gdpr-erasure` (confidence: 9/10) — must architect person_id pseudonymization before first OMOP table creation. Cascading deletes conflict with HIPAA 6-year audit retention. Resolution: pseudonymize (replace person_id with a hash) rather than delete.

### 4.3 OMOP ETL Consistency

> **Prior learning applied:** `omop-dual-denorm-consistency` (confidence: 9/10) — PatientInfo and timeline_event must be rebuilt in a coordinated job chain, not independent debounced jobs.

```python
# core/omop_etl.py — coordinated rebuild

@app.task(bind=True)
def rebuild_patient_data_chain(self, patient_id: int):
    """
    Chain enforces order: PatientInfo denorm → timeline_event → OMOP domains.
    All three run in sequence in the same Celery chain.
    If any step fails, subsequent steps do not run.
    """
    chain(
        rebuild_patient_info_denorm.s(patient_id),
        rebuild_timeline_events.s(),
        rebuild_omop_domains.s(),
    ).apply_async()
```

### 4.4 PatientInfo `details` JSONB — Schema Validation

The `details` JSONB column holds all disease-conditional clinical fields. A JSON Schema is enforced on write:

```python
# patient_profile/validators.py
PATIENT_INFO_DETAILS_SCHEMA = {
    "type": "object",
    "properties": {
        # Disease-shared fields
        "stage": {"type": "string"},
        "ecogPerformanceStatus": {"type": "number", "minimum": 0, "maximum": 5},
        # Multiple Myeloma
        "clonalPlasmaCells": {"type": "number"},
        "monoclonalProteinSerum": {"type": ["number", "null"]},
        # Breast cancer
        "estrogenReceptorStatus": {"enum": ["negative", "positive", "low", "high", null]},
        # ... all fields from requirements section 2.5
        # Lab values — always store with units
        "hemoglobinLevel": {"type": ["number", "null"]},
        "hemoglobinLevelUnit": {"type": "string", "enum": ["g/dL", "mmol/L"]},
    },
    "additionalProperties": True   # allow future fields without migration
}
```

---

## 5. Security Architecture

### 5.1 Encryption Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENCRYPTION LAYERS                                   │
│                                                                             │
│  Layer 1: Transport (TLS 1.3)                                               │
│  ──────────────────────────                                                 │
│  All traffic client ↔ server via HTTPS/TLS 1.3                              │
│                                                                             │
│  Layer 2: At-Rest Encryption (AES-256-CBC, server key)                      │
│  ─────────────────────────────────────────────────────                      │
│  Postgres column-level: EncryptedCharField, EncryptedTextField (django-pgp) │
│  Applied to: first_name, last_name, dob, EHR OAuth tokens                  │
│  Server manages encryption key (AWS KMS / HashiCorp Vault)                  │
│                                                                             │
│  Layer 3: Zero-Knowledge Sharing Layer (AES-256-GCM, client key)            │
│  ────────────────────────────────────────────────────────────────           │
│  When patient generates a share link:                                       │
│  1. Client generates random AES-256-GCM key                                 │
│  2. Client assembles scoped FHIR bundle                                     │
│  3. Client encrypts bundle with key (Web Crypto API)                        │
│  4. Encrypted bundle sent to server → stored in S3                          │
│  5. Decryption key stored in URL fragment (#key=...) — never sent to server │
│  6. Provider's browser fetches encrypted bundle + decrypts locally          │
│                                                                             │
│  Layer 4: Document Encryption (client-side, before upload)                  │
│  ─────────────────────────────────────────────────────────                  │
│  Client encrypts documents with session key before upload                   │
│  Server stores ciphertext only; AI extraction requires ephemeral key grant  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Authentication Flow

```
Sign Up:
  1. Email + password (bcrypt, PBKDF2 with 600k iterations)
  2. Email verification
  3. TOTP MFA enrollment (required before any health data access)
  4. On first data import: prompt IAL2 (CLEAR / ID.me) — NOT during signup

Sign In:
  1. Email + password
  2. TOTP code (or passkey if enrolled)
  3. JWT access token (15min) + refresh token (7d, httpOnly cookie)
  4. Access token stored in memory (not localStorage)

IAL2 Flow (phased — per learning ial2-conversion-barrier):
  Account creation → MFA → full app access
  IAL2 required only at: first EHR connection, CMS query, or user initiates IAL2 explicitly
  Reason: elderly/oncology patients often can't complete biometric verification immediately
```

### 5.3 HIPAA Compliance Checklist

| Requirement | Implementation |
|---|---|
| Access controls | Role-based: patient, caregiver (view), caregiver (view+add), admin |
| Audit logging | `audit_auditlog` — immutable, 6-year retention (HIPAA §164.312) |
| Encryption at rest | AES-256 column-level + S3 SSE-KMS |
| Encryption in transit | TLS 1.3 only |
| Minimum necessary | Share scopes are explicit; server never returns data outside grant scopes |
| Breach notification | Monitoring via CloudWatch + HIPAA breach response runbook |
| Business Associate Agreements | Required for: AWS, AI extraction vendor, EHR proxy (1upHealth/Particle Health) |

---

## 6. Integration Architecture

### 6.1 FHIR / EHR Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FHIR INTEGRATION PIPELINE                            │
│                                                                             │
│  Patient initiates EHR connection                                           │
│       │                                                                     │
│       ▼                                                                     │
│  SMART on FHIR OAuth 2.0 flow                                               │
│  ├── Redirect to EHR patient portal                                         │
│  ├── Patient authenticates at EHR                                           │
│  ├── Patient approves USCDI v3 scope                                        │
│  └── EHR returns auth code → server exchanges for access + refresh tokens   │
│       │                                                                     │
│       ▼                                                                     │
│  Initial full sync (Celery: fhir_sync queue)                                │
│  ├── Fetch FHIR R4 resources: Patient, Condition, Observation,              │
│  │   MedicationStatement, Procedure, AllergyIntolerance, DiagnosticReport   │
│  ├── Fetch unstructured documents (C-CDA, PDFs, discharge summaries)        │
│  ├── Store raw bundle in S3 (encrypted, per sync timestamp)                 │
│  ├── Map to PatientInfo fields (core/fhir_mapper.py)                        │
│  ├── Detect conflicts with existing manual entries                           │
│  └── Queue OMOP ETL + trial matching                                        │
│       │                                                                     │
│       ▼                                                                     │
│  Scheduled sync (daily minimum, Celery Beat)                                │
│  └── Same pipeline, delta-only if EHR supports If-Modified-Since            │
│                                                                             │
│  Fallback: FHIR proxy (1upHealth / Particle Health)                         │
│  └── Use if Epic App Orchard registration is delayed (4-8 week lead time)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

> **Prior learning applied:** `smart-on-fhir-registration-lead-time` (confidence: 9/10) — Epic App Orchard registration takes 4-8 weeks. Start now. 1upHealth or Particle Health as V1 fallback.

**Supported EHR systems:** Epic, Oracle Cerner, Allscripts, athenahealth, MEDITECH — all support SMART on FHIR R4/USCDI v3.

**CMS Aligned Networks (Kill the Clipboard):** Separate IAL2-gated flow. Patient authenticates with mDL credentials → queries CMS network → retrieves both USCDI structured data and payer claims without knowing provider in advance.

### 6.2 Document Processing Pipeline

```
Patient uploads document (PDF / JPEG / DICOM)
       │
       ├── Client-side: AES-256-GCM encrypt before upload
       │
       ▼
Django /api/v1/documents/upload/
       ├── Store encrypted ciphertext in S3
       ├── Create Document record (mime_type, size, source, linked_step)
       └── Enqueue documents.tasks.process_document
              │
              ├── Decrypt (ephemeral key from session)
              ├── Extract text (pdfminer.six / pytesseract for images)
              ├── Call AI extraction service (OpenAI / Claude API)
              │   └── Structured prompt: extract PatientInfo fields from text
              ├── Store ExtractedField proposals:
              │   {field_name, proposed_value, confidence, source: "llm_extraction"}
              └── Notify patient: "X fields found for review"
                     │
                     ▼
              Patient reviews AI proposals in ExtractionReview.tsx
              └── Accept / Reject per field
                     │
                     ▼
              Accepted fields → PATCH PatientInfo (source: "document_extraction")
              PatientInfoVersion record created (source: "document_extraction")
```

> **Prior learning applied:** `llm-source-trust-in-conflict-ui` (confidence: 9/10) — ExtractedField records must store `source_type: "llm_extraction"` and `confidence_score` so patients can adjudicate correctly in the conflict resolution UI.

### 6.3 SMART Health Links (Sharing)

```
Patient creates share:
  1. Select scopes (Identity / Conditions / Labs / Disease Profile / ...)
  2. Select duration (1h / 24h / 7d / 30d / one-time)
  3. Server creates AccessGrant (token, scopes, expires_at)
  4. Client assembles FHIR R4 bundle from granted scopes
  5. Client encrypts bundle (AES-256-GCM, Web Crypto API)
  6. Encrypted bundle stored in S3
  7. Server creates SMARTHealthLink record (S3 URL, expiry, flags)
  8. Share URL: healthkey.io/r/{token}#key={base64url_key}
     └── Key is in fragment → never sent to server (zero-knowledge)
  9. QR code generated from URL

Provider accesses:
  1. Browser loads /r/{token}
  2. Server validates token (not revoked, not expired) → returns encrypted bundle from S3
  3. Browser extracts key from URL fragment
  4. Browser decrypts bundle locally (Web Crypto API)
  5. ProviderView.tsx renders read-only scoped data
  6. Server logs access in audit_auditlog
```

> **Prior learning applied:** `zero-knowledge-platform-api` (confidence: 9/10) — the sharing layer must use client-side key generation with key in URL fragment. Server-side re-encryption would break zero-knowledge guarantees.

### 6.4 Wearable Integration

- Apple Health: HealthKit framework (mobile only — deferred to mobile app V2)
- Fitbit / Google Fit: OAuth 2.0 API, Celery sync task
- Dexcom (continuous glucose): Dexcom API, push webhook
- Omron / Withings: vendor APIs

Data mapped to `omop.observation` + `omop.measurement` tables.

---

## 7. API Design

### 7.1 Core Endpoints (Django REST Framework)

```
Authentication
  POST   /api/v1/auth/register/
  POST   /api/v1/auth/login/
  POST   /api/v1/auth/mfa/verify/
  POST   /api/v1/auth/token/refresh/
  POST   /api/v1/auth/passkey/register/
  POST   /api/v1/auth/passkey/authenticate/
  DELETE /api/v1/auth/logout/

Patient Profile
  GET    /api/v1/patient-info/user/
  PATCH  /api/v1/patient-info/user/
  GET    /api/v1/patient-info/profile-completeness/
  GET    /api/v1/form-settings/

Health Records
  GET    /api/v1/records/timeline/          ?category=&provider=&from=&to=
  GET    /api/v1/records/labs/              ?field=&from=&to=
  GET    /api/v1/records/conflicts/
  PATCH  /api/v1/records/conflicts/{id}/resolve/

FHIR / EHR
  GET    /api/v1/fhir/connections/
  POST   /api/v1/fhir/connections/
  DELETE /api/v1/fhir/connections/{id}/
  POST   /api/v1/fhir/connections/{id}/sync/
  GET    /api/v1/fhir/connections/{id}/status/

Documents
  POST   /api/v1/documents/upload/          (multipart)
  GET    /api/v1/documents/
  GET    /api/v1/documents/{id}/extractions/
  POST   /api/v1/documents/{id}/extractions/{field_id}/accept/
  POST   /api/v1/documents/{id}/extractions/{field_id}/reject/

Sharing
  GET    /api/v1/sharing/grants/
  POST   /api/v1/sharing/grants/
  DELETE /api/v1/sharing/grants/{id}/       (revoke)
  GET    /api/v1/sharing/grants/{token}/resolve/  (public endpoint, validates token)
  GET    /api/v1/sharing/grants/{token}/bundle/   (returns encrypted bundle ciphertext)
  GET    /api/v1/sharing/audit/

Clinical Trials
  GET    /api/v1/trials/matches/
  GET    /api/v1/trials/matches/{nct_id}/

Notifications
  GET    /api/v1/notifications/preferences/
  PATCH  /api/v1/notifications/preferences/

Caregiver Access
  GET    /api/v1/caregivers/grants/
  POST   /api/v1/caregivers/grants/
  DELETE /api/v1/caregivers/grants/{id}/
```

### 7.2 Response Conventions

```python
# Standard success response
{
    "data": { ... },
    "meta": { "page": 1, "total": 42 }   # for paginated responses
}

# Standard error response
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable message",
        "fields": { "hemoglobinLevel": ["Must be a positive number"] }
    }
}
```

### 7.3 Authentication Scheme

- JWT Bearer tokens (access: 15min, stored in memory; refresh: 7d, httpOnly cookie)
- All patient endpoints: `IsAuthenticated` + `IsOwner` permission
- Share link endpoints (`/r/{token}/*`): `TokenIsValid` permission only (no account required)
- Admin endpoints: `IsAdminUser`

---

## 8. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT DIAGRAM                                   │
│                                                                             │
│  CDN (Cloudflare)                                                           │
│  ├── React SPA static assets (Vite build → S3/CDN)                         │
│  └── Edge caching for /r/{token} public share pages                         │
│                                                                             │
│  Application Layer (Docker containers on ECS / Fly.io / Render)             │
│  ├── Django API (gunicorn, 2-4 workers)                                     │
│  ├── Celery worker: fhir_sync + documents queues                            │
│  ├── Celery worker: omop_etl + trial_matching queues                        │
│  └── Celery beat: scheduled FHIR syncs (daily)                              │
│                                                                             │
│  Data Layer                                                                 │
│  ├── PostgreSQL (RDS / Supabase — HIPAA BAA required)                       │
│  │   ├── healthkey schema (primary, Django ORM)                             │
│  │   └── omop schema (analytics, managed migrations)                        │
│  ├── Redis (ElastiCache / Upstash — Celery broker + cache)                  │
│  └── S3 (AWS S3 / Cloudflare R2 — encrypted FHIR bundles + documents)       │
│                                                                             │
│  External Services                                                          │
│  ├── FHIR proxy: 1upHealth or Particle Health (V1 fallback)                 │
│  ├── AI extraction: OpenAI / Anthropic API (ephemeral, no data retained)    │
│  ├── Identity verification: CLEAR or ID.me (IAL2)                           │
│  ├── Trial matching engine: cancerbot internal API                          │
│  └── Push notifications: APNs + FCM (for mobile V2)                        │
│                                                                             │
│  Observability                                                              │
│  ├── Sentry (error tracking, both frontend + backend)                       │
│  ├── CloudWatch / Datadog (metrics, logs, alerting)                         │
│  └── Django admin + custom health endpoints for Celery queue depth          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Environment variables required:**
```
DATABASE_URL, REDIS_URL, SECRET_KEY
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME
DJANGO_ENCRYPTION_KEY      # AES-256 server key for column encryption (via KMS)
FHIR_PROXY_API_KEY         # 1upHealth / Particle Health
AI_EXTRACTION_API_KEY      # OpenAI / Anthropic
IAL2_PROVIDER_API_KEY      # CLEAR / ID.me
TRIAL_MATCHING_API_URL, TRIAL_MATCHING_API_KEY
SENTRY_DSN
```

---

## 9. Implementation Phases

### Phase 1 — Core Auth + Profile (4–6 weeks)

Priority: get the form working, data stored, basic auth.

| # | Task | Req Coverage |
|---|---|---|
| 1.1 | Django project scaffolding, Docker, CI | — |
| 1.2 | `accounts` app: email/password auth, TOTP MFA, JWT | §1.1 |
| 1.3 | `patient_profile` app: PatientInfo model, PATCH/GET API | §2, §9.2 |
| 1.4 | `form-settings` API: dropdown options for all select fields | §9.2 |
| 1.5 | React onboarding wizard: Demographics → Conditions → Lifestyle → Family | §1.2, §2 |
| 1.6 | Disease Profile step: Multiple Myeloma + Breast Cancer fields | §2.5.1, §2.5.2 |
| 1.7 | Profile completeness scoring | §4.1.2 |
| 1.8 | Dashboard shell: Home + Records tabs | §4 |
| 1.9 | Basic lab values display (no trend charts yet) | §4.2.5 |

**Launch gate:** `accounts` tests, `patient_profile` tests, E2E onboarding flow test.

### Phase 2 — FHIR Integration + Documents (4–6 weeks)

| # | Task | Req Coverage |
|---|---|---|
| 2.1 | SMART on FHIR OAuth + EHR connection management | §3.1 |
| 2.2 | FHIR R4 parser + PatientInfo mapper | §3.1, §9.4 |
| 2.3 | Celery FHIR sync worker | §3.1 |
| 2.4 | Conflict detection + resolution UI | §4.3 |
| 2.5 | Document upload + S3 storage | §3.2 |
| 2.6 | AI document extraction pipeline | §3.2.3, §2.1.11 |
| 2.7 | Lab trend charts (Recharts, time-series + reference ranges) | §4.2.11 |
| 2.8 | OMOP ETL pipeline (coordinated chain) | §8.5 |

**Launch gate:** Epic sandbox FHIR sync test, document extraction accuracy eval, conflict resolution E2E test.

> **Start Epic App Orchard registration in Phase 1.** 4-8 week lead time means if registration starts at Phase 2 kickoff, it won't be approved until Phase 3.

### Phase 3 — Sharing + Trial Matching (3–4 weeks)

| # | Task | Req Coverage |
|---|---|---|
| 3.1 | Access grants + SMART Health Links (zero-knowledge) | §5 |
| 3.2 | QR code generation + ProviderView | §5.2, §5.3 |
| 3.3 | Audit log (immutable, HIPAA-compliant) | §5.4 |
| 3.4 | Trial matching integration (cancerbot API) | §6.1 |
| 3.5 | Trial detail view + notification on new match | §6.1.3, §6.1.4 |
| 3.6 | IAL2 identity verification (CLEAR / ID.me) | §1.1.7 |

### Phase 4 — Polish + Remaining Features (ongoing)

| # | Task | Req Coverage |
|---|---|---|
| 4.1 | Caregiver delegation | §1.3 |
| 4.2 | Wearable integration (Fitbit / Dexcom / Withings) | §3.3 |
| 4.3 | CMS Kill the Clipboard integration | §8.8 |
| 4.4 | Standard-of-care recommendations | §6.2 |
| 4.5 | Research consent management | §5.5 |
| 4.6 | FHIR + OMOP export | §7.5, §7.6 |
| 4.7 | Remaining disease profiles (FL, CLL, Lung, Prostate...) | §2.5.3–2.5.x |

---

## 10. Design Decisions & Trade-offs

### 10.1 `details` JSONB vs. Separate Disease Tables

**Decision:** Store all disease-conditional clinical fields in `PatientInfo.details` JSONB.

**Why:** The schema has 200+ disease-specific fields across 8+ cancer types. Separate tables would require a migration per new field and complex query joins. JSONB with JSON Schema validation gives us schema flexibility without sacrificing data integrity. PostgreSQL JSONB supports indexing on nested keys if needed for querying.

**Trade-off:** Full-text search and complex OMOP joins are harder. Mitigation: OMOP ETL materializes the important fields into typed OMOP tables for analytics.

### 10.2 Zero-Knowledge Sharing Only (Not Full ZK)

**Decision:** Zero-knowledge encryption applies to the sharing layer only. Operational data (PatientInfo) is encrypted at rest with a server-managed key.

**Why:** True zero-knowledge (client holds all keys) makes server-side trial matching, conflict detection, and OMOP ETL impossible — the server can't operate on ciphertext. The sharing layer (SMART Health Links) genuinely needs ZK because the share URL's key fragment never touches the server. For operational data, AES-256 at rest + TLS in transit + HIPAA-compliant infrastructure meets the security requirements.

### 10.3 OMOP as Analytics Layer, Not Primary Store

**Decision:** Raw FHIR bundles are the source of truth (S3). OMOP is a derived analytics layer.

**Why:** PHResolution-style conflict resolution requires preserving the original source claims (Epic says hemoglobin = 10.2, Cerner says 11.1). OMOP's normalized structure loses source provenance. Storing raw bundles lets the ETL be re-run on schema changes without re-importing from providers.

**Trade-off:** OMOP data can be temporarily stale between ETL runs. Mitigation: coordinated job chain rebuilds both PatientInfo and OMOP in sequence, not independently.

### 10.4 IAL2 Phased Verification

**Decision:** IAL2 identity verification required only at first health data import, not at account creation.

**Why:** IAL2 (government ID + biometric) has high friction. Oncology patients are often elderly, post-surgery, or seriously ill. Requiring IAL2 at signup would cause significant drop-off in the most important segment. MFA-enrolled accounts can fully use the app; IAL2 unlocks EHR connection and CMS network queries.

### 10.5 Django + JSONB vs. NoSQL

**Decision:** PostgreSQL + Django ORM, not MongoDB or DynamoDB.

**Why:** OMOP CDM requires a relational store. HIPAA audit logs require ACID transactions. JSONB gives us document flexibility inside Postgres without the operational complexity of a separate document store. Boring technology choice — PostgreSQL has been the right answer for 30 years.

---

## Appendix A — FHIR → PatientInfo Field Mapping

| FHIR Resource | FHIR Field | PatientInfo Field |
|---|---|---|
| `Patient` | `name.given[0]` | `first_name` |
| `Patient` | `name.family` | `last_name` |
| `Patient` | `birthDate` | `dob` |
| `Patient` | `gender` | `gender` |
| `Condition` | `code.coding[SNOMED]` | `details.disease` / `details.preExistingConditionCategories` |
| `Observation` | LOINC 718-7 (hemoglobin) | `details.hemoglobinLevel` |
| `Observation` | LOINC 2160-0 (creatinine) | `details.serumCreatinineLevel` |
| `Observation` | LOINC 33914-3 (eGFR) | `details.estimatedGlomerularFiltrationRate` |
| `Observation` | LOINC 89243-0 (ECOG) | `details.ecogPerformanceStatus` |
| `MedicationStatement` | `medication.coding[RxNorm]` | `details.currentMedications` |
| `AllergyIntolerance` | `reaction.substance.coding` | `details.drugAllergies` |
| `Procedure` | `code.coding[SNOMED]` | `details.surgicalHistory` |
| `MedicationAdministration` | `medication` + `effective` | `details.treatmentLines[]` |

---

## Appendix B — Calculated Field Implementations

| Field | Formula | Trigger |
|---|---|---|
| `bmi` | `weight_kg / (height_m ** 2)` | PatientInfo save (height or weight changed) |
| `estimatedGlomerularFiltrationRate` | CKD-EPI equation: uses `serumCreatinineLevel`, `patientAge`, `gender`, `ethnicity` | PatientInfo save |
| `tnbcStatus` | `True if ER==negative AND PR==negative AND HER2==negative` | PatientInfo save |
| `meetsCRAB` | Calcium > 11.5 OR Creatinine > 2.0 OR Hemoglobin < 10 OR boneLesions == True | PatientInfo save |
| `meetsSLIM` | 60% plasma cells OR FLC ratio > 100 OR MRI bone lesions | PatientInfo save |

All calculated fields stored in `details` JSONB and recomputed server-side on every relevant field change via Django `post_save` signal.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR (main branch, 2026-04-03) | 6 scope proposals, all accepted |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 6 prior learnings applied |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |

**VERDICT:** ENG REVIEW CLEAR — architecture document created. Run `/plan-design-review` to audit UX gaps before implementation begins.
