import { useCallback, useEffect, useState } from 'react';
import type { ChartTimeAxisMode } from '../utils/chartTimeAxis';

const LS_PREFIX = 'shatter.chartTimeAxis.';

function readStored(storageKey: string): ChartTimeAxisMode {
  try {
    const v = localStorage.getItem(LS_PREFIX + storageKey);
    return v === 'absolute' ? 'absolute' : 'relative';
  } catch {
    return 'relative';
  }
}

/**
 * Per-chart axis mode (relative vs clock), persisted under a unique storage key.
 */
export function useLocalChartTimeAxisMode(storageKey: string) {
  const [timeAxisMode, setTimeAxisModeState] = useState<ChartTimeAxisMode>(() =>
    readStored(storageKey)
  );

  useEffect(() => {
    setTimeAxisModeState(readStored(storageKey));
  }, [storageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(LS_PREFIX + storageKey, timeAxisMode);
    } catch {
      /* ignore */
    }
  }, [storageKey, timeAxisMode]);

  const setTimeAxisMode = useCallback((m: ChartTimeAxisMode) => {
    setTimeAxisModeState(m);
  }, []);

  const toggleTimeAxisMode = useCallback(() => {
    setTimeAxisModeState((p) => (p === 'relative' ? 'absolute' : 'relative'));
  }, []);

  return { timeAxisMode, setTimeAxisMode, toggleTimeAxisMode };
}
