import { API_BASE_URL } from '../config/api';

export type CompressorChartTimeRange = '1h' | '8h' | '24h' | '7d';

/** Profile for compressor `/status-samples`: tablet kiosk uses smaller payloads + slower refetch. */
export type CompressorChartSamplesProfile = 'default' | 'tablet';

/** Slower than 1 Hz avoids stacking slow /status-samples calls (browser connection limit → Failed to fetch). */
export const COMPRESSOR_CHART_REFETCH_MS = 2_500;

/** Tablet kiosk: fewer rows per request + longer poll interval (first reduced-data preset). */
export const COMPRESSOR_CHART_TABLET_REFETCH_MS = 10_000;

export function compressorChartRefetchMs(profile: CompressorChartSamplesProfile = 'default'): number {
  return profile === 'tablet' ? COMPRESSOR_CHART_TABLET_REFETCH_MS : COMPRESSOR_CHART_REFETCH_MS;
}

/** Smaller payloads for short windows; charts decimate anyway. Reduces JSON parse + transfer time. */
export function compressorStatusSamplesLimit(
  range: CompressorChartTimeRange,
  profile: CompressorChartSamplesProfile = 'default'
): number {
  if (profile === 'tablet') {
    switch (range) {
      case '1h':
        return 2_800;
      case '8h':
        return 2_000;
      case '24h':
        return 2_800;
      case '7d':
        return 4_000;
    }
  }
  switch (range) {
    case '1h':
      return 4_500;
    case '8h':
      return 9_000;
    case '24h':
      return 14_000;
    case '7d':
      return 20_000;
  }
}

export function compressorChartRangeBounds(timeRange: CompressorChartTimeRange): { start: Date; end: Date } {
  const end = new Date();
  const start = new Date(end);
  switch (timeRange) {
    case '1h':
      start.setHours(start.getHours() - 1);
      break;
    case '8h':
      start.setHours(start.getHours() - 8);
      break;
    case '24h':
      start.setHours(start.getHours() - 24);
      break;
    case '7d':
      start.setDate(start.getDate() - 7);
      break;
  }
  return { start, end };
}

export function buildCompressorStatusSamplesUrl(
  compressorId: number,
  timeRange: CompressorChartTimeRange,
  profile: CompressorChartSamplesProfile = 'default'
): string {
  const { start, end } = compressorChartRangeBounds(timeRange);
  const limit = compressorStatusSamplesLimit(timeRange, profile);
  return `${API_BASE_URL}/api/compressors/${compressorId}/status-samples?start_time=${encodeURIComponent(
    start.toISOString()
  )}&end_time=${encodeURIComponent(end.toISOString())}&limit=${limit}`;
}

export function isCompressorChartAbortError(e: unknown): boolean {
  if (e instanceof DOMException && e.name === 'AbortError') return true;
  const name = (e as { name?: string })?.name;
  return name === 'AbortError';
}

/** Initial load retries (transient pool / network blips when multiple chart panes mount together). */
const INITIAL_FETCH_RETRIES = 3;
const INITIAL_BACKOFF_MS = 350;

export async function fetchCompressorStatusSamples(
  url: string,
  signal: AbortSignal,
  options: { isInitial: boolean }
): Promise<unknown[]> {
  const attempts = options.isInitial ? INITIAL_FETCH_RETRIES : 1;
  let lastErr: unknown;
  for (let attempt = 0; attempt < attempts; attempt++) {
    if (signal.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }
    try {
      const r = await fetch(url, { signal, cache: 'no-store' });
      if (!r.ok) throw new Error(r.statusText || `HTTP ${r.status}`);
      const samp = await r.json();
      return Array.isArray(samp) ? samp : [];
    } catch (e) {
      lastErr = e;
      if (signal.aborted || isCompressorChartAbortError(e)) throw e;
      if (attempt < attempts - 1) {
        await new Promise<void>((resolve, reject) => {
          const delay = INITIAL_BACKOFF_MS * 2 ** attempt;
          const onAbort = () => {
            window.clearTimeout(t);
            reject(new DOMException('Aborted', 'AbortError'));
          };
          const t = window.setTimeout(() => {
            signal.removeEventListener('abort', onAbort);
            resolve();
          }, delay);
          signal.addEventListener('abort', onAbort, { once: true });
        });
      }
    }
  }
  throw lastErr;
}
