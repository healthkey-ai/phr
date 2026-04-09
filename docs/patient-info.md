# Patient Information Requirements

Source: `cancerbot/ui.v2` analysis (2026-04-09)

This document captures the full set of patient data fields collected by the cancerbot UI v2,
organized by category. Used to inform the PHR data model and FHIR mapping layer.

---

## 1. Demographics

| Field | Type | Notes |
|---|---|---|
| `firstName` | string | |
| `lastName` | string | |
| `patientAge` | number | |
| `gender` | select | |
| `ethnicity` | select / multiselect | Affects lab interpretation (e.g. creatinine reference ranges) |
| `weight` | number + units | kg or lbs |
| `height` | number + units | cm or inches |
| `country` | select | From `allCountries` list |
| `postalCode` | string | |

---

## 2. Diagnosis & Clinical Status

| Field | Type | Notes |
|---|---|---|
| `disease` | select | breast cancer, multiple myeloma, follicular lymphoma, chronic lymphocytic leukemia |
| `stage` | select | Disease-specific values |
| `karnofskyPerformanceScore` | number (0–100) | Describes functional ability |
| `ecogPerformanceStatus` | number (0–5) | Describes limitation in daily activities |
| `systolicBloodPressure` | number | SBP |
| `diastolicBloodPressure` | number | DBP |
| `noOtherActiveMalignancies` | boolean | YES = patient does NOT have other active cancers |
| `noActiveInfectionStatus` | boolean | YES = patient does NOT have active infections |
| `preExistingConditionCategories` | multiselect | List of pre-existing conditions |
| `peripheralNeuropathyGrade` | number (0–4) | Nerve damage severity |

---

## 3. Blood / CBC Labs

| Field | Notes |
|---|---|
| `whiteBloodCellCount` | Numeric with units |
| `hemoglobinLevel` | Numeric with units |
| `plateletCount` | Numeric with units |
| `absoluteNeutrophileCount` | Numeric with units |
| `absoluteLymphocyteCount` | Numeric with units |
| `serumCreatinineLevel` | Numeric with units — absolute value |
| `creatinineClearanceRate` | Numeric with units — calculated kidney function |
| `estimatedGlomerularFiltrationRate` | Calculated / read-only — derived from creatinine + demographics |
| `renalAdequacyStatus` | Select — adequacy classification |
| `serumCalciumLevel` | Numeric with units |

---

## 4. Liver Function Labs

| Field | Notes |
|---|---|
| `liverEnzymeLevelsAst` | AST — aspartate aminotransferase |
| `liverEnzymeLevelsAlt` | ALT — alanine aminotransferase |
| `liverEnzymeLevelsAlp` | ALP — alkaline phosphatase |
| `serumBilirubinLevelTotal` | Absolute value |
| `serumBilirubinLevelDirect` | Absolute value |
| `albumin` | Numeric with units |

---

## 5. Specialized Labs

### Hemato-Oncology
| Field | Context |
|---|---|
| `monoclonalProteinSerum` | M-spike serum — Multiple Myeloma |
| `monoclonalProteinUrine` | M-spike urine — Multiple Myeloma |
| `kappaFLC` | Kappa free light chain — Multiple Myeloma |
| `lambdaFLC` | Lambda free light chain — Multiple Myeloma |
| `clonalPlasmaCells` | Percentage — Multiple Myeloma |
| `lactateDehydrogenaseLevel` | LDH — MM / CLL |
| `serumBeta2MicroglobulinLevel` | CLL marker |

### Cardiac & Pulmonary
| Field | Notes |
|---|---|
| `ejectionFraction` | Cardiac function — percentage |
| `qtcfValue` | QTcF interval — cardiac measure |
| `pulmonaryFunctionTestResult` | Boolean / text result |

### Bone & Imaging
| Field | Notes |
|---|---|
| `boneImagingResult` | Boolean / text result |
| `boneLesions` | Boolean |
| `boneMarrowInvolvement` | Boolean |

### Infection Screen
| Field | Notes |
|---|---|
| `noHivStatus` | YES = HIV negative |
| `noHepatitisBStatus` | YES = Hepatitis B negative |
| `noHepatitisCStatus` | YES = Hepatitis C negative |

---

## 6. Breast Cancer–Specific

### Receptor & Subtype Status
| Field | Notes |
|---|---|
| `estrogenReceptorStatus` | Select — ER negative / positive / low / high |
| `progesteroneReceptorStatus` | Select — PR negative / positive / low / high |
| `her2Status` | Select — HER2 negative / positive / low |
| `tnbcStatus` | Calculated — triple negative breast cancer |
| `hrdStatus` | Select — homologous recombination deficiency |
| `menopausalStatus` | Select — pre-menopausal / post-menopausal |

### Histology & Grade
| Field | Notes |
|---|---|
| `histologicType` | Select — specific histological type |
| `biopsyGrade` | 1–3 — tumor differentiation |

### Staging (TNM)
| Field | Notes |
|---|---|
| `tumorStage` | T-stage — size / extent of main tumor |
| `nodesStage` | N-stage — lymph node involvement |
| `distantMetastasisStage` | M-stage — distant metastasis |
| `stagingModalities` | Select — cTNM (clinical) vs pTNM (pathological) |
| `metastaticStatus` | Boolean |
| `boneOnlyMetastasisStatus` | Boolean — spread limited to bones only |
| `measurableDiseaseByRecistStatus` | Boolean — RECIST criteria met |

### Proliferation & Immunology
| Field | Notes |
|---|---|
| `ki67ProliferationIndex` | Percentage — cell proliferation rate |
| `pdL1TumorCels` | Percentage — PD-L1 expression on tumor cells |
| `pdL1IcPercentage` | Percentage — PD-L1 on immune cells |
| `pdL1CombinedPositiveScore` | Numeric — combined PD-L1 score (CPS) |
| `pdL1Assay` | Select — assay type used |

### Genetic Mutations

Array of rows — auto-grows as user adds mutations.

| Sub-field | Type | Notes |
|---|---|---|
| `gene` | select | BRCA1, BRCA2, TP53, PIK3CA, ESR1, etc. |
| `variant` | select | Options depend on selected gene |
| `origin` | select | somatic / germline |
| `interpretation` | select | Clinical significance |

---

## 7. Multiple Myeloma–Specific

| Field | Type | Notes |
|---|---|---|
| `cytogenicMarkers` | multiselect | Chromosomal abnormalities |
| `molecularMarkers` | multiselect | Molecular / genetic markers |
| `plasmaCellLeukemia` | boolean | Plasma cell leukemia diagnosis |
| `progression` | select | Disease status |
| `meetsCRAB` | boolean (calculated) | Calcium / Renal / Anemia / Bone criteria |
| `meetsSLIM` | boolean (calculated) | SLIM-CRAB criteria |
| `measurableDiseaseImwg` | boolean (calculated) | IMWG measurable disease criteria |

---

## 8. Follicular Lymphoma–Specific

| Field | Type | Notes |
|---|---|---|
| `flipiScoreOptions` | multiselect | FLIPI risk factors: age, stage, hemoglobin, nodal areas, LDH |
| `gelfCriteriaStatus` | multiselect | GELF criteria met |
| `tumorGrade` | select (1–3B) | FL grade |

---

## 9. Chronic Lymphocytic Leukemia (CLL)–Specific

| Field | Type | Notes |
|---|---|---|
| `cytogenicMarkers` | multiselect | Chromosomal markers |
| `molecularMarkers` | multiselect | Molecular markers |
| `binetStage` | select | Binet staging |
| `diseaseActivity` | select | Disease activity level |
| `measurableDiseaseIwcll` | select | IWCLL criteria |
| `tumorBurden` | select | Disease burden level |
| `lymphocyteDoublingTime` | number + units | Time for lymphocyte count to double |
| `proteinExpressions` | multiselect | Protein expression markers |
| `tp53Disruption` | select | TP53 disruption status |
| `richterTransformation` | boolean | Richter transformation status |
| `lymphadenopathy` | select | Lymph node enlargement |
| `splenomegaly` | select | Spleen enlargement |
| `hepatomegaly` | select | Liver enlargement |
| `clonalBoneMarrowBLymphocytes` | number (%) | Clonal B-lymphocytes in bone marrow |
| `clonalBLymphocyteCount` | number + units | Absolute clonal B-lymphocyte count |
| `autoimmuneCytopeniasRefractoryToSteroids` | boolean | Refractory autoimmune cytopenias |
| `btkInhibitorRefractory` | boolean | BTK inhibitor resistance |
| `bcl2InhibitorRefractory` | boolean | BCL-2 inhibitor resistance |

---

## 10. Treatment History

### Prior Therapy Summary
| Field | Type | Notes |
|---|---|---|
| `priorTherapy` | select | None / One line / Two lines / More than two lines |
| `treatmentRefractoryStatus` | select | Refractory / relapsed / responsive |
| `relapseCount` | number | Number of relapses |
| `stemCellTransplantHistory` | multiselect / text | SCT history |
| `concomitantMedications` | multiselect | Concurrent medications |
| `plannedTherapies` | multiselect | Scheduled / planned treatments |

### Therapy Lines

Each line contains `{therapy, date, outcome}`. Second line disabled unless prior therapy ≥ 2 lines; later lines only shown for 2+ lines.

| Field | Notes |
|---|---|
| `firstLineTherapy`, `firstLineDate`, `firstLineOutcome` | |
| `secondLineTherapy`, `secondLineDate`, `secondLineOutcome` | |
| `laterTherapy`, `laterDate`, `laterOutcome` | For > 2 lines |

### Supportive Therapies

Dynamic array — auto-grows when last row is completed.

| Sub-field | Type |
|---|---|
| `therapy` | select |
| `date` | date |

---

## 11. Behavioral & Lifestyle

| Field | Type | Notes |
|---|---|---|
| `consentCapability` | boolean | Able to provide consent |
| `noPregnancyOrLactationStatus` | boolean | YES = NOT pregnant/lactating (female only) |
| `pregnancyTestResult` | select | Female only |
| `contraceptiveUse` | select | Female only |
| `noTobaccoUseStatus` | boolean | YES = does not use tobacco |
| `noSubstanceUseStatus` | boolean | YES = does not use substances |
| `noMentalHealthDisorderStatus` | boolean | YES = no mental health disorders |
| `caregiverAvailabilityStatus` | boolean | Caregiver available |
| `noGeographicExposureRisk` | boolean | YES = no geographic exposure risk |
| `languagesSkills` | multiselect | Languages spoken |

---

## 12. Data Model

### API Types

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

### API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/patient-info/user/` | Retrieve patient info |
| PATCH | `/api/v1/patient-info/user/` | Update patient info |
| GET | `/api/v1/patient-info/profile-completeness/` | Profile completion percentage |
| GET | `/api/v1/form-settings/` | Available options / dropdowns |

---

## 13. UI Form Controls

| Control | Usage |
|---|---|
| `BooleanControl` | Yes/No toggle or checkbox |
| `SelectControl` | Single-select dropdown |
| `MultiSelectControl` | Multi-select scrollable list |
| `DateControl` | Date picker |
| `TextNumberControl` | Text or numeric input with optional units |
| `UnitsSelect` | Unit dropdown (kg/lbs, cm/inches, etc.) |

---

## 14. Notes for PHR App Integration

**No FHIR in source.** Cancerbot uses a custom schema. The PHR app will need a mapping layer
to populate these fields from FHIR resources:

| Cancerbot category | FHIR resource(s) |
|---|---|
| Demographics | `Patient` |
| Disease / diagnosis | `Condition` |
| Genetic mutations | `Observation` (with `valueCodeableConcept`) |
| Lab values | `Observation` (LOINC codes) |
| Treatment lines | `MedicationAdministration`, `Procedure` |
| Supportive therapies | `MedicationAdministration` |
| Performance status | `Observation` (LOINC 89243-0, 89247-1) |

**Calculated fields** — eGFR, TNBC status, CRAB/SLIM criteria, FLIPI score — should be
recomputed client-side from raw inputs rather than stored as derived values, to avoid
stale data.

**Disease-conditional structure.** Many fields are disease-gated.

**Mutation arrays and therapy lines** are dynamic arrays. Each entry maps to a separate
encrypted record in the DB (one FHIR `Observation` or `MedicationAdministration`
per row) to allow individual timeline entries rather than a single opaque blob.
