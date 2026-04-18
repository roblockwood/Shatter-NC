/** Persists chosen compressor id per browser for compressor kiosk (`/tablet/compressor/...`). */
export const TABLET_COMPRESSOR_STORAGE_KEY = 'shatter.tablet.compressor_id';

export function readStoredTabletCompressorId(): number | null {
  try {
    const raw = localStorage.getItem(TABLET_COMPRESSOR_STORAGE_KEY);
    if (raw == null || !String(raw).trim()) {
      return null;
    }
    const n = Number.parseInt(String(raw).trim(), 10);
    if (!Number.isFinite(n) || n <= 0) {
      return null;
    }
    return n;
  } catch {
    return null;
  }
}

export function writeStoredTabletCompressorId(compressorId: number): void {
  try {
    localStorage.setItem(TABLET_COMPRESSOR_STORAGE_KEY, String(compressorId));
  } catch {
    /* quota / private mode */
  }
}

export function clearStoredTabletCompressorId(): void {
  try {
    localStorage.removeItem(TABLET_COMPRESSOR_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
