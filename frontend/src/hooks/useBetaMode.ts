import { useCallback, useRef } from 'react';
import { useBetaModeContext } from '../contexts/BetaModeContext';

const BETA_CLICK_THRESHOLD = 10;
const BETA_CLICK_WINDOW_MS = 5000; // 5 seconds

/**
 * Hook to access beta mode state from context
 * Use this hook in components that need to check or modify beta mode
 */
export const useBetaMode = () => {
  return useBetaModeContext();
};

/**
 * Hook to track rapid clicks for beta mode activation/deactivation
 * Returns a function to call on each click
 * Toggles beta mode: activates if off, deactivates if on
 */
export const useBetaModeActivator = (
  isBetaMode: boolean,
  onActivate: () => void,
  onDeactivate: () => void
) => {
  const clickTimesRef = useRef<number[]>([]);

  const handleClick = useCallback(() => {
    const now = Date.now();
    const windowStart = now - BETA_CLICK_WINDOW_MS;

    // Remove clicks outside the time window
    clickTimesRef.current = clickTimesRef.current.filter(
      (time) => time > windowStart
    );

    // Add current click
    clickTimesRef.current.push(now);

    // Check if threshold reached
    if (clickTimesRef.current.length >= BETA_CLICK_THRESHOLD) {
      // Toggle: activate if off, deactivate if on
      if (isBetaMode) {
        onDeactivate();
      } else {
        onActivate();
      }
      // Clear the array after toggle
      clickTimesRef.current = [];
    }
  }, [isBetaMode, onActivate, onDeactivate]);

  return handleClick;
};

