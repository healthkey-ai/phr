/**
 * React Query hooks for the labs endpoints — v2.
 *
 * Every hook accepts an optional `apiClient` (AxiosInstance) parameter.
 * When omitted, the global `api` instance is used (backwards-compatible).
 * The federation layer injects the host-provided client via this parameter.
 */
import type { AxiosInstance } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  Catalog,
  LabValue,
  LabValueCreateInput,
  UploadCommitInput,
  UploadCommitResponse,
  UploadJob,
} from "@/types/labs";

const KEYS = {
  catalog: ["labs", "catalog"] as const,
  results: (filters?: LabResultFilters) => ["labs", "results", filters ?? {}] as const,
  upload: (id: number) => ["labs", "uploads", id] as const,
  uploads: ["labs", "uploads", "list"] as const,
};

export interface LabResultFilters {
  test?: string;
  from?: string;
  to?: string;
}

export function useCatalog(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  return useQuery({
    queryKey: KEYS.catalog,
    queryFn: async () => {
      const r = await client.get<Catalog>("/labs/catalog/");
      return r.data;
    },
    staleTime: 1000 * 60 * 60 * 24,
    gcTime: 1000 * 60 * 60 * 24,
  });
}

export function useLabResults(filters?: LabResultFilters, apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  return useQuery({
    queryKey: KEYS.results(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.test) params.set("test", filters.test);
      if (filters?.from) params.set("from", filters.from);
      if (filters?.to) params.set("to", filters.to);
      const query = params.toString();
      const r = await client.get<{ results?: LabValue[] } | LabValue[]>(
        `/labs/results/${query ? `?${query}` : ""}`,
      );
      const data = r.data as { results?: LabValue[] } | LabValue[];
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });
}

export function useCreateLabResult(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: LabValueCreateInput) => {
      const r = await client.post<LabValue>("/labs/results/", input);
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
    },
  });
}

export function useUpdateLabResult(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: LabValueCreateInput & { id: number }) => {
      const r = await client.patch<LabValue>(`/labs/results/${id}/`, input);
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
    },
  });
}

export function useDeleteLabResult(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await client.delete(`/labs/results/${id}/`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
    },
  });
}

// ── Uploads ────────────────────────────────────────────────────────────────

export interface UploadCreateInput {
  files: File[];
  lab_date?: string;
  notes?: string;
}

export function useDeleteLabUpload(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await client.delete(`/labs/uploads/${id}/`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
      queryClient.invalidateQueries({ queryKey: KEYS.uploads });
    },
  });
}

export function useCreateLabUpload(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: UploadCreateInput) => {
      const form = new FormData();
      for (const file of input.files) {
        form.append("files", file);
      }
      if (input.lab_date) form.append("lab_date", input.lab_date);
      if (input.notes) form.append("notes", input.notes);

      const r = await client.post<UploadJob>("/labs/uploads/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return r.data;
    },
    onSuccess: (upload) => {
      queryClient.setQueryData(KEYS.upload(upload.id), upload);
      queryClient.invalidateQueries({ queryKey: KEYS.uploads });
    },
  });
}

export function useCommitLabUpload(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: UploadCommitInput & { id: number }) => {
      const r = await client.post<UploadCommitResponse>(
        `/labs/uploads/${id}/commit/`,
        body,
      );
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
      queryClient.invalidateQueries({ queryKey: ["labs", "catalog"] });
      queryClient.invalidateQueries({ queryKey: KEYS.uploads });
    },
  });
}

export function useRetryExtraction(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const r = await client.post<UploadJob>(`/labs/uploads/${id}/extract/`);
      return r.data;
    },
    onSuccess: (upload) => {
      queryClient.setQueryData(KEYS.upload(upload.id), upload);
    },
  });
}

export function useLabUploads(apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  return useQuery({
    queryKey: KEYS.uploads,
    queryFn: async () => {
      const r = await client.get<{ results?: UploadJob[] } | UploadJob[]>(
        "/labs/uploads/",
      );
      const data = r.data;
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });
}

export function useLabUpload(id: number | null, enabled = true, apiClient?: AxiosInstance) {
  const client = apiClient ?? api;
  return useQuery({
    queryKey: id ? KEYS.upload(id) : ["labs", "uploads", "none"],
    queryFn: async () => {
      const r = await client.get<UploadJob>(`/labs/uploads/${id}/`);
      return r.data;
    },
    enabled: enabled && id !== null,
    refetchInterval: (query) => {
      const data = query.state.data as UploadJob | undefined;
      if (!data) return 2000;
      if (data.status === "completed" || data.status === "failed") return false;
      return 2000;
    },
  });
}
