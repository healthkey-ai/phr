import { lazy, Suspense } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { usePromopApi } from "@/hooks/useApi";

const PatientInfo = lazy(() => import("labs_results_remote/PatientInfo"));

export default function PatientRecordPage() {
  const apiClient = usePromopApi();
  const queryClient = useQueryClient();

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Patient Record">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <PatientInfo apiClient={apiClient} queryClient={queryClient} />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
