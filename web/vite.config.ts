import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 单一后端代理：所有 /api 请求转发到 :5000（开发模式）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
