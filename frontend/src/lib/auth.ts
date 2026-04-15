/**
 * In-memory access token store + persistent refresh token in localStorage.
 *
 * Per docs/patient-app-architecture.md §5.2: access tokens stay in memory
 * (not localStorage) to mitigate XSS exfiltration. Refresh token persists
 * across reloads to keep users logged in.
 */
const REFRESH_KEY = "hk_refresh";

let accessToken: string | null = null;
const subscribers = new Set<() => void>();

export const authStore = {
  getAccessToken: () => accessToken,
  getRefreshToken: () => localStorage.getItem(REFRESH_KEY),
  setTokens: ({ access, refresh }: { access: string; refresh: string }) => {
    accessToken = access;
    localStorage.setItem(REFRESH_KEY, refresh);
    subscribers.forEach((cb) => cb());
  },
  clear: () => {
    accessToken = null;
    localStorage.removeItem(REFRESH_KEY);
    subscribers.forEach((cb) => cb());
  },
  subscribe: (cb: () => void) => {
    subscribers.add(cb);
    return () => subscribers.delete(cb);
  },
  isAuthenticated: () => Boolean(accessToken || localStorage.getItem(REFRESH_KEY)),
};
