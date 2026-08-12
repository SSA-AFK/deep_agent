import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND = process.env.VITE_BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: BACKEND,
        changeOrigin: true,
      },
      "/ws": {
        target: BACKEND,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  test: { environment: "jsdom", setupFiles: "./src/test/setup.ts", exclude: ["e2e/**", "node_modules/**", "dist/**"] },
});
