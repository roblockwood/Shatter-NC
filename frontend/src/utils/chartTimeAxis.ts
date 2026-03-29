export type ChartTimeAxisMode = 'relative' | 'absolute';

export type ChartTimeRange = '1h' | '8h' | '24h' | '7d';

/** Multiples of 5 minutes (local), coarse enough for long spans. */
const CLOCK_SNAP_STEPS_MIN = [
  5, 10, 15, 20, 30, 60, 120, 180, 360, 720, 1440, 2880, 4320, 10080,
] as const;

function minutesSinceLocalMidnight(d: Date): number {
  return d.getHours() * 60 + d.getMinutes();
}

/** Floor to previous grid instant (local); step is in minutes, always a multiple of 5. */
function floorLocalToMinuteGrid(d: Date, stepMinutes: number): Date {
  const x = new Date(d);
  x.setMilliseconds(0);
  if (x.getSeconds() !== 0) {
    x.setSeconds(0, 0);
  }
  let msm = minutesSinceLocalMidnight(x);
  msm -= msm % stepMinutes;
  x.setHours(Math.floor(msm / 60), msm % 60, 0, 0);
  return x;
}

function ceilLocalToMinuteGrid(d: Date, stepMinutes: number): Date {
  const f = floorLocalToMinuteGrid(d, stepMinutes);
  if (f.getTime() < d.getTime()) {
    return new Date(f.getTime() + stepMinutes * 60_000);
  }
  return f;
}

function countGridTicksInclusive(startTime: Date, endTime: Date, stepMinutes: number): number {
  let t = ceilLocalToMinuteGrid(startTime, stepMinutes);
  let n = 0;
  while (t.getTime() <= endTime.getTime()) {
    n++;
    t = new Date(t.getTime() + stepMinutes * 60_000);
  }
  return n;
}

function pickClockSnapStepMinutes(startTime: Date, endTime: Date): number {
  for (const step of CLOCK_SNAP_STEPS_MIN) {
    const n = countGridTicksInclusive(startTime, endTime, step);
    if (n >= 4 && n <= 14) return step;
  }
  for (const step of CLOCK_SNAP_STEPS_MIN) {
    const n = countGridTicksInclusive(startTime, endTime, step);
    if (n >= 2) return step;
  }
  return 60;
}

/**
 * Absolute (CLK) mode: ticks on local wall-clock grid (:00, :05, :10, …), step scales with span.
 */
export function getClockSnapOscilloscopeTicks(
  startTime: Date,
  endTime: Date
): Array<{ x: number; time: Date }> {
  const totalMs = endTime.getTime() - startTime.getTime();
  if (totalMs <= 0) return [];

  const stepM = pickClockSnapStepMinutes(startTime, endTime);
  const out: Array<{ x: number; time: Date }> = [];
  let t = ceilLocalToMinuteGrid(startTime, stepM);

  while (t.getTime() <= endTime.getTime()) {
    const x = ((t.getTime() - startTime.getTime()) / totalMs) * 100;
    out.push({ x, time: new Date(t) });
    t = new Date(t.getTime() + stepM * 60_000);
  }

  if (out.length === 0) {
    return [
      { x: 0, time: new Date(startTime) },
      { x: 100, time: new Date(endTime) },
    ];
  }
  if (out.length === 1) {
    return [
      { x: 0, time: new Date(startTime) },
      out[0]!,
      { x: 100, time: new Date(endTime) },
    ];
  }
  return out;
}

/** Tick positions (x = 0–100) and instants, shared by status oscilloscopes and compressor line charts. */
export function getOscilloscopeTimeTicks(
  timeRange: ChartTimeRange,
  startTime: Date,
  endTime: Date
): Array<{ x: number; time: Date }> {
  const totalMs = endTime.getTime() - startTime.getTime();
  if (totalMs <= 0) return [];

  const segmentCount =
    timeRange === '1h' ? 4 : timeRange === '8h' ? 8 : timeRange === '24h' ? 4 : 7;
  const tickCount = segmentCount + 1;
  const out: Array<{ x: number; time: Date }> = [];

  for (let i = 0; i < tickCount; i++) {
    const x = (i / segmentCount) * 100;
    const divTime = new Date(startTime.getTime() + (i / segmentCount) * totalMs);
    out.push({ x, time: divTime });
  }
  return out;
}

/** Relative: even divisions; absolute: clock-aligned (:05, :10, … with adaptive step). */
export function getOscilloscopeTicksForMode(
  timeRange: ChartTimeRange,
  startTime: Date,
  endTime: Date,
  mode: ChartTimeAxisMode
): Array<{ x: number; time: Date }> {
  if (mode === 'relative') {
    return getOscilloscopeTimeTicks(timeRange, startTime, endTime);
  }
  return getClockSnapOscilloscopeTicks(startTime, endTime);
}

function sameLocalCalendarDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/** Compact date: 3.29 (month.day) */
export function formatMonthDotDay(d: Date): string {
  return `${d.getMonth() + 1}.${d.getDate()}`;
}

/** 24-hour clock, no seconds — e.g. 15:05 */
export function formatHourMinute24(d: Date): string {
  const h = d.getHours();
  const m = d.getMinutes();
  return `${h}:${m.toString().padStart(2, '0')}`;
}

function formatRelativeTick(timeRange: ChartTimeRange, divTime: Date, endTime: Date): string {
  const msBeforeNow = Math.max(0, endTime.getTime() - divTime.getTime());
  if (timeRange === '1h') return `${Math.round(msBeforeNow / 60000)}m`;
  if (timeRange === '8h' || timeRange === '24h') return `${Math.round(msBeforeNow / 3600000)}h`;
  return `${Math.round(msBeforeNow / 86400000)}d`;
}

/**
 * Absolute labels along the axis: mostly H:MM; at each local calendar-day change from the
 * previous tick (earlier time, to the left), show M.D only (midnight / date line).
 */
export function formatAbsoluteDivisionLabel(divTime: Date, previousDivTime: Date | null): string {
  if (previousDivTime != null && sameLocalCalendarDay(previousDivTime, divTime)) {
    return formatHourMinute24(divTime);
  }
  if (previousDivTime != null && !sameLocalCalendarDay(previousDivTime, divTime)) {
    return formatMonthDotDay(divTime);
  }
  return formatHourMinute24(divTime);
}

export function buildOscilloscopeAxisDivisionLabels(
  timeRange: ChartTimeRange,
  ticks: Array<{ x: number; time: Date }>,
  endTime: Date,
  mode: ChartTimeAxisMode
): Array<{ x: number; time: Date; label: string }> {
  if (mode === 'relative') {
    return ticks.map((d) => ({
      ...d,
      label: formatRelativeTick(timeRange, d.time, endTime),
    }));
  }
  return ticks.map((d, i) => ({
    ...d,
    label: formatAbsoluteDivisionLabel(d.time, i > 0 ? ticks[i - 1]!.time : null),
  }));
}

function formatAbsoluteAxisEndpoint(t: Date, startTime: Date, endTime: Date): string {
  if (sameLocalCalendarDay(startTime, endTime)) {
    return formatHourMinute24(t);
  }
  return `${formatMonthDotDay(t)} ${formatHourMinute24(t)}`;
}

export function oscilloscopeAxisEndLabels(
  _timeRange: ChartTimeRange,
  startTime: Date,
  endTime: Date,
  mode: ChartTimeAxisMode
): { left: string; right: string } {
  if (mode === 'relative') {
    return { left: 'PAST', right: 'NOW' };
  }
  return {
    left: formatAbsoluteAxisEndpoint(startTime, startTime, endTime),
    right: formatAbsoluteAxisEndpoint(endTime, startTime, endTime),
  };
}
