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
} from "@/types/labs";

const KEYS = {
  catalog: ["labs", "catalog"] as const,
  results: (filters?: LabResultFilters) => ["labs", "results", filters ?? {}] as const,
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
