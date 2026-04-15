/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL for backend API requests.
   * Defaults to `/api/v1` (proxied by Vite dev server) when not set.
   * In production, set to absolute URL e.g. `https://api.healthkey.io/api/v1`.
   */
  readonly VITE_API_URL?: string;

  /**
   * Dev-only: target host:port for the Vite proxy.
   * Defaults to `http://127.0.0.1:8000` (Django dev server).
   * Not bundled into production builds.
   */
  readonly VITE_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
