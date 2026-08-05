# HealthKey PHR Portal

Patient-controlled Personal Health Record portal — Django 5 + DRF backend,
React 19 + Vite + Tailwind 4 frontend, styled with the cancerbot ui.v2 design
system (Manrope, HealthKey blue).

**phr is the identity provider for the HealthKey service family.** User
accounts live in this service's Postgres. Sibling services (hk-labs,
importers, …) authenticate requests with phr-issued JWTs:

- **RS256 + JWKS (production):** set the `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`
  PEM pair; siblings fetch `GET /api/v1/auth/jwks/` once and verify tokens
  offline. Tokens carry `user_id`, `email`, `identity_level`, and role
  `claims`.
- **Introspection (dev / revocation-aware):** `POST /api/v1/auth/introspect/`
  with `{"token": "..."}` returns RFC 7662-shaped `{"active": true, ...}`.

## Repo layout

```
phr/
├── backend/                 # Django 5 + DRF
│   ├── apps/
│   │   ├── accounts/        # Email-first User, JWT, JWKS + introspection, roles
│   │   ├── patient_profile/ # Onboarding state + JSONB health details
│   │   └── health/          # Health check
│   ├── config/              # settings, urls, wsgi
│   └── tests/
├── frontend/                # Vite + React 19 + TS + Tailwind 4
│   └── src/
│       ├── components/      # layout (sidebar/header shells), ui (shadcn), guards
│       ├── contexts/        # AuthContext (JWT session)
│       ├── pages/           # auth, dashboard, profile, labs (federated), admin
│       └── lib/             # authStore (access in memory, refresh in localStorage)
└── Dockerfile               # single container: Django serves API + built SPA
```

## Quick start

### Database — locally running Postgres (no Docker)

```bash
psql -d postgres -c "CREATE ROLE phr LOGIN PASSWORD 'phr_dev_password' CREATEDB"
createdb -O phr phr
```

### Backend

```bash
cd backend
cp .env.example .env        # DATABASE_URL points at local Postgres
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:9000
```

API at http://127.0.0.1:9000/api/v1/ — admin at http://127.0.0.1:9000/admin/

Tests: `.venv/bin/python -m pytest`

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

App at http://localhost:5173/ — proxies `/api` to the backend.

## Auth endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register/` | Create account (+ empty profile), returns user + token pair |
| `POST /api/v1/auth/login/` | Email/password → access + refresh JWT |
| `POST /api/v1/auth/refresh/` | Rotate refresh → new pair (old refresh blacklisted) |
| `POST /api/v1/auth/logout/` | Blacklist a refresh token |
| `GET /api/v1/auth/me/` | Current user |
| `GET /api/v1/auth/jwks/` | Public keys for offline RS256 verification |
| `POST /api/v1/auth/introspect/` | Token introspection (service-to-service) |
| `GET /api/v1/auth/admins/` | Role overview (ADMIN only) |
| `POST /api/v1/auth/set-claims/` | Grant/revoke ADMIN / MEDICAL_RECORDS (ADMIN only) |

## Federated labs

The portal is a Module Federation host (`phr_host`). `/labs/uploads` and
`/labs/results` mount components from the hk-labs service (`labs_remote`,
`VITE_LABS_REMOTE_URL`), passing a pre-authenticated axios client that
carries the phr JWT. When the remote is down the pages degrade gracefully.

Pre-rebuild history (previous portal + labs pipeline) lives on the
`archive/dev-2026-08-05` and `archive/main-2026-08-05` branches.
