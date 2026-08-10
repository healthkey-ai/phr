import { Suspense } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { useExactApi, usePromopApi } from "@/hooks/useApi";
import { lazyRemote } from "@/lib/lazyRemote";

const TrialMatches = lazyRemote(() => import("exact_remote/TrialMatches"));

export default function FindTrialsPage() {
  const exactApi = useExactApi();
  const promopApi = usePromopApi();
  const queryClient = useQueryClient();

  /**
   * The signed-in patient's record, normalised by EXACT itself.
   *
   * Deliberately not a hand-written field mapping like the Find Treatments
   * page uses: EXACT exposes `/normalize-ctomop-row/` for exactly this, and
   * it does work we should not reimplement — receptor statuses to codes, TNM
   * strings to short codes. Reproducing that here would drift from whatever
   * EXACT does next.
   *
   * Left at the default staleTime so it refetches on window focus: a patient
   * who edits their country and postcode in the Health Profile and comes back
   * sees matches for the new location without a manual reload. Filtering
   * inside the remote does not remount this query, so it costs nothing while
   * they browse.
   */
  const patientInfo = useQuery({
    queryKey: ["exact", "normalized-patient-info", "me"],
    queryFn: async () => {
      const res = await promopApi.get("/patient-info/me/");
      const row = (res.data as { patient_info?: Record<string, unknown> }).patient_info;
      if (!row) return null;
      const normalized = await exactApi.post("/normalize-ctomop-row/", row);
      return normalized.data as Record<string, unknown>;
    },
  });

  if (patientInfo.isLoading) {
    return (
      <div className="federated-content rounded-lg bg-background p-6">
        <LoadingIndicator className="py-12" />
      </div>
    );
  }

  // A record we could not read or normalise is not a reason to block the
  // page: the remote still renders its own filters and an unfiltered trial
  // list, which is more useful than an error.
  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Find Trials">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <TrialMatches
            apiClient={exactApi}
            queryClient={queryClient}
            patientInfo={patientInfo.data ?? null}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
