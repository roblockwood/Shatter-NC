/**
 * API Configuration
 *
 * This file centralizes all API endpoint configuration.
 * The API URL is determined at build time from environment variables.
 *
 * For development: Uses VITE_API_URL or defaults to http://localhost:8000
 * For production: Must be set during build with VITE_API_URL
 */

// Get API URL from environment variable or use default
const getApiUrl = (): string => {
  // Check for Vite environment variable
  const envApiUrl = import.meta.env.VITE_API_URL;

  if (envApiUrl) {
    return envApiUrl;
  }

  // Development fallback
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }

  // Production fallback - use window.location to build URL dynamically
  // This allows the frontend to work when accessed from any device
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const apiPort = '8000'; // Backend always runs on 8000

  return `${protocol}//${hostname}:${apiPort}`;
};

export const API_BASE_URL = getApiUrl();
export const API_BASE = `${API_BASE_URL}/api`;

// WebSocket URL (convert http to ws, https to wss)
export const WS_URL = `${API_BASE_URL.replace(/^http/, 'ws')}/api/ws`;

// Helper function to build full API URLs
export const buildApiUrl = (path: string): string => {
  // Remove leading slash if present
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `${API_BASE_URL}/${cleanPath}`;
};

console.log('API Configuration:', {
  API_BASE_URL,
  API_BASE,
  WS_URL,
  hostname: window.location.hostname,
});
