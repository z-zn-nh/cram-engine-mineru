import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendTarget = process.env.CRAM_BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true,
    proxy: {
      "/health": backendTarget,
      "/subjects": backendTarget,
    },
  },
});
