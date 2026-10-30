import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: 'all',
    cors: true,
    proxy: {
      '/files': 'http://172.20.10.6:8000',
      '/upload': 'http://172.20.10.6:8000',
      '/schedules': 'http://172.20.10.6:8000',
      '/admin': 'http://172.20.10.6:8000',
      '/playlists': 'http://172.20.10.6:8000',
      '/trash': 'http://172.20.10.6:8000',
      '/storage-stats': 'http://172.20.10.6:8000',
      '/monitoring': 'http://172.20.10.6:8000',
      '/analytics': 'http://172.20.10.6:8000',
      '/history': 'http://172.20.10.6:8000',
      '/storage-history': 'http://172.20.10.6:8000',
      '/request-reset': 'http://172.20.10.6:8000',
      '/change-password': 'http://172.20.10.6:8000',
      '/screens': 'http://172.20.10.6:8000',
      '/public-broadcast': 'http://172.20.10.6:8000',
      '/log-login': 'http://172.20.10.6:8000',
      '/log-logout': 'http://172.20.10.6:8000',
      '/media-file': 'http://172.20.10.6:8000',
      '/server-ip': 'http://172.20.10.6:8000',
      '/settings': 'http://172.20.10.6:8000'
    }
  }
})