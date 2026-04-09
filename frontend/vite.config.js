import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // Use 127.0.0.1, not localhost. Node 18+ resolves "localhost" to ::1
            // (IPv6), but Django's dev server only binds to 0.0.0.0 (IPv4) by default,
            // so the proxy gets ECONNREFUSED even though curl localhost:8000 works.
            "/api": {
                target: "http://127.0.0.1:8000",
                changeOrigin: true,
            },
        },
    },
});
