import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,
    proxy: {
      '/files': 'http://127.0.0.1:8000',
      '/upload': 'http://127.0.0.1:8000',
      '/schedules': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
      '/playlists': 'http://127.0.0.1:8000',
      '/trash': 'http://127.0.0.1:8000',
      '/storage-stats': 'http://127.0.0.1:8000',
      '/monitoring': 'http://127.0.0.1:8000',
      '/analytics': 'http://127.0.0.1:8000',
      '/history': 'http://127.0.0.1:8000',
      '/storage-history': 'http://127.0.0.1:8000',
      '/request-reset': 'http://127.0.0.1:8000',
      '/change-password': 'http://127.0.0.1:8000',
      '/screens': 'http://127.0.0.1:8000'
    }
  }
});