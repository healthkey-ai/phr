import { Suspense } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import { RemoteBoundary } from "@/components/RemoteFallback";
import { useSocApi, usePromopApi } from "@/hooks/useApi";
import { lazyRemote } from "@/lib/lazyRemote";

const Recommendations = lazyRemote(() => import("soc_remote/Recommendations"));

// promop's disease slug is not always soc's catalog key. Only the known
// divergences are listed; anything absent passes through unchanged so other
// diseases keep resolving.
const PROMOP_TO_SOC_DISEASE_SLUG: Record<string, string> = {
  "multiple-myeloma": "myeloma",
};

// promop only fills disease_slug on its OMOP-derived path; a disease entered
// through the record form leaves the slug null while the canonical title is
// saved. Derive the slug from the title so both paths land on the same key.
function diseaseNameToSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

/**
 * Project promop's record onto the fields soc's pipeline reads.
 *
 * Deliberately partial. soc tolerates sparse input and falls back to
 * UNKNOWN, so a field is forwarded only where the two services agree on
 * its shape — passing a value whose meaning differs would mislead the
 * pipeline more than omitting it does.
 */
function toSocPatientInfo(record: Record<string, unknown>): Record<string, unknown> {
  const sexMap: Record<string, string> = { Male: "M", Female: "F" };
  const info: Record<string, unknown> = {};

  // Disease is the recommend lookup key, passed separately as a prop — it is
  // not part of soc's patient_info contract.
  if (typeof record.stage === "string" && record.stage) info.stage = record.stage;
  const age = record.age ?? record.patient_age;
  if (typeof age === "number") info.age = age;
  if (typeof record.gender === "string" && record.gender) {
    info.sex = sexMap[record.gender] ?? "other";
  }
  if (typeof record.ecog_performance_status === "number") {
    info.ecog_score = record.ecog_performance_status;
  }
  if (typeof record.therapy_lines_count === "number") {
    info.therapy_lines_count = record.therapy_lines_count;
  }
  // soc derives its neuropathy answer from this CTCAE grade, which drives
  // regimen exclusions. The other comorbidity axes need condition-code
  // parsing soc does not do yet, so they are left unset rather than guessed.
  if (typeof record.peripheral_neuropathy_grade === "number") {
    info.peripheral_neuropathy_grade = record.peripheral_neuropathy_grade;
  }
  // Therapy history in both shapes: free text, and concept ids. Which one
  // soc uses depends on its own toggle, so send whichever are present.
  for (const f of ["first_line_therapy", "second_line_therapy", "later_therapy"] as const) {
    if (typeof record[f] === "string" && record[f]) info[f] = record[f];
  }
  for (const f of ["first_line_therapy_id", "second_line_therapy_id"] as const) {
    if (typeof record[f] === "number") info[f] = record[f];
  }
  if (Array.isArray(record.later_therapy_ids) && record.later_therapy_ids.length) {
    info.later_therapy_ids = record.later_therapy_ids;
  }
  return info;
}

export default function FindTreatmentsPage() {
  const socApi = useSocApi();
  const promopApi = usePromopApi();
  const queryClient = useQueryClient();

  // The signed-in patient's own record, resolved server-side from the token.
  // On failure we render with no disease and soc offers its own picker,
  // which is a better outcome than blocking the page.
  const profile = useQuery({
    queryKey: ["promop", "patient-info", "me"],
    queryFn: async () => {
      const res = await promopApi.get("/patient-info/me/");
      return res.data as { patient_info?: Record<string, unknown> };
    },
  });

  if (profile.isLoading) {
    return (
      <div className="federated-content rounded-lg bg-background p-6">
        <LoadingIndicator className="py-12" />
      </div>
    );
  }

  const record = profile.data?.patient_info ?? {};
  const promopSlug =
    typeof record.disease_slug === "string" && record.disease_slug
      ? record.disease_slug
      : typeof record.disease === "string" && record.disease
        ? diseaseNameToSlug(record.disease)
        : undefined;
  const disease = promopSlug
    ? (PROMOP_TO_SOC_DISEASE_SLUG[promopSlug] ?? promopSlug)
    : undefined;

  return (
    <div className="federated-content rounded-lg bg-background p-6">
      <RemoteBoundary name="Find Treatments">
        <Suspense fallback={<LoadingIndicator className="py-12" />}>
          <Recommendations
            apiClient={socApi}
            queryClient={queryClient}
            disease={disease}
            initialPatientInfo={toSocPatientInfo(record)}
          />
        </Suspense>
      </RemoteBoundary>
    </div>
  );
}
