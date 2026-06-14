/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Production build is served under /picnic-frontend/ on Uberspace; the
  // dev server stays at the root so `npm run dev` works without a prefix.
  base: command === "build" ? "/picnic-frontend/" : "/",
  server: {
    proxy: {
      "/picnic/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
}));
