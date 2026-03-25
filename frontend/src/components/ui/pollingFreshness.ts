export type PollingFreshness = 'fresh' | 'waning' | 'stale' | 'unknown';

/**
 * For panes backed by HTTP + machine state: HTTP 200 can succeed while the CNC is offline
 * (DB/history still serves). Use the *older* of the two instants so the dot only looks fresh
 * when both a recent API read and a recent successful fast poll exist.
 *
 * When `machineLastSuccessfulPollAt` is omitted (`undefined`), only the API time is used (legacy).
 * When it is `null` (never had a successful fast poll), returns `null` (unknown / not fresh).
 */
export function earlierIsoTimestamp(
  apiFetchAt: string | null | undefined,
  machineLastSuccessfulPollAt: string | null | undefined,
): string | null | undefined {
  const ta =
    apiFetchAt == null || apiFetchAt === '' ? NaN : new Date(apiFetchAt).getTime();

  if (machineLastSuccessfulPollAt === undefined) {
    if (!Number.isFinite(ta)) return null;
    return apiFetchAt!;
  }

  if (machineLastSuccessfulPollAt === null || machineLastSuccessfulPollAt === '') {
    return null;
  }

  const tb = new Date(machineLastSuccessfulPollAt).getTime();
  if (!Number.isFinite(tb)) return null;

  if (!Number.isFinite(ta)) return machineLastSuccessfulPollAt;

  return ta <= tb ? apiFetchAt! : machineLastSuccessfulPollAt;
}

/** Bucket from age vs expected poll interval (stable colors, no per-second UI churn). */
export function freshnessFromAgeMs(ageMs: number, expectedIntervalMs: number): PollingFreshness {
  if (ageMs < 0) return 'fresh';
  const freshMax = Math.max(expectedIntervalMs * 2, 5000);
  const waningMax = Math.max(expectedIntervalMs * 6, 60_000);
  if (ageMs <= freshMax) return 'fresh';
  if (ageMs <= waningMax) return 'waning';
  return 'stale';
}
