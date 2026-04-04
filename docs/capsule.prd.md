# Capsule — Personal EHR Vault: Product Requirements Document v1.0

**Status:** Draft  
**Date:** 2026-04-03  
**Repo:** healthkey-ai/phr  
**Design doc:** `~/.gstack/projects/healthkey-ai-phr/vtrv101-main-design-20260403-211136.md`

---

## 1. Problem Statement

Patients managing chronic conditions — cancer, diabetes, IBD, autoimmune disease — interact with 3-10 specialists across institutions that don't share records. The practical result: the patient IS the health record. They re-dictate their history at every appointment. They maintain their own spreadsheets. They fax records between providers.

Every existing solution (Epic MyChart, PicnicHealth, Google Health, Microsoft HealthVault) stores patient data on the vendor's servers under the vendor's keys. When the startup folds or the provider revokes access, the patient's record disappears. Even "patient-facing" portals are patient-viewable, not patient-owned.

Capsule is the first personal health record where the patient holds the only decryption key. The operator cannot read your data. Not "we promise not to" — structurally cannot.

---

## 2. Target Users

### Primary: Chronic Condition Patient
- Managing a condition across 3+ specialists (oncologist, primary care, endocrinologist, radiologist)
- Keeps their own tracking document — they're already motivated, just under-tooled
- Frustrated by re-dictating history at every new appointment
- Values privacy; skeptical of "we protect your data" claims
- Willing to pay $10-15/month for a tool that actually works

### Secondary: Caregiver
- Managing records for a family member (aging parent, child with complex condition)
- Needs proxy access with the same permissions as the patient
- Currently the most underserved segment in health record tooling

### Tertiary: Clinician (Doctor/Specialist)
- Receives share links from patients
- Needs read-only access without creating an account
- Does NOT want another portal to log into

### Tertiary (V1): Third-Party App Developer
- Integrates their health app with patient consent via Platform API
- Receives FHIR R4 formatted records scoped by patient approval

### Quaternary (V1): Researcher / Data Scientist
- Queries anonymized cohort data with patient consent
- Access controlled per data category (labs OK, genomics requires separate consent)
- Never receives raw patient records — only aggregate queries

---

## 3. Core Principles

1. **Cryptographic sovereignty, not contractual.** The patient holds the decryption key. The operator cannot produce plaintext PHI even under legal compulsion.
2. **Pull model first.** Patient initiates all data connections. No data enters the capsule without patient action or pre-authorization.
3. **Minimum viable trust surface.** Every component that touches plaintext data is in the patient's browser/device, open-source, and auditable.
4. **Graceful degradation.** If FHIR pull fails, document upload works. If the key is lost, 2-of-3 Shamir recovery works. The patient is never locked out.
5. **Ship the wedge, plan the platform.** V1 serves the individual chronic condition patient. V2 expands to the platform API. Platform architecture is designed in from day one.

---

## 4. Feature Requirements

### 4.1 Account & Identity

| ID | Requirement |
|----|-------------|
| ACC-001 | Patient creates an account with email + password (bcrypt, server-side) |
| ACC-002 | Passkey (WebAuthn Level 2) supported as second factor for session auth |
| ACC-003 | Email verification required before data import is enabled |
| ACC-004 | Account deletion triggers cryptographic key destruction client-side + server-side ciphertext deletion |

### 4.2 Key Management

| ID | Requirement |
|----|-------------|
| KEY-001 | On first login, patient's browser generates a 256-bit master key via `crypto.getRandomValues()` |
| KEY-002 | Master key is never transmitted to the server in plaintext |
| KEY-003 | Master key is stored in IndexedDB, encrypted with a PIN-derived key (PBKDF2-SHA256, 600,000 iterations, random salt) |
| KEY-004 | Master key is split into 3 shards using 2-of-3 Shamir Secret Sharing. Any 2 shards reconstruct the key. |
| KEY-005 | Shard 1: stored in IndexedDB on primary device |
| KEY-006 | Shard 2 (a Shamir shard — NOT the full master key): encrypted with recovery contact's ECDH public key, stored on server. Recovery contact receives an email notification with a link to access their stored shard when needed. The shard is NOT included in the email itself (email contains notification + access URL only; shard remains server-side until patient initiates recovery). |
| KEY-007 | Shard 3: displayed as a BIP39-encoded 24-word phrase (raw shard bits → BIP39 word list, no PBKDF2 derivation) for patient to write down |
| KEY-008 | Key recovery flow: patient provides any 2 of 3 shards → master key reconstructed → new device enrolled |
| KEY-009 | Key rotation: patient can trigger full re-encryption of all stored ciphertext. Server sets `key_rotation_in_progress` flag; other sessions receive 423 Locked until rotation completes. Key rotation MUST invalidate all proxy sessions and platform API tokens; proxy key re-delegation and new app consent grants are required after rotation. |
| KEY-012 | Key rotation is resumable: server tracks rotation status per record (pending/rotated). If rotation is interrupted, patient sees "Key rotation interrupted — resume?" on next login and can continue from where it stopped. Rotation must complete within 60 minutes for ≤ 1,500 records on a standard connection. |
| KEY-010 | New device onboarding (non-emergency): patient logs in on new device → prompted for any 2-of-3 shards → master key loaded |
| KEY-011 | WebAuthn PRF extension for key protection deferred to V2 (browser support <70% as of 2025) |

### 4.3 Data Encryption

| ID | Requirement |
|----|-------------|
| ENC-001 | All records encrypted client-side with AES-GCM-256 before transmission to server |
| ENC-002 | Each record uses a unique 96-bit nonce (IV) generated via `crypto.getRandomValues()` |
| ENC-003 | Server stores only ciphertext blobs. No plaintext PHI at rest on server. |
| ENC-004 | Strict Content Security Policy enforced on all web pages: `script-src 'self'`, no inline scripts, SRI on all assets |
| ENC-005 | Metadata stored server-side: record UUID, resource type (encrypted), approximate creation date range (week-granularity to reduce metadata leakage), provider ID (encrypted), ciphertext size. Provider records: `provider_name` and `fhir_base_url` stored encrypted (quasi-identifiers — knowing a patient uses `fhir.cancercenter.org` is PHI-adjacent). |
| ENC-006 | Client-side decryption on page load: metadata decrypted in browser; filtered/sorted in browser before rendering |

### 4.4 FHIR Provider Connections

| ID | Requirement |
|----|-------------|
| FHIR-001 | Provider connections use SMART on FHIR standalone launch (OAuth2 + PKCE) |
| FHIR-002 | V1 sandbox targets: Epic (open.epic.com), Cerner (fhir.cerner.com/r4) |
| FHIR-003 | V1 production targets: pending Epic App Orchard + Cerner Code Program approval |
| FHIR-004 | Resources pulled: Condition, MedicationRequest, MedicationStatement, Observation, Procedure, DiagnosticReport, AllergyIntolerance, Immunization |
| FHIR-005 | OAuth refresh tokens stored encrypted in capsule; silent refresh on app load; expired tokens prompt re-auth |
| FHIR-006 | Pull failure: patient dashboard shows clear error with re-auth action. No silent failure. |
| FHIR-007 | Partial bundle: records imported with "incomplete — partial pull" indicator on timeline |
| FHIR-008 | Malformed FHIR resource: logged to `unmapped_resource_log` (metadata only), patient notified of import gap |
| FHIR-009 | If FHIR normalization proved infeasible by prototype: document upload becomes primary V1 onramp; FHIR pull deferred to V2 |

### 4.5 Document Upload

| ID | Requirement |
|----|-------------|
| DOC-001 | Patient can upload PDF, C-CDA XML, JPEG, PNG documents |
| DOC-002 | C-CDA XML: deterministic structured extraction (conditions, medications, allergies, procedures) |
| DOC-003 | PDF: basic text extraction; structured fields extracted where possible from typed PDFs |
| DOC-004 | JPEG/PNG/scanned PDFs: stored as attachments; no structured extraction in V1 |
| DOC-005 | All documents encrypted client-side before upload |
| DOC-006 | Patient sees import progress and any fields that could not be extracted |
| DOC-007 | Documents appear in timeline as events with source type "manual upload" |

### 4.6 Timeline View

| ID | Requirement |
|----|-------------|
| TML-001 | Unified chronological timeline of all imported records: conditions, medications, labs, procedures, documents |
| TML-002 | Filter by: date range, resource type, provider, conflict status |
| TML-003 | Client-side filtering: no server-side query (server is blind to record content) |
| TML-004 | Timeline loads in < 3 seconds for a patient with ≤ 1,500 records |
| TML-005 | For patients with > 1,500 records: lazy-load by time window (most recent 2 years on initial load) |
| TML-006 | Each timeline event shows: date, resource type icon, provider name, summary (decrypted client-side), conflict indicator if applicable |
| TML-007 | Empty state: clear onboarding prompt to connect first provider or upload first document |

### 4.7 Lab Trend Visualization

| ID | Requirement |
|----|-------------|
| LAB-001 | Labs view: group Observation resources by LOINC code into trend series |
| LAB-002 | Line chart for each lab series: x-axis = date, y-axis = value, reference range bands shown |
| LAB-003 | Reference ranges sourced from FHIR Observation.referenceRange; fallback to standard LOINC reference values |
| LAB-004 | Click any data point to expand full lab report (decrypted client-side) |
| LAB-005 | Supported standard panels in V1: CBC, CMP, lipid panel, HbA1c, TSH, urinalysis. Others rendered as generic trend. |
| LAB-006 | Labs chart renders in < 1 second for a panel with ≤ 200 data points |

### 4.8 Conflict Detection

| ID | Requirement |
|----|-------------|
| CON-001 | On import, capsule detects when the same clinical entity (condition, medication, allergy) is recorded with conflicting attributes across two providers |
| CON-002 | Conflict definition: same entity type, matching clinical concept (SNOMED/RxNorm code exact match first; if code missing, Levenshtein distance ≤ 2 on normalized label as fallback), but different value, status, or date. SNOMED/RxNorm code mapping table bundled client-side (OHDSI Athena concepts subset, compressed). No external terminology lookup for privacy reasons. |
| CON-003 | Duplicate definition: same entity type, same clinical concept, same value — silently deduplicated, not surfaced as conflict |
| CON-004 | Patient shown conflict summary: "Epic says 'Type 2 Diabetes with complications'; Mayo Clinic says 'Type 2 Diabetes mellitus'" with a prompt to choose the accurate version |
| CON-005 | Patient resolution creates a `conflict_resolution` record stored in their capsule |
| CON-006 | Unresolved conflicts shown in timeline with a conflict indicator icon |
| CON-007 | Patient can defer resolution; unresolved conflicts do NOT block timeline use |
| CON-008 | Clinician escalation domains (cancer staging, genomics): patient cannot choose; escalation path offered instead |

### 4.9 Doctor Share Link

| ID | Requirement |
|----|-------------|
| SHR-001 | Patient generates share link scoped to: selected resource types, date range |
| SHR-002 | Selected records re-encrypted client-side with an ephemeral AES-GCM-256 key |
| SHR-003 | Share URL format: `https://[domain]/share/[LINK_ID]#[KEY_BASE64]` — ephemeral key in URL fragment (never sent to server) |
| SHR-004 | Server stores encrypted package indexed by LINK_ID; cannot decrypt it |
| SHR-005 | Link expiry: 24h, 72h (default), 7 days, or 30 days — patient-configurable |
| SHR-006 | Revocation: patient marks link revoked; server returns 404 on next LINK_ID access |
| SHR-007 | No recipient account required |
| SHR-008 | Access log: server records `{link_id, access_time, IP_hash}` — no PHI; patient sees access count and last-accessed timestamp |

### 4.10 Emergency Access QR Code

| ID | Requirement |
|----|-------------|
| EMR-001 | Patient generates an Emergency Access QR code from their capsule |
| EMR-002 | QR code encodes a URL containing a read-only, pre-decrypted emergency data subset |
| EMR-003 | Emergency data subset: blood type, active allergies, current medications, emergency contacts, primary conditions |
| EMR-004 | QR data is encrypted at rest on the server; URL contains decryption key in fragment |
| EMR-005 | Emergency QR page: no login required for viewer; renders in any modern browser using a minimal JS-only decryption bundle (no framework, no CDN, self-contained). No account creation required. |
| EMR-006 | Patient controls which fields appear in the emergency view |
| EMR-007 | Patient can regenerate QR code (revokes old URL); old URL returns 410 Gone |
| EMR-008 | QR code page labeled "Emergency Medical Information — [Patient First Name]" |

### 4.11 Caregiver Proxy Access

| ID | Requirement |
|----|-------------|
| PRX-001 | Patient can invite a trusted person as a "caregiver proxy" |
| PRX-001a | Recovery contact registration: recovery contact does NOT require a Capsule account. Invitation sends a one-time setup URL (valid 7 days) to the contact's email. Contact opens URL, browser generates ECDH keypair, public key sent to server. Patient's browser (on next login if not currently open) encrypts Shard 2 (the Shamir shard, not a full key copy) with contact's public key and uploads to server. Distinction from proxy: proxy receives a FULL master key copy (see PRX-002); recovery contact receives only a Shamir shard (requires 2-of-3 to reconstruct master key). If contact never accepts within 7 days, invitation expires and patient is notified to re-invite. |
| PRX-002 | Proxy invitation: patient's browser (at consent time or on next login) encrypts a copy of their master key with the proxy's ECDH public key. Server stores encrypted key copy. Server holds proxy's public key until patient's browser completes the encryption step — proxy cannot access records until this step is complete. |
| PRX-003 | Proxy has full read access to patient's capsule: same timeline, lab charts, and conflict view |
| PRX-004 | Proxy can generate share links on the patient's behalf |
| PRX-005 | Proxy cannot change key management, settings, or invite other proxies |
| PRX-006 | Patient can revoke proxy access at any time; revocation invalidates proxy's session and encrypted key copy |
| PRX-007 | Maximum 3 proxies per patient in V1 |

### 4.12 Capsule Platform API

| ID | Requirement |
|----|-------------|
| API-001 | Capsule exposes an OAuth2 authorization server; third-party apps can request access on behalf of a patient |
| API-002 | Per-app, per-scope consent: patient approves or denies each app's request for each resource category |
| API-003 | Scopes: `read:conditions`, `read:medications`, `read:observations`, `read:procedures`, `read:documents`, `read:emergency` |
| API-004 | Token grant: access token (1-hour expiry) + refresh token (30-day rolling). No long-lived tokens. On token refresh, server returns the app's current `encrypted_key_copy` from `platform_app_keys`. If patient has rotated their key since last grant, the encrypted key copy will be stale and the app must prompt the patient to re-grant consent (re-encryption with new master key). |
| API-005 | Zero-knowledge app data delivery: patient's browser encrypts a scoped key copy with the app's ECDH public key at consent grant time. Server stores the encrypted key copy. On API calls, server returns the encrypted blobs + the encrypted key copy. App decrypts the key copy with its own private key, then decrypts the blobs. Server never holds or derives the decryption key. (Same delegation pattern as caregiver proxy access — see PRX-002.) |
| API-006 | App developer portal: register app, manage OAuth2 credentials, view consent stats |
| API-007 | Patient can revoke app access at any time; revocation takes effect within 60 seconds |
| API-008 | API responses are FHIR R4 format |

### 4.13 Researcher Data Sharing

| ID | Requirement |
|----|-------------|
| RES-001 | Patient grants research consent per data category: conditions, medications, labs, procedures, genomics (separate explicit consent) |
| RES-002 | Genomics consent requires re-identification disclosure: patient explicitly acknowledges genomic data can identify them |
| RES-003 | Research queries are aggregate only: no individual record access for researchers |
| RES-004 | Minimum cohort size for any query result: 10 patients (queries over smaller cohorts return no results + privacy advisory) |
| RES-005 | Patient can revoke research consent at any time; data excluded from future queries within 24 hours |
| RES-006 | Patient receives notification when their data contributed to a research query (aggregate confirmation, no specific study details in V1) |
| RES-007 | Researcher account type: separate approval workflow; institutional affiliation required |
| RES-008 | Research consent is independent from clinical sharing (SHR-001 through SHR-008) |

### 4.14 Local Export

| ID | Requirement |
|----|-------------|
| EXP-001 | Patient can export their full capsule as an encrypted FHIR R4 Bundle |
| EXP-002 | Export format: `.capsule` file (JSON, AES-GCM-256 encrypted with patient's master key) |
| EXP-003 | In-browser decryption tool available at `/decrypt` — patient can decrypt export using their master key without any server involvement |
| EXP-004 | Export is complete (all records, all documents) and reflects current state |
| EXP-005 | Export can be re-imported into a new capsule instance |

---

## 5. Non-Functional Requirements

### 5.1 Security

| ID | Requirement |
|----|-------------|
| NFR-SEC-001 | Zero plaintext PHI stored on operator servers. Verified by third-party security audit before launch. |
| NFR-SEC-002 | All data in transit over TLS 1.3 |
| NFR-SEC-003 | AES-GCM-256 for all symmetric encryption |
| NFR-SEC-004 | Content Security Policy: `script-src 'self'`, no inline scripts, SRI on all loaded assets |
| NFR-SEC-005 | Subresource Integrity (SRI) enforced on all CDN assets |
| NFR-SEC-006 | OWASP Top 10 addressed in security audit |
| NFR-SEC-007 | Penetration testing required before accepting real patient data |

### 5.2 Compliance

| ID | Requirement |
|----|-------------|
| NFR-CMP-001 | Product operates as a PHR vendor (HITECH 13400), not a HIPAA covered entity |
| NFR-CMP-002 | BAA required with: cloud infrastructure provider (GCP or AWS), CDN, email delivery service |
| NFR-CMP-003 | HIPAA legal review required pre-launch: confirm PHR vendor classification, breach notification obligations |
| NFR-CMP-004 | GDPR: patients in EU can request erasure; erasure deletes all ciphertext + key material |
| NFR-CMP-005 | Audit logs retained for 7 years (metadata only, no PHI) |

### 5.3 Performance

| ID | Requirement |
|----|-------------|
| NFR-PERF-001 | Timeline loads in < 3 seconds for ≤ 1,500 records (client-side decryption) |
| NFR-PERF-002 | Lab chart renders in < 1 second for ≤ 200 data points per panel |
| NFR-PERF-003 | FHIR pull completes (or times out with partial) in < 30 seconds per provider |
| NFR-PERF-004 | Share link loads for recipient in < 2 seconds |
| NFR-PERF-005 | Key recovery flow completes in < 10 minutes |
| NFR-PERF-006 | Platform API: 99.9% uptime SLA; < 200ms p99 for token validation |
| NFR-INFRA-001 | Object storage client abstracted behind a provider interface (V1: GCS or S3). Swap to another provider without API changes. Required for V2 multi-cloud. |

### 5.4 Observability

| ID | Requirement |
|----|-------------|
| NFR-OBS-001 | FHIR pull success/failure rate per provider, tracked in operator dashboard |
| NFR-OBS-002 | Client-side encryption error rate (Web Crypto API failures) tracked via anonymized telemetry |
| NFR-OBS-003 | Key recovery funnel: track where patients drop off in the recovery flow |
| NFR-OBS-004 | Unmapped FHIR resource log: resources that couldn't be normalized |
| NFR-OBS-005 | Share link access events (LINK_ID, timestamp, IP hash) — no PHI |
| NFR-OBS-006 | Audit log: `{patient_id_hash, action, resource_types, provider_id, timestamp}` — no plaintext PHI |

---

## 6. Launch Gates

The following must be complete before accepting real patient data:

1. **Epic App Orchard registration** — submit immediately. 4-8 week approval. Launch blocked until approved.
2. **Cerner Code Program registration** — submit in parallel with Epic.
3. **HIPAA legal review** — outside healthcare counsel. Confirm PHR vendor classification and breach notification obligations.
4. **Security audit** — zero-knowledge architecture reviewed by third-party (Trail of Bits, NCC Group, or Cure53). This is a launch gate, not a post-launch item.
5. **48-hour FHIR prototype** — validates FHIR normalization feasibility. Run this before the V1 engineering sprint begins.

---

## 7. Out of Scope (V1)

- Multi-cloud Terraform deployment (V2, enterprise accounts)
- Push model (provider-initiated data push to capsule)
- Mobile app (iOS/Android)
- Wearable device integration
- AI/LLM document extraction
- CommonWell network connectivity (requires organizational membership, not a developer sandbox)
- WebAuthn PRF key protection (V2, pending browser support)
- Open-source npm encryption library (V2, after V1 proves the model)

---

## 8. V2 Roadmap (Not in Scope, but Design Accommodated)

- Multi-cloud Terraform modules for enterprise
- Mobile apps (React Native wrapping web crypto client)
- Push model with per-source approval flow
- Wearable + Apple Health integration
- AI/LLM document extraction (with HIPAA BAA)
- Open-source client encryption library (npm/PyPI)
- WebAuthn PRF key protection
- CommonWell network connectivity
- Research bulk data delivery API (V2): V1 supports consent collection and aggregate queries; V2 adds a bulk export API for approved research institutions to receive approved cohort data at scale

---

## 9. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | HIPAA legal review: PHR vendor vs. covered entity; breach notification for AES-256 with patient-held key | Requires outside counsel |
| 2 | Epic App Orchard + Cerner Code Program registration | Submit immediately |
| 3 | FHIR normalization feasibility | Answered by 48-hour prototype |
| 4 | Security audit vendor and budget | To be selected; required before launch |
