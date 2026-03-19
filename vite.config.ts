import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
  ],

  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "client", "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
  },

  root: path.resolve(import.meta.dirname, "client"),

  build: {
    outDir: path.resolve(import.meta.dirname, "dist/public"),
    emptyOutDir: true,
  },

  server: {
    port: 5000,
    host: "0.0.0.0",
    strictPort: false,
    allowedHosts: true,

    proxy: {
      // Forward /api/* to FastAPI unchanged.
      // FastAPI routes are all mounted under /api (see main.py include_router calls).
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },

    fs: {
      strict: true,
      deny: ["**/.*"],
    },
  },
});
