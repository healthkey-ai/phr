import { useEffect, useMemo } from "react";
import axios, { type AxiosInstance } from "axios";
import { authStore } from "@/lib/authStore";
import { refreshAccessToken } from "@/api/client";

/**
 * Pre-authenticated axios factory for a sibling service. The phr-issued
 * access token is attached per request; the remote component only ever
 * sees an opaque configured client. On 401 the client refreshes the
 * access token (deduped with the host client's refresh) and retries once
 * — without this, a user lingering on a federated page past token TTL
 * gets bare 401s inside the remote with no recovery.
 */
function useServiceApi(baseURL: string) {
  return useMemo(() => {
    const client = axios.create({
      baseURL,
      headers: { "Content-Type": "application/json" },
    });

    client.interceptors.request.use((config) => {
      const token = authStore.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401 && !error.config._retry && authStore.getRefreshToken()) {
          error.config._retry = true;
          try {
            const token = await refreshAccessToken();
            error.config.headers.Authorization = `Bearer ${token}`;
            return client.request(error.config);
          } catch {
            // Refresh failed — session is gone; the host auth store clears
            // and the guard redirects on the next route interaction.
          }
        }
        return Promise.reject(error as Error);
      },
    );

    return client;
  }, [baseURL]);
}

/** hk-labs — verifies phr-issued JWTs against the phr accounts DB
 * (via /api/v1/auth/jwks/ or /api/v1/auth/introspect/). */
export function useLabsApi() {
  return useServiceApi(import.meta.env.VITE_LABS_API_URL || "http://localhost:9100/api/v1");
}

/** promop — patient record service (PatientInfo). Verifies phr-issued JWTs
 * via its PhrTokenProvider. Base ends at the API root; the PatientInfo
 * remote appends "/patient-info/me/". */
export function usePromopApi() {
  return useServiceApi(import.meta.env.VITE_PROMOP_API_URL || "http://localhost:9200/api");
}

/** soc — treatment recommendations (Find Treatments). Verifies phr-issued
 * JWTs via its PhrTokenProvider, same as the other siblings. */
export function useSocApi() {
  return useServiceApi(import.meta.env.VITE_SOC_API_URL || "http://localhost:9300/api");
}

/** promop's /patient-info/me/ auto-provisions the Person for a first-time
 * phr user, but its lab-results endpoints do NOT — a brand-new user whose
 * first click is Lab Results would 404 until they visit the Health Profile
 * once. Fire-and-forget the provisioning call on labs pages to kill the
 * navigation-order dependency. */
export function useEnsurePromopPerson(apiClient: AxiosInstance) {
  useEffect(() => {
    apiClient.get("/patient-info/me/").catch(() => {});
  }, [apiClient]);
}
