# HealthKey — Patient App Requirements

**Sources:** `Allen_claude_prototype` (UX reference), `docs/PRD.md` (product requirements), `docs/patient-info.md` (field-level data model from `cancerbot/ui.v2`)  
**Scope:** Patient-facing application only (PRD Section 5 + CMS Section 8)  
**Date:** April 2026

---

## How to Read This Document

Each requirement is tagged with:
- **Status:** `To Build` (reference design exists in `Allen_claude_prototype`), `To Design` (no reference design — needs UX work), or `Gap` (needs specification before design can begin)
- **Priority:** `Must Have` / `Should Have` / `Could Have` (from PRD where assigned)
- **PRD Ref:** requirement ID from PRD.md

---

## 1. Identity Verification & Onboarding

### 1.1 Account Creation & Authentication

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 1.1.1 | Patients can create an account using email/password or social sign-in (Apple, Google) | To Build | Must Have | PAT-002 |
| 1.1.2 | Password strength meter with minimum requirements (8+ chars, uppercase, number, special char) | To Build | Must Have | PAT-002 |
| 1.1.3 | Terms & conditions agreement required on sign-up | To Build | Must Have | PAT-002 |
| 1.1.4 | Show/hide password toggle | To Build | Must Have | — |
| 1.1.5 | Multi-factor authentication (MFA) required for all accounts holding health data | To Design | Must Have | PAT-002 |
| 1.1.6 | Passkey and mobile driver's licence (mDL) authentication (AAL2) | To Design | Must Have | CMS-002 |
| 1.1.7 | Bank-grade identity verification (IAL2 via CLEAR or ID.me) before any data import | To Design | Must Have | PAT-001, CMS-001 |
| 1.1.8 | Portal-free operation: no provider portal login required to retrieve records | To Design | Must Have | CMS-004 |

### 1.2 Onboarding Flow

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 1.2.1 | Guided multi-step onboarding: Welcome → Auth → Identity → Conditions → Lifestyle → Family → (Disease Profile) → Summary | To Build | Must Have | PAT-005 |
| 1.2.2 | Linear progress bar with step indicators throughout onboarding | To Build | Must Have | PAT-005 |
| 1.2.3 | Each data step offers three input modes: Manual, Upload, Connect EHR | To Build | Must Have | PAT-005 |
| 1.2.4 | Wearable/device sync available as a fourth input mode on relevant steps | To Build | Should Have | PAT-013 |
| 1.2.5 | "Skip for now" option on every data step — no forced completion | To Build | Must Have | PAT-005 |
| 1.2.6 | Onboarding completable in under 5 minutes | Gap | Must Have | PAT-005 |
| 1.2.7 | Disease Profile step conditionally unlocked only when user selects cancer diagnoses | To Build | Must Have | — |
| 1.2.8 | Completion percentage indicator on summary screen (animated circular SVG) | To Build | Should Have | — |
| 1.2.9 | "Start over" option on summary screen | To Build | Could Have | — |

### 1.3 Caregiver & Multi-Patient Access

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 1.3.1 | Patient can grant delegated access to caregivers with configurable permission levels (view-only, view + add notes) | To Design | Must Have | PAT-003 |
| 1.3.2 | Patient retains full control and can revoke caregiver access at any time | To Design | Must Have | PAT-003 |
| 1.3.3 | Single account can manage records for multiple dependants, each with an isolated record | To Design | Should Have | PAT-004 |

---

## 2. Data Collection — Patient Information Schema

The following data categories map to the Common Patient Information Schema (CB-2) required for clinical trial matching. Field names in `code` match the `cancerbot/ui.v2` API schema (`patient-info.md`) and the HealthKey backend.

### 2.1 Core Demographics

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.1.1 | `firstName`, `lastName` | string | To Build | Must Have | PAT-020 |
| 2.1.2 | `dob` (date of birth) — displayed as age `patientAge` downstream | date | To Build | Must Have | PAT-020 |
| 2.1.3 | `gender` — select (Male / Female / Non-binary / Prefer not to say) | select | To Build | Must Have | PAT-020 |
| 2.1.4 | `ethnicity` — multiselect; affects lab interpretation (e.g. creatinine reference ranges) | multiselect | To Design | Must Have | PAT-020 |
| 2.1.5 | `height` + units (cm / inches), `weight` + units (kg / lbs); BMI auto-calculated | number + units | To Build | Must Have | PAT-021 |
| 2.1.6 | `country` (from standardised country list), `postalCode` | select / string | To Design | Must Have | PAT-020 |
| 2.1.7 | Geographic coordinates (lat/long) derived from postal code — used for distance-to-trial-site | derived | To Design | Must Have | PAT-020 |
| 2.1.8 | `languagesSkills` — multiselect (languages spoken; stored in PersonLanguageSkill extension) | multiselect | To Build | Should Have | PAT-028 |
| 2.1.9 | Insurance status, employment status | select | To Design | Should Have | PAT-028 |
| 2.1.10 | Document upload for identity: passport, insurance card, government ID | file | To Build | Must Have | PAT-012 |
| 2.1.11 | AI-assisted extraction of structured data from uploaded identity documents | — | Gap | Must Have | PAT-012 |

### 2.2 Medical History & Conditions

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.2.1 | Chronic condition selection from curated list (diabetes, hypertension, asthma, COPD, heart disease, hypothyroidism, depression/anxiety, arthritis, IBS/Crohn's, MS, lupus, kidney disease) | multiselect chips | To Build | Must Have | PAT-023 |
| 2.2.2 | `disease` — primary cancer diagnosis (multiple myeloma, breast, follicular lymphoma, CLL, lung, prostate, colorectal, melanoma, other) | select | To Build | Must Have | PAT-022 |
| 2.2.3 | `preExistingConditionCategories` — prior malignancies, cardiac, autoimmune, neurologic conditions | multiselect | To Design | Must Have | PAT-023 |
| 2.2.4 | `noOtherActiveMalignancies` — boolean; YES = patient does NOT have other active cancers | boolean | To Design | Must Have | PAT-023 |
| 2.2.5 | `noActiveInfectionStatus` — boolean; YES = no active infections | boolean | To Design | Must Have | PAT-023 |
| 2.2.6 | `peripheralNeuropathyGrade` — nerve damage severity (0–4) | number | To Design | Must Have | PAT-023 |
| 2.2.7 | Drug allergies — free-text tag input | tags | To Build | Must Have | PAT-023 |
| 2.2.8 | Current medications — free-text tag input | tags | To Build | Must Have | PAT-023 |
| 2.2.9 | Surgical history — free-text tag input | tags | To Build | Must Have | PAT-023 |
| 2.2.10 | Document upload: discharge summaries, lab results, clinical documents | file | To Build | Must Have | PAT-012 |
| 2.2.11 | Cancer fields visually distinguished with rose/red accent | — | To Build | Should Have | — |

### 2.3 Lifestyle & Behavioural Factors

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.3.1 | `noTobaccoUseStatus` — boolean (YES = non-user); also collect frequency detail: Never / Former / Occasional / Daily | boolean + select | To Build | Must Have | PAT-027 |
| 2.3.2 | Alcohol frequency: None / Rarely / Socially / Weekly / Daily | select | To Build | Must Have | PAT-027 |
| 2.3.3 | Exercise level: Sedentary / Light / Moderate / Active | select | To Build | Must Have | PAT-027 |
| 2.3.4 | Diet type: Omnivore / Vegetarian / Vegan / Keto / Gluten-free | select | To Build | Must Have | PAT-027 |
| 2.3.5 | Occupation — free-text | string | To Build | Must Have | PAT-027 |
| 2.3.6 | `consentCapability` — boolean; able to provide informed consent | boolean | To Design | Must Have | PAT-027 |
| 2.3.7 | `noPregnancyOrLactationStatus` — boolean (female only); YES = not pregnant/lactating | boolean | To Design | Must Have | PAT-027 |
| 2.3.8 | `pregnancyTestResult` — select (female only) | select | To Design | Must Have | PAT-027 |
| 2.3.9 | `contraceptiveUse` — select (female only) | select | To Design | Must Have | PAT-027 |
| 2.3.10 | `noSubstanceUseStatus` — boolean; YES = no substance use | boolean | To Design | Must Have | PAT-027 |
| 2.3.11 | `noMentalHealthDisorderStatus` — boolean; YES = no mental health disorders | boolean | To Design | Must Have | PAT-027 |
| 2.3.12 | `caregiverAvailabilityStatus` — boolean; caregiver available | boolean | To Design | Should Have | PAT-028 |
| 2.3.13 | `noGeographicExposureRisk` — boolean; YES = no geographic exposure risk | boolean | To Design | Must Have | PAT-027 |

### 2.4 Family History

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 2.4.1 | Family history matrix: relatives × conditions toggle grid | To Build | Must Have | PAT-023 |
| 2.4.2 | Relatives: Mother, Father, Maternal/Paternal Grandparents, Sibling | To Build | Must Have | PAT-023 |
| 2.4.3 | Conditions: Heart Disease, Diabetes, Cancer, Stroke, Alzheimer's, Mental Health, Kidney Disease | To Build | Must Have | PAT-023 |

### 2.5 Disease Profile — Oncology (Conditional Step)

Displayed only when a cancer diagnosis is selected. Gated by `disease` field. All fields feed directly into trial eligibility screening.

#### 2.5.0 All Cancers — Shared Clinical Status

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.5.0.1 | `stage` — disease stage; values are disease-specific (see subsections) | select | To Build | Must Have | PAT-022 |
| 2.5.0.2 | `ecogPerformanceStatus` — ECOG score (0–5) | number | To Build | Must Have | PAT-022 |
| 2.5.0.3 | `karnofskyPerformanceScore` — Karnofsky score (0–100) | number | To Design | Must Have | PAT-022 |
| 2.5.0.4 | `systolicBloodPressure`, `diastolicBloodPressure` | number | To Design | Must Have | PAT-021 |
| 2.5.0.5 | Upload: pathology reports, bone marrow biopsies, imaging results | file | To Build | Must Have | PAT-012 |
| 2.5.0.6 | Disease profile annotated as powering trial eligibility matching | — | To Build | Should Have | PAT-060 |

#### 2.5.1 Multiple Myeloma–Specific

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.5.1.1 | `stage` — ISS Stage I / II / III / Unknown | select | To Build | Must Have | PAT-022 |
| 2.5.1.2 | `monoclonalProteinSerum` — M-spike serum (g/dL) | number | To Design | Must Have | PAT-026 |
| 2.5.1.3 | `monoclonalProteinUrine` — M-spike urine (mg/24h) | number | To Design | Must Have | PAT-026 |
| 2.5.1.4 | M-protein type: IgG / IgA / IgM / Light chain / Unknown | select | To Build | Must Have | PAT-026 |
| 2.5.1.5 | `kappaFLC` — kappa free light chain; `lambdaFLC` — lambda free light chain | number | To Design | Must Have | PAT-026 |
| 2.5.1.6 | `clonalPlasmaCells` — bone marrow plasma cell % (BMPC) | number | To Build | Must Have | PAT-026 |
| 2.5.1.7 | `progression` — disease status / treatment status (Newly diagnosed / Relapsed / Refractory / Remission) | select | To Build | Must Have | PAT-025 |
| 2.5.1.8 | Prior lines of therapy — tag input (e.g. VRd, Daratumumab, ASCT) | tags | To Build | Must Have | PAT-025 |
| 2.5.1.9 | `cytogenicMarkers` — chromosomal abnormalities (multiselect) | multiselect | To Design | Must Have | PAT-026 |
| 2.5.1.10 | `molecularMarkers` — molecular/genetic markers (multiselect) | multiselect | To Design | Must Have | PAT-026 |
| 2.5.1.11 | `plasmaCellLeukemia` — boolean | boolean | To Design | Must Have | PAT-026 |
| 2.5.1.12 | `meetsCRAB` — calculated: Calcium/Renal/Anemia/Bone criteria met | calculated | To Design | Must Have | PAT-022 |
| 2.5.1.13 | `meetsSLIM` — calculated: SLIM-CRAB criteria met | calculated | To Design | Must Have | PAT-022 |
| 2.5.1.14 | `measurableDiseaseImwg` — calculated: IMWG measurable disease criteria | calculated | To Design | Must Have | PAT-022 |
| 2.5.1.15 | `lactateDehydrogenaseLevel` — LDH | number | To Design | Must Have | PAT-024 |
| 2.5.1.16 | `serumBeta2MicroglobulinLevel` | number | To Design | Must Have | PAT-024 |

#### 2.5.2 Breast Cancer–Specific

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.5.2.1 | `estrogenReceptorStatus` — ER negative / positive / low / high | select | To Design | Must Have | PAT-026 |
| 2.5.2.2 | `progesteroneReceptorStatus` — PR negative / positive / low / high | select | To Design | Must Have | PAT-026 |
| 2.5.2.3 | `her2Status` — HER2 negative / positive / low (IHC and FISH) | select | To Design | Must Have | PAT-026 |
| 2.5.2.4 | `tnbcStatus` — triple-negative breast cancer; calculated from ER/PR/HER2 | calculated | To Design | Must Have | PAT-026 |
| 2.5.2.5 | `hrdStatus` — homologous recombination deficiency | select | To Design | Must Have | PAT-026 |
| 2.5.2.6 | `menopausalStatus` — pre-menopausal / post-menopausal | select | To Design | Must Have | PAT-026 |
| 2.5.2.7 | `histologicType` — specific histological type | select | To Design | Must Have | PAT-022 |
| 2.5.2.8 | `biopsyGrade` — tumor differentiation grade (1–3) | number | To Design | Must Have | PAT-022 |
| 2.5.2.9 | TNM staging: `tumorStage` (T), `nodesStage` (N), `distantMetastasisStage` (M) | select | To Design | Must Have | PAT-022 |
| 2.5.2.10 | `stagingModalities` — cTNM (clinical) vs pTNM (pathological) | select | To Design | Must Have | PAT-022 |
| 2.5.2.11 | `metastaticStatus` — boolean | boolean | To Design | Must Have | PAT-022 |
| 2.5.2.12 | `boneOnlyMetastasisStatus` — spread limited to bones only | boolean | To Design | Must Have | PAT-022 |
| 2.5.2.13 | `measurableDiseaseByRecistStatus` — RECIST criteria met | boolean | To Design | Must Have | PAT-022 |
| 2.5.2.14 | `ki67ProliferationIndex` — cell proliferation rate (%) | number | To Design | Must Have | PAT-026 |
| 2.5.2.15 | `pdL1TumorCels` — PD-L1 expression on tumour cells (%); `pdL1IcPercentage` — PD-L1 on immune cells (%); `pdL1CombinedPositiveScore` (CPS); `pdL1Assay` — assay type used | number / select | To Design | Must Have | PAT-026 |
| 2.5.2.16 | Genetic mutations array — dynamic, auto-grows: `gene` (BRCA1, BRCA2, TP53, PIK3CA, ESR1, etc.) / `variant` / `origin` (somatic/germline) / `interpretation` (clinical significance) | array | To Design | Must Have | PAT-026 |

#### 2.5.3 Follicular Lymphoma–Specific

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.5.3.1 | `flipiScoreOptions` — FLIPI risk factors: age, stage, haemoglobin, nodal areas, LDH | multiselect | To Design | Must Have | PAT-022 |
| 2.5.3.2 | `gelfCriteriaStatus` — GELF criteria met | multiselect | To Design | Must Have | PAT-022 |
| 2.5.3.3 | `tumorGrade` — FL grade (1 / 2 / 3A / 3B) | select | To Design | Must Have | PAT-022 |

#### 2.5.4 Chronic Lymphocytic Leukaemia (CLL)–Specific

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.5.4.1 | `cytogenicMarkers` — chromosomal markers (multiselect) | multiselect | To Design | Must Have | PAT-026 |
| 2.5.4.2 | `molecularMarkers` — molecular markers (multiselect) | multiselect | To Design | Must Have | PAT-026 |
| 2.5.4.3 | `tp53Disruption` — TP53 disruption status | select | To Design | Must Have | PAT-026 |
| 2.5.4.4 | `binetStage` — Binet staging | select | To Design | Must Have | PAT-022 |
| 2.5.4.5 | `diseaseActivity` — disease activity level | select | To Design | Must Have | PAT-022 |
| 2.5.4.6 | `measurableDiseaseIwcll` — IWCLL criteria | select | To Design | Must Have | PAT-022 |
| 2.5.4.7 | `tumorBurden` — disease burden level | select | To Design | Must Have | PAT-022 |
| 2.5.4.8 | `lymphocyteDoublingTime` + units — time for lymphocyte count to double | number | To Design | Must Have | PAT-022 |
| 2.5.4.9 | `proteinExpressions` — protein expression markers (multiselect) | multiselect | To Design | Must Have | PAT-026 |
| 2.5.4.10 | `richterTransformation` — boolean | boolean | To Design | Must Have | PAT-022 |
| 2.5.4.11 | `lymphadenopathy`, `splenomegaly`, `hepatomegaly` — lymph node / spleen / liver enlargement | select | To Design | Must Have | PAT-022 |
| 2.5.4.12 | `clonalBoneMarrowBLymphocytes` — clonal B-lymphocytes in bone marrow (%) | number | To Design | Must Have | PAT-026 |
| 2.5.4.13 | `clonalBLymphocyteCount` + units — absolute clonal B-lymphocyte count | number | To Design | Must Have | PAT-026 |
| 2.5.4.14 | `autoimmuneCytopeniasRefractoryToSteroids` — boolean | boolean | To Design | Must Have | PAT-023 |
| 2.5.4.15 | `btkInhibitorRefractory` — BTK inhibitor resistance | boolean | To Design | Must Have | PAT-025 |
| 2.5.4.16 | `bcl2InhibitorRefractory` — BCL-2 inhibitor resistance | boolean | To Design | Must Have | PAT-025 |

### 2.6 Laboratory Values

All numeric lab fields must store value + units. Units stored alongside values — unit conversion failures break matching logic.

#### 2.6.1 CBC (Complete Blood Count) & Haematology

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.1.1 | `whiteBloodCellCount` | number + units | To Design | Must Have | PAT-024 |
| 2.6.1.2 | `hemoglobinLevel` | number + units | To Design | Must Have | PAT-024 |
| 2.6.1.3 | `plateletCount` | number + units | To Design | Must Have | PAT-024 |
| 2.6.1.4 | `absoluteNeutrophileCount` (ANC) | number + units | To Design | Must Have | PAT-024 |
| 2.6.1.5 | `absoluteLymphocyteCount` (ALC) | number + units | To Design | Must Have | PAT-024 |

#### 2.6.2 Renal Function

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.2.1 | `serumCreatinineLevel` | number + units | To Design | Must Have | PAT-024 |
| 2.6.2.2 | `creatinineClearanceRate` | number + units | To Design | Must Have | PAT-024 |
| 2.6.2.3 | `estimatedGlomerularFiltrationRate` (eGFR) — calculated from creatinine + demographics | calculated | To Design | Must Have | PAT-024 |
| 2.6.2.4 | `renalAdequacyStatus` — adequacy classification | select | To Design | Must Have | PAT-024 |
| 2.6.2.5 | `serumCalciumLevel` | number + units | To Design | Must Have | PAT-024 |

#### 2.6.3 Liver Function

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.3.1 | `liverEnzymeLevelsAst` (AST) | number + units | To Design | Must Have | PAT-024 |
| 2.6.3.2 | `liverEnzymeLevelsAlt` (ALT) | number + units | To Design | Must Have | PAT-024 |
| 2.6.3.3 | `liverEnzymeLevelsAlp` (ALP) | number + units | To Design | Must Have | PAT-024 |
| 2.6.3.4 | `serumBilirubinLevelTotal`, `serumBilirubinLevelDirect` | number + units | To Design | Must Have | PAT-024 |
| 2.6.3.5 | `albumin` | number + units | To Design | Must Have | PAT-024 |

#### 2.6.4 Cardiac & Pulmonary

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.4.1 | `ejectionFraction` — cardiac function (%) | number | To Design | Must Have | PAT-021 |
| 2.6.4.2 | `qtcfValue` — QTcF interval; required for targeted therapies | number | To Design | Must Have | PAT-021 |
| 2.6.4.3 | `pulmonaryFunctionTestResult` | boolean / text | To Design | Must Have | PAT-021 |

#### 2.6.5 Bone & Imaging

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.5.1 | `boneImagingResult` | boolean / text | To Design | Must Have | PAT-022 |
| 2.6.5.2 | `boneLesions` — boolean | boolean | To Design | Must Have | PAT-022 |
| 2.6.5.3 | `boneMarrowInvolvement` — boolean | boolean | To Design | Must Have | PAT-022 |

#### 2.6.6 Infection Screen

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.6.1 | `noHivStatus` — YES = HIV negative | boolean | To Design | Must Have | PAT-023 |
| 2.6.6.2 | `noHepatitisBStatus` — YES = Hepatitis B negative | boolean | To Design | Must Have | PAT-023 |
| 2.6.6.3 | `noHepatitisCStatus` — YES = Hepatitis C negative | boolean | To Design | Must Have | PAT-023 |

#### 2.6.7 General / Other

| # | Field | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.6.7.1 | HbA1c, LDL | number + units | To Design | Must Have | PAT-024 |
| 2.6.7.2 | Lab values displayed as time-series trend charts with reference range overlays | — | To Design | Must Have | PAT-041 |
| 2.6.7.3 | Out-of-range values highlighted in plain view | — | To Build | Must Have | PAT-041 |

### 2.7 Treatment History

| # | Field / Requirement | Type | Status | Priority | PRD Ref |
|---|---|---|---|---|---|
| 2.7.1 | `priorTherapy` — None / One line / Two lines / More than two lines | select | To Design | Must Have | PAT-025 |
| 2.7.2 | `treatmentRefractoryStatus` — Refractory / Relapsed / Responsive | select | To Design | Must Have | PAT-025 |
| 2.7.3 | `relapseCount` — number of relapses | number | To Design | Must Have | PAT-025 |
| 2.7.4 | `stemCellTransplantHistory` — SCT history | multiselect / text | To Design | Must Have | PAT-025 |
| 2.7.5 | `concomitantMedications` — concurrent medications | multiselect | To Design | Must Have | PAT-025 |
| 2.7.6 | `plannedTherapies` — scheduled/planned treatments | multiselect | To Design | Should Have | PAT-025 |
| 2.7.7 | Therapy lines (dynamic, structured): `firstLineTherapy` / `firstLineDate` / `firstLineOutcome`; second line (enabled only when prior therapy ≥ 2 lines); later lines (shown for 2+ lines) | array | To Design | Must Have | PAT-025 |
| 2.7.8 | Supportive therapies — dynamic array: `therapy` + `date`; auto-grows when last row completed | array | To Design | Must Have | PAT-025 |
| 2.7.9 | Washout durations and CTCAE toxicity grades per therapy line | — | To Design | Must Have | PAT-025 |

---

## 3. Data Import & Provider Connection

### 3.1 FHIR / EHR Connection

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 3.1.1 | Connect to provider EHRs via FHIR R4 API, authorised via patient OAuth | To Build | Must Have | PAT-010 |
| 3.1.2 | Support simultaneous connections to multiple EHR systems (Epic, Oracle Cerner, Allscripts, athenahealth, MEDITECH) | To Build | Must Have | PAT-010, PAT-011 |
| 3.1.3 | Data from different sources deduplicated and reconciled, not stacked | To Design | Must Have | PAT-011 |
| 3.1.4 | Connected sources display sync status: "Synced just now" with LIVE badge | To Build | Must Have | PAT-016 |
| 3.1.5 | Continuous sync on configurable schedule (minimum: daily); new data triggers patient notification | To Design | Must Have | PAT-015 |
| 3.1.6 | Every import event logged with timestamp, source, and result | To Design | Must Have | PAT-016 |
| 3.1.7 | Failed imports surface clear error messages and recovery guidance | To Design | Must Have | PAT-016 |
| 3.1.8 | Query CMS Aligned Networks using IAL2 patient credentials — no prior knowledge of provider required | To Design | Must Have | CMS-010 |
| 3.1.9 | Retrieve both structured USCDI v3 data and unstructured clinical documents (PDFs, images, notes) | To Design | Must Have | CMS-011 |
| 3.1.10 | Retrieve claims and benefits data from participating payers via CMS Aligned Networks | To Design | Must Have | CMS-012 |

### 3.2 Document Upload

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 3.2.1 | Upload via camera, scan, or file picker on each data entry step | To Build | Must Have | PAT-012 |
| 3.2.2 | Supported formats: PDF, JPEG/PNG images, DICOM, discharge summaries | To Design | Must Have | PAT-012 |
| 3.2.3 | AI extraction of structured data from uploaded documents | To Build | Must Have | PAT-012 |
| 3.2.4 | Non-parseable documents stored as attachments linked to the record | To Design | Must Have | PAT-012 |
| 3.2.5 | Files encrypted before leaving the device | To Build | Must Have | PAT-012 |
| 3.2.6 | Patient-specified data retrieval scope: all data, specific categories, or date range | To Design | Must Have | CMS-013 |
| 3.2.7 | Sensitive data suppression (mental health, substance use, reproductive health) | To Design | Must Have | CMS-014 |

### 3.3 Wearable & Device Integration

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 3.3.1 | Connect wearable devices: Apple Health, Fitbit/Google Fit, Garmin, Dexcom, Omron, Withings | To Build | Should Have | PAT-013 |
| 3.3.2 | Device data stored in OMOP Observation and Measurement tables | To Design | Should Have | PAT-013 |
| 3.3.3 | Auto-sync toggle in settings (wearables continuous sync) | To Build | Should Have | PAT-013 |

---

## 4. Health Record Vault (Post-Onboarding Dashboard)

### 4.1 Home Tab

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 4.1.1 | Personalised greeting with time of day (Good morning/afternoon/evening, [Name]) | To Build | Should Have | — |
| 4.1.2 | PPR completion indicator (circular progress, status label, last-updated timestamp) | To Build | Must Have | — |
| 4.1.3 | Recent activity feed (record creation, EHR syncs, encryption events) | To Build | Should Have | PAT-016 |
| 4.1.4 | Quick actions grid: Share record, Add data, Trial matcher, Export PPR | To Build | Must Have | — |
| 4.1.5 | Scrollable record section cards with progress indicators per category | To Build | Should Have | — |

### 4.2 Records Tab (Longitudinal Record View)

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 4.2.1 | Health records browser with filter by category: All, Identity, Conditions, Lifestyle, Family, Sources | To Build | Must Have | PAT-040 |
| 4.2.2 | Identity card: name, DOB, sex, VERIFIED badge, height/weight | To Build | Must Have | PAT-040 |
| 4.2.3 | Active diagnoses card with condition badges | To Build | Must Have | PAT-040 |
| 4.2.4 | Drug allergies highlighted with amber alert card | To Build | Must Have | PAT-040 |
| 4.2.5 | Lab results panel with out-of-range value highlighting and FHIR badge | To Build | Must Have | PAT-041 |
| 4.2.6 | Lifestyle profile card with emoji-prefixed tags | To Build | Should Have | PAT-040 |
| 4.2.7 | Family history cards per relative with condition list | To Build | Should Have | PAT-040 |
| 4.2.8 | Connected sources cards: EHR (LIVE/FHIR badge) and device (SYNC badge) | To Build | Must Have | PAT-016 |
| 4.2.9 | Full longitudinal timeline view — conditions, medications, procedures, labs chronologically across all providers | To Design | Must Have | PAT-040 |
| 4.2.10 | Filter by date range and provider | To Design | Must Have | PAT-040 |
| 4.2.11 | Lab trend charts with time-series display and reference range overlays | To Design | Must Have | PAT-041 |
| 4.2.12 | Plain-language summaries alongside clinical codes; technical terms link to definitions | To Design | Must Have | PAT-042 |
| 4.2.13 | Medication tracking: active medications, dosage reminders, dose logging | To Design | Should Have | PAT-044 |
| 4.2.14 | Symptom & side effect logging with CTCAE categorisation where applicable | To Design | Should Have | PAT-045 |
| 4.2.15 | Appointment preparation view — curated one-page summary for upcoming appointment | To Design | Should Have | PAT-043 |

### 4.3 Conflict Detection & Resolution

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 4.3.1 | Automated detection of conflicting data between providers (duplicate conditions, conflicting labs, contradictory medication dates) | To Design | Must Have | PAT-030 |
| 4.3.2 | Dashboard flag for detected conflicts | To Design | Must Have | PAT-030 |
| 4.3.3 | Patient-led reconciliation: plain-language explanation of discrepancy, both versions with sources, guided choice of authoritative version | To Design | Must Have | PAT-031 |
| 4.3.4 | All reconciliation decisions logged with timestamp and patient ID; original data preserved | To Design | Must Have | PAT-032 |
| 4.3.5 | Optional: patient can flag a conflict as likely provider-system error and generate a structured report to send back | To Design | Could Have | PAT-033 |

---

## 5. Access Control & Sharing

### 5.1 Share Tab

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 5.1.1 | Generate time-limited, scope-specific access grants for clinicians | To Build | Must Have | PAT-050 |
| 5.1.2 | Scope selection: Identity, Conditions, Lifestyle, Labs, Family History, Disease Profile | To Build | Must Have | PAT-051 |
| 5.1.3 | Duration options: 1 hour, 24 hours, 7 days, 30 days, one-time | To Build | Must Have | PAT-050 |
| 5.1.4 | Access grants displayed with progress bar showing time remaining | To Build | Should Have | — |
| 5.1.5 | Revoke access instantly at any time | To Build | Must Have | PAT-050 |
| 5.1.6 | Access expires automatically; recipient cannot re-share or download | To Build | Must Have | PAT-050 |
| 5.1.7 | Patient can see all active, expired, and revoked access grants | To Build | Must Have | PAT-052 |

### 5.2 QR Code & SMART Health Links

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 5.2.1 | QR code generation for each access grant (with HealthKey branding and animated scan line) | To Build | Must Have | PAT-050, CMS-022 |
| 5.2.2 | QR code encodes a SMART Health Link — not raw PHI | To Design | Must Have | CMS-020, CMS-022 |
| 5.2.3 | SMART Health Links are live encrypted pointers to FHIR resources with configurable expiry | To Design | Must Have | CMS-020 |
| 5.2.4 | Shareable link generated alongside QR code (healthkey.io/r/{token}) | To Build | Must Have | PAT-050 |
| 5.2.5 | QR code can be saved or shared from modal (Save QR, Share link, Preview as recipient) | To Build | Should Have | — |
| 5.2.6 | SMART Health Card (SHC) generation for static verifiable presentations (vaccination records, medication snapshots) | To Design | Should Have | CMS-021 |
| 5.2.7 | FHIR R4 bundle assembled from patient-selected data for sharing, including a PDF summary for non-FHIR providers | To Design | Must Have | CMS-024 |
| 5.2.8 | Patient-added data (wearables, manual entries, uploads) included in share bundles | To Design | Must Have | CMS-026 |
| 5.2.9 | Post-encounter: retrieve visit summary (notes, diagnoses, instructions) from provider via SHL | To Design | Should Have | CMS-025 |

### 5.3 Recipient (Provider) View

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 5.3.1 | Full-screen read-only provider view showing only granted data scopes | To Build | Must Have | PAT-050 |
| 5.3.2 | Patient name, DOB, sex, expiry countdown, and scope badges in branded header | To Build | Must Have | — |
| 5.3.3 | Read-only watermark: data cannot be downloaded, copied, or re-shared | To Build | Must Have | PAT-050 |
| 5.3.4 | Provider can request additional scopes (sent to patient for approval) | To Build | Should Have | — |
| 5.3.5 | Exit button returns provider to neutral view | To Build | Must Have | — |

### 5.4 Access Audit Log

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 5.4.1 | Immutable log of who accessed the record, what they accessed, and when | To Design | Must Have | PAT-052 |
| 5.4.2 | Audit log accessible from Profile tab in plain language | To Build | Must Have | PAT-052 |

### 5.5 Research Consent Management

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 5.5.1 | Patient can opt in to share de-identified data with specific research cohorts/studies | To Design | Must Have | PAT-055 |
| 5.5.2 | Each consent is specific, time-stamped, auditable, and revocable | To Design | Must Have | PAT-055 |
| 5.5.3 | Consent withdrawal immediately removes patient from all active research cohorts | To Design | Must Have | PAT-055 |

---

## 6. Clinical Decision Support

### 6.1 Clinical Trial Matching

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 6.1.1 | Real-time trial eligibility screening against open clinical trials; results in under 2 seconds | To Build | Must Have | PAT-060 |
| 6.1.2 | Ranked list of matched trials with eligibility rationale | To Design | Must Have | PAT-060 |
| 6.1.3 | Trial detail view: NCT number, title, phase, endpoint, sponsor, sites, eligibility criteria with patient status per criterion, estimated duration, contact | To Design | Must Have | PAT-062 |
| 6.1.4 | Push and email notification when a new matching trial opens | To Design | Must Have | PAT-061 |
| 6.1.5 | Filter trials by distance from patient location (uses lat/long from demographics) | To Design | Should Have | PAT-063 |
| 6.1.6 | Disease profile annotated as powering 6,400+ global trial matches | To Build | Should Have | PAT-060 |
| 6.1.7 | Patient twin matching: anonymised profiles of patients with similar clinical histories | To Design | Could Have | PAT-064 |

### 6.2 Standard-of-Care Recommendations

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 6.2.1 | Show standard-of-care options per framework (NCCN, disease-specific guidelines, publications) with framework attribution | To Design | Must Have | PAT-061 |
| 6.2.2 | Probabilistic ranking of treatment options personalised to patient profile, with confidence intervals | To Design | Should Have | PAT-065, RES-041 |

---

## 7. Profile & Settings

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 7.1 | Edit personal info (name, DOB), email, and password from Profile tab | To Build | Must Have | — |
| 7.2 | Auto-sync toggle for wearables | To Build | Should Have | PAT-013 |
| 7.3 | Notifications toggle (labs, trial matches) | To Build | Must Have | PAT-061 |
| 7.4 | Biometric lock toggle (Face ID / fingerprint) | To Build | Should Have | — |
| 7.5 | Export record as FHIR R4 bundle (machine-readable, importable into other systems) | To Build | Must Have | PAT-053 |
| 7.6 | Export record as OMOP-structured data | To Design | Must Have | PAT-054 |
| 7.7 | Export record as PDF summary | To Design | Must Have | CMS-024 |
| 7.8 | Terms of Service and Privacy Policy links | To Build | Must Have | — |
| 7.9 | Sign out | To Build | Must Have | — |

---

## 8. Non-Functional & Platform Requirements

| # | Requirement | Status | Priority | PRD Ref |
|---|---|---|---|---|
| 8.1 | Native mobile application on iOS and Android with feature parity to web for core patient functions | To Design | Must Have | PAT-006 |
| 8.2 | Zero-knowledge AES-256 encryption for all health data | To Build | Must Have | — |
| 8.3 | HIPAA-compliant data handling and audit logging | To Design | Must Have | — |
| 8.4 | FHIR R4 as the primary ingestion and export format | To Build | Must Have | PAT-010, PAT-053 |
| 8.5 | All clinical data stored in OMOP CDM v5.4 with OHDSI standard vocabularies (SNOMED, LOINC, RxNorm, ICD-O-3) | To Design | Must Have | INF-001, INF-005 |
| 8.6 | PatientInfo denormalised flat table maintained for trial matching and AI/ML workloads | To Design | Must Have | INF-004 |
| 8.7 | Every data import, correction, and access event versioned and time-stamped | To Design | Must Have | PAT-032 |
| 8.8 | CMS HTE participation: register as Kill the Clipboard early adopter | To Design | Must Have | CMS-KTC |
| 8.9 | Trial eligibility screening completes in under 2 seconds | To Design | Must Have | PAT-060 |
| 8.10 | All patient data portable and exportable free of charge regardless of account status | To Design | Must Have | PAT-053, PAT-054 |

---

## 9. Data Model & API

### 9.1 Core TypeScript Interfaces

```typescript
// Server response
interface PatientInfo {
  id: string;
  firstName: string;
  lastName: string;
  details: JSONValue; // dynamic object containing all clinical data
}

// Client-side form input
interface PatientInfoInput {
  firstName?: string;
  lastName?: string;
  patientAge?: number;
  gender?: string;
  [key: string]: any; // disease-specific and clinical fields
}
```

### 9.2 API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/patient-info/user/` | Retrieve patient info |
| PATCH | `/api/v1/patient-info/user/` | Update patient info |
| GET | `/api/v1/patient-info/profile-completeness/` | Profile completion percentage |
| GET | `/api/v1/form-settings/` | Available options / dropdown values |

### 9.3 Calculated Fields

The following fields must be recomputed client-side from raw inputs rather than stored as derived values, to avoid stale data:

| Field | Inputs Required |
|---|---|
| `estimatedGlomerularFiltrationRate` (eGFR) | `serumCreatinineLevel`, `patientAge`, `gender`, `ethnicity` |
| `tnbcStatus` | `estrogenReceptorStatus`, `progesteroneReceptorStatus`, `her2Status` |
| `meetsCRAB` | Calcium (`serumCalciumLevel`), Renal (`creatinineClearanceRate`), Anaemia (`hemoglobinLevel`), Bone (`boneLesions`) |
| `meetsSLIM` | SLIM-CRAB components |
| `measurableDiseaseImwg` | M-protein, FLC, BMPC |
| FLIPI score | Age, stage, haemoglobin, nodal areas, LDH |

### 9.4 FHIR Mapping

The cancerbot schema uses a custom structure. The PHR ingestion layer must map FHIR resources to these internal fields:

| Patient-Info Category | FHIR Resource(s) |
|---|---|
| Demographics | `Patient` |
| Disease / diagnosis | `Condition` |
| Genetic mutations | `Observation` (with `valueCodeableConcept`) |
| Lab values | `Observation` (LOINC codes) |
| Treatment lines | `MedicationAdministration`, `Procedure` |
| Supportive therapies | `MedicationAdministration` |
| Performance status | `Observation` (LOINC 89243-0 ECOG, 89247-1 Karnofsky) |
| Imaging / bone results | `ImagingStudy`, `DiagnosticReport` |

**Dynamic arrays** (mutation rows, therapy lines, supportive therapies) map to separate encrypted records in the DB (one FHIR `Observation` or `MedicationAdministration` per row) to enable individual timeline entries rather than opaque blobs.

**Disease-conditional structure**: many fields are disease-gated. The ingestion layer must activate the correct field set based on the `disease` value.

---

## 10. Design System (Derived from Prototype)

### Colors
| Token | Value | Usage |
|---|---|---|
| Primary teal | `#1A8A7A` / `#26B09C` | Primary actions, active states, EHR badges |
| Secondary amber | `#C97D2E` / `#E8963A` | Alerts, warnings, drug allergy cards |
| Accent rose | `#C0435A` | Cancer/oncology fields, disease profile |
| Ink | `#0F1923` | Body text |
| Mist | `#F2F5F7` | Backgrounds, ghost buttons |
| Muted | `#8FA3B1` | Placeholder text, secondary labels |

### Typography
- Headings: Inter
- Body: DM Sans
- 8px spacing grid

### UI Form Controls

| Control | Usage |
|---|---|
| `BooleanControl` | Yes/No toggle or checkbox (e.g. `noHivStatus`, `consentCapability`) |
| `SelectControl` | Single-select dropdown (e.g. `gender`, `stage`, `progression`) |
| `MultiSelectControl` | Multi-select scrollable list (e.g. `ethnicity`, `cytogenicMarkers`) |
| `DateControl` | Date picker (e.g. therapy line dates, DOB) |
| `TextNumberControl` | Text or numeric input with optional units (e.g. lab values, height/weight) |
| `UnitsSelect` | Unit dropdown (kg/lbs, cm/inches, g/dL, etc.) |
| Chip selectors | Multi-select with toggle state; rose variant for cancer fields |
| Tag inputs | Enter/comma delimiter for free-form lists (allergies, medications, treatments) |
| Scale rows | Horizontal scale for staging, ECOG, M-protein type |
| Option rows | Single-select button groups for categorical choices |

### Key Component Patterns
- **Circular SVG progress meter:** Used on Summary screen and Vault Home for PPR completion
- **Bottom-sheet modals:** Dimmed overlay, slide-up animation
- **Cards:** 16px radius, light shadow `0 2px 14px rgba(15,25,35,.08)`
- **Badges:** Small pill-shaped, colour-coded (LIVE, FHIR R4, HIPAA, VERIFIED, SYNC)

---

## 11. Gaps & Open Questions

| # | Gap | Notes |
|---|---|---|
| G-1 | FHIR OAuth integration flow | Prototype shows EHR connection UI but no OAuth handshake spec. Need to define the exact provider-authorization flow for each EHR system. |
| G-2 | AI document parsing accuracy standards | PRD requires AI extraction but sets no accuracy threshold or error-handling UX for failed extractions. |
| G-3 | Conflict resolution UX | No prototype exists. Needs dedicated UX design — this is a core differentiator (PAT-030–033). |
| G-4 | Genomics data capture UI | Breast cancer mutation array (2.5.2.16) and biomarker fields (2.5.2.1–2.5.2.15) need a specialised repeating-row input design. |
| G-5 | Lab results manual entry UX | No UI designed for manual lab entry. Should this be a guided form per test type, or a free-form entry with LOINC lookup? |
| G-6 | Trial matching results UI | Prototype has "Trial matcher" entry point but no results screen or trial detail view (6.1.2–6.1.3). Needs full design. |
| G-7 | SMART Health Link vs. current share link | Current prototype generates a static token-based link. CMS-compliant implementation requires SHL (live encrypted FHIR pointer). Architecture decision needed. |
| G-8 | Research consent management UI | PAT-055 requires consent management. No prototype screen exists. Likely belongs in Profile or a dedicated Consent section. |
| G-9 | Caregiver delegation UX | PAT-003/004 have no prototype representation. Needs design for how caregivers onboard and navigate to a dependant's record. |
| G-10 | Symptom & side effect logging | PAT-045 Should Have — no prototype representation. Belongs in Records tab or as a separate entry flow. |
| G-11 | Calculated field refresh strategy | eGFR, TNBC, CRAB/SLIM must be recomputed from raw inputs (see 9.3). Need to define when recalculation is triggered (on save, on input change, on view). |
| G-12 | Disease-conditional field activation | The `disease` selector gates entire subsections (2.5.1–2.5.4). Need to specify behaviour when a patient has multiple cancers (e.g. breast + MM). |
| G-13 | Female-only field gating | Fields 2.3.7–2.3.9 are female-only. Need to define gating logic based on `gender` and edge cases (Intersex, Prefer not to say). |
