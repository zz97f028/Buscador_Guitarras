import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

const apiPort = Number(process.env.ACORDE_API_PORT ?? '8000')
if (!Number.isInteger(apiPort) || apiPort < 1 || apiPort > 65535) {
  throw new Error('ACORDE_API_PORT must be an integer between 1 and 65535.')
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${apiPort}`,
        changeOrigin: true,
      },
    },
  },
})
