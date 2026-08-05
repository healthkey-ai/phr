import api from "./client";
import type { AppUser } from "@/types/user";

export async function listAdmins(): Promise<AppUser[]> {
  const { data } = await api.get<AppUser[]>("/auth/admins/");
  return data;
}

export async function setUserClaims(
  userId: number,
  claims: Partial<Record<"ADMIN" | "MEDICAL_RECORDS", boolean>>,
): Promise<AppUser> {
  const { data } = await api.post<AppUser>("/auth/set-claims/", {
    user_id: userId,
    claims,
  });
  return data;
}
