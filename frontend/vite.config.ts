import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  appType: "spa",
  server: {
    port: 5173,
    // Разрешаем открывать dev-сервер по внешнему домену (serveo/ngrok и т.п.)
    allowedHosts: true,
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        main: "index.html",
        "admin-carwash": "admin-carwash.html",
        "system-admin": "system-admin.html",
      },
    },
  },
});
