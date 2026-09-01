import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Dev server proxies /api to a backend chosen by VITE_DEV_API_PROXY.
 *
 * Defaults to the local backend. Point it at the deployed API to run the
 * frontend against AWS data without a local database:
 *   VITE_DEV_API_PROXY=https://roadbuddy-vic.duckdns.org npm run dev
 *
 * Proxying keeps requests same-origin from the browser's point of view, so it
 * works regardless of the backend's CORS allowlist.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_DEV_API_PROXY || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: true,
        },
      },
    },
  }
})
