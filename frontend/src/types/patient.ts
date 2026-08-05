/**
 * PatientInfo — mirrors the HealthKey PHR PatientInfo model (200+ fields).
 * Only include fields the frontend actively uses. Extend as needed.
 */
export interface PatientInfo {
  person_id: number;
  patient_name?: string;
  age?: number;
  gender?: string;
  disease?: string;
  stage?: string;
  updated_at?: string;
}
