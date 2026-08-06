# TODO

- [ ] **Wire promop-staging to phr and merge promop PR [#388](https://github.com/healthkey-ai/promop/pull/388)**
  1. In the Render dashboard, on `promop-staging` (srv-d90j0d3tqb8s73fstm80) set:
     - `PHR_BASE_URL` — the deployed phr backend origin (promop derives the
       JWKS + introspection URLs from it)
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
