/** Relative timestamps for demo fixtures (stable at page load, moves with real time). */
const boot = Date.now();

export function msAgo(ms: number): string {
  return new Date(boot - ms).toISOString();
}

export function minutesAgo(m: number): string {
  return msAgo(m * 60 * 1000);
}

export function hoursAgo(h: number): string {
  return msAgo(h * 3600 * 1000);
}

export function daysAgo(d: number): string {
  return msAgo(d * 24 * 3600 * 1000);
}

export function durationSeconds(startIso: string, endIso: string | null): number {
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : boot;
  return Math.max(0, Math.round((end - start) / 1000));
}

export const DEMO_NOW = () => new Date(boot).toISOString();

/** Demo session boot time (ms) — used for panel animation phasing. */
export const DEMO_BOOT_MS = boot;
