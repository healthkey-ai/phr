import type { AxiosInstance } from "axios";
import type { QueryClient } from "@tanstack/react-query";
import type { UploadJob, UploadCommitResponse, LabValue } from "@/types/labs";

export interface LabsThemeTokens {
  colorPrimary: string;
  colorSuccess: string;
  colorWarning: string;
  colorDanger: string;
  colorMuted: string;
  fontFamily: string;
  borderRadius: string;
}

export interface LabsBaseProps {
  apiClient: AxiosInstance;
  apiBasePath?: string;
  queryClient?: QueryClient;
  className?: string;
  theme?: Partial<LabsThemeTokens>;
}

export interface LabUploadsProps extends LabsBaseProps {
  onUploadComplete?: (upload: UploadJob) => void;
  onResultsSaved?: (response: UploadCommitResponse) => void;
}

export interface LabResultsProps extends LabsBaseProps {
  selectedTest?: string;
  onNavigateToDetail?: (testAbbreviation: string) => void;
  onBack?: () => void;
  onResultDeleted?: (resultId: number) => void;
  filters?: { test?: string; from?: string; to?: string };
}

export type { UploadJob, UploadCommitResponse, LabValue };
