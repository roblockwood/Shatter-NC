export type TimeRange = '1h' | '8h' | '24h' | '7d';

export type MachineStatus = 'operating' | 'standby' | 'stopped' | 'error' | 'off';

/** Main chart area: oscilloscope trace or duration pie */
export type TimelineDisplayMode = 'oscilloscope' | 'pie';

export const STATUS_LEVELS: Record<MachineStatus, number> = {
  operating: 4,
  standby: 3,
  stopped: 2,
  error: 1,
  off: 0,
};

export const STATUS_COLORS: Record<MachineStatus, string> = {
  operating: '#00ff00',
  standby: '#ffff00',
  stopped: '#ff8800',
  error: '#ff0000',
  off: '#808080',
};

/** Display order: top to bottom on oscilloscope / legend */
export const STATUS_ORDER: MachineStatus[] = [
  'operating',
  'standby',
  'stopped',
  'error',
  'off',
];

export const STATUS_LABELS: Record<MachineStatus, string> = {
  operating: 'OPERATING',
  standby: 'STANDBY',
  stopped: 'STOPPED',
  error: 'ERROR',
  off: 'OFF',
};

export interface StatusHistoryEvent {
  time: string;
  status: string;
  previous_status?: string;
}

export interface TimeRangeBounds {
  startTime: Date;
  endTime: Date;
  totalMs: number;
}

export interface StatusDurationSlice {
  status: MachineStatus;
  ms: number;
  percent: number;
}

const DISPLAY_MODE_KEY = 'statusTimelineViewMode';

export function loadTimelineDisplayMode(): TimelineDisplayMode {
  const saved = localStorage.getItem(DISPLAY_MODE_KEY);
  return saved === 'pie' ? 'pie' : 'oscilloscope';
}

export function saveTimelineDisplayMode(mode: TimelineDisplayMode): void {
  localStorage.setItem(DISPLAY_MODE_KEY, mode);
}

export function toggleTimelineDisplayMode(
  current: TimelineDisplayMode
): TimelineDisplayMode {
  return current === 'pie' ? 'oscilloscope' : 'pie';
}

export function normalizeStatus(
  status: string | undefined,
  online?: boolean
): MachineStatus {
  if (online === false) {
    return 'off';
  }
  if (!status) return 'standby';
  const lower = status.toLowerCase().trim();

  if (lower === 'operating') return 'operating';
  if (lower === 'standby') return 'standby';
  if (lower === 'stopped') return 'stopped';
  if (lower === 'error') return 'error';
  if (lower === 'off') return 'off';

  if (lower.includes('error') || lower === 'occurred' || lower.includes('occurred')) {
    return 'error';
  }
  if (lower.includes('alarm')) return 'error';
  if (lower.includes('running') || lower.includes('operating')) return 'operating';
  if (lower.includes('idle') || lower.includes('standby')) return 'standby';
  if (lower.includes('stopped') || lower.includes('off')) return 'stopped';
  return 'standby';
}

export function getTimeRangeBounds(timeRange: TimeRange): TimeRangeBounds {
  const endTime = new Date();
  const startTime = new Date();

  switch (timeRange) {
    case '1h':
      startTime.setHours(startTime.getHours() - 1);
      break;
    case '8h':
      startTime.setHours(startTime.getHours() - 8);
      break;
    case '24h':
      startTime.setHours(startTime.getHours() - 24);
      break;
    case '7d':
      startTime.setDate(startTime.getDate() - 7);
      break;
  }

  const totalMs = Math.max(0, endTime.getTime() - startTime.getTime());
  return { startTime, endTime, totalMs };
}

export function formatDuration(ms: number): string {
  if (ms < 60000) return '<1m';
  const totalMinutes = Math.floor(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) {
    return `${hours}h ${minutes.toString().padStart(2, '0')}m`;
  }
  return `${minutes}m`;
}

export function timeRangeDisplayLabel(timeRange: TimeRange): string {
  return timeRange.toUpperCase();
}

/**
 * Duration-weighted breakdown of machine status over a time window.
 */
export function computeStatusDurations(
  events: StatusHistoryEvent[],
  bounds: TimeRangeBounds,
  currentStatus: string | undefined,
  isOnline?: boolean
): StatusDurationSlice[] {
  const { startTime, endTime, totalMs } = bounds;
  const startMs = startTime.getTime();
  const endMs = endTime.getTime();

  const durations: Record<MachineStatus, number> = {
    operating: 0,
    standby: 0,
    stopped: 0,
    error: 0,
    off: 0,
  };

  const addMs = (status: MachineStatus, ms: number) => {
    if (ms > 0) durations[status] += ms;
  };

  let initialStatus = normalizeStatus(currentStatus, isOnline);
  if (!currentStatus) {
    const sortedForInit = [...events]
      .filter((e) => {
        const t = new Date(e.time).getTime();
        return t >= startMs && t <= endMs;
      })
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
    if (sortedForInit.length > 0) {
      initialStatus = normalizeStatus(sortedForInit[0].status);
    }
  }

  if (totalMs === 0) {
    return STATUS_ORDER.map((status) => ({
      status,
      ms: 0,
      percent: 0,
    }));
  }

  const sorted = [...events]
    .filter((e) => {
      const t = new Date(e.time).getTime();
      return t >= startMs && t <= endMs;
    })
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

  if (sorted.length === 0) {
    const hasLiveData = currentStatus !== undefined || isOnline !== undefined;
    if (hasLiveData) {
      addMs(initialStatus, totalMs);
    }
  } else {
    let segmentStart = startMs;
    let activeStatus = initialStatus;

    for (const event of sorted) {
      const eventMs = new Date(event.time).getTime();
      if (eventMs > segmentStart) {
        addMs(activeStatus, eventMs - segmentStart);
      }
      activeStatus = normalizeStatus(event.status);
      segmentStart = eventMs;
    }

    if (currentStatus !== undefined && endMs > segmentStart) {
      const finalStatus = normalizeStatus(currentStatus, isOnline);
      addMs(finalStatus, endMs - segmentStart);
    }
  }

  return STATUS_ORDER.map((status) => ({
    status,
    ms: durations[status],
    percent: (durations[status] / totalMs) * 100,
  }));
}
