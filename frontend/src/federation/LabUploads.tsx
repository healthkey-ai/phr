import { LabsProvider } from "./LabsProvider";
import type { LabUploadsProps } from "./types";

export function LabUploads({
  apiClient,
  apiBasePath,
  queryClient,
  className,
  theme,
  onUploadComplete: _onUploadComplete,
  onResultsSaved: _onResultsSaved,
}: LabUploadsProps) {
  return (
    <LabsProvider
      apiClient={apiClient}
      apiBasePath={apiBasePath}
      queryClient={queryClient}
      theme={theme}
      className={className}
    >
      <div>LabUploads — placeholder (Phase 3)</div>
    </LabsProvider>
  );
}

export default LabUploads;
