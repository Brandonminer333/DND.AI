import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    root: repoRoot,
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.join(repoRoot, 'tests', 'frontend', 'vitest.setup.js')],
    include: ['tests/frontend/**/*.{test,spec}.{js,jsx}'],
  },
})
