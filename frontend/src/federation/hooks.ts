/**
 * Federation-aware hooks — thin wrappers that inject apiClient from LabsContext.
 */
import { useLabsContext } from "./LabsContext";
import {
  useCatalog as _useCatalog,
  useLabResults as _useLabResults,
  useCreateLabResult as _useCreateLabResult,
  useUpdateLabResult as _useUpdateLabResult,
  useDeleteLabResult as _useDeleteLabResult,
  useLabUploads as _useLabUploads,
  useLabUpload as _useLabUpload,
  useCreateLabUpload as _useCreateLabUpload,
  useCommitLabUpload as _useCommitLabUpload,
  useRetryExtraction as _useRetryExtraction,
  useDeleteLabUpload as _useDeleteLabUpload,
  type LabResultFilters,
} from "@/features/labs/api";

export function useCatalog() {
  const { apiClient } = useLabsContext();
  return _useCatalog(apiClient);
}

export function useLabResults(filters?: LabResultFilters) {
  const { apiClient } = useLabsContext();
  return _useLabResults(filters, apiClient);
}

export function useCreateLabResult() {
  const { apiClient } = useLabsContext();
  return _useCreateLabResult(apiClient);
}

export function useUpdateLabResult() {
  const { apiClient } = useLabsContext();
  return _useUpdateLabResult(apiClient);
}

export function useDeleteLabResult() {
  const { apiClient } = useLabsContext();
  return _useDeleteLabResult(apiClient);
}

export function useLabUploads() {
  const { apiClient } = useLabsContext();
  return _useLabUploads(apiClient);
}

export function useLabUpload(id: number | null, enabled = true) {
  const { apiClient } = useLabsContext();
  return _useLabUpload(id, enabled, apiClient);
}

export function useCreateLabUpload() {
  const { apiClient } = useLabsContext();
  return _useCreateLabUpload(apiClient);
}

export function useCommitLabUpload() {
  const { apiClient } = useLabsContext();
  return _useCommitLabUpload(apiClient);
}

export function useRetryExtraction() {
  const { apiClient } = useLabsContext();
  return _useRetryExtraction(apiClient);
}

export function useDeleteLabUpload() {
  const { apiClient } = useLabsContext();
  return _useDeleteLabUpload(apiClient);
}
