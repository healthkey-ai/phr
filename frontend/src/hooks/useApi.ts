import { useMemo } from "react";
import axios from "axios";
import { authStore } from "@/lib/authStore";

/**
 * Pre-authenticated axios factory for a sibling service. The phr-issued
 * access token is attached per request; the remote component only ever
 * sees an opaque configured client.
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
