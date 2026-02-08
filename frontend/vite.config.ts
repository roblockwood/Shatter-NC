import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { execSync } from 'child_process'

// Get version from git tags, fallback to VERSION file or default
function getVersion(): string {
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
      return '0.1.0'
    }
  }
}

const version = getVersion()

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
