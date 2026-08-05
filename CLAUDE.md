
## Project context

HealthKey PHR portal — the identity provider for the HealthKey service family.
No Firebase: accounts live in this service's Postgres (`accounts_user`), auth is
SimpleJWT (RS256 + JWKS in prod, HS256 dev fallback). Sibling services verify
phr-issued tokens via `GET /api/v1/auth/jwks/` or `POST /api/v1/auth/introspect/`.

- `backend/` — Django 5 + DRF. Apps: `accounts` (user, JWT, JWKS/introspect),
  `patient_profile` (PatientInfo + versions), `health` (probes). Postgres via
  `docker compose up -d db` (host port 5433); tests run on SQLite.
- `frontend/` — Vite + React 19 + Tailwind 4. Portal shell modeled on ht-phr
  (`src/components/layout/`), design tokens from cancerbot ui.v2 in
  `src/index.css`. Backend proxy target: 127.0.0.1:9000.
- Labs features were extracted to the hk-labs service; pre-extraction code is
  on the `archive/*` branches. Git flow is dev → main; never merge archived
  branches back.

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
