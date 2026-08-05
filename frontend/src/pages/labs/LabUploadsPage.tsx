import { lazy, Suspense } from "react";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { useLabsApi } from "@/hooks/useApi";

const LabUploads = lazy(() => import("labs_remote/LabUploads"));

export default function LabUploadsPage() {
  const apiClient = useLabsApi();

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Lab Uploads">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <LabUploads
          apiClient={apiClient}
          apiBasePath="/api/v1"
          title="Upload Lab Reports"
          description={[
            "Already connected your medical records? You may still have results that aren't in your provider's system — genetics tests, outside lab work, or records from a previous provider. Upload those here so your health profile stays complete.",
            "If your provider doesn't support electronic record sharing, you can use this page to upload all of your lab reports directly.",
          ]}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
