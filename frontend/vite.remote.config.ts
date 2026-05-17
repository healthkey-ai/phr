import dns from "node:dns";
import path from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { federation } from "@module-federation/vite";

dns.setDefaultResultOrder("ipv4first");

function devHarnessRedirect(): Plugin {
  return {
    name: "dev-harness-redirect",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.url === "/" || req.url === "/index.html") {
          req.url = "/dev-harness.html";
        }
        next();
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || "http://localhost:9000";

  return {
    plugins: [
      devHarnessRedirect(),
      react(),
      federation({
        name: "labs_remote",
        filename: "remoteEntry.js",
        exposes: {
          "./LabUploads": "./src/federation/LabUploads.tsx",
          "./LabResults": "./src/federation/LabResults.tsx",
          "./types": "./src/federation/types.ts",
        },
        shared: {
          react: { singleton: true, requiredVersion: "^18.3.0" },
          "react-dom": { singleton: true, requiredVersion: "^18.3.0" },
          "@tanstack/react-query": { singleton: true, requiredVersion: "^5.0.0" },
          axios: { singleton: true, requiredVersion: "^1.6.0" },
        },
        dts: false,
      }),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      outDir: "dist/remote",
      target: "esnext",
    },
    server: {
      port: 5174,
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
