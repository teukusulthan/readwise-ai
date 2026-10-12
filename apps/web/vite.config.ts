/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

interface ProxyConfigEntry {
  context: string
  target: string
  secure?: boolean
  changeOrigin?: boolean
  logLevel?: string
  pathRewrite?: Record<string, string>
}

// env/.env overrides proxy targets per context:
//   BACKEND_PROXY_TARGET   → `/api/v1/apps` (e.g. when port 8020 is taken by another project)
//   ICON_CDN_PROXY_TARGET  → `/cdn-assets` (icon font CDN; kept out of the repo, required for icons)
// Entries left without a target are skipped.
function loadProxyConfig(overrides: Record<string, string | undefined>): Record<string, import('vite').ProxyOptions> {
  const configPath = path.resolve(__dirname, 'proxy.config.json')
  const entries: ProxyConfigEntry[] = JSON.parse(fs.readFileSync(configPath, 'utf-8'))

  return entries.reduce<Record<string, import('vite').ProxyOptions>>((proxy, entry) => {
    const rewriteRules = Object.entries(entry.pathRewrite ?? {})
    const target = overrides[entry.context] || entry.target
    if (!target) {
      console.warn(`[vite] no proxy target for ${entry.context} — set it in env/.env`)
      return proxy
    }

    proxy[entry.context] = {
      target,
      changeOrigin: entry.changeOrigin ?? true,
      secure: entry.secure ?? true,
      rewrite: rewriteRules.length
        ? (path) =>
          rewriteRules.reduce((result, [pattern, replacement]) => result.replace(new RegExp(pattern), replacement), path)
        : undefined,
    }
    return proxy
  }, {})
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, 'env'), '')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: Number(env.PORT) || 3000,
      cors: true,
      proxy: loadProxyConfig({
        '/api/v1/apps': env.BACKEND_PROXY_TARGET,
        '/cdn-assets': env.ICON_CDN_PROXY_TARGET,
      }),
    },
    preview: {
      host: true,
      port: 4173,
      allowedHosts: true,
    },
    build: {
      outDir: 'build',
      sourcemap: false,
      chunkSizeWarningLimit: 244,
      rollupOptions: {
        output: {
          entryFileNames: '[name].[hash].js',
          chunkFileNames: '[name].[hash].js',
          assetFileNames: (info) =>
            info.name?.endsWith('.css') ? 'css/[name].[hash][extname]' : 'assets/[name].[hash][extname]',
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            // Only direct dependencies — chunking a transitive package breaks when it's not installed.
            'vendor-radix': ['@radix-ui/react-dialog', '@radix-ui/react-slot', '@radix-ui/react-tooltip'],
            'vendor-query': ['@tanstack/react-query'],
            'vendor-form': ['react-hook-form', 'zod', '@hookform/resolvers'],
            'vendor-state': ['zustand'],
          },
        },
      },
    },
    envDir: 'env',
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/setup-tests.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
      css: false,
    },
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode === 'production' || mode === 'staging' ? 'production' : 'development'),
    },
  }
})
