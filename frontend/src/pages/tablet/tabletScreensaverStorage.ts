/** Idle delay before auto screensaver on CNC / compressor tablet shells (`localStorage`). */

export const TABLET_SCREENSAVER_STORAGE_KEY = 'shatter.tablet.screensaver_idle_minutes';

export const TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT = 5;
export const TABLET_SCREENSAVER_IDLE_MINUTES_MIN = 1;
export const TABLET_SCREENSAVER_IDLE_MINUTES_MAX = 240;

/** Same-tab updates when `/tablet/setup` saves (storage event only fires across tabs). */
export const TABLET_SCREENSAVER_IDLE_CHANGED_EVENT = 'shatter-tablet-screensaver-idle-changed';

export const TABLET_SCREENSAVER_IDLE_MS_DEFAULT =
  TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT * 60_000;

function clampMinutes(n: number): number {
  if (!Number.isFinite(n)) return TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT;
  return Math.min(
    TABLET_SCREENSAVER_IDLE_MINUTES_MAX,
    Math.max(TABLET_SCREENSAVER_IDLE_MINUTES_MIN, Math.round(n))
  );
}

export function readStoredTabletScreensaverIdleMinutes(): number {
  try {
    const raw = localStorage.getItem(TABLET_SCREENSAVER_STORAGE_KEY);
    if (raw == null || !String(raw).trim()) {
      return TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT;
    }
    const n = Number.parseInt(String(raw).trim(), 10);
    if (!Number.isFinite(n)) {
      return TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT;
    }
    return clampMinutes(n);
  } catch {
    return TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT;
  }
}

export function readStoredTabletScreensaverIdleMs(): number {
  return readStoredTabletScreensaverIdleMinutes() * 60_000;
}

export function writeStoredTabletScreensaverIdleMinutes(minutes: number): void {
  const m = clampMinutes(minutes);
  try {
    localStorage.setItem(TABLET_SCREENSAVER_STORAGE_KEY, String(m));
  } catch {
    /* quota / private mode */
  }
  try {
    window.dispatchEvent(new CustomEvent(TABLET_SCREENSAVER_IDLE_CHANGED_EVENT, { detail: { minutes: m } }));
  } catch {
    /* ignore */
  }
}
