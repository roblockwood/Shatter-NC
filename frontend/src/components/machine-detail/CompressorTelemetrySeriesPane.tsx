import React, { useEffect, useMemo, useState } from 'react';
import {
  buildCompressorStatusSamplesUrl,
  COMPRESSOR_CHART_REFETCH_MS,
  fetchCompressorStatusSamples,
  isCompressorChartAbortError,
} from '../../utils/compressorChartSamples';
import {
  buildOscilloscopeAxisDivisionLabels,
  getOscilloscopeTicksForMode,
} from '../../utils/chartTimeAxis';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import { useLocalChartTimeAxisMode } from '../../hooks/useLocalChartTimeAxisMode';
import { ChartTimeAxisToggle } from '../ui/ChartTimeAxisToggle';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { readNumericPressureTemp } from '../../utils/compressorTelemetry';
import './AlarmPane.css';

interface SampleRow {
  time: string;
  compressor_id: number;
  status: string;
  metrics?: Record<string, unknown> | null;
}

type TimeRange = '1h' | '8h' | '24h' | '7d';

export type CompressorTelemetrySeries = 'psi' | 'temp';

const MAX_DRAW_POINTS = 1_400;

const COLOR_PSI = '#3b82f6';
const COLOR_TEMP = '#f97316';

function numFromMetrics(m: Record<string, unknown> | undefined, key: string): number | null {
  if (!m) return null;
  const v = m[key];
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function strFromMetrics(m: Record<string, unknown> | undefined, key: string): string | null {
  if (!m) return null;
  const v = m[key];
  return typeof v === 'string' && v.trim() ? v.trim() : null;
}

interface TelemetryPoint {
  t: number;
  psi: number | null;
  temp: number | null;
}

function rowsToPoints(rows: SampleRow[]): TelemetryPoint[] {
  const out: TelemetryPoint[] = [];
  for (const row of rows) {
    const m = row.metrics ?? undefined;
    const psi = numFromMetrics(m, 'psi');
    const temp = numFromMetrics(m, 'outlet_temp');
    if (psi == null && temp == null) continue;
    const t = new Date(row.time).getTime();
    if (!Number.isFinite(t)) continue;
    out.push({ t, psi, temp });
  }
  return out.sort((a, b) => a.t - b.t);
}

function decimatePoints(points: TelemetryPoint[], maxCount: number): TelemetryPoint[] {
  if (points.length <= maxCount) return points;
  const step = Math.ceil(points.length / maxCount);
  const out: TelemetryPoint[] = [];
  for (let i = 0; i < points.length; i += step) {
    out.push(points[i]!);
  }
  const last = points[points.length - 1]!;
  if (out[out.length - 1]!.t !== last.t) out.push(last);
  return out;
}

/** Re-inject global min/max of `key` so decimation cannot drop the only spike (PEAK / trough). */
function mergeExtremaSamples(
  decimated: TelemetryPoint[],
  fullSeries: TelemetryPoint[],
  key: 'psi' | 'temp'
): TelemetryPoint[] {
  if (fullSeries.length === 0) return decimated;
  let maxP: TelemetryPoint | null = null;
  let minP: TelemetryPoint | null = null;
  let maxV = -Infinity;
  let minV = Infinity;
  for (const p of fullSeries) {
    const v = p[key];
    if (v == null || !Number.isFinite(v)) continue;
    if (v > maxV) {
      maxV = v;
      maxP = p;
    }
    if (v < minV) {
      minV = v;
      minP = p;
    }
  }
  const byTime = new Map<number, TelemetryPoint>();
  for (const p of decimated) {
    byTime.set(p.t, p);
  }
  if (maxP) byTime.set(maxP.t, maxP);
  if (minP) byTime.set(minP.t, minP);
  return Array.from(byTime.values()).sort((a, b) => a.t - b.t);
}

function filterSeries(points: TelemetryPoint[], key: 'psi' | 'temp'): TelemetryPoint[] {
  return points.filter((p) => p[key] != null && Number.isFinite(p[key] as number));
}

/** Y-axis padding: ratio of span plus at least `minMarginEachSide` (psi or °F) so stepped data is not edge-to-edge. */
function yRange(
  values: number[],
  padRatio: number,
  flatPad: number,
  minMarginEachSide: number
): { lo: number; hi: number } | null {
  const finite = values.filter((v) => Number.isFinite(v));
  if (finite.length === 0) return null;
  let lo = Math.min(...finite);
  let hi = Math.max(...finite);
  const margin = Math.max(0, minMarginEachSide);
  if (hi <= lo) {
    const half = Math.max(flatPad, margin);
    lo -= half;
    hi += half;
  } else {
    const span = hi - lo;
    const pad = Math.max(span * padRatio, margin, span * 0.02 + 1e-6);
    lo -= pad;
    hi += pad;
  }
  return { lo, hi };
}

const Y_PAD_RATIO = 0.14;
const Y_FLAT_PAD = 1.5;
/** Minimum headroom below min and above max (SC2 often reports integer psi / °F). */
const Y_MARGIN_PSI = 5;
const Y_MARGIN_TEMP = 5;

/**
 * Spread haze: 7d uses wide bins (blocky polygons) — strong blur softens edges; keep opacity near other
 * ranges so the band doesn’t read as faint / uneven.
 */
interface TelemetryRangeSmoothing {
  displayBinMs: number;
  smoothRadius: number;
  emaAlpha: number;
  spreadFillOpacity: number;
  spreadBlurStd: number;
}

function telemetrySmoothingForRange(range: TimeRange): TelemetryRangeSmoothing {
  switch (range) {
    case '1h':
      return {
        displayBinMs: 10_000,
        smoothRadius: 7,
        emaAlpha: 0.28,
        spreadFillOpacity: 1,
        spreadBlurStd: 3.5,
      };
    case '8h':
      return {
        // 8h is visually “stair-steppy” if we keep too many knots (quantized telemetry).
        // Bin more aggressively and smooth longer.
        displayBinMs: 60_000,
        smoothRadius: 18,
        emaAlpha: 0.12,
        // Keep haze, but make it wispy instead of blocky.
        spreadFillOpacity: 0.22,
        spreadBlurStd: 8,
      };
    case '24h':
      return {
        // 24h needs fewer knots still; otherwise the line reads as steps.
        displayBinMs: 180_000,
        smoothRadius: 26,
        emaAlpha: 0.1,
        // Keep haze, but make it wispy instead of blocky.
        spreadFillOpacity: 0.2,
        spreadBlurStd: 9,
      };
    case '7d':
      return {
        displayBinMs: 900_000,
        smoothRadius: 14,
        emaAlpha: 0.12,
        // Keep a softer, subtler envelope on 7d (bins are wide).
        spreadFillOpacity: 0.35,
        spreadBlurStd: 6,
      };
  }
}

/** Per time window: true min / max + mean (mean → smooth line; min/max → spread fill). */
function downsampleByTimeMinMaxMean(
  points: Array<{ t: number; v: number }>,
  windowMs: number
): Array<{ t: number; min: number; max: number; mean: number }> {
  if (points.length === 0 || windowMs <= 0) return [];
  const out: Array<{ t: number; min: number; max: number; mean: number }> = [];
  let i = 0;
  while (i < points.length) {
    const winStart = points[i]!.t;
    let sum = 0;
    let c = 0;
    let lastT = winStart;
    let minV = points[i]!.v;
    let maxV = points[i]!.v;
    while (i < points.length && points[i]!.t < winStart + windowMs) {
      const v = points[i]!.v;
      sum += v;
      c++;
      lastT = points[i]!.t;
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
      i++;
    }
    out.push({ t: lastT, min: minV, max: maxV, mean: sum / c });
  }
  return out;
}

/** Area between smoothed mean and bin max (upper) / min (lower); filled + blurred as one band. */
function telemetrySpreadFillPaths(
  bins: Array<{ t: number; min: number; max: number }>,
  smoothedMean: number[],
  xOf: (t: number) => number,
  yFn: (v: number) => number
): { upper: string; lower: string } | null {
  const n = bins.length;
  if (n < 2 || smoothedMean.length !== n) return null;
  const x = (i: number) => xOf(bins[i]!.t);
  const yA = (i: number) => yFn(smoothedMean[i]!);
  const yMx = (i: number) => yFn(bins[i]!.max);
  const yMn = (i: number) => yFn(bins[i]!.min);

  let upper = `M ${x(0)} ${yA(0)}`;
  for (let i = 1; i < n; i++) upper += ` L ${x(i)} ${yA(i)}`;
  for (let i = n - 1; i >= 0; i--) upper += ` L ${x(i)} ${yMx(i)}`;
  upper += ' Z';

  let lower = `M ${x(0)} ${yA(0)}`;
  for (let i = 1; i < n; i++) lower += ` L ${x(i)} ${yA(i)}`;
  for (let i = n - 1; i >= 0; i--) lower += ` L ${x(i)} ${yMn(i)}`;
  lower += ' Z';

  return { upper, lower };
}

/** Exponential moving average (display only); after MA on per-bin means. */
function exponentialSmooth1D(values: number[], alpha: number): number[] {
  if (values.length === 0) return [];
  const a = Math.min(1, Math.max(0.05, alpha));
  const out: number[] = [values[0]!];
  for (let i = 1; i < values.length; i++) {
    out.push(a * values[i]! + (1 - a) * out[i - 1]!);
  }
  return out;
}

/** Simple moving average (odd window via radius); softens integer-quantized telemetry for display only. */
function smoothMovingAverage(values: number[], radius: number): number[] {
  if (radius <= 0 || values.length === 0) return values.slice();
  const n = values.length;
  const out = new Array<number>(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    let c = 0;
    for (let j = i - radius; j <= i + radius; j++) {
      if (j >= 0 && j < n) {
        s += values[j]!;
        c++;
      }
    }
    out[i] = s / c;
  }
  return out;
}

function contiguousSegments(
  drawPoints: TelemetryPoint[],
  seriesKey: 'psi' | 'temp'
): TelemetryPoint[][] {
  const segs: TelemetryPoint[][] = [];
  let cur: TelemetryPoint[] = [];
  for (const p of drawPoints) {
    const v = p[seriesKey];
    if (v == null || !Number.isFinite(v)) {
      if (cur.length) {
        segs.push(cur);
        cur = [];
      }
      continue;
    }
    cur.push(p);
  }
  if (cur.length) segs.push(cur);
  return segs;
}

/**
 * Smoothed values are already MA+EMA filtered; we want a smooth curve without introducing
 * visual overshoot. Use a monotone cubic interpolation (Fritsch–Carlson) in x.
 */
function smoothSvgPathThroughPoints(pts: Array<{ x: number; y: number }>): string | null {
  if (pts.length === 0) return null;
  if (pts.length === 1) {
    const a = pts[0]!;
    return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)}`;
  }
  if (pts.length === 2) {
    const a = pts[0]!;
    const b = pts[1]!;
    return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} L ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
  }

  // Ensure increasing x; if not, fall back to lines.
  for (let i = 1; i < pts.length; i++) {
    if (!(pts[i]!.x > pts[i - 1]!.x)) {
      let d = `M ${pts[0]!.x.toFixed(2)} ${pts[0]!.y.toFixed(2)}`;
      for (let j = 1; j < pts.length; j++) {
        const p = pts[j]!;
        d += ` L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`;
      }
      return d;
    }
  }

  const n = pts.length;
  const x = pts.map((p) => p.x);
  const y = pts.map((p) => p.y);
  const dx: number[] = new Array(n - 1);
  const m: number[] = new Array(n - 1);
  for (let i = 0; i < n - 1; i++) {
    dx[i] = x[i + 1]! - x[i]!;
    m[i] = (y[i + 1]! - y[i]!) / dx[i]!;
  }

  // Tangents (slopes) at each knot.
  const t: number[] = new Array(n);
  t[0] = m[0]!;
  t[n - 1] = m[n - 2]!;
  for (let i = 1; i < n - 1; i++) {
    const mPrev = m[i - 1]!;
    const mNext = m[i]!;
    if (mPrev === 0 || mNext === 0 || (mPrev > 0) !== (mNext > 0)) {
      t[i] = 0;
    } else {
      // Weighted harmonic mean (Fritsch–Carlson)
      const w1 = 2 * dx[i]! + dx[i - 1]!;
      const w2 = dx[i]! + 2 * dx[i - 1]!;
      t[i] = (w1 + w2) / (w1 / mPrev + w2 / mNext);
    }
  }

  // Clamp tangents to prevent overshoot.
  for (let i = 0; i < n - 1; i++) {
    const mi = m[i]!;
    if (mi === 0) {
      t[i] = 0;
      t[i + 1] = 0;
      continue;
    }
    const a = t[i]! / mi;
    const b = t[i + 1]! / mi;
    const s = a * a + b * b;
    if (s > 9) {
      const tau = 3 / Math.sqrt(s);
      t[i] = tau * a * mi;
      t[i + 1] = tau * b * mi;
    }
  }

  let d = `M ${x[0]!.toFixed(2)} ${y[0]!.toFixed(2)}`;
  for (let i = 0; i < n - 1; i++) {
    const x0 = x[i]!;
    const y0 = y[i]!;
    const x1 = x[i + 1]!;
    const y1 = y[i + 1]!;
    const h = dx[i]!;
    // Convert Hermite to cubic Bezier control points.
    const cp1x = x0 + h / 3;
    const cp1y = y0 + (t[i]! * h) / 3;
    const cp2x = x1 - h / 3;
    const cp2y = y1 - (t[i + 1]! * h) / 3;
    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(
      2
    )}, ${x1.toFixed(2)} ${y1.toFixed(2)}`;
  }
  return d;
}

function peakInRange(points: TelemetryPoint[], key: 'psi' | 'temp'): number | null {
  const vals = points
    .map((p) => p[key])
    .filter((v): v is number => v != null && Number.isFinite(v));
  if (vals.length === 0) return null;
  return Math.max(...vals);
}

function minMaxInRange(
  points: TelemetryPoint[],
  key: 'psi' | 'temp',
  startMs: number,
  endMs: number
): { min: number; max: number } | null {
  let min = Infinity;
  let max = -Infinity;
  let saw = false;
  for (const p of points) {
    if (p.t < startMs || p.t > endMs) continue;
    const v = p[key];
    if (v == null || !Number.isFinite(v)) continue;
    saw = true;
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (!saw) return null;
  return { min, max };
}

function formatTick(n: number): string {
  const a = Math.abs(n);
  if (a >= 1000) return n.toFixed(0);
  if (a >= 100) return n.toFixed(0);
  if (a >= 10) return n.toFixed(1);
  return n.toFixed(2);
}

function rangeToWindowMs(timeRange: TimeRange): { startMs: number; endMs: number } {
  const endMs = Date.now();
  let startMs: number;
  switch (timeRange) {
    case '1h':
      startMs = endMs - 3600_000;
      break;
    case '8h':
      startMs = endMs - 8 * 3600_000;
      break;
    case '24h':
      startMs = endMs - 24 * 3600_000;
      break;
    case '7d':
      startMs = endMs - 7 * 24 * 3600_000;
      break;
  }
  return { startMs, endMs };
}

function SingleSeriesChart({
  drawPoints,
  axisExtentPoints,
  seriesKey,
  color,
  startMs,
  endMs,
  timeRange,
  timeAxisStorageKey,
  ariaLabel,
}: {
  drawPoints: TelemetryPoint[];
  /** Full-resolution points for Y-axis span — drawPoints may be decimated and omit true PEAK/min. */
  axisExtentPoints?: TelemetryPoint[];
  seriesKey: 'psi' | 'temp';
  color: string;
  startMs: number;
  endMs: number;
  timeRange: TimeRange;
  timeAxisStorageKey: string;
  ariaLabel: string;
}): React.ReactNode {
  const { timeAxisMode, toggleTimeAxisMode } = useLocalChartTimeAxisMode(timeAxisStorageKey);
  const spreadBlurFilterId = React.useId().replace(/:/g, '');
  const smooth = telemetrySmoothingForRange(timeRange);
  const W = 560;
  const H = 210;
  const ml = 48;
  const mr = 14;
  const mt = 8;
  const mb = 28;
  const pw = W - ml - mr;
  const ph = H - mt - mb;
  const span = Math.max(1, endMs - startMs);
  const xOf = (t: number) => ml + ((t - startMs) / span) * pw;

  const vals: number[] = [];
  for (const p of drawPoints) {
    const v = p[seriesKey];
    if (v != null && Number.isFinite(v)) vals.push(v);
  }
  if (axisExtentPoints) {
    for (const p of axisExtentPoints) {
      const v = p[seriesKey];
      if (v != null && Number.isFinite(v)) vals.push(v);
    }
  }
  const hasData = drawPoints.some((p) => {
    const v = p[seriesKey];
    return v != null && Number.isFinite(v);
  });
  const yMargin = seriesKey === 'psi' ? Y_MARGIN_PSI : Y_MARGIN_TEMP;
  const yR = yRange(vals, Y_PAD_RATIO, Y_FLAT_PAD, yMargin);
  const yFn = (v: number) => {
    if (!yR) return mt + ph / 2;
    const { lo, hi } = yR;
    const spanY = hi - lo || 1;
    return mt + ph - ((v - lo) / spanY) * ph;
  };

  const segs = contiguousSegments(drawPoints, seriesKey);
  const pathParts: string[] = [];
  const spreadPairs: Array<{ upper: string; lower: string }> = [];

  const {
    displayBinMs: binMs,
    smoothRadius: maRadius,
    emaAlpha,
    spreadFillOpacity,
    spreadBlurStd,
  } = smooth;

  segs.forEach((seg) => {
    let tvpairs = seg.map((p) => ({ t: p.t, v: p[seriesKey] as number }));
    let mmBins: Array<{ t: number; min: number; max: number; mean: number }> | null = null;
    if (binMs > 0 && tvpairs.length >= 2) {
      mmBins = downsampleByTimeMinMaxMean(tvpairs, binMs);
      tvpairs = mmBins.map((b) => ({ t: b.t, v: b.mean }));
    }
    let vs = tvpairs.map((p) => p.v);
    if (maRadius > 0 && vs.length >= 3) {
      vs = smoothMovingAverage(vs, maRadius);
    }
    if (vs.length >= 2) {
      vs = exponentialSmooth1D(vs, emaAlpha);
    }
    if (mmBins && mmBins.length >= 2 && mmBins.length === vs.length) {
      const sp = telemetrySpreadFillPaths(mmBins, vs, xOf, yFn);
      if (sp) spreadPairs.push(sp);
    }
    const pixelPts = tvpairs.map((pair, i) => ({
      x: xOf(pair.t),
      y: yFn(vs[i]!),
    }));
    const segD = smoothSvgPathThroughPoints(pixelPts);
    if (segD) pathParts.push(segD);
  });
  const pathD = pathParts.length ? pathParts.join(' ') : null;

  const spreadFills =
    spreadPairs.length > 0 && spreadFillOpacity > 0.01 ? (
      <>
        <defs>
          <filter
            id={spreadBlurFilterId}
            x="-55%"
            y="-55%"
            width="210%"
            height="210%"
            filterUnits="objectBoundingBox"
          >
            <feGaussianBlur in="SourceGraphic" stdDeviation={spreadBlurStd} />
          </filter>
        </defs>
        <g filter={`url(#${spreadBlurFilterId})`}>
          {spreadPairs.map((sp, i) => (
            <React.Fragment key={`spf-${i}`}>
              <path d={sp.upper} fill={color} fillOpacity={spreadFillOpacity} stroke="none" />
              <path d={sp.lower} fill={color} fillOpacity={spreadFillOpacity} stroke="none" />
            </React.Fragment>
          ))}
        </g>
      </>
    ) : null;

  const ticks = 4;
  const gridLines: React.ReactNode[] = [];
  for (let i = 0; i <= ticks; i++) {
    const gy = mt + (ph * i) / ticks;
    gridLines.push(
      <line
        key={`h${i}`}
        x1={ml}
        y1={gy}
        x2={ml + pw}
        y2={gy}
        stroke="var(--color-border)"
        strokeOpacity={0.45}
        strokeWidth={1}
      />
    );
  }

  const yTicks: React.ReactNode[] = [];
  if (yR && hasData) {
    for (let i = 0; i <= ticks; i++) {
      const frac = i / ticks;
      const v = yR.lo + (yR.hi - yR.lo) * (1 - frac);
      const gy = mt + ph * frac;
      yTicks.push(
        <text
          key={`y${i}`}
          x={ml - 6}
          y={gy + 4}
          textAnchor="end"
          fill={color}
          fontSize={10}
          fontFamily="var(--font-mono)"
        >
          {formatTick(v)}
        </text>
      );
    }
  }

  const startDate = new Date(startMs);
  const endDate = new Date(endMs);
  const xTimeTicks = getOscilloscopeTicksForMode(timeRange, startDate, endDate, timeAxisMode);
  const xLabeled = buildOscilloscopeAxisDivisionLabels(timeRange, xTimeTicks, endDate, timeAxisMode);
  const xTickLabels: React.ReactNode[] = [];
  xLabeled.forEach((tick, i) => {
    const gx = ml + (tick.x / 100) * pw;
    xTickLabels.push(
      <text
        key={`xt${i}`}
        x={gx}
        y={H - 6}
        textAnchor="middle"
        fill="var(--color-text-muted)"
        fontSize={9}
        fontFamily="var(--font-mono)"
      >
        {tick.label}
      </text>
    );
  });

  return (
    <div className="compressor-telemetry-chart-stack">
      <svg
        className="compressor-telemetry-svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        width="100%"
        height="100%"
        aria-label={ariaLabel}
      >
        <rect x={ml} y={mt} width={pw} height={ph} fill="rgba(0,0,0,0.12)" stroke="none" />
        {gridLines}
        {spreadFills}
        {pathD && (
          <path
            d={pathD}
            fill="none"
            stroke={color}
            strokeWidth={1.75}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        )}
        {yTicks}
        {xTickLabels}
      </svg>
      <div className="compressor-telemetry-axis-toggle">
        <ChartTimeAxisToggle
          timeAxisMode={timeAxisMode}
          toggleTimeAxisMode={toggleTimeAxisMode}
        />
      </div>
    </div>
  );
}

interface CompressorTelemetrySeriesPaneProps {
  compressorId: number;
  series: CompressorTelemetrySeries;
  liveOperational?: Record<string, unknown>;
  isOnline?: boolean;
  pollTimestamp?: string | null;
}

export const CompressorTelemetrySeriesPane: React.FC<CompressorTelemetrySeriesPaneProps> = ({
  compressorId,
  series,
  liveOperational,
  isOnline,
  pollTimestamp,
}) => {
  const seriesKey = series === 'psi' ? 'psi' : 'temp';
  const color = series === 'psi' ? COLOR_PSI : COLOR_TEMP;
  const headerTitle = series === 'psi' ? 'PSI' : 'TEMP';

  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const [samples, setSamples] = useState<SampleRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const abortInitial = new AbortController();
    let pollAbort: AbortController | null = null;
    let pollChainTimeout: ReturnType<typeof setTimeout> | null = null;

    const samplesUrl = () => buildCompressorStatusSamplesUrl(compressorId, timeRange);

    const runInitial = async () => {
      setLoading(true);
      setError(null);
      try {
        const samp = await fetchCompressorStatusSamples(samplesUrl(), abortInitial.signal, {
          isInitial: true,
        });
        if (cancelled) return;
        setSamples(samp as SampleRow[]);
        setLastFetchSuccessAt(new Date().toISOString());
        setError(null);
      } catch (e) {
        if (cancelled || abortInitial.signal.aborted) return;
        if (!isCompressorChartAbortError(e)) {
          setError(e instanceof Error ? e.message : 'Failed to load samples');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    const scheduleNextPoll = () => {
      if (cancelled) return;
      pollChainTimeout = window.setTimeout(() => void runPoll(), COMPRESSOR_CHART_REFETCH_MS);
    };

    const runPoll = async () => {
      if (cancelled) return;
      pollAbort?.abort();
      pollAbort = new AbortController();
      const signal = pollAbort.signal;
      try {
        const samp = await fetchCompressorStatusSamples(samplesUrl(), signal, { isInitial: false });
        if (cancelled || signal.aborted) return;
        setSamples(samp as SampleRow[]);
        setLastFetchSuccessAt(new Date().toISOString());
        setError(null);
      } catch (e) {
        if (cancelled || signal.aborted || isCompressorChartAbortError(e)) {
          /* keep last good samples */
        }
      } finally {
        if (!cancelled) scheduleNextPoll();
      }
    };

    void runInitial().then(() => {
      if (cancelled) return;
      const jitter = Math.floor(Math.random() * 700);
      pollChainTimeout = window.setTimeout(() => void runPoll(), COMPRESSOR_CHART_REFETCH_MS + jitter);
    });

    return () => {
      cancelled = true;
      abortInitial.abort();
      pollAbort?.abort();
      if (pollChainTimeout !== null) window.clearTimeout(pollChainTimeout);
    };
  }, [compressorId, timeRange]);

  const pointsFromApi = useMemo(() => rowsToPoints(samples), [samples]);

  const pointsWithLiveTail = useMemo(() => {
    if (isOnline === false || pollTimestamp == null || pollTimestamp === '') {
      return pointsFromApi;
    }
    const live = readNumericPressureTemp(liveOperational);
    if (live.psi == null && live.outletTemp == null) {
      return pointsFromApi;
    }
    const tMs = new Date(pollTimestamp).getTime();
    if (!Number.isFinite(tMs)) return pointsFromApi;
    const lastMs = pointsFromApi.length ? pointsFromApi[pointsFromApi.length - 1]!.t : 0;
    if (tMs <= lastMs) return pointsFromApi;
    return [
      ...pointsFromApi,
      {
        t: tMs,
        psi: live.psi,
        temp: live.outletTemp,
      },
    ];
  }, [pointsFromApi, liveOperational, isOnline, pollTimestamp]);

  const { startMs, endMs } = useMemo(() => rangeToWindowMs(timeRange), [timeRange]);

  const drawPoints = useMemo(() => {
    const filtered = filterSeries(pointsWithLiveTail, seriesKey);
    return mergeExtremaSamples(decimatePoints(filtered, MAX_DRAW_POINTS), filtered, seriesKey);
  }, [pointsWithLiveTail, seriesKey]);

  const { unit, peak, hasSeries } = useMemo(() => {
    const unitKey = series === 'psi' ? 'psi_unit' : 'temp_unit';
    let u: string | null = null;
    for (const row of samples) {
      const m = row.metrics ?? undefined;
      u = strFromMetrics(m, unitKey);
      if (u) break;
    }
    const live = readNumericPressureTemp(liveOperational);
    if (!u) {
      u = series === 'psi' ? live.psiUnit : live.tempUnit;
    }

    const pk = peakInRange(pointsWithLiveTail, seriesKey);
    const hs = pk != null;

    return { unit: u, peak: pk, hasSeries: hs };
  }, [samples, liveOperational, pointsWithLiveTail, series, seriesKey]);

  const range = useMemo(
    () => minMaxInRange(pointsWithLiveTail, seriesKey, startMs, endMs),
    [pointsWithLiveTail, seriesKey, startMs, endMs]
  );

  const tooltipLines = useMemo(() => {
    const lines: string[] = [
      isOnline === false
        ? 'TELEMETRY: OFFLINE'
        : isOnline === true
          ? 'TELEMETRY: ONLINE'
          : 'TELEMETRY: UNKNOWN',
    ];
    const live = readNumericPressureTemp(liveOperational);
    if (series === 'psi' && live.psi != null) {
      lines.push(`PSI: ${formatTick(live.psi)}${live.psiUnit ? live.psiUnit : ''}`);
    }
    if (series === 'temp' && live.outletTemp != null) {
      lines.push(`TEMP: ${formatTick(live.outletTemp)}${live.tempUnit ? live.tempUnit : ''}`);
    }
    if (series === 'temp' && peak != null) {
      lines.push(`PEAK (${timeRange}): ${formatTick(peak)}${unit ? unit : ''}`);
    }
    if (series === 'psi' && peak != null) {
      lines.push(`PEAK (${timeRange}): ${formatTick(peak)}${unit ? unit : ''}`);
    }
    if (range) {
      lines.push(
        `RANGE (${timeRange}): ${formatTick(range.min)}–${formatTick(range.max)}${unit ? unit : ''}`
      );
    }
    return lines;
  }, [isOnline, liveOperational, series, peak, unit, timeRange, range]);

  const subtitle = unit ? `${headerTitle} (${unit})` : headerTitle;
  const peakLine = peak != null ? `PEAK ${formatTick(peak)}${unit ? unit : ''}` : null;
  const rangeLine =
    range != null
      ? `RANGE ${formatTick(range.min)}–${formatTick(range.max)}${unit ? unit : ''}`
      : null;
  const ariaChart =
    series === 'psi' ? 'Compressor pressure over time' : 'Compressor outlet temperature over time';

  return (
    <div
      className={`alarm-pane terminal-box compressor-terminal-pane compressor-timeline-pane compressor-timeline-pane--telemetry compressor-timeline-pane--telemetry-${series}`}
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label={headerTitle}>
        <PollingStatusLight
          lastUpdatedAt={lastFetchSuccessAt}
          expectedIntervalMs={COMPRESSOR_CHART_REFETCH_MS}
          ariaLabel={`Compressor ${headerTitle} chart data freshness`}
          tooltipDetailLines={tooltipLines}
        />
      </PaneTerminalHeader>

      <div className="terminal-box-content">
        <div className="compressor-timeline-pane-inner">
          <div className="compressor-timeline-range-row">
            {(['1h', '8h', '24h', '7d'] as const).map((r) => (
              <button
                key={r}
                type="button"
                className={`time-range-btn ${timeRange === r ? 'active' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setTimeRange(r);
                }}
              >
                [{r.toUpperCase()}]
              </button>
            ))}
          </div>

          <div className="compressor-telemetry-pane-head">
            <span
              className={
                series === 'psi'
                  ? 'compressor-telemetry-pane-series compressor-telemetry-legend-psi'
                  : 'compressor-telemetry-pane-series compressor-telemetry-legend-temp'
              }
            >
              {subtitle}
            </span>
            {rangeLine && (
              <span
                className={
                  series === 'psi'
                    ? 'compressor-telemetry-peak compressor-telemetry-legend-psi'
                    : 'compressor-telemetry-peak compressor-telemetry-legend-temp'
                }
              >
                {rangeLine}
              </span>
            )}
            {peakLine && (
              <span
                className={
                  series === 'psi'
                    ? 'compressor-telemetry-peak compressor-telemetry-legend-psi'
                    : 'compressor-telemetry-peak compressor-telemetry-legend-temp'
                }
              >
                {peakLine}
              </span>
            )}
          </div>

          {loading && <p className="text-dim">LOADING…</p>}
          {error && <p className="compressor-error">{error}</p>}

          {!loading && !error && samples.length > 0 && hasSeries && (
            <div className="compressor-telemetry-chart-wrap">
              <SingleSeriesChart
                drawPoints={drawPoints}
                axisExtentPoints={filterSeries(pointsWithLiveTail, seriesKey)}
                seriesKey={seriesKey}
                color={color}
                startMs={startMs}
                endMs={endMs}
                timeRange={timeRange}
                timeAxisStorageKey={`compressor-${compressorId}-${series}`}
                ariaLabel={ariaChart}
              />
            </div>
          )}

          {!loading && !error && samples.length > 0 && !hasSeries && (
            <p className="text-dim">
              No {series === 'psi' ? 'pressure' : 'temperature'} samples in this range (data may predate
              telemetry).
            </p>
          )}

          {!loading && !error && samples.length === 0 && (
            <p className="text-dim">No data for this time range.</p>
          )}
        </div>
      </div>

      <PaneTerminalFooter />
    </div>
  );
};
