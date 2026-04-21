/**
 * TypeScript types for the labs domain.
 * Mirrors backend/apps/labs/serializers.py.
 * Per eng review §CQ3, MatchMethod is the single source of truth.
 */

export const MATCH_METHODS = [
  "loinc",
  "name_fallback",
  "manual",
  "unmatched",
  // Legacy (Phase 2a catalog matching; never produced by Phase 2c+ code,
  // kept here so old rows serialized from the DB still validate)
  "exact_alias",
  "fuzzy",
  "disambiguation",
] as const;
export type MatchMethod = (typeof MATCH_METHODS)[number];

export type ReferenceSource = "report" | "catalog" | "none";

export type LabValueType = "numeric" | "qualitative" | "ratio";

export type LabResultStatus = "in_range" | "below" | "above" | "unknown";

export interface LabCategory {
  key: string;
  name: string;
  display_order: number;
}

export interface LabTestType {
  id: number;
  abbreviation: string;
  name: string;
  loinc_code: string;
  /** Canonical storage unit. Every LabResult for this test is normalised to this. */
  default_unit: string;
  /**
   * Other units the patient may enter (regional variants: US/UK/EU).
   * Does NOT include default_unit. Backend auto-converts on save via unit_converter.
   * Empty list means only default_unit is accepted.
   */
  alternative_units: string[];
  /**
   * Realistic example value per unit, rendered as the input placeholder.
   * Keyed by unit string. E.g. hemoglobin: `{"g/dL": "14.0", "g/L": "140"}`.
   * Always defined, may be empty for qualitative tests.
   */
  sample_values: Record<string, string>;
  reference_ranges: Record<string, [number, number]>;
  /**
   * Reference range pre-converted to every unit the UI may render.
   * Computed server-side via the same unit_converter that runs on save, so
   * the numbers here match what a stored LabResult would resolve to.
   * Keyed by unit string. Empty object if the test has no default range
   * (qualitative tests, or ones where `reference_ranges.default` is [0,0]).
   */
  reference_ranges_by_unit: Record<string, [number, number]>;
  value_type: LabValueType;
  molecular_weight: number | null;
  category: string; // category.key
  display_order: number;
}

export interface Catalog {
  categories: LabCategory[];
  tests: LabTestType[];
}

export interface LabResultTestRef {
  id: number;
  abbreviation: string;
  name: string;
  category: string;
  default_unit: string;
  value_type: LabValueType;
}

export interface LabResult {
  id: number;
  test: LabResultTestRef;
  value: number | null;
  value_qualitative: string;
  unit: string;
  source_text: string;
  source_unit: string;
  reference_min: number | null;
  reference_max: number | null;
  reference_source: ReferenceSource;
  match_method: MatchMethod;
  source: "manual" | "document_extraction" | "fhir";
  confidence: number;
  status: LabResultStatus;
  measured_at: string | null;
  created_at: string;
  /** FK to the LabUpload this result was committed from, null for manual entry. */
  upload: number | null;
  /** Original filename of the source upload, "" for manual entries. */
  source_filename: string;
}

export interface LabResultCreateInput {
  test_type_id: number;
  value?: number | null;
  value_qualitative?: string;
  unit?: string;
  measured_at?: string | null;
  reference_min?: number | null;
  reference_max?: number | null;
}

// ── Lab uploads (Phase 2b) ──────────────────────────────────────────────────

export type LabUploadStatus = "pending" | "processing" | "completed" | "failed";

export interface LabUploadFile {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  file_order: number;
  sha256: string;
  created_at: string;
}

/**
 * Parsed result row inside LabUpload.parsed_results.
 *
 * Produced by backend/apps/labs/tasks.py:_run_extraction_pipeline. Every
 * field below comes from either the LLM (raw_*) or the identity resolver
 * (matched_test_*, match_method). Value stays as a STRING — the commit
 * endpoint coerces to float when the patient accepts a row.
 */
export interface ParsedLabResultRow {
  source_index: number;
  raw_name: string;
  raw_loinc_code: string;
  raw_unit: string;
  value: string | null;
  unit: string;
  reference_min: number | null;
  reference_max: number | null;
  measured_date: string | null;
  page: number;
  confidence: number;
  matched_test_id: number;
  matched_test_abbreviation: string;
  matched_test_name: string;
  match_method: MatchMethod;
  accepted: boolean | null;
}

export interface LabUpload {
  id: number;
  status: LabUploadStatus;
  provider: string;
  lab_date: string | null;
  notes: string;
  parsed_results: ParsedLabResultRow[];
  celery_task_id: string;
  error_message: string;
  files: LabUploadFile[];
  created_at: string;
  completed_at: string | null;
}

// ── Commit (Phase 2d) ──────────────────────────────────────────────────────

export interface LabUploadCommitRow {
  source_index: number;
  test_type_id: number;
  value?: number | null;
  value_qualitative?: string;
  unit?: string;
  measured_at?: string | null;
  reference_min?: number | null;
  reference_max?: number | null;
}

export interface LabUploadCommitInput {
  accepted: LabUploadCommitRow[];
}

export interface LabUploadCommitResponse {
  saved_count: number;
  skipped_count: number;
  results: LabResult[];
}
