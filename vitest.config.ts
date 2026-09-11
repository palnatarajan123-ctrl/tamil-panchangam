import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// Minimal frontend test setup (added 2026-09-11, Task 1 fix) -- this repo
// had no frontend test runner at all before this. Reuses the same @/
// alias as vite.config.ts so tests import production code exactly the
// way the app does, not a parallel path.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "client", "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
    },
  },
  test: {
    environment: "jsdom",
    // NOTE: this repo's `npm test` script sets
    // NODE_OPTIONS=--no-experimental-webstorage -- required on Node 22+.
    // Node ships its own (unconfigured, non-functional without
    // --localstorage-file) global `localStorage` now, and vitest's jsdom
    // environment setup only overrides a global key that already exists
    // on Node's global object if that key is in its own internal
    // allowlist (predates this Node feature) -- so without the flag,
    // `localStorage` silently resolves to Node's broken stub instead of
    // jsdom's working one, in tests AND in the app code under test
    // (lib/auth.ts reads localStorage directly). Running `vitest` (or
    // `vitest run`) directly instead of via `npm test` will hit this.
    environmentOptions: {
      jsdom: { url: "http://localhost:3000/" },
    },
    include: ["client/src/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
