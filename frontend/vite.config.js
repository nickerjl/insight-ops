import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // Forward API calls to the FastAPI container during local dev.
      "/api": {
        target: process.env.API_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
      "/health": {
        target: process.env.API_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
      "/ready": {
        target: process.env.API_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
      "/demo": {
        target: process.env.API_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});
