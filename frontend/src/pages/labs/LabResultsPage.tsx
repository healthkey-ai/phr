import { Suspense, useEffect } from "react";
import { useNavigate, useNavigationType } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { useEnsurePromopPerson, usePromopApi } from "@/hooks/useApi";
import { lazyRemote } from "@/lib/lazyRemote";

const SCROLL_KEY = "lab-results-scroll";
// promop's remote exposes LabResults over its OMOP measurements — the same
// deployed remoteEntry.js the Health Profile already loads.
const LabResults = lazyRemote(() => import("labs_results_remote/LabResults"));

export default function LabResultsPage() {
  const apiClient = usePromopApi();
  const navigate = useNavigate();
  const navigationType = useNavigationType();
  const queryClient = useQueryClient();
  useEnsurePromopPerson(apiClient);

  useEffect(() => {
    const saved = sessionStorage.getItem(SCROLL_KEY);
    if (saved === null) return;
    sessionStorage.removeItem(SCROLL_KEY);
    // Restore only when arriving via back/forward — a fresh visit from the
    // sidebar must not jump to a stale offset from a previous session.
    if (navigationType !== "POP") return;
    const y = parseInt(saved, 10);
    requestAnimationFrame(() => window.scrollTo(0, y));
  }, [navigationType]);

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Lab Results">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <LabResults
            apiClient={apiClient}
            queryClient={queryClient}
            onNavigateToDetail={(test) => {
              sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
              // concept codes can contain "/" or "%" — raw values break the
              // :test route match or throw URI-malformed.
              navigate(`/labs/results/${encodeURIComponent(test)}`);
            }}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
