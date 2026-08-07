import { defineConfig, type Plugin } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { existsSync, readFileSync, statSync } from 'fs'
import { resolve, join, extname } from 'path'
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
  } catch (error) {
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
const isDemoMode = process.env.VITE_DEMO_MODE === 'true'

function getReleaseChannel(): string {
  const channel = process.env.VITE_RELEASE_CHANNEL
  return channel?.trim() ?? ''
}

const GITHUB_PAGES_ROOT = '/Shatter-NC'
const SITE_ROOT = resolve(__dirname, '../site')

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
}

/** Serve landing + install kit from ../site during `npm run dev:demo`. */
function githubPagesSitePlugin(): Plugin {
  return {
    name: 'github-pages-site',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = (req.url ?? '').split('?')[0]
        if (!pathname.startsWith(GITHUB_PAGES_ROOT)) {
          return next()
        }
        // Vite handles the demo SPA under /Shatter-NC/demo/
        if (pathname.startsWith(`${GITHUB_PAGES_ROOT}/demo`)) {
          return next()
        }

        let filePath: string | null = null
        if (pathname === GITHUB_PAGES_ROOT || pathname === `${GITHUB_PAGES_ROOT}/`) {
          filePath = join(SITE_ROOT, 'index.html')
        } else if (pathname.startsWith(`${GITHUB_PAGES_ROOT}/install`)) {
          const rest = pathname.slice(`${GITHUB_PAGES_ROOT}/install`.length)
          if (!rest || rest === '/') {
            filePath = join(SITE_ROOT, 'install', 'index.html')
          } else {
            filePath = join(SITE_ROOT, 'install', rest)
          }
        }

        if (!filePath || !existsSync(filePath)) {
          return next()
        }

        if (statSync(filePath).isDirectory()) {
          filePath = join(filePath, 'index.html')
          if (!existsSync(filePath)) {
            return next()
          }
        }

        const mime = MIME[extname(filePath)] ?? 'application/octet-stream'
        res.statusCode = 200
        res.setHeader('Content-Type', mime)
        res.end(readFileSync(filePath))
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  base: isDemoMode ? '/Shatter-NC/demo/' : '/',
  plugins: [react(), ...(isDemoMode ? [githubPagesSitePlugin()] : [])],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(version),
    'import.meta.env.VITE_RELEASE_CHANNEL': JSON.stringify(getReleaseChannel()),
    'import.meta.env.VITE_DEMO_MODE': JSON.stringify(isDemoMode ? 'true' : ''),
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
