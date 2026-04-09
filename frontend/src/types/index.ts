export interface User {
  id: number;
  email: string;
  identity_level: "unverified" | "mfa" | "ial1" | "ial2";
  mfa_enabled: boolean;
  created_at: string;
}

export interface PatientInfo {
  id: number;
  first_name: string;
  last_name: string;
  dob: string | null;
  gender: string;
  ethnicity: string[];
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  country: string;
  postal_code: string;
  geo_lat: number | null;
  geo_long: number | null;
  languages: string[];
  insurance_status: string;
  employment_status: string;
  disease: string;
  details: Record<string, unknown>;
  completeness_score: number;
  completeness_by_category: Record<string, number>;
  updated_at: string;
}

export type PatientInfoUpdate = Partial<Omit<PatientInfo, "id" | "bmi" | "completeness_score" | "completeness_by_category" | "updated_at">>;

export interface FormSettingOption {
  value: string | number;
  label: string;
}

export interface FormSettings {
  gender: FormSettingOption[];
  ethnicity: FormSettingOption[];
  diseases: FormSettingOption[];
  common_conditions: FormSettingOption[];
  smoking_status: FormSettingOption[];
  alcohol_frequency: FormSettingOption[];
  exercise_level: FormSettingOption[];
  diet_type: FormSettingOption[];
  family_relatives: FormSettingOption[];
  family_conditions: FormSettingOption[];
  ecog_performance_status: FormSettingOption[];
  iss_stage: FormSettingOption[];
  myeloma_disease_status: FormSettingOption[];
}
