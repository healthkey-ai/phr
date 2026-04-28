/**
 * TypeScript types for the labs domain — v2.
 * Mirrors backend/apps/labs/serializers.py.
 */

export const MATCH_METHODS = [
  "loinc",
  "alias_exact",
  "name_fallback",
  "manual",
  "unmatched",
] as const;
export type MatchMethod = (typeof MATCH_METHODS)[number];

export type ReferenceSource = "report" | "none";

export type LabValueType = "numeric" | "qualitative" | "ratio";

export type LabValueStatus = "in_range" | "below" | "above" | "unknown";

export interface LabTestEntry {
  id: number;
  abbreviation: string;
  name: string;
  /** Canonical storage unit. Every LabValue for this test is normalised to this. */
  default_unit: string;
  alternative_units: string[];
  sample_values: Record<string, string>;
  value_type: LabValueType;
  molecular_weight: number | null;
  /** Category from LoincEntry.category, or "" for unlinked entries. */
  category: string;
  display_order: number;
}

export interface Catalog {
  tests: LabTestEntry[];
}

export interface LabValueTestRef {
  id: number;
  abbreviation: string;
  name: string;
  loinc_name: string;
  category: string;
  default_unit: string;
  value_type: LabValueType;
}

export interface LabValue {
  id: number;
  test: LabValueTestRef;
  value: number | null;
  value_qualitative: string;
  unit: string;
  source_text: string;
  source_unit: string;
  reference_min: number | null;
  reference_max: number | null;
  reference_text: string;
  reference_source: ReferenceSource;
  match_method: MatchMethod;
  source: "manual" | "document_extraction" | "fhir";
  confidence: number;
  status: LabValueStatus;
  measured_at: string | null;
  created_at: string;
  upload: number | null;
  source_filename: string;
}

export interface LabValueCreateInput {
  test_type_id: number;
  value?: number | null;
  value_qualitative?: string;
  unit?: string;
  measured_at?: string | null;
  reference_min?: number | null;
  reference_max?: number | null;
}

// ── Uploads ────────────────────────────────────────────────────────────────

export type UploadStatus = "pending" | "processing" | "completed" | "failed";

export interface UploadFile {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  file_order: number;
  sha256: string;
  created_at: string;
}

export interface ParsedLabResultRow {
  source_index: number;
  raw_name: string;
  raw_loinc_code: string;
  raw_unit: string;
  value: string | null;
  unit: string;
  reference_min: number | null;
  reference_max: number | null;
  reference_text: string;
  measured_date: string | null;
  page: number;
  confidence: number;
  matched_test_id: number;
  matched_test_abbreviation: string;
  matched_test_name: string;
  match_method: MatchMethod;
  accepted: boolean | null;
}

export interface UploadJob {
  id: number;
  status: UploadStatus;
  provider: string;
  lab_date: string | null;
  notes: string;
  parsed_results: ParsedLabResultRow[];
  celery_task_id: string;
  error_message: string;
  files: UploadFile[];
  created_at: string;
  completed_at: string | null;
}

// ── Commit ─────────────────────────────────────────────────────────────────

export interface UploadCommitRow {
  source_index: number;
  test_type_id: number;
  value?: number | null;
  value_qualitative?: string;
  unit?: string;
  measured_at?: string | null;
  reference_min?: number | null;
  reference_max?: number | null;
  reference_text?: string;
}

export interface UploadCommitInput {
  accepted: UploadCommitRow[];
}

export interface UploadCommitResponse {
  saved_count: number;
  skipped_count: number;
  results: LabValue[];
}
