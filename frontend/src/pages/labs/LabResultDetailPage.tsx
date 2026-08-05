import { lazy, Suspense } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { useLabsApi } from "@/hooks/useApi";

const LabResults = lazy(() => import("labs_remote/LabResults"));

export default function LabResultDetailPage() {
  const { test } = useParams<{ test: string }>();
  const apiClient = useLabsApi();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Lab Results">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <LabResults
            apiClient={apiClient}
            queryClient={queryClient}
            selectedTest={test}
            onBack={() => navigate(-1)}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
