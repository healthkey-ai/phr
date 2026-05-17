import { LabsProvider } from "./LabsProvider";
import type { LabResultsProps } from "./types";

export function LabResults({
  apiClient,
  apiBasePath,
  queryClient,
  className,
  theme,
  onNavigateToDetail: _onNavigateToDetail,
  onResultDeleted: _onResultDeleted,
  filters: _filters,
}: LabResultsProps) {
  return (
    <LabsProvider
      apiClient={apiClient}
      apiBasePath={apiBasePath}
      queryClient={queryClient}
      theme={theme}
      className={className}
    >
      <div>LabResults — placeholder (Phase 3)</div>
    </LabsProvider>
  );
}

export default LabResults;
