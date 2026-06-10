import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api and /healthz to the FastAPI backend during dev so the browser
// talks to one origin and API keys never leave the server.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/healthz": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
