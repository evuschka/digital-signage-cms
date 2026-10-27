import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,
    proxy: {
      '/files': 'http://198.18.0.1:8000',
      '/upload': 'http://198.18.0.1:8000',
      '/schedules': 'http://198.18.0.1:8000',
      '/admin': 'http://198.18.0.1:8000',
      '/playlists': 'http://198.18.0.1:8000',
      '/trash': 'http://198.18.0.1:8000',
      '/storage-stats': 'http://198.18.0.1:8000',
      '/monitoring': 'http://198.18.0.1:8000',
      '/analytics': 'http://198.18.0.1:8000',
      '/history': 'http://198.18.0.1:8000',
      '/storage-history': 'http://198.18.0.1:8000',
      '/request-reset': 'http://198.18.0.1:8000',
      '/change-password': 'http://198.18.0.1:8000',
      '/screens': 'http://198.18.0.1:8000',
      '/public-broadcast': 'http://198.18.0.1:8000',
      '/log-login': 'http://198.18.0.1:8000',
      '/log-logout': 'http://198.18.0.1:8000',
      '/media-file': 'http://198.18.0.1:8000',
      '/server-ip': 'http://198.18.0.1:8000',
      // РАЗРЕШАЕМ МАРШРУТ НАСТРОЕК (ДЛЯ ФОНОВОЙ ЗАГЛУШКИ)
      '/settings': 'http://198.18.0.1:8000'
    }
  }
});