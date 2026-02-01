import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Prevent vite from clearing the screen and hiding Tauri logs
  clearScreen: false,
  // Tauri expects a fixed port, fail if unavailable
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      // Don't watch Tauri source files
      ignored: ["**/src-tauri/**"],
    },
  },
  // For Tauri, use relative paths in production
  build: {
    // Don't minify for debugging
    minify: process.env.TAURI_DEBUG ? false : "esbuild",
    // Produce source maps for debugging
    sourcemap: !!process.env.TAURI_DEBUG,
  },
});
