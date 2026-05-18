import dns from "node:dns";
import path from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { federation } from "@module-federation/vite";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

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
          react: { singleton: true, strictVersion: false },
          "react-dom": { singleton: true, strictVersion: false },
          "react/jsx-runtime": { singleton: true, strictVersion: false },
          "react/jsx-dev-runtime": { singleton: true, strictVersion: false },
          "@tanstack/react-query": { singleton: true, strictVersion: false },
          axios: { singleton: true, strictVersion: false },
          recharts: { singleton: true, strictVersion: false },
          "@radix-ui/react-dialog": { singleton: true, strictVersion: false },
          "@radix-ui/react-select": { singleton: true, strictVersion: false },
          "@radix-ui/react-progress": { singleton: true, strictVersion: false },
          "@radix-ui/react-checkbox": { singleton: true, strictVersion: false },
          "@radix-ui/react-label": { singleton: true, strictVersion: false },
        },
        dts: false,
      }),
    ],
    css: {
      postcss: {
        plugins: [
          tailwindcss({ config: path.resolve(__dirname, "tailwind.remote.config.ts") }),
          autoprefixer(),
        ],
      },
    },
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
