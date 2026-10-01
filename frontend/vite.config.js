import { readFileSync } from 'node:fs'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Versão do frontend (AAAA.MM.DD-HHMM da última mudança, ver scripts/versao.py na raiz),
// embutida no bundle no build. Fica em frontend/ para entrar no contexto do Docker.
function lerVersaoFront() {
  try {
    return readFileSync(new URL('./VERSAO', import.meta.url), 'utf-8').trim() || 'desconhecida'
  } catch {
    return 'desconhecida'
  }
}

export default defineConfig(({ mode }) => {
  // Padrão: backend Docker em 8000 (docker-compose up).
  // Dev nativo (backend/run.sh na 8001): crie frontend/.env com VITE_DEV_API_PROXY=http://127.0.0.1:8001
  const env = loadEnv(mode, process.cwd(), '')
  const devPort = Number(env.VITE_DEV_PORT || 3001)
  const apiProxy = env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8000'

  const proxyOpts = {
    target: apiProxy,
    changeOrigin: true,
    configure: (proxy) => {
      proxy.on('error', (err) => {
        console.error(
          `[vite] proxy ${apiProxy} indisponível (${err.code || err.message}). ` +
            'Backend Docker: use VITE_DEV_API_PROXY=http://127.0.0.1:8000. ' +
            'Dev nativo (run.sh): use http://127.0.0.1:8001.',
        )
      })
    },
  }

  return {
    plugins: [react()],
    define: {
      __VERSAO_FRONT__: JSON.stringify(lerVersaoFront()),
    },
    server: {
      port: devPort,
      strictPort: true,
      allowedHosts: ['.trycloudflare.com'],
      proxy: {
        '/api': proxyOpts,
        '/webhook': proxyOpts,
        '/health': proxyOpts,
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})
