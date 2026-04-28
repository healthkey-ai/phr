/**
 * LabUploadReview — Phase 2d review + commit step.
 *
 * Shows the parsed_results from a completed LabUpload and lets the patient:
 *   - toggle which rows to save
 *   - edit value / unit / measured_at / reference range inline
 *   - see duplicate indicators for rows already in their record
 *
 * Commits via POST /uploads/{id}/commit/. The parent dialog hands us the
 * completed upload and two callbacks (onCancel, onSaved) so we stay focused.
 *
 * Design notes:
 *   - test_type override (swap a row to a different test) is NOT exposed
 *     here — if the auto-resolution got the wrong test, the patient can
 *     edit the resulting LabResult via the existing manual-entry dialog
 *     after commit. Keeps this UI bounded.
 *   - Duplicate detection is client-side best-effort: we check against the
 *     patient's existing LabResults cached by useLabResults. The backend
 *     also dedups at commit time, so a race here is caught server-side.
 */
import { useMemo, useState } from "react";
import { CheckCircle2, Loader2, Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useCommitLabUpload,
  useLabResults,
} from "@/features/labs/api";
import type {
  LabValue,
  UploadJob,
  UploadCommitResponse,
  UploadCommitRow,
  MatchMethod,
  ParsedLabResultRow,
} from "@/types/labs";

const DUP_TOLERANCE = 0.01; // 1% — matches backend _DUPLICATE_RELATIVE_TOLERANCE

interface Props {
  upload: UploadJob;
  onCancel: () => void;
  onSaved: (response: UploadCommitResponse) => void;
  /**
   * Re-run extraction on the stored upload. Useful when the LLM found nothing
   * on the first pass — the backend model or prompt may have changed since,
   * so a retry can yield a different result without re-uploading the file.
   */
  onRetry?: () => void;
  retrying?: boolean;
}

interface RowState {
  /** Immutable reference into upload.parsed_results */
  source_index: number;
  accepted: boolean;
  /** Editable fields, bound to text inputs so empty-state is "". */
  value: string;
  value_qualitative: string;
  unit: string;
  measured_at: string;
  reference_min: string;
  reference_max: string;
}

export function LabUploadReview({ upload, onCancel, onSaved, onRetry, retrying = false }: Props) {
  const parsed = upload.parsed_results;
  const { data: existingResults = [] } = useLabResults();
  const commit = useCommitLabUpload();
  const [serverError, setServerError] = useState<string | null>(null);

  const [rows, setRows] = useState<RowState[]>(() =>
    parsed.map((p): RowState => ({
      source_index: p.source_index,
      // Low-confidence rows default-unchecked per design §10.4
      accepted: p.confidence >= 0.6,
      value: p.value ?? "",
      value_qualitative: "",
      unit: p.unit ?? "",
      measured_at: p.measured_date ?? "",
      reference_min: p.reference_min != null ? String(p.reference_min) : "",
      reference_max: p.reference_max != null ? String(p.reference_max) : "",
    })),
  );

  // Pre-compute duplicate status per source_index. Runs whenever existing
  // results or edited values change.
  const duplicateByIndex = useMemo(() => {
    const out = new Map<number, string>();
    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i];
      const parsedRow = parsed[i];
      const dup = findDuplicate(row, parsedRow, existingResults);
      if (dup) out.set(row.source_index, dup);
    }
    return out;
  }, [rows, parsed, existingResults]);

  // Auto-uncheck a row when it becomes a duplicate — patient can re-check
  // to force-save anyway. We only auto-uncheck ONCE per source_index per
  // duplicate transition (tracked via rows state); manual re-check sticks.
  const acceptedCount = rows.filter(
    (r) => r.accepted && !duplicateByIndex.has(r.source_index),
  ).length;
  const duplicateCount = duplicateByIndex.size;

  function updateRow(source_index: number, patch: Partial<RowState>) {
    setRows((prev) =>
      prev.map((r) => (r.source_index === source_index ? { ...r, ...patch } : r)),
    );
  }

  async function handleSave() {
    setServerError(null);
    const accepted: UploadCommitRow[] = rows
      .filter((r) => r.accepted && (r.value.trim() !== "" || r.value_qualitative.trim() !== ""))
      .map((r) => {
        const parsedRow = parsed.find((p) => p.source_index === r.source_index)!;
        // Route strings that don't parse as a number (e.g. "Not Detected",
        // "Positive", "1+") to value_qualitative. The test_type auto-created
        // by the pipeline already has value_type="qualitative" in that case
        // (see matching._infer_value_type), so the backend accepts this.
        const trimmed = r.value.trim();
        const numeric = Number(trimmed);
        const isNumeric = trimmed !== "" && !Number.isNaN(numeric);
        // Explicit qualitative override wins over the inferred route.
        const qualitativeOverride = r.value_qualitative.trim();

        return {
          source_index: r.source_index,
          test_type_id: parsedRow.matched_test_id,
          value: isNumeric && !qualitativeOverride ? numeric : null,
          value_qualitative:
            qualitativeOverride ||
            (isNumeric ? undefined : trimmed || undefined),
          unit: r.unit || undefined,
          measured_at: r.measured_at || null,
          reference_min: r.reference_min === "" ? null : Number(r.reference_min),
          reference_max: r.reference_max === "" ? null : Number(r.reference_max),
          reference_text: parsedRow.reference_text || "",
        };
      });

    try {
      const response = await commit.mutateAsync({ id: upload.id, accepted });
      onSaved(response);
    } catch (err: unknown) {
      setServerError(extractErrorMessage(err));
    }
  }

  if (parsed.length === 0) {
    return (
      <div className="space-y-3 py-2">
        <p className="text-body text-foreground">
          We couldn't find any lab values on this report.
        </p>
        <p className="text-caption text-muted-foreground">
          Try again (reading may improve over time), upload a clearer scan, or add values
          manually via the <span className="font-semibold">Add lab result</span> button.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onCancel} disabled={retrying}>
            Done
          </Button>
          {onRetry && (
            <Button onClick={onRetry} disabled={retrying}>
              {retrying && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
              Try again
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-body text-foreground">
        We found <span className="font-semibold">{parsed.length}</span> value
        {parsed.length === 1 ? "" : "s"} in your report. Review, edit, then save what you want to
        keep.
      </p>

      <div className="max-h-[60vh] overflow-y-auto rounded-md border border-border">
        <ul className="divide-y divide-border">
          {rows.map((row) => {
            const parsedRow = parsed.find((p) => p.source_index === row.source_index)!;
            const duplicateNote = duplicateByIndex.get(row.source_index) ?? null;
            return (
              <li key={row.source_index} className="p-3">
                <ReviewRow
                  row={row}
                  parsed={parsedRow}
                  duplicateNote={duplicateNote}
                  onChange={(patch) => updateRow(row.source_index, patch)}
                />
              </li>
            );
          })}
        </ul>
      </div>

      {duplicateCount > 0 && (
        <p className="text-caption text-muted-foreground">
          {duplicateCount} {duplicateCount === 1 ? "row" : "rows"} already saved. Check a row to
          save it again anyway.
        </p>
      )}

      {serverError && (
        <p className="text-caption text-error-700" role="alert">
          {serverError}
        </p>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        <Button variant="ghost" onClick={onCancel} disabled={commit.isPending}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          disabled={commit.isPending || acceptedCount === 0}
        >
          {commit.isPending && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
          Save {acceptedCount} {acceptedCount === 1 ? "result" : "results"}
        </Button>
      </div>
    </div>
  );
}

// ── Row ──────────────────────────────────────────────────────────────────────

interface RowProps {
  row: RowState;
  parsed: ParsedLabResultRow;
  duplicateNote: string | null;
  onChange: (patch: Partial<RowState>) => void;
}

function ReviewRow({ row, parsed, duplicateNote, onChange }: RowProps) {
  const [editing, setEditing] = useState(false);
  const confidenceTone =
    parsed.confidence >= 0.85 ? "brand" : parsed.confidence >= 0.6 ? "warning" : "error";
  const isDuplicate = duplicateNote !== null;

  return (
    <div className="flex gap-3">
      <Checkbox
        id={`row-${row.source_index}`}
        checked={row.accepted}
        onCheckedChange={(checked) => onChange({ accepted: Boolean(checked) })}
        className="mt-1"
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <label
            htmlFor={`row-${row.source_index}`}
            className="text-body font-semibold text-foreground"
          >
            {parsed.matched_test_name}
          </label>
          <div className="flex items-center gap-1">
            <ConfidenceDot tone={confidenceTone} label={confidenceLabel(parsed.confidence)} />
            <MatchMethodBadge method={parsed.match_method} />
          </div>
        </div>

        {!editing ? (
          <div className="mt-1 flex items-baseline justify-between gap-3">
            <div className="text-body text-foreground">
              {row.value || <span className="italic text-muted-foreground">(no value)</span>}
              {row.unit && <span className="ml-1 text-muted-foreground">{row.unit}</span>}
              {row.measured_at && (
                <span className="ml-2 text-caption text-muted-foreground">
                  · {formatShortDate(row.measured_at)}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="text-caption text-brand-700 hover:underline"
              aria-label={`Edit ${parsed.matched_test_name}`}
            >
              <Pencil className="inline h-3 w-3" />
            </button>
          </div>
        ) : (
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor={`value-${row.source_index}`} className="text-caption">
                Value
              </Label>
              <Input
                id={`value-${row.source_index}`}
                inputMode="decimal"
                value={row.value}
                onChange={(e) => onChange({ value: e.target.value })}
                className="h-8"
              />
            </div>
            <div>
              <Label htmlFor={`unit-${row.source_index}`} className="text-caption">
                Unit
              </Label>
              <Input
                id={`unit-${row.source_index}`}
                value={row.unit}
                onChange={(e) => onChange({ unit: e.target.value })}
                className="h-8"
              />
            </div>
            <div>
              <Label htmlFor={`date-${row.source_index}`} className="text-caption">
                Date
              </Label>
              <Input
                id={`date-${row.source_index}`}
                type="date"
                value={row.measured_at}
                onChange={(e) => onChange({ measured_at: e.target.value })}
                className="h-8"
              />
            </div>
            <div>
              <Label className="text-caption">Range</Label>
              <div className="flex items-center gap-1">
                <Input
                  inputMode="decimal"
                  value={row.reference_min}
                  onChange={(e) => onChange({ reference_min: e.target.value })}
                  placeholder="min"
                  className="h-8"
                />
                <span className="text-muted-foreground">–</span>
                <Input
                  inputMode="decimal"
                  value={row.reference_max}
                  onChange={(e) => onChange({ reference_max: e.target.value })}
                  placeholder="max"
                  className="h-8"
                />
              </div>
            </div>
            <div className="col-span-2 flex justify-end">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setEditing(false)}
              >
                Done
              </Button>
            </div>
          </div>
        )}

        {/* Reference range summary when not editing */}
        {!editing && (row.reference_min || row.reference_max) && (
          <p className="text-caption text-muted-foreground">
            Reference{" "}
            {row.reference_min && row.reference_max
              ? `${row.reference_min}–${row.reference_max}`
              : row.reference_max
                ? `< ${row.reference_max}`
                : `> ${row.reference_min}`}
          </p>
        )}

        {isDuplicate && (
          <p className="mt-1 flex items-center gap-1 text-caption text-brand-700">
            <CheckCircle2 className="h-3 w-3" />
            Already saved — {duplicateNote}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Small presentational bits ────────────────────────────────────────────────

function ConfidenceDot({ tone, label }: { tone: "brand" | "warning" | "error"; label: string }) {
  const toneClass =
    tone === "brand"
      ? "bg-brand-700"
      : tone === "warning"
      ? "bg-warning-700"
      : "bg-error-700";
  return (
    <span className="flex items-center gap-1 text-caption text-muted-foreground">
      <span className={`h-2 w-2 rounded-full ${toneClass}`} />
      {label}
    </span>
  );
}

function MatchMethodBadge({ method }: { method: MatchMethod }) {
  const label = METHOD_LABELS[method] ?? method;
  return (
    <span className="rounded-sm bg-muted px-1.5 py-0.5 text-caption text-muted-foreground">
      {label}
    </span>
  );
}

const METHOD_LABELS: Partial<Record<MatchMethod, string>> = {
  loinc: "LOINC",
  alias_exact: "Alias",
  name_fallback: "By name",
  manual: "Manual",
  unmatched: "Unmatched",
};

function confidenceLabel(c: number): string {
  if (c >= 0.85) return "High";
  if (c >= 0.6) return "Med";
  return "Low";
}

function formatShortDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

// ── Duplicate detection ──────────────────────────────────────────────────────

function findDuplicate(
  row: RowState,
  parsed: ParsedLabResultRow,
  existing: LabValue[],
): string | null {
  if (!row.measured_at) return null;
  if (row.value === "" && !row.value_qualitative) return null;

  const numericValue = Number(row.value);
  const isNumeric = !Number.isNaN(numericValue) && row.value !== "";

  for (const e of existing) {
    if (e.test.id !== parsed.matched_test_id) continue;
    if (e.measured_at !== row.measured_at) continue;

    if (isNumeric && e.value != null) {
      const denom = Math.max(Math.abs(e.value), Math.abs(numericValue), 1e-9);
      if (Math.abs(e.value - numericValue) / denom <= DUP_TOLERANCE) {
        return `${formatShortDate(row.measured_at)} · ${e.value}${e.unit ? " " + e.unit : ""}`;
      }
    } else if (row.value_qualitative && e.value_qualitative === row.value_qualitative) {
      return `${formatShortDate(row.measured_at)} · ${e.value_qualitative}`;
    }
  }
  return null;
}

// ── Error extraction (shared with LabUploadDialog pattern) ───────────────────

function extractErrorMessage(err: unknown): string {
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { data?: unknown } }).response;
    const data = response?.data;
    if (typeof data === "string") return data;
    if (data && typeof data === "object") {
      for (const key of ["detail", "non_field_errors", "accepted"]) {
        const v = (data as Record<string, unknown>)[key];
        if (typeof v === "string") return v;
        if (Array.isArray(v) && v.length > 0 && typeof v[0] === "string") return v[0];
      }
    }
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong saving. Please try again.";
}
