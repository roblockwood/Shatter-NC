import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// Read VERSION file from repo root
let version = '0.1.0'
try {
  version = readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()
} catch (error) {
  console.warn('Could not read VERSION file, using default:', error)
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(version),
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
})
