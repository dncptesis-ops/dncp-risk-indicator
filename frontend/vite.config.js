import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
//visualizer para analizar bundle, mirar que optimizar !
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      filename: 'dist/stats.html',
      // Abre el reporte al terminar el build; en CI (CI=1) no hay navegador.
      open: !process.env.CI,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(import.meta.dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    env: {
      VITE_API_BASE_URL: 'http://api.test',
    },
  },
});
