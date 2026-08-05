# hk-labs Service Extraction Plan

Extract all labs-related code from `phr` into a standalone service at `../hk-labs`.
The new service owns lab uploads, LOINC matching, lab results CRUD, and the
federated frontend components. The `phr` app keeps patient profile, onboarding,
and health checks — it becomes a pure consumer of the labs federation remote.

---

## 1. Target Repository Layout

```
hk-labs/
├── frontend/                          # Vite + React 19 + MF remote
│   ├── src/
│   │   ├── main.tsx                   # Standalone app entry
│   │   ├── App.tsx                    # Routes: /, /sign-in, /sign-up, /dashboard/*
│   │   ├── types/
│   │   │   └── labs.ts                # ← from phr/frontend/src/types/labs.ts
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx        # ← from phr (adapted for hk-labs API base)
│   │   ├── lib/
│   │   │   ├── api.ts                 # ← from phr (Axios + JWT interceptor)
│   │   │   ├── auth.ts               # ← from phr (token store)
│   │   │   ├── queryClient.ts        # ← from phr
│   │   │   └── utils.ts              # ← from phr
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   │   ├── SignIn.tsx         # ← from phr
│   │   │   │   └── SignUp.tsx         # ← from phr
│   │   │   └── dashboard/
│   │   │       ├── Home.tsx           # New: labs-only dashboard (uploads + results)
│   │   │       └── LabTrendDetail.tsx # ← from phr
│   │   ├── components/
│   │   │   ├── ui/                    # ← from phr (shadcn/ui components used by labs)
│   │   │   ├── layout/
│   │   │   │   └── DashboardShell.tsx # Simplified: labs-only nav
│   │   │   └── labs/                  # ← from phr/frontend/src/components/labs/
│   │   │       ├── LabUploadDialog.tsx
│   │   │       ├── LabUploadReview.tsx
│   │   │       ├── LabManualEntryDialog.tsx
│   │   │       ├── LabValueCard.tsx
│   │   │       ├── LabTrendChart.tsx
│   │   │       ├── FileSourceBadge.tsx
│   │   │       └── RecordsChangeLog.tsx
│   │   ├── features/
│   │   │   └── labs/
│   │   │       └── api.ts             # ← from phr (React Query hooks)
│   │   └── federation/                # ← from phr/frontend/src/federation/ (unchanged)
│   │       ├── LabUploads.tsx
│   │       ├── LabResults.tsx
│   │       ├── LabsProvider.tsx
│   │       ├── LabsContext.tsx
│   │       ├── types.ts
│   │       ├── hooks.ts
│   │       ├── assertLabsTokens.ts
│   │       ├── injectStyles.ts
│   │       ├── labs.css
│   │       ├── dev-harness.tsx
│   │       └── README.md
│   ├── vite.config.ts                 # ← from phr (MF config, name stays "labs_remote")
│   ├── vite.remote.config.ts          # ← from phr
│   ├── package.json                   # Subset: React, RQ, Axios, Recharts, Radix, MF, Tailwind
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── index.html
│
├── backend/                           # Django 5 + DRF + Celery
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py                # Trimmed: only accounts + labs apps
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py                    # /api/v1/auth/*, /api/v1/labs/*, /health-check/
│   │   ├── celery.py                  # ← from phr
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── accounts/                  # ← from phr/backend/apps/accounts/ (full copy)
│   │   │   ├── models.py             # User model (email, firebase_uid, identity_level)
│   │   │   ├── views.py              # login, register, partner-token, me
│   │   │   ├── serializers.py
│   │   │   ├── partner_auth.py       # DRF auth backend for partner tokens
│   │   │   ├── providers/
│   │   │   │   ├── base.py           # TokenProvider ABC
│   │   │   │   ├── firebase.py       # FirebaseTokenProvider
│   │   │   │   ├── jwt_provider.py   # JwtTokenProvider
│   │   │   │   └── registry.py       # Provider registry
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── migrations/           # Fresh squash (new DB)
│   │   ├── labs/                      # ← from phr/backend/apps/labs/ (full copy)
│   │   │   ├── models.py             # LoincEntry, LoincAlias, LabTestEntry, LabValue, Upload*
│   │   │   ├── views.py              # CatalogView, LabValueViewSet, UploadJobViewSet
│   │   │   ├── serializers.py
│   │   │   ├── matching.py           # Tier 0/1 LOINC matching
│   │   │   ├── normalize.py          # Text normalization
│   │   │   ├── unit_converter.py     # Unit conversion
│   │   │   ├── unit_family.py        # Unit family classification
│   │   │   ├── tasks.py              # Celery: process_lab_upload
│   │   │   ├── signals.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── parsers/
│   │   │   │   ├── pdf_rasteriser.py
│   │   │   │   ├── llm_parser.py
│   │   │   │   └── prompts/
│   │   │   ├── alias_rules/
│   │   │   │   ├── egfr.py
│   │   │   │   └── __init__.py
│   │   │   ├── data/
│   │   │   │   └── loinc_common.json
│   │   │   ├── fixtures/
│   │   │   │   └── curated_loinc_aliases.json
│   │   │   ├── management/commands/
│   │   │   │   ├── loinc_reset.py
│   │   │   │   ├── sync_loinc_csv.py
│   │   │   │   ├── curate_loinc_aliases.py
│   │   │   │   ├── prepare_alias_audit.py
│   │   │   │   ├── pack_loinc_bundle.py
│   │   │   │   ├── fix_stale_units.py
│   │   │   │   └── reset_stuck_uploads.py
│   │   │   ├── tests/                # ← all from phr
│   │   │   └── migrations/           # Fresh squash
│   │   └── health/                    # ← from phr/backend/apps/health/
│   │       ├── views.py
│   │       └── urls.py
│   ├── requirements.txt               # ← from phr (no patient_profile deps)
│   ├── pytest.ini
│   ├── manage.py
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── loinc-codes-aliases/               # ← from phr/loinc-codes-aliases/ (full copy)
│   ├── Loinc.csv                     # ~78 MB official LOINC CSV
│   ├── LoincClass.csv
│   ├── curated_loinc_aliases.json    # ~37 MB curated aliases
│   └── VERSION
│
├── samples/                           # ← from phr/samples/ (test PDFs)
├── docs/                              # Labs-specific docs
│   ├── loinc-data-pipeline.md        # ← from phr/docs/
│   ├── loinc-matcher.md              # ← from phr/docs/
│   ├── module-federation-plan.md     # ← from phr/docs/ (updated)
│   ├── css-federation-fix-plan.md    # ← from phr/docs/
│   └── lab-upload-design.md          # ← from phr/docs/patient-app-lab-upload-design.md
│
├── .claude/                           # Claude Code config
│   └── skills/
│       └── curate-loinc-aliases/     # ← from phr/backend/.claude/skills/
│           └── SKILL.md
├── render.yaml                        # Deployment config (separate service)
├── CLAUDE.md
├── CHANGELOG.md
└── README.md
```

---

## 2. What Moves

### 2.1 Backend (Django)

| Source (phr)                               | Destination (hk-labs)                      | Notes                                       |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------- |
| `backend/apps/labs/`                       | `backend/apps/labs/`                       | Full copy — models, views, matching, parsers, tasks, management commands, tests |
| `backend/apps/accounts/`                   | `backend/apps/accounts/`                   | Full copy — User model, auth views, partner_auth, providers/ |
| `backend/apps/health/`                     | `backend/apps/health/`                     | Full copy — health check endpoint           |
| `backend/config/settings/`                 | `backend/config/settings/`                 | Trimmed: remove `apps.patient_profile` from INSTALLED_APPS, remove PatientInfo import from RegisterView |
| `backend/config/urls.py`                   | `backend/config/urls.py`                   | Remove patient_profile URL include          |
| `backend/config/celery.py`                 | `backend/config/celery.py`                 | Identical                                   |
| `backend/requirements.txt`                 | `backend/requirements.txt`                 | Identical (patient_profile has no extra deps) |
| `backend/Dockerfile`                       | `backend/Dockerfile`                       | Identical                                   |
| `backend/docker-compose.yml`               | `backend/docker-compose.yml`               | Identical                                   |
| `backend/pytest.ini`                       | `backend/pytest.ini`                       | Identical                                   |
| `loinc-codes-aliases/`                     | `loinc-codes-aliases/`                     | Full copy — LOINC CSV + curated aliases     |
| `samples/`                                 | `samples/`                                 | Full copy — test PDFs                       |

**Changes needed after copy:**
1. `config/settings/base.py`: Remove `apps.patient_profile` from `INSTALLED_APPS`
2. `config/urls.py`: Remove `path("api/v1/", include("apps.patient_profile.urls"))`
3. `accounts/views.py` → `RegisterView.create()`: Remove the auto-create `PatientInfo` block (lines 42-43). Registration creates a user only — no patient profile in hk-labs.
4. Fresh migrations: `makemigrations accounts labs` from scratch (new DB, no need for migration history)

### 2.2 Frontend (React)

| Source (phr)                               | Destination (hk-labs)                      | Notes                                       |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------- |
| `frontend/src/federation/`                | `frontend/src/federation/`                | Full copy — unchanged, still exposes `./LabUploads`, `./LabResults`, `./types` |
| `frontend/src/components/labs/`           | `frontend/src/components/labs/`           | Full copy                                   |
| `frontend/src/features/labs/api.ts`       | `frontend/src/features/labs/api.ts`       | Full copy                                   |
| `frontend/src/types/labs.ts`              | `frontend/src/types/labs.ts`              | Full copy                                   |
| `frontend/src/contexts/AuthContext.tsx`   | `frontend/src/contexts/AuthContext.tsx`   | Copy + adapt: remove PatientInfo references  |
| `frontend/src/lib/auth.ts`               | `frontend/src/lib/auth.ts`               | Full copy                                   |
| `frontend/src/lib/api.ts`                | `frontend/src/lib/api.ts`                | Full copy                                   |
| `frontend/src/lib/queryClient.ts`        | `frontend/src/lib/queryClient.ts`        | Full copy                                   |
| `frontend/src/lib/utils.ts`              | `frontend/src/lib/utils.ts`              | Full copy                                   |
| `frontend/src/pages/auth/SignIn.tsx`      | `frontend/src/pages/auth/SignIn.tsx`      | Full copy                                   |
| `frontend/src/pages/auth/SignUp.tsx`      | `frontend/src/pages/auth/SignUp.tsx`      | Full copy                                   |
| `frontend/src/pages/dashboard/LabTrendDetail.tsx` | `frontend/src/pages/dashboard/LabTrendDetail.tsx` | Full copy               |
| `frontend/src/components/ui/*`            | `frontend/src/components/ui/*`            | Copy only shadcn components used by labs     |
| `frontend/vite.config.ts`                | `frontend/vite.config.ts`                | Copy — MF config stays the same              |
| `frontend/vite.remote.config.ts`         | `frontend/vite.remote.config.ts`         | Copy                                        |

**New files to create:**
1. `frontend/src/App.tsx` — Labs-only routing: `/sign-in`, `/sign-up`, `/dashboard` (labs home), `/dashboard/labs/:abbreviation` (trend detail)
2. `frontend/src/pages/dashboard/Home.tsx` — Combines `<LabUploads />` and `<LabResults />` on a single dashboard page (replaces the phr Records page which also shows patient profile)
3. `frontend/src/components/layout/DashboardShell.tsx` — Simplified: no onboarding, no patient profile nav items

### 2.3 Docs

| Source (phr)                               | Destination (hk-labs)                      |
| ------------------------------------------ | ------------------------------------------ |
| `docs/loinc-data-pipeline.md`             | `docs/loinc-data-pipeline.md`             |
| `docs/loinc-matcher.md`                   | `docs/loinc-matcher.md`                   |
| `docs/module-federation-plan.md`          | `docs/module-federation-plan.md`          |
| `docs/css-federation-fix-plan.md`         | `docs/css-federation-fix-plan.md`         |
| `docs/patient-app-lab-upload-design.md`   | `docs/lab-upload-design.md`               |

### 2.4 Claude Code Config

| Source (phr)                                       | Destination (hk-labs)                     |
| -------------------------------------------------- | ----------------------------------------- |
| `backend/.claude/skills/curate-loinc-aliases/`    | `.claude/skills/curate-loinc-aliases/`   |

---

## 3. What Stays in phr

After extraction, `phr` retains:
- `backend/apps/patient_profile/` — patient onboarding, demographics, conditions, etc.
- `backend/apps/accounts/` — **kept as-is** (phr still needs its own auth)
- `backend/apps/health/` — health check
- `frontend/src/pages/onboarding/` — Welcome, Demographics, Conditions, Lifestyle, Family, Summary
- `frontend/src/pages/dashboard/Home.tsx` — phr home (profile overview)
- `frontend/src/pages/dashboard/Profile.tsx`
- `frontend/src/pages/dashboard/Share.tsx`
- `frontend/src/components/healthkey/` — ThreeModeInput, DataSourceBadge, etc.

**phr becomes a host-only consumer of hk-labs:**
- Mounts `<LabUploads />` and `<LabResults />` via Module Federation
- Gets federation remote from hk-labs at runtime (no code dependency)
- Uses `LabsProvider` with its own Axios instance pointed at hk-labs backend

---

## 4. What Changes in phr (Post-Extraction)

### 4.1 Remove Labs Code

Delete from phr after confirming hk-labs works:
- `frontend/src/components/labs/` (entire directory)
- `frontend/src/features/labs/` (entire directory)
- `frontend/src/types/labs.ts`
- `frontend/src/federation/` (entire directory — now lives in hk-labs)
- `frontend/src/pages/dashboard/LabTrendDetail.tsx`
- `backend/apps/labs/` (entire directory)
- `loinc-codes-aliases/` (entire directory)
- `samples/` (entire directory)
- `docs/loinc-*.md`, `docs/css-federation-fix-plan.md`, `docs/patient-app-lab-upload-design.md`
- Module Federation plugin from `vite.config.ts`

### 4.2 Update phr to Consume hk-labs as Federation Remote

**Frontend changes:**
- `vite.config.ts`: Remove `federation()` plugin config (phr is now host-only, remote comes from ht-phr host or loads hk-labs directly)
- `package.json`: Remove `@module-federation/vite`, `@module-federation/runtime`
- `pages/dashboard/Records.tsx`: Import `LabUploads`, `LabResults` from the hk-labs federation remote via `@module-federation/runtime`

**Backend changes:**
- `config/settings/base.py`: Remove `apps.labs` from INSTALLED_APPS, remove LAB_UPLOAD_* settings, remove LLM settings
- `config/urls.py`: Remove `path("api/v1/labs/", ...)`
- `requirements.txt`: Remove `anthropic`, `openai`, `pymupdf`, `Pint`, `ucumvert` (labs-only deps)

### 4.3 phr ↔ hk-labs Integration

phr's frontend talks to the hk-labs backend directly (separate origin).
Auth flow when accessed through phr:
1. User logs in to phr (gets phr JWT)
2. phr frontend calls hk-labs `/auth/partner-token/` with Firebase token (if using Firebase) or creates a session via email/password on hk-labs directly
3. hk-labs returns its own JWT
4. phr creates an Axios instance with hk-labs JWT, passes to `<LabUploads apiClient={labsClient} />`

When hk-labs runs standalone:
1. User signs up / signs in directly on hk-labs
2. Gets hk-labs JWT
3. Uses labs dashboard normally

---

## 5. Execution Steps

### Phase 1: Scaffold hk-labs (no code removal from phr yet)

1. **Backend scaffold**
   - Copy `backend/apps/accounts/` → hk-labs
   - Copy `backend/apps/labs/` → hk-labs
   - Copy `backend/apps/health/` → hk-labs
   - Copy `backend/config/` → hk-labs
   - Trim: remove patient_profile from settings, urls, RegisterView
   - Copy `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `manage.py`, `pytest.ini`
   - Run `makemigrations` to generate fresh migrations

2. **Frontend scaffold**
   - Copy `frontend/src/federation/` → hk-labs
   - Copy `frontend/src/components/labs/` → hk-labs
   - Copy `frontend/src/features/labs/` → hk-labs
   - Copy `frontend/src/types/labs.ts` → hk-labs
   - Copy auth files: `AuthContext.tsx`, `auth.ts`, `api.ts`, `queryClient.ts`, `utils.ts`
   - Copy auth pages: `SignIn.tsx`, `SignUp.tsx`
   - Copy `LabTrendDetail.tsx`
   - Copy needed `components/ui/` (button, dialog, input, label, progress, select, checkbox)
   - Copy vite configs, tailwind config, tsconfig
   - Create new: `App.tsx`, `main.tsx`, dashboard `Home.tsx`, simplified `DashboardShell.tsx`
   - Create `package.json` with subset of phr deps

3. **Data & docs**
   - Copy `loinc-codes-aliases/` → hk-labs
   - Copy `samples/` → hk-labs
   - Copy relevant docs → hk-labs/docs/
   - Copy `curate-loinc-aliases` skill → hk-labs/.claude/

4. **Verify hk-labs standalone**
   - Backend: `python manage.py migrate && python manage.py test`
   - Frontend: `npm install && npm run dev` → sign up, upload, view results
   - Federation: `npm run dev:remote` → confirm `remoteEntry.js` serves

### Phase 2: Wire phr as consumer (parallel, non-breaking)

5. **Update ht-phr host** (at `../ht-phr`)
   - Point Module Federation remote URL to hk-labs dev server (port 5174)
   - Mount `<LabUploads />` and `<LabResults />` in Records page
   - Implement token exchange: Firebase token → hk-labs `/auth/partner-token/`

### Phase 3: Clean up phr (after hk-labs is confirmed working)

6. **Remove labs code from phr**
   - Delete `frontend/src/federation/`, `frontend/src/components/labs/`, `frontend/src/features/labs/`, `frontend/src/types/labs.ts`
   - Delete `backend/apps/labs/`, `loinc-codes-aliases/`, `samples/`
   - Remove MF plugin from `vite.config.ts`
   - Remove labs-only Python deps from `requirements.txt`
   - Remove labs settings from `config/settings/base.py`
   - Remove labs URLs from `config/urls.py`
   - Delete labs docs from `docs/`
   - Run phr tests to confirm nothing broke

---

## 6. Auth Architecture in hk-labs

hk-labs supports two auth modes:

### Standalone Mode
User signs up / signs in on hk-labs directly → gets hk-labs JWT → full access.

### Federated Mode (consumed by ht-phr or other hosts)
1. Host app has its own auth (Firebase, Auth0, etc.)
2. Host calls `POST /api/v1/auth/partner-token/` with host's token
3. hk-labs verifies via pluggable provider (FirebaseTokenProvider, etc.)
4. hk-labs finds or creates a linked user (via `firebase_uid` or email match)
5. Returns hk-labs JWT pair (access + refresh)
6. Host creates Axios instance with hk-labs tokens
7. Host mounts federated component: `<LabUploads apiClient={labsClient} />`

The pluggable `PARTNER_AUTH_PROVIDERS` system already supports this — no new code needed.

---

## 7. Database

hk-labs gets its own database. Tables:

**accounts:**
- `accounts_user` — email, firebase_uid, identity_level, mfa_enabled

**labs:**
- `labs_loincentry` — ~60k LOINC codes
- `labs_loincalias` — ~190k searchable aliases
- `labs_labtestentry` — test identity + display metadata
- `labs_labvalue` — individual lab results (FK to user)
- `labs_uploadjob` — upload sessions
- `labs_uploadfile` — files within uploads

No shared tables with phr. Users exist independently in each service's DB — linked by `firebase_uid` when accessed via federation, or by email when the same person signs up on both.

---

## 8. Deployment

hk-labs deploys as a separate service:
- **Backend**: Django on Render (or similar) — own web + worker (Celery)
- **Frontend**: Vite build → static hosting (Vercel / Render static / S3+CF)
- **Federation remote**: `remoteEntry.js` served from frontend static host, consumed by ht-phr at runtime
- **Database**: Separate PostgreSQL instance
- **Redis**: Separate Redis for Celery broker
- **Storage**: Own GCS/S3 bucket for lab file uploads

`render.yaml` in hk-labs defines the full stack.

---

## 9. Risk & Decisions

| Risk | Mitigation |
|------|------------|
| User data split across two DBs | Users are linked by firebase_uid or email. Lab data lives in hk-labs, patient profile in phr. No cross-DB joins needed — the host app fetches each independently. |
| LOINC data duplication (120 MB) | Acceptable. hk-labs is the canonical owner. phr stops carrying LOINC data after Phase 3. |
| Auth duplication (accounts app in both repos) | Necessary — each service needs its own User model and JWT issuance. Could extract into a shared library later, but premature now. |
| MF remote URL changes per environment | Already handled by ht-phr's env config. hk-labs just serves `remoteEntry.js` at a known URL. |
| Breaking phr during extraction | Phase 1 is additive (copy, don't move). Phase 3 cleanup only happens after hk-labs is verified. phr continues working throughout. |

---

## 10. Dependency Inventory

### Python (backend/requirements.txt)

All phr Python deps are needed by hk-labs except the ones used exclusively by patient_profile (there are none — patient_profile uses only Django core). So `requirements.txt` is identical.

### Node (frontend/package.json)

hk-labs needs:
- `react`, `react-dom` (19.x)
- `react-router-dom` (routing)
- `@tanstack/react-query` (server state)
- `axios` (HTTP client)
- `react-hook-form`, `zod` (forms)
- `recharts` (trend charts)
- `@radix-ui/react-checkbox`, `@radix-ui/react-dialog`, `@radix-ui/react-label`, `@radix-ui/react-progress`, `@radix-ui/react-select` (UI primitives)
- `lucide-react` (icons)
- `@module-federation/vite`, `@module-federation/runtime` (federation)
- `tailwindcss`, `@tailwindcss/vite` (styling)
- `vite`, `typescript`, `@vitejs/plugin-react` (build)

Does NOT need:
- `@radix-ui/react-slot` (only used by healthkey components in phr)
- Any onboarding-specific deps (there are none)
