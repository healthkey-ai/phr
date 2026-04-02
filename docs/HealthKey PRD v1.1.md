**HEALTHKEY**

Personal Health Record

**Product Requirements Definition**

Version 1.1  ·  April 2026

**CONFIDENTIAL — INTERNAL WORKING DOCUMENT**

# **Contents**

This document is structured in ten sections:

1\.   Introduction & Strategic Context

2\.   Sources & References

3\.   Stakeholder Personas

4\.   Design Principles

5\.   Patient-Facing Application Requirements

6\.   Researcher-Facing Analytics Requirements

7\.   Shared Platform & Infrastructure Requirements

8\.   CMS Health Tech Ecosystem — Kill the Clipboard

9\.   Non-Functional Requirements

10\.  Out of Scope

# **1\. Introduction & Strategic Context**

## **1.1 Purpose of This Document**

This Product Requirements Definition (PRD) specifies the functional and non-functional requirements for HealthKey's Personal Health Record (PHR) product. It is the primary reference for engineering, design, clinical, and commercial teams. Requirements are drawn from six primary sources: the HealthKey architecture specification, the HealthKey marketing website, the Harvard-Radcliffe patient data workshop, the CancerBot Common Patient Information Schema, competitive analysis of HealthTree and Novellia, and the broader OHDSI/OMOP literature.

The document maintains a strict separation between Patient-Facing Application Requirements (Section 5\) and Researcher-Facing Analytics Requirements (Section 6). Shared infrastructure requirements that serve both personas are consolidated in Section 7\.

## **1.2 Product Vision**

| *"A patient-controlled, centralized repository for health data — one that aggregates structured information from all sources, so both patients and clinicians can make informed, confident decisions."* — A Vision for Centralized Patient Data Repositories \[CB-1\] |
| :---- |

HealthKey is a patient-owned Personal Health Record built on the OMOP Common Data Model (CDM) and HL7 FHIR standards. It serves two distinct but interdependent user populations: patients who want a complete, accurate, and actionable view of their own health history; and researchers and clinicians who need clean, consented, longitudinal data to accelerate discovery and improve care.

The founding insight is that FHIR has standardized the pipes but not the container \[CB-1\]. HealthKey provides the container — a single, coherent, patient-controlled record that persists across institutional boundaries.

## **1.3 Market Context & Competitive Landscape**

### **HealthTree (healthtree.org)**

HealthTree is a nonprofit blood cancer patient platform offering patient record tracking, clinical trial matching, community, and a 'Twin Machine' for peer matching. Its Cure Hub product demonstrates strong patient engagement — 14,000+ patients actively using the platform — and a research data model funded by pharmaceutical sponsors including Johnson & Johnson, Amgen, and Bristol Myers Squibb \[HT\]. HealthTree's approach validates the dual patient-research model but is disease-specific (blood cancers only) and lacks the standardised OMOP data layer that HealthKey provides. HealthKey differentiates through standards compliance, broader disease coverage, and deeper analytics infrastructure. HealthTree is not a competitor per se. It is a popular platform that provides many of the functions that we are discussing.

### **Novellia (novellia.com)**

Novellia is a direct commercial competitor offering a free patient health record aggregator. It connects to 50,000+ healthcare systems, supports symptom and medication tracking, and is free to patients — funded through de-identified data partnerships with biopharmaceutical companies \[NOV\]. Novellia's tagline — 'one secure spot for everything you need to understand, manage, and advocate for your care' — closely mirrors HealthKey's patient proposition. 

**Key differentiators for HealthKey:** 

**\- OMOP-standardised storage (enabling genuine research-grade analytics)**

**\- oncology-specific depth (genomics, biomarkers, lines of therapy)**

**\- integrated clinical trial matching engine powered by CancerBot.**

**\-  Novellia currently has no mobile app; HealthKey should ensure mobile app at launch.**

## **1.4 Founding Requirements from the Harvard-Radcliffe Workshop**

The Harvard-Radcliffe Institute seminar on patient data repositories, convened by Yuri Quintana and attended by clinicaltrials.gov creator Alexa McCray, patient-data-rights pioneer e-Patient Dave deBronkart, and OpenNotes director Cait Desroches, identified two foundational principles that directly shape this PRD \[CB-1\]:

* Patient Control of Data Creation: patients grant write access to providers, reconcile records from multiple sources, decide which version of overlapping data is authoritative, and enrich records with lifestyle and wearable data.

* Patient Control of Data Usage: patients choose who can see what — providers, caregivers, peers, navigators — and can delegate access rights to trusted clinicians or family members.

The workshop also identified the critical barriers HealthKey must navigate:

* Provider trust: clinicians hesitate to rely on patient-held or cross-institutional data.

* Data ownership resistance: institutions resist sharing data for patient-retention reasons.

* Billing incentives: providers may prefer repeating billable diagnostics to reusing existing data.

* Error correction reluctance: institutions resist correcting legacy data, requiring patient-initiated feedback loops.

The workshop proposed measurable success metrics including 13 million patient sign-ups within five years of launch, 20% of FHIR-adopting providers pushing data within five years, and two-thirds of users rating the service as valuable \[CB-1\]. These targets inform HealthKey's scalability and adoption requirements.

# **2\. Sources & References**

All requirements in this PRD are traceable to one or more of the following sources. Inline citations use the codes below.

| Code | Source | Description |
| :---- | :---- | :---- |
| HK-W | [HealthKey Website](http://healthkey.ai) | healthkey.ai — product, pricing, and positioning pages |
| HK-A | [PHR Architecture Doc](https://docs.google.com/document/d/13ISsyzP9ojEmsFuGv_PVunw0-lRwXoModQQzhnEL3MM/edit?tab=t.0#heading=h.gt7d5ei9lvf4) | An Architecture for a Personal Health Record (HealthKey internal, March 2026\) |
| HT | [HealthTree](https://healthtree.org/)  | healthtree.org and Cure Hub — blood cancer patient platform and research model |
| NOV | [Novellia](https://novellia.com/) | novellia.com — direct competitor personal health record platform |
| CB-1 | [Harvard-Radcliffe Patient Workshop Report](https://medium.com/cancerbot/a-vision-for-centralized-patient-data-repositories-80be97b92dda) | A Vision for Centralized Patient Data Repositories (Medium, Nov 2025\) |
| CB-2 | [Patient Information Schema Article](https://medium.com/cancerbot/towards-a-common-patient-information-schema-a1460a835b2f) | Towards a Common Patient Information Schema (Medium, Nov 2025\) |
| OHDSI | [OHDSI/OMOP](https://www.ohdsi.org/) | OMOP CDM specification, OHDSI Achilles, Data Quality Dashboard, oncology extension (ascopubs.org/doi/full/10.1200/CCI.20.00079) |
| CMS-HTE | CMS Health Tech Ecosystem | cms.gov/priorities/health-technology-ecosystem — overview, interoperability framework, and early adopter pledges (July 2025\) |
| CMS-MVP | CMS HTE MVP Requirements | MVP\_Requirements\_Detail\_FINAL.pdf — detailed MVP requirements for patient apps, networks, providers, EHRs, and payers (provided) |
| CMS-KTC-PPTX | CMS HTE MVP Criteria Deck | CMS\_HTE\_MVP\_033126\_Criteria\_clean.pptx — MVP criteria for Kill the Clipboard patient-facing apps (provided) |
| CMS-KTC | CMS KtC Early Adopters | cms.gov/health-tech-ecosystem/early-adopters/kill-the-clipboard — pledge page and company commitments |

# **3\. Stakeholder Personas**

## **3.1 Primary Personas**

| P1 · The Complex Patient A patient managing a serious or chronic illness — most likely oncology — whose records are fragmented across multiple institutions and countries. The founding persona, drawn directly from the author's experience navigating follicular lymphoma across four healthcare systems \[CB-1\]. Needs: complete longitudinal record, conflict resolution, clinician sharing, trial matching. | P2 · The Caregiver A family member managing the health records of one or more dependents — like Betsy Lowe at the Harvard-Radcliffe workshop, who maintains Excel spreadsheets for several children with chronic illness \[CB-1\]. Caregivers need delegated access, not just a copy of someone else's record. Needs: delegated access, multi-patient management, simplified sharing. |
| :---- | :---- |

| P3 · The Clinician An oncologist or specialist receiving a shared patient record, seeking a complete, reconciled view of treatment history, biomarkers, and prior therapy lines. Clinicians trust a record that is sourced, audited, and conflict-resolved. Needs: complete, sourced, auditable record; FHIR-compatible export. | P4 · The Academic Researcher A clinical informatician or biostatistician at a university or cancer centre who needs clean, consented, OMOP-standardised longitudinal cohort data — without months of ETL and cleaning. Often working within IRB constraints. Needs: OMOP data access, outcome metrics, cohort tools, RWE survey delivery. |
| :---- | :---- |

| P5 · The Pharma/Biotech Partner A data scientist or medical affairs lead at a pharmaceutical or biotech company seeking real-world evidence (RWE) cohorts, outcome analysis, and potentially predictive model building for specific indications. Analogous to HealthTree's pharma sponsors (J\&J, Amgen, BMS) \[HT\]. Needs: large consented cohorts, automated outcome analysis, predictive models, custom SLA. | P6 · The Patient Navigator A clinical navigator or health coach who helps patients prepare for appointments, locate trials, and understand their record. Modelled on HealthTree's Patient Navigator service \[HT\]. Requires read access to a patient's shared record with appropriate consent. Needs: permissioned read access, secure messaging, record summary view. |
| :---- | :---- |

# **4\. Design Principles**

These principles are non-negotiable constraints that govern all product decisions.

| Principle | Statement |
| :---- | :---- |
| **Patient Primacy** | Every product decision must give the patient more control, clarity, or a better outcome. Patients are always free. HealthKey's revenue comes from research access, never from patient data monetisation \[HK-W\]. |
| **Standards-First** | All clinical data is stored in OMOP CDM with OHDSI standard vocabularies (SNOMED, LOINC, RxNorm, ICD-O-3). FHIR R4 is the primary ingestion format. Proprietary schemas are only permitted for performance layers (PatientInfo) that sit on top of, not instead of, standard OMOP tables \[HK-A\]. |
| **Patient-Controlled Access** | Patients decide who sees what, for how long, with full audit trails. All research access requires explicit, time-stamped, revocable patient consent. No data is ever shared with third parties without this consent \[CB-1, NOV\]. |
| **Conflict-Positive Design** | Conflicting data between providers is surfaced to the patient, not silently resolved. The PHResolution engine provides a guided reconciliation workflow. Patient decisions are logged and versioned \[HK-A\]. |
| **Data Portability** | Patients can always export their complete record in OMOP and FHIR formats, free of charge, regardless of account status. This is a non-negotiable commitment \[HK-W, CB-1\]. |
| **Separation of Concerns** | The patient-facing application and the researcher-facing analytics platform are architecturally and experientially distinct. Patient UX must not be compromised by analytics requirements. The two surfaces share the same underlying data layer \[HK-A\]. |
| **Longitudinal by Default** | The PHR is not a snapshot. Every data import, correction, and access event is versioned and time-stamped. Snapshot semantics (PatientInfo versioning) enable auditable eligibility decisions \[HK-A\]. |
| **Open & Interoperable** | Where possible, HealthKey contributes to open standards. The CTOMOP extensions are published open-source. The architecture is compatible with the OHDSI ecosystem \[CB-1\]. |

# **5\. Patient-Facing Application Requirements**

| This section covers all requirements for the patient-facing PHR application — the surface used by Personas P1 (Complex Patient), P2 (Caregiver), P3 (Clinician receiving a shared record), and P6 (Patient Navigator). All features in this section must be available free of charge to patients. Revenue is never generated from patient data without explicit consent. |
| :---- |

## **5.1 Identity Verification & Onboarding**

Patient identity verification is foundational. A health record is only valuable if it unambiguously belongs to one person. HealthKey must prevent record mixing and protect against unauthorised access.

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-001 | **Identity Verification** | The system must verify patient identity at registration using a bank-grade identity verification mechanism (e.g., government ID check via CLEAR or equivalent) before any health data import is permitted. Identity must be tied to the account permanently. | Must Have | HK-W, CB-1 |
| PAT-002 | **Account Creation** | Patients can create an account using email or social sign-in (Google, Apple). Multi-factor authentication (MFA) is required for all accounts holding health data. | Must Have | HK-W |
| PAT-003 | **Caregiver Delegation** | A patient can grant delegated access to one or more caregivers. The caregiver sees only the patient's record, with granular permission levels (view-only, view \+ add notes). The patient retains full control and can revoke at any time. | Must Have | CB-1, HT |
| PAT-004 | **Multi-Patient Management** | A single account holder can manage records for multiple dependants (e.g., children with chronic illness). Each dependant has a distinct, isolated record. This directly addresses the caregiver persona identified at the Harvard-Radcliffe workshop. | Should Have | CB-1 |
| PAT-005 | **Onboarding Walkthrough** | A guided onboarding flow explains what HealthKey does, how data is protected, how to connect providers, and what patients control. Must be completable in under 5 minutes. | Must Have | NOV |
| PAT-006 | **Mobile Application** | HealthKey must be available as a native mobile application on iOS and Android. The mobile app must achieve feature parity with the web application for core patient functions. Novellia currently lacks a mobile app, representing a differentiation opportunity. | Must Have | NOV, HT |

## **5.2 Data Import & Provider Connection**

The core value of the PHR depends entirely on the completeness of the data it holds. The system must support every realistic data import pathway. The Common Patient Information Schema \[CB-2\] defines the minimum data set required for clinical trial matching; all seven schema categories must be representable in the imported record.

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-010 | **FHIR R4 Provider Connection** | The system must connect to provider EHRs via FHIR R4 API to pull patient records. Connection is authorised by the patient via OAuth. The system must support connections to multiple providers simultaneously. | Must Have | HK-A, CB-1 |
| PAT-011 | **Multi-Provider Import** | Records from multiple providers — hospitals, GP surgeries, labs, specialist clinics — must be importable into a single patient record. Data from different sources must be deduplicated and reconciled, not stacked. | Must Have | CB-1, NOV |
| PAT-012 | **Manual Document Upload** | Patients can upload records manually: PDFs, images of paper documents, DICOM files, discharge summaries, and CD imports. The system must extract structured data where possible using document parsing. Non-parseable documents are stored as attachments linked to the record. | Must Have | CB-1, NOV |
| PAT-013 | **Wearable & Device Integration** | The system should accept data from patient wearables and devices: Apple Watch, Fitbit, continuous glucose monitors. Data is stored in OMOP Observation and Measurement tables. | Should Have | CB-1 |
| PAT-014 | **Patient-Entered Data** | Patients can enter data directly: symptoms, side effects, lifestyle factors (tobacco, alcohol, diet, exercise), and quality-of-life scores. All patient-entered data is clearly labelled by source to distinguish it from provider-supplied records. | Must Have | CB-1, CB-2, HT |
| PAT-015 | **Continuous Sync** | Connected provider sources must be re-synced on a configurable schedule (minimum: daily). New lab results, prescriptions, or clinical notes must update the record automatically. Patients receive notifications of significant new data. | Must Have | HK-W |
| PAT-016 | **Import Status & Audit** | Every import event is logged with timestamp, source, and result. Patients can see exactly what data came from which provider and when. Failed imports generate clear error messages and recovery guidance. | Must Have | HK-W |

## **5.3 Patient Information Schema Requirements**

The Common Patient Information Schema \[CB-2\] defines the minimum structured data the PHR must capture for clinical trial matching. The following seven categories — derived from the breast cancer trial-matching use case — establish the data model requirements for the patient record. **That said the initial focus will be the physiologic measurements and gene mutations necessary for breast cancer and blood cancers.** 

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-020 | **Core Demographics** | Capture: age, gender, ethnicity, country, region, postal code, latitude/longitude. Stored in OMOP Person table. Geographic coordinates enable distance-to-trial-site calculations required by trial eligibility logic. | Must Have | CB-2, HK-A |
| PAT-021 | **Physiologic Measurements** | Capture: height, weight, BMI (auto-calculated), blood pressure, heart rate, ejection fraction, QTc interval, pulmonary function summaries. Critical for therapy safety assessments — QTc is required for targeted therapies; ejection fraction for HER2-directed trials. | Must Have | CB-2 |
| PAT-022 | **Clinical Status** | Capture: primary diagnosis (ICD-10, ICD-O-3), disease stage (AJCC/TNM), ECOG and Karnofsky performance status, histology. These are the first-pass eligibility gates for virtually every oncology trial. | Must Have | CB-2, HK-A |
| PAT-023 | **Medical History & Comorbidities** | Capture: prior malignancies, cardiac conditions, autoimmune and neurologic conditions, neuropathy grade, HIV/hepatitis B/C status, prior ILD and pneumonitis (with grade), geographic exposure risks. Comorbidities affect safety and appear in exclusion criteria of most modern oncology trials. | Must Have | CB-2 |
| PAT-024 | **Haematology, Renal & Hepatic Labs** | Capture with units: ANC, platelets, WBC, RBC, Hgb; creatinine clearance, serum creatinine, eGFR; AST, ALT, ALP, total and direct bilirubin, albumin; serum calcium. Units must be stored alongside values — matching logic breaks on unit conversion failures. | Must Have | CB-2 |
| PAT-025 | **Treatment History & Lines of Therapy** | Capture: treatment lines (1L, 2L, later) with dates, agents, regimens, and outcomes (PR, PD, intolerance); supportive care (bisphosphonates, steroids, G-CSF); disease course (relapse count, remission duration); refractory status (endocrine, CDK4/6, ADC); washout durations; CTCAE toxicity grades. This is the most complex and critical data category for trial matching. | Must Have | CB-2, HK-A |
| PAT-026 | **Genomics & Biomarkers** | Capture: BRCA1/2, EGFR, KRAS, PD-L1 (with TPS/CPS scores), HER2 (IHC and FISH), ER/PR status, MSI/TMB. Mapped to LOINC in OMOP Measurement table. Genomic assay metadata stored in the HealthKey oncology extension validated with OMOP architects. | Must Have | HK-A, OHDSI |
| PAT-027 | **Behavioural & Reproductive Safety Factors** | Capture: consent and cognitive status, pregnancy/lactation status, pregnancy test results, contraception use, tobacco and alcohol use, occupational exposures (healthcare, lab, industrial). Often overlooked but required by exclusion criteria for modern ADC and immunotherapy trials. | Must Have | CB-2 |
| PAT-028 | **Social & Contextual Data** | Capture: insurance status, employment status, primary language (PersonLanguageSkill model), caregiver availability. These influence trial eligibility and care planning. Language data stored in the HealthKey-specific PersonLanguageSkill extension. | Should Have | HK-A, CB-2 |

## **5.4 Conflict Detection & Resolution (PHResolution)**

When the same clinical fact appears differently in records from different providers — different lab values, different diagnoses, conflicting medication dates — the PHR must surface this to the patient rather than silently overriding one record with another.

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-030 | **Automated Conflict Detection** | The PHResolution engine must automatically detect conflicts between records from different providers: duplicate conditions with different dates, conflicting lab values for the same date, contradictory medication histories. Conflicts are flagged in the patient's dashboard. | Must Have | HK-A, HK-W |
| PAT-031 | **Patient-Led Reconciliation Workflow** | For each detected conflict, the patient is presented with a clear, plain-language explanation of the discrepancy, both versions with their sources, and a guided interface to choose which version is authoritative (or create a third, reconciled version). | Must Have | HK-A, CB-1 |
| PAT-032 | **Correction Logging** | All reconciliation decisions are logged with timestamp, patient identifier, and action taken. The original data is preserved; only the authoritative version is used downstream. This satisfies the 'transparent correction log' requirement identified at the Harvard workshop. | Must Have | CB-1 |
| PAT-033 | **Provider Correction Feedback** | Patients can optionally flag a conflict as a likely error in a provider's source system. HealthKey provides a structured report the patient can send back to the originating provider. This is the bidirectional exchange milestone described in the roadmap. | Could Have | CB-1 |

## **5.5 Patient Record Interface**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-040 | **Longitudinal Timeline View** | The patient dashboard presents their health history as a longitudinal timeline — conditions, medications, procedures, labs, and imaging events ordered chronologically across all providers. The patient can filter by category, date range, or provider. | Must Have | HK-W, NOV, HT |
| PAT-041 | **Lab Trends & Out-of-Range Highlighting** | Lab results are displayed as time-series charts with reference range overlays. Out-of-range values are highlighted in plain view. Patients can track trends across time — e.g., ANC recovering after chemotherapy. Modelled on HealthTree's Track My Disease feature. | Must Have | HT |
| PAT-042 | **Plain-Language Summaries** | Clinical data is presented in plain language alongside clinical codes. A patient should be able to understand their own record without medical training. Technical terms link to plain-language definitions. | Must Have | CB-1, NOV |
| PAT-043 | **Appointment Preparation View** | A curated 'share with doctor' summary compiles the most relevant recent data for an upcoming appointment — recent labs, medication changes, symptom logs — in a one-page printable or shareable format. | Should Have | NOV, HT |
| PAT-044 | **Medication & Reminder Management** | Patients can track active medications, set dosage reminders, and log whether doses were taken. Medication history is automatically populated from FHIR imports and kept current with provider updates. | Should Have | NOV |
| PAT-045 | **Symptom & Side Effect Logging** | Patients log symptoms, side effects, and quality-of-life scores with date, severity, and free-text notes. Side effects are categorised using CTCAE terminology where applicable. HealthTree's Side Effect Solutions feature demonstrates patient appetite for this. | Should Have | HT, CB-2 |

## **5.6 Clinician Sharing & Access Control**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-050 | **Clinician Sharing Link** | Patients can generate a time-limited, permissioned share link for any clinician. The link grants read-only access to a specified subset of the record (e.g., oncology history only). Links expire after a configurable duration and can be revoked immediately. | Must Have | HK-W, CB-1 |
| PAT-051 | **Granular Permission Scopes** | Sharing permissions are granular by data category: demographics, labs, medications, genomics, imaging, and documents can each be included or excluded independently from any sharing grant. | Must Have | CB-1 |
| PAT-052 | **Access Audit Log** | Patients can see a complete, immutable log of who accessed their record, what they accessed, and when. This is presented in the patient dashboard in plain language. | Must Have | HK-W, CB-1 |
| PAT-053 | **FHIR Export** | Patients can export their complete record as a FHIR R4 bundle at any time. The export must be machine-readable and suitable for import into another system. This is the interoperability guarantee. | Must Have | HK-W, CB-1, NOV |
| PAT-054 | **OMOP Export** | Patients can export their full OMOP-structured record. This satisfies the data portability guarantee and enables patient-directed research contribution. | Must Have | HK-W, HK-A |
| PAT-055 | **Research Consent Management** | Patients can opt in to share de-identified data with specific research cohorts or studies. Each consent is specific, time-stamped, auditable, and revocable. Consent withdrawal triggers automatic removal from active research cohorts. | Must Have | CB-1, HK-W |

## 

## **5.7 Clinical Decision Support (Standard of Care)**

Clinical decision support for standard of care is a core patient-facing feature, providing actionable, personalized recommendations derived from the patient's comprehensive health record. This service suggests the most promising treatment options, drawing on anonymized real-world evidence from the research cohort.

| ID | Requirement | Description | Priority |
| ----- | ----- | ----- | ----- |
| PAT-061 | **Standard-of-Care Options** | Show the standard of care options based on various frameworks (NCCN, specific disease support groups, specific publications).  Show the framework next to each standard of care option | Must Have |
| PAT-061 | **Standard-of-Care Ranking** | The PHR recommends standard-of-care treatment options personalized to the patient's profile. These options must be ranked probabilistically based on trained predictive models for the patient's condition or disease (RES-041), when such data is available. The ranking is drawn from predictive models trained on the research cohort and presented with confidence intervals. This feature is modelled on HealthTree's Treatment Options feature. | Should Have |

## 

## **5.8 Clinical Trial Matching**

Clinical trial matching is another clinical decision-support feature of the HealthKey PHR, powered by the PatientInfo layer and CancerBot's matching engine. The HealthTree Twin Machine and Cure Hub trial finder demonstrate that patients actively use and value this feature \[HT\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| PAT-060 | **Real-Time Eligibility Screening** | The system automatically screens the patient's record against open clinical trials using the PatientInfo flat table. Screening must complete in under 2 seconds. Results are displayed as a ranked list of matched trials with eligibility rationale. | Must Have | HK-A, HK-W, HT |
| PAT-061 | **Match Notifications** | When a new trial opens that matches the patient's current profile, the patient receives a push notification (mobile) and email alert. Notification preferences are configurable. | Must Have | HK-W, HT |
| PAT-062 | **Trial Detail View** | Each matched trial displays: NCT number, title, phase, primary endpoint, sponsor, sites, eligibility criteria with the patient's status against each criterion, estimated trial duration, and contact information. | Must Have | HT |
| PAT-063 | **Distance & Site Filtering** | Trial results can be filtered by distance from the patient's location. Distance calculations use the lat/long from the demographics schema \[CB-2\]. | Should Have | CB-2, HT |
| PAT-064 | **Patient Twin Matching** | Patients can browse anonymised profiles of patients with similar clinical histories (treatment lines, biomarkers, stage) to understand what treatments worked for people like them. Modelled on HealthTree's Twin Machine feature. | Could Have | HT |
| PAT-065 | **Treatment Option Personalisation** | Beyond trials, the system recommends standard-of-care treatment options personalised to the patient's profile, drawing on predictive models trained on the research cohort. Modelled on HealthTree's Treatment Options feature. | Should Have | HT, HK-A |

# **6\. Researcher-Facing Analytics Requirements**

| This section covers all requirements for the researcher-facing analytics platform — the surface used by Personas P4 (Academic Researcher) and P5 (Pharma/Biotech Partner). Access to this platform is always gated by patient consent and is subject to commercial licensing. No patient-identifiable data is accessible to researchers without explicit patient opt-in. |
| :---- |

The research platform is architecturally distinct from the patient-facing application. It exposes the same underlying OMOP data through a dedicated analytics interface, with access controlled by patient consent status and researcher authorisation level. The architecture document describes this as 'five layers, each building on the one below — from raw EHR data sources through ETL, OMOP storage, a flattened analytics model, and finally a rich services layer' \[HK-A\].

## **6.1 Data Access & Cohort Management**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| RES-001 | **Consented Cohort Access** | Researchers can access OMOP-structured patient records only for patients who have explicitly consented to research data sharing. Consent status is checked in real time; withdrawn consents immediately remove the patient from all active research queries. | Must Have | CB-1, HK-W |
| RES-002 | **Cohort Builder** | Researchers can define cohorts using a structured query interface across OMOP domains: condition, drug exposure, measurement, procedure, observation period. Cohort definitions can be saved, versioned, and shared with collaborators. | Must Have | HK-A, OHDSI |
| RES-003 | **De-identification** | All research-accessible data is pseudonymised to HIPAA Safe Harbor standard by default. Direct identifiers (name, DOB, MRN, full postal code) are removed or generalised. Researchers cannot link records back to individuals without a separate IRB-approved data access agreement. | Must Have | HK-W, CB-1 |
| RES-004 | **OMOP Export for Analysis** | Approved researchers can export cohort data in standard OMOP CDM format, compatible with the full OHDSI tool ecosystem (ATLAS, R packages, Python). | Must Have | HK-A, OHDSI |
| RES-005 | **PatientInfo Flat Table Access** | The PatientInfo denormalised table — collapsing 6–8 OMOP table joins into one row per patient across 100+ fields — is exposed to researchers for AI/ML workloads and real-time screening that require flat feature vectors. This table is the primary AI/ML interface. | Must Have | HK-A |
| RES-006 | **Cohort Size Minimum** | To protect patient privacy, no query result is returned for a cohort of fewer than 10 patients. Results between 10 and 50 patients are flagged with a privacy advisory. | Must Have | CB-1 |

## **6.2 Automated Outcome Analysis**

Outcome analysis is the flagship research capability. The architecture document specifies that HealthKey provides 'out-of-the-box outcome analysis' as a differentiating capability. These metrics are pre-computed from the longitudinal record rather than requiring researchers to write their own survival analysis code \[HK-A\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| RES-010 | **Overall Response Rate (ORR)** | Automatically computed ORR for any researcher-defined cohort and therapy. Expressed as percentage of patients achieving at least partial response. Calculated directly from treatment outcome data in OMOP DrugExposure and Observation tables. | Must Have | HK-A |
| RES-011 | **Complete & Partial Response Rates** | CR and PR rates computed separately, allowing researchers to distinguish deep responses from partial ones. Both metrics available per cohort, therapy, and time period. | Must Have | HK-A |
| RES-012 | **Median Duration of Response (DOR)** | Median DOR computed using Kaplan-Meier methodology. Time from confirmed response to documented progression or death. Exportable as a survival curve with confidence intervals. | Must Have | HK-A |
| RES-013 | **Median Progression-Free Survival (PFS)** | Median PFS computed per cohort and therapy subgroup. Time from start of therapy to first progression or death. Kaplan-Meier curves generated automatically with standard confidence intervals. | Must Have | HK-A |
| RES-014 | **Median Overall Survival (OS)** | Median OS computed with Kaplan-Meier methodology. Time from diagnosis or therapy start to death. Censored appropriately for patients lost to follow-up. | Must Have | HK-A |
| RES-015 | **Adverse Event Rates** | Adverse event rates computed from patient-reported and provider-documented data, including CRS, ICANS, neuropathy, and haematologic toxicities. Categorised by CTCAE grade. Particularly relevant for bispecific antibody and CAR-T outcome analysis. | Must Have | HK-A |
| RES-016 | **Outcome Analysis by Subgroup** | All outcome metrics are sliceable by: disease and subtype, line of therapy (1L/2L/later), therapy type (adjuvant vs neo-adjuvant), biomarker status (EGFR, HER2, BRCA, PD-L1), demographics (age group, sex, ethnicity), and treatment setting. This multidimensional slicing is the core analytical differentiator. | Must Have | HK-A, HK-W |
| RES-017 | **Outcome Export & Reproducibility** | All outcome analyses are exportable as structured data (CSV, JSON) and as reproducible query definitions. Researchers can re-run analyses as the cohort grows and compare results across time points. | Must Have | HK-A |

## **6.3 Multidimensional Metrics & Dataset Characterisation**

Beyond individual outcome metrics, the researcher platform provides a comprehensive characterisation of the dataset — including the OHDSI Achilles analytics suite, which executes over 250 descriptive analyses \[HK-A\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| RES-020 | **OHDSI Achilles Integration** | The research platform executes the full Achilles R package against the HealthKey OMOP instance, producing over 250 descriptive analyses: demographics, condition prevalence, drug distributions, procedure distributions, and temporal coverage. Results are accessible via the researcher dashboard. | Must Have | HK-A, OHDSI |
| RES-021 | **Patient Count by Demographics** | Distinct patient counts segmented by gender, race, age group, disease, and geographic region. Enables cohort characterisation and representativeness assessment before beginning a study. | Must Have | HK-A |
| RES-022 | **Condition Prevalence** | Distinct patient counts per condition with temporal and demographic breakdowns. Researchers can assess the size and composition of potential cohorts before committing to a study. | Must Have | HK-A |
| RES-023 | **Drug Exposure Counts** | Event and patient counts by drug, with filters for key treatments (e.g., anti-CD20 agents, EGFR inhibitors, CDK4/6 inhibitors, ADCs). Includes treatment line distributions and combination regimen analysis. | Must Have | HK-A |
| RES-024 | **Temporal Coverage Analysis** | Data density and concept prevalence tracked over time, enabling assessment of longitudinal data quality and identification of follow-up gaps in the cohort. | Must Have | HK-A, OHDSI |
| RES-025 | **Lines of Therapy Analytics** | Validated lines-of-therapy model (core\_\_lines\_of\_therapy\_validated) computing 1L/2L/later assignments from drug exposure patterns. Includes platinum-based and immunotherapy flags. This derived model is not native to OMOP and is a key HealthKey value-add. | Must Have | HK-A |
| RES-026 | **Cohort Comparison** | Researchers can compare two cohort definitions head-to-head on any metric — enabling comparative effectiveness studies without requiring raw individual-level data export. | Should Have | HK-A, OHDSI |
| RES-027 | **Disease-Specific Analytics Models** | Pre-built disease-specific characterisation models (analogous to HK-A's dq\_\_ reports) provide granular completeness and quality views for specific indications: completeness of biomarker data, lab coverage rates, follow-up duration distributions. | Should Have | HK-A |

## **6.4 Data Quality Infrastructure**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| RES-030 | **Achilles Heel Surface Checks** | Rapid, automated surface-level data quality checks run on each ETL update cycle. Checks identify obvious anomalies: impossible dates, out-of-range values, missing required fields. Results accessible to researchers to assess dataset reliability. | Must Have | HK-A, OHDSI |
| RES-031 | **Data Quality Dashboard (DQD)** | The OHDSI DQD executes thousands of granular conformance, completeness, and plausibility checks. DQD results are published to researchers as a structured quality report for each OMOP domain. This enables informed assessment of dataset fitness for purpose. | Must Have | HK-A, OHDSI |
| RES-032 | **Source Provenance Tracking** | Every data point in the research cohort is tagged with its original source (provider, import date, ETL version). Researchers can filter by data source and assess the relative quality of different source systems. | Must Have | HK-A |
| RES-033 | **PHRofile Pre-Import Profiling** | Before ETL, the PHRofile component profiles incoming FHIR bundles for structure, gaps, and anomalies. PHRofile output logs are available to data engineering teams and, at a summary level, to enterprise research partners. | Should Have | HK-A |

## **6.5 Predictive Model Building**

Automated predictive model building is the most advanced capability in the research platform. It leverages the PatientInfo feature vector — 100+ structured fields per patient — to train and deploy outcome prediction models without requiring researchers to perform their own feature engineering \[HK-A\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| RES-040 | **Automated Model Training** | The platform automatically generates and maintains trained outcome prediction models for common diseases and cohorts as patient data accumulates. Models are trained on PatientInfo feature vectors. All models are versioned and auditable. | Must Have | HK-A, HK-W |
| RES-041 | **Standard-of-Care Ranking** | Trained models run at inference to rank standard-of-care treatment options for individual patients based on their PatientInfo feature vector. Ranking is probabilistic and presented with confidence intervals. This is the primary clinical decision-support output of the model layer. | Must Have | HK-A |
| RES-042 | **Model Performance Reporting** | Each model's performance is reported to researchers: AUC-ROC, calibration plots, feature importance, cohort size, and training date. Researchers can assess model reliability before incorporating results in research. | Must Have | HK-A |
| RES-043 | **Feature Vector Access** | Researchers with appropriate authorisation can access the PatientInfo flat table as a feature vector for their own model training. The schema definition — all 100+ fields across 7 groupings — is published as a data dictionary. | Should Have | HK-A |
| RES-044 | **Custom Indication Models (Enterprise)** | Enterprise partners can commission indication-specific models trained on custom cohort definitions, with bespoke feature engineering. Models can be deployed via API or integrated into clinical workflows. This is an Enterprise tier feature. | Should Have | HK-W |
| RES-045 | **Model Versioning & Reproducibility** | All model versions are retained with their training data snapshot, hyperparameters, and performance metrics. Researchers can reference a specific model version in publications for reproducibility. | Must Have | HK-A |

## **6.6 Real-World Evidence & Longitudinal Surveys**

HealthTree demonstrates patient appetite for research participation — its Surveys & Studies feature invites patients to contribute to academic studies \[HT\]. HealthKey's structural advantage is that survey responses sit in the same OMOP environment as clinical records, eliminating the data linkage step that makes most RWE studies slow and expensive.

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| RES-050 | **Survey Design & Delivery** | Researchers can design survey instruments using a structured builder. Surveys are delivered to consented patients through the patient-facing application on a configurable schedule. Completion rates and drop-off are tracked per survey. | Must Have | HK-A, HT |
| RES-051 | **PRO Linkage to Clinical Record** | Patient-Reported Outcome (PRO) survey responses are stored in OMOP Observation tables and automatically linked to the patient's longitudinal clinical record. No separate data linkage step is required — PROs and clinical data are queryable in the same environment. | Must Have | HK-A |
| RES-052 | **Survey Aggregation & Analysis** | Survey response aggregation is built in. Researchers see response distributions, trend analyses, and cross-tabulations against clinical variables without requiring a separate analytics environment. | Must Have | HK-A |
| RES-053 | **Longitudinal Survey Retention** | Because HealthKey is the patient's ongoing health record (not a standalone study app), retention rates in longitudinal surveys are structurally higher. The platform tracks survey completion rates and identifies at-risk drop-off. | Should Have | HK-W |
| RES-054 | **Academic Study Support** | The platform supports formal academic study protocols — IRB documentation templates, data use agreement tracking, cohort lock for publication, and study-specific data exports — enabling use of HealthKey data in peer-reviewed research. | Should Have | HT, CB-1 |

# **7\. Shared Platform & ETL Infrastructure Requirements**

## **7.1 OMOP Data Layer**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| INF-001 | **OMOP CDM v5.4 Core Tables** | The primary data store conforms to OMOP CDM v5.4. All core tables must be populated: Person, Observation Period, Visit Occurrence, Condition Occurrence, Drug Exposure, Measurement, Observation, Procedure Occurrence, Device Exposure, Death, Note. | Must Have | HK-A, OHDSI |
| INF-002 | **OMOP Oncology Extension** | The ratified OMOP Oncology Extension (Episode/Episode\_Event tables) must be implemented, enabling representation of lines of therapy, cancer episodes, and treatment regimens. Validated with OMOP architects \[HK-A, OHDSI\]. | Must Have | HK-A, OHDSI |
| INF-003 | **HealthKey OMOP Extensions** | HealthKey-specific schema extensions — validated with OMOP architects — must be implemented: additional oncology/genomics metadata columns, PersonLanguageSkill model. These extend but do not replace the standard schema. | Must Have | HK-A |
| INF-004 | **PatientInfo Denormalised Layer** | The PatientInfo table must be implemented and maintained in omop\_core alongside standard OMOP tables. It collapses 6–8 OMOP joins into one row per patient across 100+ fields across 7 groupings. Populated via populate\_patient\_info and re-computed on each data update. | Must Have | HK-A |
| INF-005 | **OHDSI Vocabulary Management** | All clinical concepts must be mapped to OHDSI standard vocabularies: SNOMED-CT for conditions, RxNorm for drugs, LOINC for measurements, ICD-O-3 for oncology histology. Vocabulary updates must be applied on a quarterly minimum cycle. | Must Have | HK-A, OHDSI |

## **7.2 ETL Pipeline**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| INF-010 | **PHRofile (Source Profiling)** | PHRofile scans and profiles incoming FHIR JSON bundles before transformation — identifying structure, gaps, and anomalies. Output feeds into ETL planning and is retained for data quality auditing. | Must Have | HK-A |
| INF-011 | **WhiteRabbit & Rabbit-in-a-Hat Integration** | WhiteRabbit is used to profile source data. Rabbit-in-a-Hat defines the mapping from source tables to OMOP and documents ETL decisions. Both tools are part of the standard OHDSI ETL stack. | Must Have | HK-A, OHDSI |
| INF-012 | **PHRogram (Automated ETL Generation)** | PHRogram generates procedural transformation scripts from source-to-OMOP mapping definitions, eliminating manual programming. All generated scripts are versioned. Dramatically reduces ETL implementation time. | Must Have | HK-A |
| INF-013 | **OHDSI Athena & Usagi Vocabulary Mapping** | OHDSI Athena manages standard vocabularies. OHDSI Usagi maps source coding systems to OMOP standard concepts. Custom mappings are reviewed and versioned. | Must Have | HK-A, OHDSI |
| INF-014 | **ETL Versioning** | All ETL scripts, mapping definitions, and transformation outputs are versioned. A given data snapshot can be reproduced or audited by referencing the ETL version active at import time. Critical for research reproducibility. | Must Have | HK-A |

# **8\. CMS Health Tech Ecosystem — Kill the Clipboard**

| Strategic priority: HealthKey should register as an early adopter of the CMS Health Tech Ecosystem (HTE) and pledge participation in the Kill the Clipboard initiative. This section defines the requirements implied by that participation. CMS HTE is a voluntary initiative launched at the White House in July 2025, with Amazon, Apple, Google, Anthropic, OpenAI and 60+ other organisations pledging commitment. CMS plans to add a patient app library to Medicare.gov — early participation is a significant distribution and credibility opportunity. |
| :---- |

## **8.1 Initiative Overview**

The CMS Health Technology Ecosystem (HTE) is a voluntary collaboration initiative announced at a White House 'Make Health Tech Great Again' event on 30 July 2025\. CMS describes it as 'a bold new vision built on collaboration, not just compliance,' calling on health app developers, EHR vendors, providers, payers, and data networks to voluntarily align around a shared interoperability framework. CMS will add a library of certified patient apps to Medicare.gov, giving HealthKey significant organic distribution among US Medicare beneficiaries if included \[CMS-HTE\].

The HTE organises participation into categories. HealthKey is relevant primarily to the Patient-Facing Apps — Kill the Clipboard category, whose pledge text reads: 'We pledge to empower patients to retrieve their health records from CMS Aligned Networks or personal health record apps and share them with providers via QR codes or Smart Health Cards/Links using FHIR bundles. When possible, we will return visit records to patients in the same format. We commit to seamless, secure data exchange — eliminating the need for patients to repeatedly recall and write out their medical history.' \[CMS-KTC\]

The MVP requirements for patient-facing apps are defined in the CMS HTE MVP Requirements document \[CMS-MVP\] and the accompanying PPTX \[CMS-KTC-PPTX\]. The following requirements are directly derived from those documents and from the CMS interoperability framework.

## **8.2 Identity & Authentication Requirements (CMS)**

The CMS framework requires that patients can retrieve their records without portal logins. This is described as 'one of the most radical burden-reduction shifts in the HTE initiative' \[CMS-MVP\]. IAL2 (Identity Assurance Level 2\) verified identity replaces passwords and portal accounts as the access mechanism. HealthKey's existing identity verification requirement (PAT-001) must be extended to meet CMS IAL2 standards.

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| CMS-001 | **IAL2 Identity Verification** | The HealthKey patient app must integrate with CMS-approved credential service providers (CSPs) using IAL2 verification. The MVP document names CLEAR and ID.me as approved services. IAL2-verified identity — not portal credentials — must be sufficient to retrieve patient records from CMS Aligned Networks. No additional HIPAA authorisation forms should be required for patient access requests. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-002 | **AAL2 Authentication** | The app must support Authentication Assurance Level 2 (AAL2) authentication mechanisms, specifically passkeys and mobile driver's licenses (mDLs). This eliminates password-based authentication for returning users and satisfies the CMS security baseline for trusted data exchange. | Must Have | CMS-MVP, CMS-HTE |
| CMS-003 | **Digital Credential Generation** | The app must generate and maintain digital tokens (credentials) representing the authenticated patient's identity and permissions. These tokens are presented to CMS Aligned Networks to retrieve data. Credentials must be short-lived, cryptographically signed, and scoped to the specific query. | Must Have | CMS-MVP |
| CMS-004 | **Portal-Free Operation** | At no point in any data retrieval flow may the patient be required to log into a provider portal, remember a portal username or password, or know which specific facility holds their data. The HealthKey app's identity credential alone must be sufficient to unlock data from any participating provider on a CMS Aligned Network. | Must Have | CMS-MVP, CMS-KTC-PPTX |

## **8.3 CMS Aligned Network Data Retrieval**

CMS Aligned Networks are healthcare data networks that meet the CMS Interoperability Framework. They must respond to patient queries for all available data including structured USCDI v3 data and unstructured documents (PDFs, images, clinical notes). HealthKey must be capable of querying these networks on behalf of patients, returning all available data into the PHR record \[CMS-MVP\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| CMS-010 | **CMS Aligned Network Query Capability** | The HealthKey app must be capable of querying CMS Aligned Networks using patient IAL2 credentials to retrieve all available patient data, including from providers the patient cannot name in advance. The network infrastructure locates records — the patient does not need to identify their providers. This eliminates 'provider-guessing' as a barrier. | Must Have | CMS-MVP |
| CMS-011 | **Structured & Unstructured Data Retrieval** | Data retrieved from CMS Aligned Networks must include both structured USCDI v3 data elements and unstructured clinical documents: clinical notes, scanned PDFs, JPEG wound photos, faxed specialist notes, imaging reports. The MVP explicitly prohibits limiting responses to structured data only — all real-world clinical artifacts must be supported. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-012 | **Claims Data Retrieval** | The app must retrieve patient claims and benefits data from participating payers on CMS Aligned Networks, alongside clinical data. Claims data must be presented in the patient dashboard alongside clinical data without requiring a separate payer portal login. | Must Have | CMS-MVP |
| CMS-013 | **Patient-Directed Data Specificity** | Before initiating a network query, the patient must be able to specify what data to retrieve: all data, specific categories (e.g., medications and allergies only), or a defined date range. This preference is stored and reused automatically for future queries unless changed. The app stores only the data the patient specifies — no silent over-collection. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-014 | **Sensitive Data Suppression** | Patients must be able to suppress specific sensitive data categories from retrieval or sharing (e.g., mental health records, substance use, reproductive health). Selective disclosure preferences must be honoured and persist across queries. | Must Have | CMS-MVP |

## **8.4 Kill the Clipboard — Provider Check-In Flow**

The Kill the Clipboard (KtC) use case is the patient-facing scenario where HealthKey enables a patient to share their selected health records with a provider at check-in, replacing paper intake forms. This is described in the MVP requirements as requiring: no EHR portal sign-in, data sourced from CMS Aligned Networks and patient-added data, a dynamic QR code pointing to FHIR resources, and SMART Health Link (SHL) functionality \[CMS-MVP, CMS-KTC-PPTX\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| CMS-020 | **SMART Health Link (SHL) Generation** | The HealthKey app must generate SMART Health Links representing a patient's selected health record subset. An SHL is a live, encrypted pointer to FHIR resources — not a static data snapshot. It enables real-time access when presented to a provider. SHLs must have configurable expiry times; they must never contain raw PHI or long-lived tokens. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-021 | **SMART Health Card (SHC) Generation** | For static, verifiable presentations of specific health facts (e.g., vaccination records, medication list snapshot), the app must generate cryptographically signed SMART Health Cards. SHCs are patient-controlled QR-based presentations that can be verified by providers without a network query. | Should Have | CMS-HTE, CMS-KTC-PPTX |
| CMS-022 | **Dynamic QR Code Generation** | The app must generate a dynamic QR code that encodes the SMART Health Link (not raw PHI). The QR code is presented by the patient on their phone at check-in. When scanned by the provider, it resolves and decrypts the patient-selected FHIR data bundle. QR codes must be time-limited and must not embed PHI directly. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-023 | **Patient Record Selection for Sharing** | Before generating a QR code or SHL, the patient selects which data to include in the share: full record, specific categories, or a specific date range. The same preference controls applied to network queries (CMS-013) apply to provider-facing shares. The patient retains full control of what is shared at each encounter. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-024 | **FHIR Bundle Preparation for Share** | The app must assemble the patient-selected data into a standards-compliant FHIR R4 bundle for sharing via SHL. The bundle must also include a PDF summary of the shared data for providers whose systems cannot ingest structured FHIR. Both formats must be delivered when the QR code is resolved. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-025 | **Post-Encounter Visit Record Retrieval** | After a clinical encounter, the app should enable the patient to retrieve a visit summary (notes, diagnoses, instructions, medication changes) from the provider in FHIR format via the same SHL mechanism used at check-in. This closes the loop: patients share in, and retrieve their summary out, in the same standard. | Should Have | CMS-MVP, CMS-KTC-PPTX, CMS-HTE |
| CMS-026 | **Patient-Added Data in Shares** | In addition to provider-sourced data, the KtC share bundle must include patient-added data: symptom logs, wearable data, manually uploaded documents, and patient notes. This fulfils the CMS requirement that the KtC experience includes patient-contributed data alongside CMS Aligned Network data. | Must Have | CMS-MVP |

## **8.5 App Certification & Trust Framework**

To participate in the CMS HTE as a patient-facing app, HealthKey must meet the CARIN Code of Conduct and achieve certification from DirectTrust or the DiME (Digital Me) seal. These certifications assure patients and providers that the app handles data ethically, communicates clearly, and meets transparency and privacy standards \[CMS-MVP\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| CMS-030 | **CARIN Code of Conduct Compliance** | HealthKey must comply with the CARIN Alliance Code of Conduct, which covers: transparent privacy policies written in plain language, clear disclosure of how patient data is used, no data selling or advertising use, patient right to access and delete their data, and prohibition on data use for underwriting or employment decisions. The CARIN Code is foundational to CMS Aligned App trust. | Must Have | CMS-MVP |
| CMS-031 | **DirectTrust or DiME Certification** | The HealthKey app must obtain certification from DirectTrust or the DiME seal to demonstrate meeting established industry transparency, privacy, and security criteria required by CMS for patient-facing apps. Certification must be maintained and renewed per the certifying body's schedule. | Must Have | CMS-MVP |
| CMS-032 | **HITRUST Certification** | CMS-aligned networks must be HITRUST certified. As a patient-facing app connecting to these networks, HealthKey should pursue HITRUST CSF certification to demonstrate the same rigorous security and compliance baseline. HITRUST does not replace HIPAA compliance but supplements it. | Should Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-033 | **Purpose of Use Declaration** | Every data request made by the HealthKey app on behalf of a patient must declare a valid HL7 Purpose of Use (PoU) code: Patient Access (for the patient retrieving their own data) or Treatment (for provider-directed requests). PoU must travel with the request so downstream systems can apply correct disclosure policies. | Must Have | CMS-MVP |

## **8.6 Audit Transparency (CMS)**

The CMS Interoperability Framework requires patient-level audit logs showing who accessed patient data, when, for what purpose, and which organisations were involved. HealthKey's existing audit log requirement (PAT-052) must be extended to meet the specific CMS requirements and integrate with network-level audit logs from CMS Aligned Networks \[CMS-MVP\].

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| CMS-040 | **Patient-Visible Audit Log (CMS)** | The HealthKey app must display a complete patient-visible audit log meeting CMS requirements: who accessed or received data (at organisation level minimum), when the access occurred, which purpose of use was declared, and which CMS Aligned Network facilitated the exchange. Presented in plain language in the patient dashboard. | Must Have | CMS-MVP, CMS-KTC-PPTX |
| CMS-041 | **Network Audit Log Integration** | HealthKey must consume and display audit log entries produced by CMS Aligned Networks for queries made on the patient's behalf. These network-level logs supplement HealthKey's own application-level logs and give patients the full picture of how their data has moved through the ecosystem. | Must Have | CMS-MVP |
| CMS-042 | **Share Audit Trail for KtC** | Every Kill the Clipboard share event — QR code generated, scanned, data retrieved by provider — must be logged and visible to the patient. The patient can see which provider scanned their code, when, and what data was retrieved. | Must Have | CMS-MVP, CMS-KTC-PPTX |

## **8.7 Strategic Rationale & Positioning**

| Why Kill the Clipboard participation matters for HealthKey: 1\. Medicare.gov app library: CMS plans to add compliant apps to Medicare.gov, providing direct distribution to tens of millions of US Medicare beneficiaries — HealthKey's primary patient population (cancer patients skew older). 2\. Provider network effects: Every provider who accepts a KtC QR code at check-in becomes a distribution point for HealthKey — patients who see the scan workflow want the app. 3\. Competitive moat: Early adopter status (pledging before December 2025\) creates a trust signal and regulatory alignment advantage over later entrants. Massive Bio (an oncology trial matching competitor) has already pledged. 4\. Data completeness: CMS Aligned Network queries surface records the patient didn't know existed — including claims data from payers — dramatically improving PHR completeness without patient effort. 5\. Alignment with founding vision: The Harvard-Radcliffe workshop described exactly this infrastructure — FHIR-based portal-free record retrieval — as the required architectural milestone before more advanced services become possible \[CB-1\]. |
| :---- |

*Note: The CMS-HTE section references three additional source codes not in the original source table:*

* CMS-MVP: CMS HTE MVP Requirements document (provided)

* CMS-KTC-PPTX: CMS HTE MVP Criteria slide deck (provided)

* CMS-HTE: CMS Health Tech Ecosystem website — cms.gov/priorities/health-technology-ecosystem

* CMS-KTC: CMS Early Adopters — Kill the Clipboard page — cms.gov/health-tech-ecosystem/early-adopters/kill-the-clipboard

# **9\. Non-Functional Requirements**

## **9.1 Security & Compliance**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| NFR-001 | **HIPAA Compliance** | The system must comply with HIPAA Privacy and Security Rules. A BAA must be signed with all infrastructure providers. Administrative, physical, and technical safeguards must be documented and audited annually. | Must Have | HK-W |
| NFR-002 | **GDPR Compliance** | The system must comply with GDPR for EU/UK patients. Data subject rights (access, erasure, portability, objection) must be implemented. A DPIA must be completed before launch. | Must Have | HK-W |
| NFR-003 | **Encryption** | All data at rest must be encrypted using AES-256. All data in transit must use TLS 1.3 minimum. Encryption keys must be managed via a dedicated KMS. | Must Have | HK-W |
| NFR-004 | **SOC 2 Type II** | The platform must achieve SOC 2 Type II certification covering Security, Availability, and Confidentiality trust service criteria within 12 months of production launch. | Must Have | HK-W |
| NFR-005 | **Data Residency** | Patients can choose their data residency region (UK, EU, US). Data must not cross jurisdictional boundaries without explicit patient authorisation. Enterprise plans support on-premises deployment. | Must Have | HK-W |
| NFR-006 | **Zero Data Selling** | Patient personal data must never be sold, licensed, or shared with advertisers or third parties without explicit patient consent. This is a non-negotiable commercial commitment, consistent with Novellia's model \[NOV\] and the Harvard-Radcliffe principles \[CB-1\]. | Must Have | HK-W, CB-1 |

## **9.2 Performance**

| ID | Requirement | Description | Priority | Source |
| :---- | :---- | :---- | :---- | :---- |
| NFR-010 | **Trial Match Latency** | Clinical trial eligibility screening using PatientInfo must complete in under 2 seconds for a patient with a fully populated record. This is the real-time performance requirement enabling instant eligibility feedback. | Must Have | HK-A |
| NFR-011 | **Record View Load Time** | The patient's longitudinal timeline view must load in under 3 seconds for a record with up to 10,000 clinical events. Lab trend charts must render in under 1 second. | Must Have | HK-W |
| NFR-012 | **ETL Processing Time** | A full FHIR bundle import for a patient with 5 years of history must complete ETL processing within 30 minutes. Incremental sync updates (new data only) must complete within 5 minutes. | Must Have | HK-A |
| NFR-013 | **Research Query Performance** | Standard Achilles characterisation queries on a cohort of up to 100,000 patients must complete within 60 minutes. PatientInfo-based queries must return results within 10 seconds. | Should Have | HK-A |
| NFR-014 | **Availability** | The patient-facing application must achieve 99.9% uptime. The research analytics platform must achieve 99.5% uptime. Planned maintenance must be communicated at least 48 hours in advance. | Must Have | HK-W |

## **9.3 Adoption & Engagement Metrics**

Targets derived from the SMART goals established at the Harvard-Radcliffe workshop \[CB-1\]:

* Patient signups: 13 million within five years of launch (approximately 5% of US adults — a proven tipping point for platform adoption).

* Engagement: each user logs at least one session per year within two years.

* Referrals: 5% of users refer a peer within two years of joining.

* Satisfaction: two-thirds of users rate the service as valuable.

* Provider participation: 20% of FHIR-adopting providers push data within five years.

* Caregiver enablement: 5% of users have linked a caregiver account within two years.

# **10\. Out of Scope for V1**

The following capabilities are recognised as valuable but are explicitly deferred from the initial release to maintain focus:

| Capability | Rationale for Deferral | Target Version |
| :---- | :---- | :---- |
| Bidirectional provider data exchange | Requires provider-side integration agreements and governance framework beyond V1 scope | V2 |
| Patient data royalties | Monetisation of patient data contributions requires legal, tax, and trust infrastructure | V3 |
| Imaging & DICOM analysis | AI-assisted imaging analysis requires significant specialist ML infrastructure | V2 |
| Non-oncology disease modules | Initial release focused on oncology where CancerBot provides domain expertise and trial-matching infrastructure | V2 |
| Federated network queries (OHDSI model) | Distributed network analytics across institutional OMOP instances requires governance not needed for hosted PHR model | V3 |
| Genomic sequencing interpretation | Raw WGS/WES interpretation is out of scope; structured variant results (e.g., BRCA, EGFR) are in scope | V2 |
| Provider-facing EHR integration (write-back) | Depends on provider agreement, regulatory approval, and V2 bidirectional exchange | V3 |

HealthKey, Inc.  ·  Product Requirements Definition v1.1  ·  April 2026  ·  Confidential