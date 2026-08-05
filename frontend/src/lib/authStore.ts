/**
 * Token store — the access token lives only in memory (XSS mitigation);
 * the refresh token persists in localStorage so a page reload can
 * re-establish the session without re-entering credentials.
 */
const REFRESH_KEY = "phr_refresh";

let accessToken: string | null = null;
const listeners = new Set<() => void>();

export const authStore = {
  getAccessToken(): string | null {
    return accessToken;
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  setTokens(tokens: { access: string; refresh: string }) {
    accessToken = tokens.access;
    localStorage.setItem(REFRESH_KEY, tokens.refresh);
    listeners.forEach((fn) => fn());
  },
  clear() {
    accessToken = null;
    localStorage.removeItem(REFRESH_KEY);
    listeners.forEach((fn) => fn());
  },
  subscribe(fn: () => void): () => void {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
