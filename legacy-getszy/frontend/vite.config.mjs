import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// CRA allowed JSX in .js files; teach esbuild to parse src/**/*.js as JSX.
// (src/index.js and other legacy entry files rely on this.)
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  esbuild: {
    loader: 'jsx',
    include: /\.(m?jsx?|jsx?)$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'jsx',
        '.jsx': 'jsx',
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('framer-motion')) return 'vendor-framer-motion';
          if (id.includes('@tanstack/react-query')) return 'vendor-react-query';
          if (id.includes('axios')) return 'vendor-axios';
          if (id.includes('lucide-react')) return 'vendor-lucide-react';
          if (id.includes('recharts')) return 'vendor-recharts';
          return undefined;
        },
      },
    },
  },
});
