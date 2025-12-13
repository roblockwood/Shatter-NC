import type { PollingDataPoint } from '../api/summary';

/**
 * Generate a live ASCII polling status line (one character per poll)
 *
 * Shows real-time polling activity with no sampling - each character represents
 * a single poll result. Most recent polls are rightmost, oldest leftmost.
 *
 * Uses characters:
 * - '█' (full block) for successful poll
 * - '░' (light shade) for failed poll
 *
 * @param history - Polling history data points (each = 1 poll)
 * @returns ASCII status string showing recent poll activity
 *
 * @example
 * // Returns "█████░████████" for recent outage
 * generatePollingGraph(polls14)
 *
 * // Returns "██████████████████████████████" for all successful
 * generatePollingGraph(polls30)
 */
export function generatePollingGraph(
  history: PollingDataPoint[]
): string {
  if (history.length === 0) {
    return '██████';
  }

  // Show each poll as one character - no sampling, no transitions
  // Just map success → '█' and failure → '░'
  return history.map(poll => (poll.success ? '█' : '░')).join('');
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
