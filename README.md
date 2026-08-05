# HealthKey PHR Portal

Patient-controlled Personal Health Record portal — Django REST + React. Modeled
on the ht-phr host app, styled with the cancerbot (`ui.v2`) design system.

**phr is the identity provider for the HealthKey service family.** User accounts
live in this service's Postgres; there is no Firebase anywhere. Sibling services
(hk-labs, fhir importers, …) authenticate requests against phr-issued JWTs:

- **RS256 + JWKS (preferred in prod):** set the `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`
  PEM pair; siblings fetch `GET /api/v1/auth/jwks/` once and verify tokens
  offline. Tokens carry `user_id`, `email`, and `identity_level` claims.
- **Introspection (dev fallback / revocation-aware):** `POST /api/v1/auth/introspect/`
  with `{"token": "..."}` returns RFC 7662-shaped `{"active": true, ...claims}`.

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
│   │   ├── accounts/              # Custom user, JWT auth, JWKS + introspection
│   │   ├── patient_profile/       # PatientInfo model + REST API
│   │   └── health/                # Liveness + readiness probes
│   ├── config/                    # settings, urls, wsgi
│   └── tests/
└── frontend/                      # Vite + React 19 + TS + shadcn + Tailwind 4
    └── src/
        ├── components/{ui,healthkey,layout}/   # layout = portal shell (sidebar/header)
        ├── contexts/              # AuthContext (JWT + React Query)
        ├── features/              # Per-feature API hooks
        └── pages/{auth,onboarding,dashboard}/
```

## Quick start

### Database (Postgres via Docker)

```bash
cd backend
docker compose up -d db     # Postgres 16 on host port 5433
```

`backend/.env` defaults `DATABASE_URL` to this instance. Without the env var,
Django falls back to SQLite (tests use that).

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:9000
```

API at http://127.0.0.1:9000/api/v1/ — admin at http://127.0.0.1:9000/admin/

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

App at http://localhost:5173/ — proxies `/api` to `VITE_API_PROXY_TARGET`
(default in `frontend/.env`: http://127.0.0.1:9000).

## Auth endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register/` | Create account (+ empty PatientInfo), returns user + token pair |
| `POST /api/v1/auth/login/` | Email/password → access + refresh JWT |
| `POST /api/v1/auth/token/refresh/` | Rotate refresh → new pair (old refresh blacklisted) |
| `POST /api/v1/auth/logout/` | Blacklist a refresh token |
| `GET /api/v1/auth/me/` | Current user |
| `GET /api/v1/auth/jwks/` | Public keys for offline RS256 verification (service-to-service) |
| `POST /api/v1/auth/introspect/` | Token introspection (service-to-service) |

## What's built

- Email/password auth with JWT (access in memory, refresh in localStorage),
  refresh rotation + blacklist, cross-service claims (`email`, `identity_level`)
- RS256/JWKS + introspection so sibling services auth against phr accounts
- Custom User model with `identity_level` field for future MFA/IAL2
- `PatientInfo` model with JSONB `details` for disease-conditional clinical fields
- Server-side calculated fields (BMI on save) and per-category completeness scoring
- Immutable `PatientInfoVersion` audit trail
- Onboarding wizard: Welcome, Demographics, Conditions, Lifestyle, Family, Summary
- Portal shell modeled on ht-phr: grouped sidebar (Overview / My Health / Account),
  header with identity + sign-out, mobile drawer
- cancerbot ui.v2 design system: Manrope, brand blue ramp, semantic
  success/warning/error scales, OS-driven dark mode via CSS variable swap
- Accessibility baseline: keyboard nav, focus rings, ARIA labels, skip-to-content link

Lab uploads/results/trends live in the separate **hk-labs** service (see
`archive/*` branches for the pre-extraction code). The portal will consume it
as a federated remote once hk-labs verifies phr tokens.

## What's deferred (later phases)

| Phase | Feature |
|---|---|
| 1.2 | MFA (TOTP), passkeys, IAL2 verification |
| 2 | FHIR/EHR sync (Epic, Cerner, athena), document upload, conflict resolution UI |
| 3 | SMART Health Links, QR codes, access grants, trial matching, labs federation |
| 4 | Researcher API, clinician API, anonymization, k-anonymity guard |
| 5 | Caregiver delegation, wearables, exports |

See `docs/patient-app-architecture.md` §9 for the full phase plan.
