/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  server: { port: 5173, proxy: { "/api": "http://localhost:8080", "/ws": { target: "ws://localhost:8080", ws: true } } },
  build: { outDir: "../static", emptyOutDir: true, sourcemap: false },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"] },
});
