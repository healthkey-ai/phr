/**
 * LabTrendDetail — /dashboard/records/labs/:abbreviation
 *
 * Full-size view of a single lab test's history:
 *   - Back link to Records
 *   - Test header (name + category + latest value + unit)
 *   - Full LabTrendChart filling the content width
 *   - Chronological history list with per-row delete
 *   - Empty state when the patient hasn't entered anything for this test
 *
 * Phase 2a: read-only except for delete. Upload + extraction land in 2b-d.
 */
import { useMemo, useState } from "react";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { DataSourceBadge } from "@/components/healthkey/DataSourceBadge";
import { FileSourceBadge } from "@/components/labs/FileSourceBadge";
import { LabManualEntryDialog } from "@/components/labs/LabManualEntryDialog";
import { LabTrendChart } from "@/components/labs/LabTrendChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  useCatalog,
  useDeleteLabResult,
  useLabResults,
} from "@/features/labs/api";
import type { LabValue } from "@/types/labs";

export function LabTrendDetail() {
  const { abbreviation = "" } = useParams<{ abbreviation: string }>();
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  // When set, the dialog opens in edit mode pre-filled with this row.
  const [editingResult, setEditingResult] = useState<LabValue | null>(null);

  const { data: catalog } = useCatalog();
  const { data: results = [], isLoading } = useLabResults({ test: abbreviation });
  const deleteResult = useDeleteLabResult();

  const openForEdit = (r: LabValue) => {
    setEditingResult(r);
    setDialogOpen(true);
  };
  const openForCreate = () => {
    setEditingResult(null);
    setDialogOpen(true);
  };
  const handleDialogOpenChange = (next: boolean) => {
    setDialogOpen(next);
    if (!next) setEditingResult(null);
  };

  const test = useMemo(
    () => catalog?.tests.find((t) => t.abbreviation === abbreviation),
    [catalog, abbreviation],
  );

  // If the catalog has loaded but the abbreviation isn't in it, bounce to Records
  if (catalog && !test) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-base text-muted-foreground">Unknown test.</p>
        <Button variant="link" onClick={() => navigate("/dashboard/records")}>
          ← Back to records
        </Button>
      </div>
    );
  }

  const latest = results[0];

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6 lg:p-10">
      {/* Back link */}
      <Button
        asChild
        variant="ghost"
        size="sm"
        className="-ml-3 mb-4 h-8 px-2 text-muted-foreground hover:text-foreground"
      >
        <Link to="/dashboard/records">
          <ArrowLeft className="mr-1 h-4 w-4" /> Back to records
        </Link>
      </Button>

      {/* Header */}
      <header className="mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {prettyCategory(test?.category)}
            </p>
            <h1 className="text-h1 text-foreground">{test?.name ?? abbreviation}</h1>
            {latest && (
              <p className="mt-2 text-base text-muted-foreground">
                Latest:{" "}
                <span className="font-mono text-foreground">
                  {formatLatest(latest)}
                </span>
                {latest.measured_at && (
                  <span className="ml-2 text-xs">
                    · {formatLongDate(latest.measured_at)}
                  </span>
                )}
              </p>
            )}
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={openForCreate}
            disabled={!catalog}
          >
            <Plus className="mr-1 h-4 w-4" /> Add
          </Button>
        </div>
      </header>

      {/* Chart — skipped entirely for qualitative tests (HIV, HBsAg, HCV Ab…)
          since "reactive / non-reactive" doesn't plot on a time-series axis.
          The history list below still shows all the measurements. */}
      {test?.value_type !== "qualitative" && (
        <section className="mb-8">
          <Card>
            <CardContent className="p-4 sm:p-6">
              {isLoading ? (
                <div className="h-64 w-full animate-pulse rounded-md bg-muted" />
              ) : (
                <LabTrendChart testAbbrev={abbreviation} />
              )}
            </CardContent>
          </Card>
        </section>
      )}

      {/* History list */}
      <section>
        <h2 className="mb-3 text-h3 text-foreground">History</h2>
        {results.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <p className="text-base text-foreground">No measurements yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Add your first value to start tracking this test over time.
              </p>
              <Button
                className="mt-4"
                size="sm"
                onClick={openForCreate}
                disabled={!catalog}
              >
                <Plus className="mr-1 h-4 w-4" /> Add first result
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <ul className="divide-y divide-border">
              {results.map((r) => (
                <li key={r.id} className="flex items-center gap-3 px-4 py-3 sm:px-6">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-base text-foreground">
                        {formatValue(r)}
                      </span>
                      {r.unit && (
                        <span className="text-xs text-muted-foreground">{r.unit}</span>
                      )}
                      <StatusDot status={r.status} />
                    </div>
                    <div className="mt-0.5 flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {r.measured_at && <span>{formatLongDate(r.measured_at)}</span>}
                      {r.source !== "manual" && r.source_filename ? (
                        <FileSourceBadge filename={r.source_filename} truncate={false} />
                      ) : (
                        <DataSourceBadge
                          source={r.source === "manual" ? "manual" : "document"}
                          detail={r.source === "manual" ? "You" : undefined}
                        />
                      )}
                      {(r.reference_min != null || r.reference_max != null) && (
                        <span>
                          ref{" "}
                          {r.reference_min != null && r.reference_max != null
                            ? `${fmtNum(r.reference_min)}–${fmtNum(r.reference_max)}`
                            : r.reference_max != null
                              ? `< ${fmtNum(r.reference_max)}`
                              : `> ${fmtNum(r.reference_min!)}`}
                        </span>
                      )}
                    </div>
                    {r.reference_text && r.reference_text.includes("\n") && (
                      <div className="mt-1 space-y-px text-[11px] leading-tight text-muted-foreground/80">
                        {r.reference_text
                          .split("\n")
                          .slice(1)
                          .filter((l: string) => l.trim())
                          .map((line: string, i: number) => (
                            <p key={i}>{line}</p>
                          ))}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => openForEdit(r)}
                      className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-healthkey-brand-700 focus-visible:ring-offset-2"
                      aria-label={`Edit ${test?.name ?? abbreviation} measurement from ${r.measured_at ?? "unknown date"}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm("Delete this measurement?")) {
                          deleteResult.mutate(r.id);
                        }
                      }}
                      className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-error-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-healthkey-brand-700 focus-visible:ring-offset-2"
                      aria-label={`Delete ${test?.name ?? abbreviation} measurement from ${r.measured_at ?? "unknown date"}`}
                      disabled={deleteResult.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </section>

      <LabManualEntryDialog
        open={dialogOpen}
        onOpenChange={handleDialogOpenChange}
        defaultTestAbbrev={abbreviation}
        editingResult={editingResult}
      />
    </div>
  );
}

function fmtNum(n: number): string {
  return String(Number(n.toFixed(2)));
}

function formatValue(r: LabValue): string {
  if (r.value != null) return fmtNum(r.value);
  return r.value_qualitative || "—";
}

function formatLatest(r: LabValue): string {
  const v = formatValue(r);
  return r.unit ? `${v} ${r.unit}` : v;
}

function formatLongDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const CATEGORY_LABELS: Record<string, string> = {
  cbc: "Complete Blood Count",
  renal: "Renal function",
  liver: "Liver function",
  myeloma: "Multiple myeloma markers",
  breast: "Breast cancer markers",
  cardiac: "Cardiac & metabolic",
  infection: "Infection screen",
};

function prettyCategory(key: string | undefined): string {
  if (!key) return "";
  return CATEGORY_LABELS[key] ?? key;
}

function StatusDot({ status }: { status: LabValue["status"] }) {
  const color =
    status === "in_range"
      ? "bg-success-700"
      : status === "unknown"
        ? "bg-muted-foreground"
        : "bg-warning-700";
  const label =
    status === "in_range"
      ? "in range"
      : status === "below"
        ? "below"
        : status === "above"
          ? "above"
          : "no range";
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} aria-hidden="true" />
      {label}
    </span>
  );
}
