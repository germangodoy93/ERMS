/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// In development the SPA calls the API through this proxy (same origin, no CORS).
// VITE_API_PROXY_TARGET points to the backend: localhost outside Docker,
// http://backend:8000 inside docker compose.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    build: {
      // Libraries change less often than our code: separate chunks keep them
      // cached in the browser across deploys.
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: "react",
                test: /node_modules[\\/](react|react-dom|scheduler|react-router)[\\/]/,
              },
              {
                name: "ui",
                test: /node_modules[\\/](radix-ui|@radix-ui|lucide-react|sonner)[\\/]/,
              },
              { name: "vendor", test: /node_modules[\\/]/ },
            ],
          },
        },
      },
    },
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": { target: apiTarget, changeOrigin: true },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: false,
    },
  };
});
