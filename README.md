# HealthKey

Patient-controlled Personal Health Record. Patient app foundation: Django REST + React.

## Repo layout

```
phr/
├── docs/                          # Specs
│   ├── patient-app-requirements.md
│   ├── patient-app-architecture.md
│   ├── patient-app-design.md
│   └── ...
├── backend/                       # Django 5 + DRF
│   ├── apps/
│   │   ├── accounts/              # Custom user, JWT auth
│   │   └── patient_profile/       # PatientInfo model + REST API
│   ├── config/                    # settings, urls, wsgi
│   └── tests/
└── frontend/                      # Vite + React 18 + TS + shadcn + Tailwind
    └── src/
        ├── components/{ui,healthkey,layout}/
        ├── contexts/              # AuthContext (JWT + React Query)
        ├── features/              # Per-feature API hooks
        └── pages/{auth,onboarding,dashboard}/
```

## Quick start

### Backend (Django + SQLite for dev)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API at http://localhost:8000/api/v1/ — admin at http://localhost:8000/admin/

Run tests:
```bash
pytest
```

### Frontend (Vite dev server)

```bash
cd frontend
npm install
npm run dev
```

App at http://localhost:5173/ — proxies `/api` to http://localhost:8000.

### Both at once with Docker

```bash
cd backend
docker compose up --build
# in another terminal
cd frontend && npm install && npm run dev
```

## What's built (Phase 1)

- Email/password auth with JWT (access in memory, refresh in localStorage)
- Custom User model with `identity_level` field for future MFA/IAL2
- `PatientInfo` model with JSONB `details` for disease-conditional clinical fields
- Server-side calculated fields (BMI on save) and per-category completeness scoring
- Immutable `PatientInfoVersion` audit trail
- Onboarding wizard: Welcome, Demographics, Conditions, Lifestyle, Family, Summary
  - Auto-save on blur, "Skip for now" on every step
  - Cancer diagnosis selector with rose accent (per design system)
  - Family history toggle grid
  - Animated completeness ring on summary
- 4-tab dashboard: Home, Records, Share, Profile
  - Mobile bottom nav, desktop sidebar
- 11 design tokens from `docs/patient-app-design.md` wired into Tailwind
- Accessibility baseline: keyboard nav, focus rings, ARIA labels, skip-to-content link
- 6/6 backend smoke tests passing

## What's deferred (later phases)

| Phase | Feature |
|---|---|
| 1.2 | MFA (TOTP), passkeys, IAL2 verification |
| 2 | FHIR/EHR sync (Epic, Cerner, athena), document upload, AI extraction, conflict resolution UI, OMOP ETL |
| 3 | SMART Health Links, QR codes, access grants, trial matching, lab trend charts |
| 4 | Researcher API, clinician API, anonymization, k-anonymity guard |
| 5 | Caregiver delegation, wearables, CMS Kill the Clipboard, exports |

See `docs/patient-app-architecture.md` §9 for the full phase plan.
