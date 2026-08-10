declare module "soc_remote/Recommendations" {
  import type { AxiosInstance } from "axios";
  import type { QueryClient } from "@tanstack/react-query";

  interface RecommendationsProps {
    apiClient: AxiosInstance;
    /** Defaults to "/api/v1" inside the remote; apiClient carries the origin. */
    apiBasePath?: string;
    queryClient?: QueryClient;
    /**
     * soc catalog key — a firestore id or slug, not a display title. Left
     * undefined when the record has no disease, in which case the remote
     * renders its own picker.
     */
    disease?: string;
    /** Sparse patient context; soc falls back to UNKNOWN for what is absent. */
    initialPatientInfo?: Record<string, unknown>;
    /** Base path for trial links, when a host routes them somewhere. */
    exactBaseUrl?: string;
    className?: string;
  }

  const Recommendations: React.FC<RecommendationsProps>;
  export default Recommendations;
}
