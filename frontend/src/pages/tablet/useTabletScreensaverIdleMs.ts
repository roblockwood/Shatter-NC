import { useEffect, useState } from 'react';
import {
  readStoredTabletScreensaverIdleMs,
  TABLET_SCREENSAVER_IDLE_CHANGED_EVENT,
  TABLET_SCREENSAVER_STORAGE_KEY,
} from './tabletScreensaverStorage';

/**
 * Reactive idle duration for `TabletScreensaver` — updates when the value changes on
 * `/tablet/setup` or in another tab.
 */
export function useTabletScreensaverIdleMs(): number {
  const [ms, setMs] = useState(() => readStoredTabletScreensaverIdleMs());

  useEffect(() => {
    const sync = () => setMs(readStoredTabletScreensaverIdleMs());

    const onStorage = (e: StorageEvent) => {
      if (e.key === TABLET_SCREENSAVER_STORAGE_KEY || e.key === null) {
        sync();
      }
    };

    window.addEventListener('storage', onStorage);
    window.addEventListener(TABLET_SCREENSAVER_IDLE_CHANGED_EVENT, sync);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener(TABLET_SCREENSAVER_IDLE_CHANGED_EVENT, sync);
    };
  }, []);

  return ms;
}
