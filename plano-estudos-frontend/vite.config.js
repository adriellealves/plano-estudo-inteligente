import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Redireciona requisições de /api para o seu backend Flask
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    }
  }
})