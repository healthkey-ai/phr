declare module "exact_remote/TrialMatches" {
  import type { AxiosInstance } from "axios";
  import type { QueryClient } from "@tanstack/react-query";

  interface TrialMatchesProps {
    /**
     * Pre-authenticated axios instance whose baseURL is EXACT's origin —
     * this remote issues relative paths (`/trials/`, `/form-settings/`).
     */
    apiClient: AxiosInstance;
    queryClient?: QueryClient;
    /** promop person id. Mutually exclusive with patientInfo, which wins. */
    personId?: string | number;
    /** Inline patient payload, normalised by EXACT's own endpoint. */
    patientInfo?: Record<string, unknown> | null;
    /** Initial filter state; the remote lets the user change it. */
    initialFilters?: Record<string, unknown>;
    className?: string;
  }

  const TrialMatches: React.FC<TrialMatchesProps>;
  export default TrialMatches;
}
