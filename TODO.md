# TODO

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
