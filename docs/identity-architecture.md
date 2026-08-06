# Identity architecture — multi-installation PHR

Decisions recorded 2026-08-06. No Firebase anywhere in the HealthKey family.

## Installation modes

There can be many phr installations, run by different orgs. Each picks an
identity mode; everything else (federated modules, sibling services) is
identical across modes.

| Mode | Who holds accounts | phr backend role |
|---|---|---|
| **Self-hosted** | This phr install's Postgres (as built today) | Full identity provider |
| **Org-owned IdP** | The org's own identity service (their Firebase, their OIDC, their DB) | Relying party only — org's issuer joins the trusted registry |
| **promop-hosted (branded shell)** | Centrally, by promop | None for auth — the shell points its auth API base at promop |

## The family auth API contract

Any identity host in the family implements the same HTTP contract phr
exposes today, so the frontend auth stack (authStore, axios interceptors,
guards) is identical regardless of who hosts identity:

```
POST /api/v1/auth/login/       {email, password} → {access, refresh}
POST /api/v1/auth/refresh/     rotate refresh → new pair
POST /api/v1/auth/logout/      blacklist refresh
GET  /api/v1/auth/me/          current user
GET  /api/v1/auth/jwks/        RFC 7517 key set (RS256)
POST /api/v1/auth/introspect/  RFC 7662 {active, ...claims}
```

Token contract: RS256 JWT, **`iss` = the installation's https origin**
(never a shared name — multiple installs must not collide), claims:
`user_id`/`sub`, `email`, `identity_level`, `claims{...roles}`, plus —
when promop hosts — `person_id` and `org`.

Sibling services (promop's API, hk-labs, future) verify through a
**trusted-issuer registry**: configured map of `iss → JWKS URL` behind the
existing `TokenProvider` chain (generalizing today's single-issuer
`PhrTokenProvider`). Unknown issuer ⇒ reject.

## promop as identity host (branded shells)

Decisions:
- **Login form stays in the branded shell** (primary): promop implements
  the contract endpoints above, backed by its existing native identity
  stack (`Identity` with `urn:local`, `EmailBackend` with lockout +
  password history, invitations, password reset). Endpoints are
  org-scoped: each branded install binds to exactly **one promop
  `Organization`** (1 install = 1 org), enforced via the org's
  first-party client credential + an origin allow-list on the org.
- **Optional SSO** per org via promop's existing OAuth2/OIDC server
  (`/o/`, authorization-code + PKCE — promop's SPA already ships an
  unused PKCE client library to crib from).

What promop already has for this (verified in code): native email/password
identities, lockout/password policies, org multi-tenancy (`Organization`,
`GroupAccess`, per-org login routes, org-scoped OAuth clients), invite +
reset emails, server-to-server provisioning, and a fully-routed OAuth2
server. What's missing, in build order:

1. **Enable OIDC issuance**: set `OIDC_RSA_PRIVATE_KEY` +
   `OIDC_ISS_ENDPOINT` (JWKS is already routed and springs to life),
   add an `OAUTH2_VALIDATOR_CLASS` for custom claims
   (`person_id`, `org`, role).
2. **Contract endpoints on promop**: `login/refresh/logout/jwks/
   introspect` issuing RS256 JWTs with `iss` = promop origin, org-scoped.
3. **Trusted-issuer registry** in sibling services (generalize
   `PhrTokenProvider`; promop + hk-labs), fixing per-install issuers at
   the same time (phr installs set `JWT_ISSUER` to their origin).
4. **Per-org branding + email plumbing** in promop: branding fields and a
   redirect/origin allow-list on `Organization`, per-brand `APP_BASE_URL`
   in invite/reset emails (today a single global with hardcoded PROMOP
   branding).

Cleanups required along the way (found during analysis): one canonical
email-resolution rule (three helpers currently disagree on local-vs-
external precedence), and tightening promop's global
`CsrfExemptSessionAuthentication` + `CORS_ALLOW_CREDENTIALS` combination
before any cross-origin cookie flows are relied on.
