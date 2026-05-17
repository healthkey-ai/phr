import { useMemo, useState } from "react";
import { ArrowLeft, Trash2 } from "lucide-react";

import { LabsProvider } from "./LabsProvider";
import { useLabsContext } from "./LabsContext";
import type { LabResultsProps } from "./types";
import { useLabResults, useDeleteLabResult } from "./hooks";
import { LabValueCard } from "@/components/labs/LabValueCard";
import { LabTrendChart } from "@/components/labs/LabTrendChart";
import type { LabValue } from "@/types/labs";

function ResultDetail({
  abbreviation,
  onBack,
  onResultDeleted,
}: {
  abbreviation: string;
  onBack: () => void;
  onResultDeleted?: (id: number) => void;
}) {
  const { apiClient } = useLabsContext();
  const { data: results = [], isLoading } = useLabResults({ test: abbreviation });
  const deleteResult = useDeleteLabResult();

  const latest = results[0];
  const testName = latest?.test.name ?? abbreviation;
  const category = latest?.test.category ?? "";
  const isQualitative = latest?.test.value_type === "qualitative";

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to results
      </button>

      <div>
        {category && (
          <p className="text-xs uppercase tracking-wide text-gray-500">{category}</p>
        )}
        <h2 className="text-xl font-bold text-gray-900">{testName}</h2>
        {latest && (
          <p className="mt-1 text-sm text-gray-500">
            Latest:{" "}
            <span className="font-mono text-gray-900">
              {formatValue(latest)}
              {latest.unit && ` ${latest.unit}`}
            </span>
            {latest.measured_at && (
              <span className="ml-2 text-xs">· {formatDate(latest.measured_at)}</span>
            )}
          </p>
        )}
      </div>

      {!isQualitative && (
        <div className="rounded-md border border-gray-200 p-4">
          {isLoading ? (
            <div className="h-64 w-full animate-pulse rounded-md bg-gray-100" />
          ) : (
            <LabTrendChart testAbbrev={abbreviation} apiClient={apiClient} />
          )}
        </div>
      )}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-gray-700">History</h3>
        {results.length === 0 ? (
          <p className="text-sm text-gray-500">No measurements yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-md border border-gray-200">
            {results.map((r) => (
              <li key={r.id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-sm text-gray-900">
                      {formatValue(r)}
                    </span>
                    {r.unit && (
                      <span className="text-xs text-gray-500">{r.unit}</span>
                    )}
                    <StatusDot status={r.status} />
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-500">
                    {r.measured_at && <span>{formatDate(r.measured_at)}</span>}
                    {r.source === "manual" ? (
                      <span>Manual</span>
                    ) : r.source_filename ? (
                      <span className="truncate">{r.source_filename}</span>
                    ) : null}
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
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm("Delete this measurement?")) {
                      deleteResult.mutate(r.id, {
                        onSuccess: () => onResultDeleted?.(r.id),
                      });
                    }
                  }}
                  disabled={deleteResult.isPending}
                  className="rounded p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function LabResultsInner({
  selectedTest: selectedTestProp,
  onNavigateToDetail,
  onBack,
  onResultDeleted,
  filters,
}: Pick<LabResultsProps, "selectedTest" | "onNavigateToDetail" | "onBack" | "onResultDeleted" | "filters">) {
  const { apiClient } = useLabsContext();
  const { data: results = [], isLoading } = useLabResults(filters);
  const [selectedTest, setSelectedTest] = useState<string | null>(null);

  const activeTest = selectedTestProp ?? selectedTest;

  const categoryGroups = useMemo(() => {
    const seen = new Set<string>();
    const groups = new Map<string, string[]>();
    for (const r of results) {
      if (seen.has(r.test.abbreviation)) continue;
      seen.add(r.test.abbreviation);
      const cat = r.test.category || "Other";
      const list = groups.get(cat);
      if (list) list.push(r.test.abbreviation);
      else groups.set(cat, [r.test.abbreviation]);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => {
      if (a === "Other") return 1;
      if (b === "Other") return -1;
      return a.localeCompare(b);
    });
  }, [results]);

  const handleNavigate = (abbrev: string) => {
    if (onNavigateToDetail) {
      onNavigateToDetail(abbrev);
    } else {
      setSelectedTest(abbrev);
    }
  };

  if (activeTest) {
    return (
      <ResultDetail
        abbreviation={activeTest}
        onBack={onBack ?? (() => setSelectedTest(null))}
        onResultDeleted={onResultDeleted}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="h-5 w-32 animate-pulse rounded bg-gray-200" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-md bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  if (categoryGroups.length === 0) {
    return (
      <div className="py-8 text-center">
        <p className="text-base font-medium text-gray-900">No lab results yet</p>
        <p className="mt-1 text-sm text-gray-500">
          Upload a lab report to see your results here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Lab Results</h2>
      {categoryGroups.map(([category, abbrevs]) => (
        <div key={category}>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">
            {category}
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {abbrevs.map((abbrev) => (
              <LabValueCard
                key={abbrev}
                testAbbrev={abbrev}
                onNavigate={handleNavigate}
                apiClient={apiClient}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function LabResults({
  apiClient,
  apiBasePath,
  queryClient,
  className,
  theme,
  selectedTest,
  onNavigateToDetail,
  onBack,
  onResultDeleted,
  filters,
}: LabResultsProps) {
  return (
    <LabsProvider
      apiClient={apiClient}
      apiBasePath={apiBasePath}
      queryClient={queryClient}
      theme={theme}
      className={className}
    >
      <LabResultsInner
        selectedTest={selectedTest}
        onNavigateToDetail={onNavigateToDetail}
        onBack={onBack}
        onResultDeleted={onResultDeleted}
        filters={filters}
      />
    </LabsProvider>
  );
}

export default LabResults;

function formatValue(r: LabValue): string {
  if (r.value != null) return String(Number(r.value.toFixed(2)));
  return r.value_qualitative || "—";
}

function fmtNum(n: number): string {
  return String(Number(n.toFixed(2)));
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function StatusDot({ status }: { status: LabValue["status"] }) {
  const color =
    status === "in_range"
      ? "bg-green-500"
      : status === "unknown"
        ? "bg-gray-400"
        : "bg-amber-500";
  const label =
    status === "in_range"
      ? "in range"
      : status === "below"
        ? "below"
        : status === "above"
          ? "above"
          : "no range";
  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-500">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} aria-hidden="true" />
      {label}
    </span>
  );
}
