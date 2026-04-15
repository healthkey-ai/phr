/**
 * TypeScript types for the labs domain.
 * Mirrors backend/apps/labs/serializers.py.
 * Per eng review §CQ3, MatchMethod is the single source of truth.
 */

export const MATCH_METHODS = [
  "loinc",
  "exact_alias",
  "fuzzy",
  "disambiguation",
  "manual",
  "unmatched",
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
  aliases: string[];
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
