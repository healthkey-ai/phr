export interface AppUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  identity_level: string;
  is_admin: boolean;
  has_medical_records: boolean;
  claims: {
    ADMIN: boolean;
    MEDICAL_RECORDS: boolean;
  };
}
