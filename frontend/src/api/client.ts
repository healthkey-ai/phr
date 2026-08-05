import axios from "axios";
import { authStore } from "@/lib/authStore";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = authStore.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Deduped refresh: concurrent 401s share one refresh round-trip.
let refreshPromise: Promise<string> | null = null;

export async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    const refresh = authStore.getRefreshToken();
    if (!refresh) return Promise.reject(new Error("No refresh token"));
    refreshPromise = axios
      .post("/api/v1/auth/refresh/", { refresh })
      .then((r) => {
        // Rotation is on server-side: a new refresh token comes back too.
        authStore.setTokens({ access: r.data.access, refresh: r.data.refresh ?? refresh });
        return r.data.access as string;
      })
      .catch((err) => {
        authStore.clear();
        throw err;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry && authStore.getRefreshToken()) {
      error.config._retry = true;
      try {
        const token = await refreshAccessToken();
        error.config.headers.Authorization = `Bearer ${token}`;
        return api.request(error.config);
      } catch {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error as Error);
  },
);

export default api;
