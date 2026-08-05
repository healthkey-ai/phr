import api, { refreshAccessToken } from "./client";
import { authStore } from "@/lib/authStore";
import type { AppUser } from "@/types/user";

export async function loginWithEmail(email: string, password: string): Promise<AppUser> {
  const { data } = await api.post("/auth/login/", { email, password });
  authStore.setTokens({ access: data.access, refresh: data.refresh });
  return fetchMe();
}

export async function registerWithEmail(
  email: string,
  password: string,
  firstName: string,
  lastName: string,
): Promise<AppUser> {
  const { data } = await api.post("/auth/register/", {
    email,
    password,
    first_name: firstName,
    last_name: lastName,
  });
  authStore.setTokens(data.tokens);
  return data.user as AppUser;
}

export async function fetchMe(): Promise<AppUser> {
  const { data } = await api.get<AppUser>("/auth/me/");
  return data;
}

/** Exchange the persisted refresh token for a fresh access token on page
 * load, so the very first authenticated request doesn't 401-then-retry.
 * Returns false when there is no session to restore. */
export async function restoreSession(): Promise<boolean> {
  if (authStore.getAccessToken()) return true;
  if (!authStore.getRefreshToken()) return false;
  try {
    await refreshAccessToken();
    return true;
  } catch {
    return false;
  }
}

export async function logout() {
  const refresh = authStore.getRefreshToken();
  if (refresh) {
    // Best-effort server-side blacklist; local state clears regardless.
    await api.post("/auth/logout/", { refresh }).catch(() => {});
  }
  authStore.clear();
}
