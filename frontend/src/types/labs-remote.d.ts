declare module "labs_remote/LabUploads" {
  import type { AxiosInstance } from "axios";
  import type { QueryClient } from "@tanstack/react-query";

  interface LabUploadsProps {
    apiClient: AxiosInstance;
    apiBasePath?: string;
    queryClient?: QueryClient;
    className?: string;
    title?: string;
    description?: string | string[];
    theme?: Partial<{
      colorPrimary: string;
      colorSuccess: string;
      colorWarning: string;
      colorDanger: string;
      colorMuted: string;
      fontFamily: string;
      borderRadius: string;
    }>;
    onUploadComplete?: (upload: unknown) => void;
    onResultsSaved?: (response: unknown) => void;
  }

  const LabUploads: React.FC<LabUploadsProps>;
  export default LabUploads;
}

declare module "labs_remote/LabResults" {
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
    onNavigateToDetail?: (testAbbreviation: string) => void;
    onBack?: () => void;
    onResultDeleted?: (resultId: number) => void;
    filters?: { test?: string; from?: string; to?: string };
  }

  const LabResults: React.FC<LabResultsProps>;
  export default LabResults;
}
