import type { PollingDataPoint } from '../api/summary';

/**
 * Generate an ASCII line graph representing polling history
 *
 * Uses characters to show communication success/failure:
 * - Online (success): '-' (horizontal line, top position)
 * - Offline (failure): '_' (horizontal line, bottom position)
 * - Transition down (online→offline): '\' (going offline)
 * - Transition up (offline→online): '/' (coming online)
 *
 * @param history - Polling history data points
 * @param width - Width of the graph in characters (default 20)
 * @returns ASCII graph string
 *
 * @example
 * // Returns "----------" for 100% uptime
 * generatePollingGraph(allSuccessful, 10)
 *
 * // Returns "-----\____/-----" for brief outage
 * generatePollingGraph(withOutage, 16)
 */
export function generatePollingGraph(
  history: PollingDataPoint[],
  width: number = 20
): string {
  if (history.length === 0) {
    return '-'.repeat(width);
  }

  // Sample the history to fit the width
  const sampled = sampleEvenly(history, width);

  // Build graph with transition detection
  let graph = '';
  for (let i = 0; i < sampled.length; i++) {
    const current = sampled[i].success;
    const prev = i > 0 ? sampled[i - 1].success : current;

    if (current && prev) {
      // Online → Online
      graph += '-';
    } else if (!current && !prev) {
      // Offline → Offline
      graph += '_';
    } else if (!current && prev) {
      // Online → Offline (transition down)
      graph += '\\';
    } else {
      // Offline → Online (transition up)
      graph += '/';
    }
  }

  return graph;
}

/**
 * Sample polling history evenly to fit a target width
 *
 * @param history - Full polling history
 * @param targetWidth - Desired number of samples
 * @returns Evenly sampled polling data points
 */
function sampleEvenly(
  history: PollingDataPoint[],
  targetWidth: number
): PollingDataPoint[] {
  if (history.length <= targetWidth) {
    return history;
  }

  const sampled: PollingDataPoint[] = [];
  const step = history.length / targetWidth;

  for (let i = 0; i < targetWidth; i++) {
    const index = Math.floor(i * step);
    sampled.push(history[Math.min(index, history.length - 1)]);
  }

  // Ensure we include the last data point
  const lastIndex = history.length - 1;
  if (sampled[sampled.length - 1] !== history[lastIndex]) {
    sampled[sampled.length - 1] = history[lastIndex];
  }

  return sampled;
}

/**
 * Get a CSS class name based on uptime percentage for styling
 *
 * @param uptimePercent - Uptime percentage (0-100)
 * @returns CSS class name
 */
export function getUptimeClass(uptimePercent: number): string {
  if (uptimePercent >= 99) {
    return 'uptime-excellent';
  } else if (uptimePercent >= 95) {
    return 'uptime-good';
  } else if (uptimePercent >= 90) {
    return 'uptime-fair';
  } else if (uptimePercent >= 75) {
    return 'uptime-poor';
  } else {
    return 'uptime-critical';
  }
}

/**
 * Format uptime percentage for display
 *
 * @param uptimePercent - Uptime percentage (0-100)
 * @returns Formatted string (e.g., "98.5%")
 */
export function formatUptimePercent(uptimePercent: number): string {
  return `${uptimePercent.toFixed(1)}%`;
}
