import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // Path aliases for cleaner imports
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/pages': path.resolve(__dirname, './src/pages'),
      '@/contexts': path.resolve(__dirname, './src/contexts'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/utils': path.resolve(__dirname, './src/utils'),
      '@/services': path.resolve(__dirname, './src/services'),
      '@/types': path.resolve(__dirname, './src/types'),
    },
  },

  // Development server configuration
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      }
    }
  },

  // Build optimizations
  build: {
    // Generate source maps for production debugging
    sourcemap: false,

    // Target modern browsers for smaller bundle size
    target: 'es2020',

    // Minification options
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,  // Remove console.log in production
        drop_debugger: true, // Remove debugger statements
      },
    },

    // Chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks - rarely change, cached longer
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['recharts'],
          'map-vendor': ['leaflet', 'react-leaflet'],
          'ui-vendor': ['lucide-react', 'framer-motion', 'clsx', 'tailwind-merge'],
        },
        // Asset naming for cache busting
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },

    // Chunk size warning limit
    chunkSizeWarningLimit: 500,
  },

  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'axios',
      'lucide-react',
      'recharts',
      'framer-motion',
    ],
  },

  // CSS optimization
  css: {
    devSourcemap: true,
  },

  // Performance hints
  esbuild: {
    // Remove pure function calls in production (e.g., console.log)
    pure: ['console.log', 'console.debug'],
  },
});
