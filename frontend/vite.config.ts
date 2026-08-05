import dns from "node:dns";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Force Node to resolve `localhost` to 127.0.0.1 (IPv4) before ::1 (IPv6).
// Node 18+ honors the system's IPv6 preference, but Django's dev server only
// binds to IPv4 by default — without this, the proxy gets ECONNREFUSED on
// every request even though `curl http://localhost:8000` works.
dns.setDefaultResultOrder("ipv4first");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(import.meta.dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
