# TODO

- [ ] **Deploy hk-labs to GCP AND Render; federate it like promop** ([#42](https://github.com/healthkey-ai/phr/issues/42))
  hk-labs (`../hk-labs`) holds the extracted labs stack (upload pipeline,
  LOINC matching, results UI, `labs_remote` exposing `./LabUploads` /
  `./LabResults`). It deploys to BOTH platforms:
  - **GCP Cloud Run** (existing home): keep/refresh the Cloud Run deploy
    (buckets, Cloud Tasks, LOINC loader job already provisioned via
    ht-phr's Terraform — consider moving that Terraform into
    `hk-labs/infra` for per-repo ownership).
  - **Render** (new, matching the family): Terraform in `hk-labs/infra`
    mirroring phr's — Docker web service (Django + remote at `/remote/`),
    Postgres, **Celery worker + Redis** (async LLM extraction), object
    storage stays external (GCS bucket or R2 — Render has none), and a
    one-off Render job to load the ~120MB LOINC dataset. Reuse the known
    fixes: `npm ci` + Node 24 Dockerfile pattern, vite/rolldown lockfile
    platform pins, migrate as `pre_deploy_command`.
  Shared federation steps (both platforms):
  1. hk-labs: `PhrTokenProvider` (JWKS + introspection against phr);
     `.hk-labs-root` / `--hk-labs-*` CSS namespace already distinct;
     serve `remoteEntry.js` from the web service.
  2. Set `PHR_BASE_URL` + CORS to the phr origin on each deployment.
  3. phr: set `VITE_LABS_REMOTE_URL` / `VITE_LABS_API_URL` in
     `infra/main.tf` (Dockerfile ARGs already declared) to whichever
     deployment phr should consume, re-enable "Upload Lab Reports" (and
     "Lab Results", if not already on promop's) in AppSidebar.

- [ ] **Finish Find Treatments: run soc on Render and turn the menu item on** ([soc#262](https://github.com/healthkey-ai/soc/issues/262))
  The portal side is done and verified locally — `/treatments` renders
  `soc_remote/Recommendations`, the sidebar item enables itself off
  `VITE_SOC_REMOTE_URL`, and patient context comes from promop's
  `/patient-info/me/` projected onto soc's `patient_info` contract.
  soc's own changes are in [soc#263](https://github.com/healthkey-ai/soc/pull/263):
  portal-token auth, the remote built into the image, and a compose web
  service. What is left:
  1. Merge soc#263, then deploy soc so `/remoteEntry.js` is actually served
     — `main` today has no node stage, so a service built from it starts
     fine but serves no remote.
  2. Apply the soc Terraform in `infra/main.tf` (written, **not applied**):
     Render project SOC with a web service and Postgres. No broker — the
     recommend pipeline answers inside the request. Plan was 4 to add, 1 to
     change.
  3. Set `soc_url` to the deployed URL and re-apply, which fills the
     portal's `VITE_SOC_REMOTE_URL` / `VITE_SOC_API_URL` build args, then
     rebuild the portal so they bake in. Until then the menu item stays
     disabled by design.
  4. Add CD so soc autodeploys on merge, matching the other services.
  5. Seed soc's disease catalog on the deployment. Locally the pipeline
     answers `disease_not_found` with an empty catalog — auth and wiring
     are fine, there is simply nothing to recommend from.
  Note the slug divergence handled in `FindTreatmentsPage`: promop emits
  `multiple-myeloma`, soc keys the same disease as `myeloma`, and an
  unmapped slug 404s the recommend lookup.

- [ ] **Multi-installation identity: promop as identity host (see docs/identity-architecture.md)** ([#43](https://github.com/healthkey-ai/phr/issues/43))
  Decisions made 2026-08-06: family auth API contract (phr's endpoint
  shapes) implementable by any identity host; iss = installation origin;
  1 branded install = 1 promop Organization; embedded login form primary,
  OIDC SSO via promop's /o/ optional. Build order:
  1. promop: enable OIDC issuance (OIDC_RSA_PRIVATE_KEY/ISS_ENDPOINT +
     claims validator) — JWKS is already routed, just keyless.
  2. promop: contract endpoints (login/refresh/logout/jwks/introspect,
     org-scoped, RS256).
  3. Services: trusted-issuer registry (generalize PhrTokenProvider in
     promop + hk-labs); phr installs set JWT_ISSUER to their origin.
  4. promop: per-org branding + redirect allow-list + per-brand
     APP_BASE_URL emails; canonical email-resolution rule; tighten
     CsrfExemptSessionAuthentication.

- [ ] **Turn off `DEBUG` on promop staging and production** ([#44](https://github.com/healthkey-ai/phr/issues/44))
  Both Render services still run with `DEBUG=True` (Django debug pages +
  allow-all CORS on a live clinical app). Flipping it requires setting
  `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and a real `FIREBASE_PROJECT_ID`
  (the DEBUG defaults currently paper over all three), and keeping the
  explicit `CORS_ALLOWED_ORIGINS` (already set on staging).

## Done

- [x] Lab Results served from promop's federated remote (#41 / PR #46) —
  menu item enabled, verified live on phr-ipyr; review hardening included
  (person-provisioning warm-up, URL-encoded concept codes, back-nav and
  scroll-restore fixes, recharts unshared).
- [x] Local `patient_profile` app removed — the federated promop PatientInfo
  is the single patient-data store; registration no longer creates local
  profile rows and `/api/v1/profile/` is gone.
- [x] promop-staging wired to phr (`PHR_BASE_URL` + CORS set, promop PR #388
  merged, remote served at `/remote/remoteEntry.js`, phr tokens verified via
  deployed JWKS).
- [x] Federated-remote origins baked into the deployed phr SPA (Dockerfile
  ARGs + `infra/main.tf` env vars); Health Profile verified live on
  phr-ipyr.onrender.com rendering promop-staging's PatientInfo.
