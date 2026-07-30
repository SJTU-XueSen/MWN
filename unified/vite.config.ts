import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/activities': { target: 'http://127.0.0.1:3001', changeOrigin: true },
      '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/auth': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/mirror-static': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/nexus': {
        target: 'http://127.0.0.1:3002',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/nexus/, ''),
      },
    }
  }
})
