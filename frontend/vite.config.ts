import dns from "node:dns";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import type { Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { federation } from "@module-federation/vite";

// Force IPv4 so the proxy reaches Django's dev server on 127.0.0.1
dns.setDefaultResultOrder("ipv4first");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || "http://localhost:9000";
  const labsRemoteUrl = env.VITE_LABS_REMOTE_URL || "http://localhost:5175";

  const enableFederation = mode !== "test";

  function federationStubs(): Plugin {
    const STUB = `export default () => null;`;
    return {
      name: "federation-stubs",
      enforce: "pre",
      resolveId(id) {
        if (id.startsWith("labs_remote/")) return `\0${id}`;
      },
      load(id) {
        if (id.startsWith("\0labs_remote/")) return STUB;
      },
    };
  }

  // @module-federation/vite emits an entry bootstrap that awaits
  // loadRemote() for every federated module BEFORE importing the app entry.
  // Each remote may be a scale-to-zero service, so first paint would wait on
  // the slowest remote cold start. Rewrite the blocking await into a
  // fire-and-forget warm-up: the app paints as soon as host assets arrive,
  // remotes warm up in the background, and lazy() routes still load them on
  // demand.
  function nonBlockingRemotePreloads(): Plugin {
    const BLOCKING = "await Promise.all(__mfRemotePreloads);";
    const WARMUP = "void Promise.allSettled(__mfRemotePreloads);";
    let outDir = "";
    return {
      name: "non-blocking-remote-preloads",
      enforce: "post",
      configResolved(config) {
        outDir = path.resolve(config.root, config.build.outDir);
      },
      // Dev: the bootstrap is served as the mf-html-entry-proxy virtual module.
      transform(code, id) {
        if (id.includes("mf-html-entry-proxy") && code.includes(BLOCKING)) {
          return code.replace(BLOCKING, WARMUP);
        }
      },
      // Build: the bootstrap is emitted as a separate file (mf-entry-bootstrap-*.js),
      // possibly after other plugins' bundle hooks, so patch it on disk.
      async closeBundle() {
        const fs = await import("node:fs");
        if (!outDir || !fs.existsSync(outDir)) return;
        const stack = [outDir];
        let found = false;
        let rewritten = false;
        while (stack.length) {
          const dir = stack.pop()!;
          for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const file = path.join(dir, entry.name);
            if (entry.isDirectory()) {
              stack.push(file);
              continue;
            }
            if (!entry.name.endsWith(".js")) continue;
            const code = fs.readFileSync(file, "utf-8");
            if (!code.includes("__mfRemotePreloads")) continue;
            found = true;
            if (!code.includes(BLOCKING)) continue;
            fs.writeFileSync(file, code.replaceAll(BLOCKING, WARMUP));
            rewritten = true;
          }
        }
        if (found && !rewritten) {
          throw new Error(
            "non-blocking-remote-preloads: found __mfRemotePreloads but not the blocking " +
              "await pattern — @module-federation/vite codegen changed; update this plugin " +
              "or first paint will block on remote cold starts again.",
          );
        }
      },
    };
  }

  return {
    plugins: [
      react(),
      tailwindcss(),
      ...(enableFederation ? [nonBlockingRemotePreloads()] : []),
      ...(enableFederation
        ? [
            federation({
              name: "phr_host",
              // "loaded-first" resolves shared modules from already-loaded
              // providers — the host's own singletons — so first paint never
              // blocks on a remote's shared-dependency version negotiation.
              shareStrategy: "loaded-first",
              remotes: {
                labs_remote: {
                  type: "module",
                  name: "labs_remote",
                  entry: `${labsRemoteUrl}/remoteEntry.js`,
                },
              },
              dts: false,
              runtimePlugins: ["./src/mf-runtime-plugin.ts"],
              shared: {
                react: { singleton: true, strictVersion: false },
                "react-dom": { singleton: true, strictVersion: false },
                "react/jsx-runtime": { singleton: true, strictVersion: false },
                "react/jsx-dev-runtime": { singleton: true, strictVersion: false },
                "@tanstack/react-query": { singleton: true, strictVersion: false },
                axios: { singleton: true, strictVersion: false },
                recharts: { singleton: true, strictVersion: false },
                "@radix-ui/react-dialog": { singleton: true },
                "@radix-ui/react-select": { singleton: true },
                "@radix-ui/react-progress": { singleton: true },
                "@radix-ui/react-checkbox": { singleton: true },
                "@radix-ui/react-label": { singleton: true },
              },
            }),
          ]
        : [federationStubs()]),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: "localhost",
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
