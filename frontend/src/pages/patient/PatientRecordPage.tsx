import { Suspense } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { usePromopApi } from "@/hooks/useApi";
import { lazyRemote } from "@/lib/lazyRemote";

const PatientInfo = lazyRemote(() => import("labs_results_remote/PatientInfo"));

export default function PatientRecordPage() {
  const apiClient = usePromopApi();
  const queryClient = useQueryClient();

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Health Profile">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <PatientInfo apiClient={apiClient} queryClient={queryClient} />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
