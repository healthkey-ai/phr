import { useMemo } from "react";

import { LabsProvider } from "./LabsProvider";
import { useLabsContext } from "./LabsContext";
import type { LabResultsProps } from "./types";
import { useLabResults } from "./hooks";
import { LabValueCard } from "@/components/labs/LabValueCard";

function LabResultsInner({
  onNavigateToDetail,
  onResultDeleted: _onResultDeleted,
  filters,
}: Pick<LabResultsProps, "onNavigateToDetail" | "onResultDeleted" | "filters">) {
  const { apiClient } = useLabsContext();
  const { data: results = [], isLoading } = useLabResults(filters);

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
                onNavigate={onNavigateToDetail}
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
  onNavigateToDetail,
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
        onNavigateToDetail={onNavigateToDetail}
        onResultDeleted={onResultDeleted}
        filters={filters}
      />
    </LabsProvider>
  );
}

export default LabResults;
