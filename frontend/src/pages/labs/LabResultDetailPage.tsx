import { Suspense } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { useEnsurePromopPerson, usePromopApi } from "@/hooks/useApi";
import { lazyRemote } from "@/lib/lazyRemote";

const LabResults = lazyRemote(() => import("labs_results_remote/LabResults"));

export default function LabResultDetailPage() {
  const { test } = useParams<{ test: string }>();
  const apiClient = usePromopApi();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  useEnsurePromopPerson(apiClient);

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Lab Results">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <LabResults
            apiClient={apiClient}
            queryClient={queryClient}
            selectedTest={test}
            onBack={() => {
              // Deep links / fresh tabs have no in-app history — going back
              // would leave the SPA instead of returning to the list.
              const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
              if (idx > 0) navigate(-1);
              else navigate("/labs/results", { replace: true });
            }}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
