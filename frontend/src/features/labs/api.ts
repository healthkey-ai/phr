/**
 * React Query hooks for the labs endpoints.
 *
 *  GET    /labs/catalog/              → useCatalog()
 *  GET    /labs/results/              → useLabResults(filters?)
 *  POST   /labs/results/              → useCreateLabResult()
 *  DELETE /labs/results/{id}/         → useDeleteLabResult()
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  Catalog,
  LabResult,
  LabResultCreateInput,
  LabUpload,
  LabUploadCommitInput,
  LabUploadCommitResponse,
} from "@/types/labs";

const KEYS = {
  catalog: ["labs", "catalog"] as const,
  results: (filters?: LabResultFilters) => ["labs", "results", filters ?? {}] as const,
  upload: (id: number) => ["labs", "uploads", id] as const,
};

export interface LabResultFilters {
  test?: string;
  from?: string;
  to?: string;
}

export function useCatalog() {
  return useQuery({
    queryKey: KEYS.catalog,
    queryFn: async () => {
      const r = await api.get<Catalog>("/labs/catalog/");
      return r.data;
    },
    // Catalog changes only via backend migration — cache aggressively
    staleTime: 1000 * 60 * 60 * 24, // 24h
    gcTime: 1000 * 60 * 60 * 24,
  });
}

export function useLabResults(filters?: LabResultFilters) {
  return useQuery({
    queryKey: KEYS.results(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.test) params.set("test", filters.test);
      if (filters?.from) params.set("from", filters.from);
      if (filters?.to) params.set("to", filters.to);
      const query = params.toString();
      const r = await api.get<{ results?: LabResult[] } | LabResult[]>(
        `/labs/results/${query ? `?${query}` : ""}`,
      );
      // DRF paginated responses wrap in { count, next, previous, results }
      const data = r.data as { results?: LabResult[] } | LabResult[];
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });
}

export function useCreateLabResult() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: LabResultCreateInput) => {
      const r = await api.post<LabResult>("/labs/results/", input);
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
    },
  });
}

/**
 * Edit an existing lab result. The `id` is immutable; test_type is also
 * immutable (even if you pass test_type_id in the body, the backend ignores
 * it). Everything else — value, unit, measured_at, reference range — gets
 * re-normalised to the test's default_unit on the server.
 */
export function useUpdateLabResult() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: LabResultCreateInput & { id: number }) => {
      const r = await api.patch<LabResult>(`/labs/results/${id}/`, input);
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
    },
  });
}

export function useDeleteLabResult() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/labs/results/${id}/`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
    },
  });
}

// ── Lab uploads (Phase 2b) ──────────────────────────────────────────────────

export interface LabUploadCreateInput {
  files: File[];
  lab_date?: string;
  notes?: string;
}

/**
 * POST /labs/uploads/ — multipart with 1..10 files + optional lab_date/notes.
 *
 * Returns 202 for fresh uploads (task enqueued) or 200 when the backend
 * dedup'd against a prior upload with the same file bytes. Both return the
 * full LabUpload body.
 */
export function useCreateLabUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: LabUploadCreateInput) => {
      const form = new FormData();
      for (const file of input.files) {
        form.append("files", file);
      }
      if (input.lab_date) form.append("lab_date", input.lab_date);
      if (input.notes) form.append("notes", input.notes);

      const r = await api.post<LabUpload>("/labs/uploads/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return r.data;
    },
    onSuccess: (upload) => {
      queryClient.setQueryData(KEYS.upload(upload.id), upload);
    },
  });
}

/**
 * POST /labs/uploads/{id}/commit/ — convert accepted parsed_results rows
 * into real LabResults. Invalidates the labs queries on success so the
 * Records tab re-renders.
 *
 * Also invalidates the CATALOG because the pipeline can have auto-created
 * new LabTestType rows (no-LOINC name fallbacks, uncurated LOINCs) during
 * extraction. Without this invalidation the trend-detail page shows
 * "Unknown test" on first navigation — the catalog cache is stale for 24h.
 */
export function useCommitLabUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: LabUploadCommitInput & { id: number }) => {
      const r = await api.post<LabUploadCommitResponse>(
        `/labs/uploads/${id}/commit/`,
        body,
      );
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labs", "results"] });
      queryClient.invalidateQueries({ queryKey: ["labs", "catalog"] });
    },
  });
}

/**
 * POST /labs/uploads/{id}/extract/ — re-run extraction on a failed or stale
 * upload. Resets status + parsed_results + error_message, then enqueues the
 * Celery task. Returns the refreshed LabUpload (status will be pending /
 * processing depending on worker availability).
 */
export function useRetryExtraction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const r = await api.post<LabUpload>(`/labs/uploads/${id}/extract/`);
      return r.data;
    },
    onSuccess: (upload) => {
      queryClient.setQueryData(KEYS.upload(upload.id), upload);
    },
  });
}

/**
 * GET /labs/uploads/{id}/ — single upload, polled while pending/processing.
 *
 * Polling interval: 2s per design doc §5.2. Stops once status is completed
 * or failed. Consumers should unmount the polling component after that — or
 * pass `enabled={false}` to stop manually.
 */
export function useLabUpload(id: number | null, enabled = true) {
  return useQuery({
    queryKey: id ? KEYS.upload(id) : ["labs", "uploads", "none"],
    queryFn: async () => {
      const r = await api.get<LabUpload>(`/labs/uploads/${id}/`);
      return r.data;
    },
    enabled: enabled && id !== null,
    refetchInterval: (query) => {
      const data = query.state.data as LabUpload | undefined;
      if (!data) return 2000;
      if (data.status === "completed" || data.status === "failed") return false;
      return 2000;
    },
  });
}
