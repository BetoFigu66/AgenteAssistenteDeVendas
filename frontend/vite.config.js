import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Dev local (run.sh): 3001 → backend 8001
  // QA (docker-compose + túnel): 3000 → backend 8000 via Nginx no container
  const env = loadEnv(mode, process.cwd(), '')
  const devPort = Number(env.VITE_DEV_PORT || 3001)
  const apiProxy = env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8001'

  return {
    plugins: [react()],
    server: {
      port: devPort,
      strictPort: true,
      allowedHosts: ['.trycloudflare.com'],
      proxy: {
        '/api': {
          target: apiProxy,
          changeOrigin: true,
        },
        '/webhook': {
          target: apiProxy,
          changeOrigin: true,
        },
        '/health': {
          target: apiProxy,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})
