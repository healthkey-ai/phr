import { Suspense, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { usePromopApi } from "@/hooks/useApi";
import { lazyRemote } from "@/lib/lazyRemote";

const SCROLL_KEY = "lab-results-scroll";
// promop's remote exposes LabResults over its OMOP measurements — the same
// deployed remoteEntry.js the Health Profile already loads.
const LabResults = lazyRemote(() => import("labs_results_remote/LabResults"));

export default function LabResultsPage() {
  const apiClient = usePromopApi();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    const saved = sessionStorage.getItem(SCROLL_KEY);
    if (saved) {
      sessionStorage.removeItem(SCROLL_KEY);
      const y = parseInt(saved, 10);
      requestAnimationFrame(() => window.scrollTo(0, y));
    }
  }, []);

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Lab Results">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <LabResults
            apiClient={apiClient}
            queryClient={queryClient}
            onNavigateToDetail={(test) => {
              sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
              navigate(`/labs/results/${test}`);
            }}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
