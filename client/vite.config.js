import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        secure: false,
        changeOrigin: true,
        // rewrite: (path) => path.replace(/^\/api/, ""),
        configure: (proxy, options) => {
          proxy.on("proxyReq", (proxyReq, req, res) => {
            console.log(`[PROXY] → ${req.method} ${req.url}`);
          });
          proxy.on("proxyRes", (proxyRes, req, res) => {
            console.log(`[PROXY RES] ← ${proxyRes.statusCode} ${req.url}`);
          });
          proxy.on("error", (err, req, res) => {
            console.error(`[PROXY ERROR] ${req.url}`, err.message);
          });
        },
      },
    },
  },
});
