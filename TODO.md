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

- [ ] **Finish Find Treatments: settle the soc catalog, then deploy** ([soc#262](https://github.com/healthkey-ai/soc/issues/262))
  Federation itself is done and verified end to end locally: `/treatments`
  renders `soc_remote/Recommendations`, soc accepts portal tokens
  (`sub="phr:<id>"`, since its `Identity.sub` is unique globally rather than
  per issuer), the sidebar item enables itself off `VITE_SOC_REMOTE_URL`, and
  patient context comes from promop's `/patient-info/me/` projected onto
  soc's `patient_info` contract. Open PRs: [soc#263](https://github.com/healthkey-ai/soc/pull/263)
  and [phr#53](https://github.com/healthkey-ai/phr/pull/53).

  **Blocker — the catalog has no source on Render.** `Disease` and the
  treatment options are populated only by `sync_collection`, which reads
  Firestore, and the Render installation has none. A deployment would come up
  healthy, authenticate correctly, and answer `disease_not_found` for every
  request. Seen locally: the API stayed at `disease_not_found` until a
  `Disease` row was inserted by hand, and even then `candidates` was empty
  because the treatment options come from the same place. Staging has 41 for
  myeloma; a fresh deployment has zero.
  The models are ordinary Django models, so no Firestore-specific code is
  needed to move the data — only an export from somewhere that has access
  (`dumpdata core.Disease core.DiseaseMedicationDetail …` → `loaddata`, or a
  one-off job like the LOINC load). The decision is where that export lives —
  committed, in object storage, or Firestore credentials on the deployment
  after all — and how it stays fresh as treatment options change.

  Once that is settled:
  1. Merge soc#263 and phr#53. soc's `main` has no node stage today, so a
     service built from it starts fine and serves no remote.
  2. Apply the soc Terraform in `infra/main.tf` (written, **not applied**):
     Render project SOC with a web service and Postgres. No broker — the
     recommend pipeline answers inside the request. Plan was 4 to add, 1 to
     change. Set `PARTNER_AUTH_PROVIDERS` to the portal provider alone; the
     chain is env-driven now, and listing Firebase where it cannot work only
     logs "no credentials configured".
  3. Load the catalog on the deployment, then confirm a real recommendation
     returns before wiring the portal to it.
  4. Set `soc_url` and re-apply, which fills the portal's `VITE_SOC_REMOTE_URL`
     / `VITE_SOC_API_URL` build args, then rebuild the portal so they bake in.
     Until then the menu item stays disabled by design.
  5. Add CD so soc autodeploys on merge, matching the other services. Needs
     the service to exist first — there is no service id until step 2.

  Two things worth remembering:
  - promop emits the slug `multiple-myeloma` where soc keys the same disease
    as `myeloma`; an unmapped slug 404s the recommend lookup. Handled in
    `FindTreatmentsPage`, but the same trap applies to any disease added later.
  - soc requires `therapy_lines_count` (or a `lines_of_therapy` list) and
    returns 400 rather than guessing. The portal forwards it only when promop
    has it, so a record without it surfaces a validation error instead of
    recommendations. Decide whether the portal should default it — inventing a
    therapy-line count on a patient's behalf is not obviously right.

- [ ] **Finish Find Trials: get EXACT's staging deploy green** ([exact#358](https://github.com/healthkey-ai/exact/issues/358))
  Federation is done and verified end to end locally: `/trials` renders
  `exact_remote/TrialMatches`, EXACT accepts portal tokens (`sub="phr:<id>"`,
  same globally-unique-`sub` reason as soc), the sidebar item enables itself
  off `VITE_EXACT_REMOTE_URL`, and patient context is normalised by EXACT
  itself through `/normalize-ctomop-row/` rather than a hand-written field
  mapping. Open PRs: [exact#359](https://github.com/healthkey-ai/exact/pull/359)
  and [phr#56](https://github.com/healthkey-ai/phr/pull/56).

  Staging is provisioned — `exact` at https://exact-ybht.onrender.com, in a
  `staging` environment added to the pre-existing EXACT project rather than a
  new one, since that project already holds another team's Production
  environment and the service running there.

  **Two blockers.**

  1. *Review* — exact's `main` is governed by a ruleset requiring one approving
     review, so [exact#359](https://github.com/healthkey-ai/exact/pull/359)
     cannot merge. `main` today has neither the node build stage (no
     `/remoteEntry.js`) nor `/healthz`, so staging is pinned to the federation
     branch via `exact_deploy_branch`. Set that back to `"main"` the moment
     #359 lands: the branch is deleted on merge, and `deploy-render.yml` only
     fires for `main`.
  2. *Corpus schema* ([exact#360](https://github.com/healthkey-ai/exact/issues/360))
     — `GET /trials/` 500s because the shared corpus is three columns and three
     tables behind the models. Not staging-specific: `dev`, which `exact-2`
     runs, expects the same fields, and the public snapshot carries the same
     stale schema. The account EXACT connects with is read-only
     (`CREATE on public=false`), so the additive DDL needs someone with rights
     on `ne_bc_trials`. It is written and ready in the issue.

  Everything either side of that endpoint is verified live against
  `exact-ybht.onrender.com` with a portal-issued RS256 token: `/healthz`,
  `/remoteEntry.js` (+ CORS), `/countries/`, `/form-settings/` and
  `/normalize-ctomop-row/` all 200, unauthenticated calls 401, and the portal
  bundle has the exact origin baked in.

  Unlike soc, there is no catalog blocker: the trial corpus lives in the
  externally managed Postgres the existing instance reads, and staging shares
  it rather than holding a copy. Two things worth remembering:
  - `TRIALS_DATABASE_INIT_FROM_BACKUP=1` restores that corpus from a public
    snapshot but **drops the public schema first** — fine against a database
    of its own, destructive against the shared one. Staging leaves it unset.
  - `CTOMOP_BASE` points at the same promop the portal reads, but only backs
    EXACT's server-side `?person_id=` resolver, which the portal never calls.
    That endpoint does not bind `person_id` to the requesting user, so giving
    it a service token would let any caller read any patient's record. Left
    empty deliberately.

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
