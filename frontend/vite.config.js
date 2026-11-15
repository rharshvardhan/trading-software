import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// `pnpm build` writes dist/, which FastAPI serves at http://127.0.0.1:8000/.
// `pnpm dev` starts the FastAPI server on :8000 and this dev server on :5173, which forwards API calls to it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
