import { defineConfig } from 'vitest/config'
import type { Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { execSync } from 'child_process'

// Get version for UI display.
// Source of truth:
// 1) VITE_APP_VERSION env var (preferred; set by Docker/workflows)
// 2) git describe (local dev convenience)
// 3) repo VERSION file (fallback when available)
// 4) hardcoded default
function getVersion(): string {
  const envVersion = process.env.VITE_APP_VERSION
  if (envVersion && envVersion.trim()) {
    return envVersion.trim()
  }

  try {
    // Try to get version from git describe (e.g., "v1.2.3" or "v1.2.3-5-gabc1234")
    const gitVersion = execSync('git describe --tags --always --dirty', { 
      encoding: 'utf-8',
      cwd: resolve(__dirname, '..'),
      stdio: ['ignore', 'pipe', 'ignore']
    }).trim()
    
    // Clean up: remove 'v' prefix and handle dirty state
    const cleanVersion = gitVersion.replace(/^v/, '').replace(/-dirty$/, '')
    
    // If it's a clean tag (no commits after), return as-is
    // If it has commits after tag, format as "1.2.3-dev.5" or similar
    if (gitVersion.includes('-')) {
      const parts = cleanVersion.split('-')
      if (parts.length >= 3) {
        // Format: "1.2.3-5-gabc1234" -> "1.2.3-dev.5"
        const [tag, commits] = parts
        return `${tag}-dev.${commits}`
      }
      return cleanVersion
    }
    
    return cleanVersion
  } catch (_error) {
    // Fallback to VERSION file (updated by semantic-release)
    try {
      return readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()
    } catch {
      // Dev containers mount only ./frontend, so ../VERSION may not exist.
      // Fall back to frontend/package.json version as a reasonable default.
      try {
        const pkg = JSON.parse(readFileSync(resolve(__dirname, './package.json'), 'utf-8'))
        if (pkg?.version) return String(pkg.version)
      } catch {
        // ignore
      }
      return '0.1.0'
    }
  }
}

const version = getVersion()

/** PWA launch URL; machine id is chosen per device at runtime (localStorage / setup), not at build time. */
function resolvePwaStartUrl(): string {
  const explicit = process.env.VITE_PWA_START_URL?.trim()
  if (explicit) {
    return explicit
  }
  return './tablet'
}

function buildPwaManifest(): Record<string, unknown> {
  return {
    name: 'Shatter',
    short_name: 'Shatter',
    description: 'CNC machine monitoring',
    start_url: resolvePwaStartUrl(),
    scope: './',
    display: 'standalone',
    display_override: ['standalone', 'minimal-ui'],
    theme_color: '#0a0a0a',
    background_color: '#0a0a0a',
    icons: [
      {
        src: './icon-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: './icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: './icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
      {
        src: './favicon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
        purpose: 'any',
      },
    ],
  }
}

function pwaManifestPlugin(): Plugin {
  return {
    name: 'shatter-pwa-manifest',
    enforce: 'pre',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split('?')[0] ?? ''
        if (url === '/manifest.webmanifest' || url === '/manifest.json') {
          try {
            const manifest = buildPwaManifest()
            res.setHeader('Content-Type', 'application/manifest+json')
            res.end(JSON.stringify(manifest, null, 2))
          } catch (e) {
            next(e as Error)
          }
          return
        }
        next()
      })
    },
    generateBundle(_options, _bundle, isWrite) {
      if (!isWrite) return
      const manifest = buildPwaManifest()
      this.emitFile({
        type: 'asset',
        fileName: 'manifest.webmanifest',
        source: JSON.stringify(manifest, null, 2),
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [pwaManifestPlugin(), react()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(version),
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/main.tsx', 'src/**/*.d.ts'],
    },
  },
})
