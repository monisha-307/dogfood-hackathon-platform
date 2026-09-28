import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, Vite proxies /api to the FastAPI server on :8000.
// In Docker, FastAPI serves the built files itself, so there is no proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: { outDir: 'dist', sourcemap: false },
})
