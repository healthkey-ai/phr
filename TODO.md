# TODO

- [x] **Wire promop-staging to phr and merge promop PR [#388](https://github.com/healthkey-ai/promop/pull/388)**
  1. In the Render dashboard, on `promop-staging` (srv-d90j0d3tqb8s73fstm80) set:
     - `PHR_BASE_URL=https://phr-ipyr.onrender.com` (promop derives the
       JWKS + introspection URLs from it; JWKS is live at
       https://phr-ipyr.onrender.com/api/v1/auth/jwks/)
     - `CORS_ALLOWED_ORIGINS` — add the phr frontend origin
     - while there: `DEBUG=False` (currently `True` on staging *and* production)
  2. Merge promop PR #388 (`phr-federation` → `dev`) — merging auto-deploys
     `promop-staging`.
  3. After deploy, verify `https://promop-staging.onrender.com/remote/remoteEntry.js`
     serves JS and point phr's `VITE_PROMOP_REMOTE_URL` at it.

- [ ] **Decide the fate of the local `patient_profile` data/endpoint**
  The federated Health Profile (promop PatientInfo) replaced the local
  profile page, but `/api/v1/profile/` (onboarding_step + JSONB details)
  still exists and registration still creates rows. Any details users
  entered pre-federation are stranded there. Options: migrate details into
  promop, repurpose the app as onboarding-state-only, or remove it.

- [x] **Bake federated-remote URLs into the deployed phr frontend**
  The Docker build compiles the SPA with default `VITE_PROMOP_REMOTE_URL` /
  `VITE_PROMOP_API_URL` (localhost) — the deployed Health Profile page points
  at localhost until the Dockerfile declares ARGs for them and the Render
  service (infra/main.tf) sets them to the promop-staging origins.

- [ ] **Add lab uploads + results to hk-labs and federate it like promop**
  The extracted labs code (upload pipeline, LOINC matching, results UI,
  `labs_remote` federation with `./LabUploads` / `./LabResults`) lives on
  the `archive/*` branches and per the extraction plan belongs in the
  hk-labs repo (`../hk-labs`). Follow the promop playbook:
  1. hk-labs: `PhrTokenProvider` (JWKS + introspection against phr),
     `.hk-labs-root` / `--hk-labs-*` CSS namespace already distinct,
     serve `remoteEntry.js` from the web service.
  2. Deploy hk-labs; set `PHR_BASE_URL` + CORS to the phr origin.
  3. phr: set `VITE_LABS_REMOTE_URL` / `VITE_LABS_API_URL` in
     `infra/main.tf` (Dockerfile ARGs already declared), re-enable the
     "Upload Lab Reports" / "Lab Results" menu items in AppSidebar.
