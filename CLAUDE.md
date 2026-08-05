## Project context

HealthKey PHR portal — the identity provider for the HealthKey service family.
Accounts live in this service's locally-run Postgres (`accounts_user`, role/db
`phr` on 127.0.0.1:5432), auth is SimpleJWT (RS256 + JWKS in prod, HS256 dev
fallback). Sibling services verify phr-issued tokens via
`GET /api/v1/auth/jwks/` or `POST /api/v1/auth/introspect/`.

- `backend/` — Django 5 + DRF. Apps: `accounts` (email-first user, JWT,
  JWKS/introspection, ADMIN/MEDICAL_RECORDS roles), `patient_profile`
  (onboarding state + JSONB details), `health`. Run on 127.0.0.1:9000.
- `frontend/` — Vite + React 19 + Tailwind 4, Module Federation host
  (`phr_host`) consuming hk-labs' `labs_remote`. Design system: cancerbot
  ui.v2 palette (Manrope, HealthKey blue #0B4A9D) in `src/index.css`,
  variable-driven dark mode. Auth: access token in memory, refresh in
  localStorage (`src/lib/authStore.ts`).
- Git flow is dev → main; `archive/*` branches hold retired code — never
  merge them back.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
