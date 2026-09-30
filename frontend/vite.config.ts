import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    proxy: {
      "/api": loadEnv(mode, ".", "KEYCAP_").KEYCAP_API_TARGET || "http://localhost:8000",
    },
  },
  test: {
    include: ["tests/**/*.{test,spec}.{ts,tsx}"],
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    globals: true,
  },
}));
