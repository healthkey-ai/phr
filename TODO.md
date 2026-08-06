# TODO

- [ ] **Quick win: serve Lab Results from promop's remote (no new deploys)**
  promop's deployed remote already exposes `./LabResults` (backed by its
  OMOP measurements) on the same `remoteEntry.js` phr loads for the
  Health Profile. Point the Lab Results pages at
  `labs_results_remote/LabResults` with `usePromopApi`, re-enable the
  "Lab Results" menu item, verify on phr-ipyr. ~1 hour; uploads still
  wait for hk-labs below.

- [ ] **Deploy hk-labs to GCP AND Render; federate it like promop**
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

- [ ] **Turn off `DEBUG` on promop staging and production**
  Both Render services still run with `DEBUG=True` (Django debug pages +
  allow-all CORS on a live clinical app). Flipping it requires setting
  `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and a real `FIREBASE_PROJECT_ID`
  (the DEBUG defaults currently paper over all three), and keeping the
  explicit `CORS_ALLOWED_ORIGINS` (already set on staging).

## Done

- [x] Local `patient_profile` app removed — the federated promop PatientInfo
  is the single patient-data store; registration no longer creates local
  profile rows and `/api/v1/profile/` is gone.
- [x] promop-staging wired to phr (`PHR_BASE_URL` + CORS set, promop PR #388
  merged, remote served at `/remote/remoteEntry.js`, phr tokens verified via
  deployed JWKS).
- [x] Federated-remote origins baked into the deployed phr SPA (Dockerfile
  ARGs + `infra/main.tf` env vars); Health Profile verified live on
  phr-ipyr.onrender.com rendering promop-staging's PatientInfo.
