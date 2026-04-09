import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { FormSettings, PatientInfo, PatientInfoUpdate } from "@/types";

const KEYS = {
  patientInfo: ["patient-info"] as const,
  completeness: ["patient-info", "completeness"] as const,
  formSettings: ["form-settings"] as const,
};

export function usePatientInfo() {
  return useQuery({
    queryKey: KEYS.patientInfo,
    queryFn: async () => {
      const r = await api.get<PatientInfo>("/patient-info/user/");
      return r.data;
    },
  });
}

export function useUpdatePatientInfo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (update: PatientInfoUpdate) => {
      const r = await api.patch<PatientInfo>("/patient-info/user/", update);
      return r.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(KEYS.patientInfo, data);
      queryClient.invalidateQueries({ queryKey: KEYS.completeness });
    },
  });
}

export function useProfileCompleteness() {
  return useQuery({
    queryKey: KEYS.completeness,
    queryFn: async () => {
      const r = await api.get<{ completeness_score: number; completeness_by_category: Record<string, number> }>(
        "/patient-info/profile-completeness/",
      );
      return r.data;
    },
  });
}

export function useFormSettings() {
  return useQuery({
    queryKey: KEYS.formSettings,
    queryFn: async () => {
      const r = await api.get<FormSettings>("/form-settings/");
      return r.data;
    },
    staleTime: 1000 * 60 * 60, // 1h — form settings rarely change
  });
}
