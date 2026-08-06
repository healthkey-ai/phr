declare module "labs_results_remote/LabResults" {
  import type { AxiosInstance } from "axios";
  import type { QueryClient } from "@tanstack/react-query";

  interface LabResultsProps {
    apiClient: AxiosInstance;
    apiBasePath?: string;
    queryClient?: QueryClient;
    className?: string;
    theme?: Partial<{
      colorPrimary: string;
      colorSuccess: string;
      colorWarning: string;
      colorDanger: string;
      colorMuted: string;
      fontFamily: string;
      borderRadius: string;
    }>;
    selectedTest?: string;
    onNavigateToDetail?: (conceptCode: string) => void;
    onBack?: () => void;
    onResultDeleted?: (measurementId: number) => void;
  }

  const LabResults: React.FC<LabResultsProps>;
  export default LabResults;
}

declare module "labs_results_remote/PatientInfo" {
  import type { AxiosInstance } from "axios";
  import type { QueryClient } from "@tanstack/react-query";

  interface PatientInfoProps {
    apiClient: AxiosInstance;
    /** Prefixed to "/patient-info/me/" — pass "" when the client's baseURL
     * already ends at the API root. */
    apiBasePath?: string;
    queryClient?: QueryClient;
    className?: string;
    theme?: Partial<{
      colorPrimary: string;
      colorSuccess: string;
      colorWarning: string;
      colorDanger: string;
      colorMuted: string;
      fontFamily: string;
      borderRadius: string;
    }>;
    readOnly?: boolean;
    onPatientUpdated?: (data: unknown) => void;
  }

  const PatientInfo: React.FC<PatientInfoProps>;
  export default PatientInfo;
}
