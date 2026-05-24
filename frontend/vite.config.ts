import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Load VITE_* from repo root .env (same file as backend / docker-compose)
const repoRoot = path.resolve(__dirname, '..')

// https://vite.dev/config/
export default defineConfig({
  envDir: repoRoot,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
