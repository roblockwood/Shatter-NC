import React, { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from '../../config/api';
import { asciiFooterLine, asciiHeaderLeft } from '../../utils/terminalFrame';
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

/** Match ~1 Hz DB samples; was 5s and made charts look poll-limited. */
const REFETCH_MS = 1_000;
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

/** PSI: light MA only (often fewer identical samples in a row). */
const PSI_SMOOTH_RADIUS = 5;
/** Temp: many 1 Hz samples per integer → bin in time, then strong MA + EMA (display only). */
const TEMP_DISPLAY_BIN_MS = 12_000;
const TEMP_SMOOTH_RADIUS = 10;
const TEMP_EMA_ALPHA = 0.38;
/** Optional PSI time bin (0 = off); softens stepped pressure a bit without lagging like temp. */
const PSI_DISPLAY_BIN_MS = 6_000;

/**
 * Collapse high-rate plateau samples into one point per time window using mean `v`.
 * Buckets that straddle an integer step get a fractional average → smoother curves than MA on raw 1 Hz plateaus.
 */
function downsampleByTimeAverage(
  points: Array<{ t: number; v: number }>,
  windowMs: number
): Array<{ t: number; v: number }> {
  if (points.length === 0 || windowMs <= 0) return points;
  const out: Array<{ t: number; v: number }> = [];
  let i = 0;
  while (i < points.length) {
    const winStart = points[i]!.t;
    let sum = 0;
    let c = 0;
    let lastT = winStart;
    while (i < points.length && points[i]!.t < winStart + windowMs) {
      sum += points[i]!.v;
      c++;
      lastT = points[i]!.t;
      i++;
    }
    out.push({ t: lastT, v: sum / c });
  }
  return out;
}

/** Exponential moving average (display only); reduces notchiness after MA. */
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

/** Catmull–Rom-style cubic Beziers through pixel points (display smoothing; raw samples unchanged in DB). */
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
  let d = `M ${pts[0]!.x.toFixed(2)} ${pts[0]!.y.toFixed(2)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = i > 0 ? pts[i - 1]! : pts[i]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = i < pts.length - 2 ? pts[i + 2]! : p2;
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
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
  seriesKey,
  color,
  startMs,
  endMs,
  ariaLabel,
}: {
  drawPoints: TelemetryPoint[];
  seriesKey: 'psi' | 'temp';
  color: string;
  startMs: number;
  endMs: number;
  ariaLabel: string;
}): React.ReactNode {
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

  const vals = drawPoints.map((p) => p[seriesKey]).filter((v): v is number => v != null && Number.isFinite(v));
  const hasData = vals.length > 0;
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
  const binMs = seriesKey === 'temp' ? TEMP_DISPLAY_BIN_MS : PSI_DISPLAY_BIN_MS;
  const maRadius = seriesKey === 'temp' ? TEMP_SMOOTH_RADIUS : PSI_SMOOTH_RADIUS;

  for (const seg of segs) {
    let tvpairs = seg.map((p) => ({ t: p.t, v: p[seriesKey] as number }));
    if (binMs > 0 && tvpairs.length >= 2) {
      tvpairs = downsampleByTimeAverage(tvpairs, binMs);
    }
    let vs = tvpairs.map((p) => p.v);
    if (vs.length >= 3) {
      vs = smoothMovingAverage(vs, maRadius);
    }
    if (seriesKey === 'temp' && vs.length >= 2) {
      vs = exponentialSmooth1D(vs, TEMP_EMA_ALPHA);
    }
    const pixelPts = tvpairs.map((pair, i) => ({
      x: xOf(pair.t),
      y: yFn(vs[i]!),
    }));
    const segD = smoothSvgPathThroughPoints(pixelPts);
    if (segD) pathParts.push(segD);
  }
  const pathD = pathParts.length ? pathParts.join(' ') : null;

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

  const xTickLabels: React.ReactNode[] = [];
  const xTicks = 5;
  for (let i = 0; i <= xTicks; i++) {
    const frac = i / xTicks;
    const t = startMs + span * frac;
    const gx = ml + pw * frac;
    const mins = Math.round((endMs - t) / 60_000);
    const label =
      mins < 60 ? `${mins}m` : mins < 1440 ? `${Math.round(mins / 60)}h` : `${Math.round(mins / 1440)}d`;
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
        {label}
      </text>
    );
  }

  return (
    <svg
      className="compressor-telemetry-svg"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      width="100%"
      height="100%"
      aria-label={ariaLabel}
    >
      <rect x={ml} y={mt} width={pw} height={ph} fill="rgba(0,0,0,0.12)" stroke="none" />
      {gridLines}
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

    const rangeBounds = () => {
      const end = new Date();
      const start = new Date(end);
      switch (timeRange) {
        case '1h':
          start.setHours(start.getHours() - 1);
          break;
        case '8h':
          start.setHours(start.getHours() - 8);
          break;
        case '24h':
          start.setHours(start.getHours() - 24);
          break;
        case '7d':
          start.setDate(start.getDate() - 7);
          break;
      }
      return { start, end };
    };

    const samplesUrl = () => {
      const { start, end } = rangeBounds();
      return `${API_BASE_URL}/api/compressors/${compressorId}/status-samples?start_time=${encodeURIComponent(
        start.toISOString()
      )}&end_time=${encodeURIComponent(end.toISOString())}&limit=20000`;
    };

    const load = (signal: AbortSignal, showLoading: boolean) => {
      if (showLoading) {
        setLoading(true);
        setError(null);
      }
      fetch(samplesUrl(), { signal, cache: 'no-store' })
        .then((r) => {
          if (!r.ok) throw new Error(r.statusText);
          return r.json();
        })
        .then((samp) => {
          if (cancelled) return;
          setSamples(Array.isArray(samp) ? samp : []);
          setLastFetchSuccessAt(new Date().toISOString());
          setError(null);
        })
        .catch((e) => {
          if (e.name === 'AbortError' || cancelled) return;
          if (showLoading) {
            setError(e.message || 'Failed to load samples');
          }
        })
        .finally(() => {
          if (!cancelled && showLoading) setLoading(false);
        });
    };

    load(abortInitial.signal, true);

    const intervalId = window.setInterval(() => {
      if (cancelled) return;
      const ic = new AbortController();
      load(ic.signal, false);
    }, REFETCH_MS);

    return () => {
      cancelled = true;
      abortInitial.abort();
      window.clearInterval(intervalId);
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

  const drawPoints = useMemo(
    () => decimatePoints(filterSeries(pointsWithLiveTail, seriesKey), MAX_DRAW_POINTS),
    [pointsWithLiveTail, seriesKey]
  );

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
    return lines;
  }, [isOnline, liveOperational, series, peak, unit, timeRange]);

  const subtitle = unit ? `${headerTitle} (${unit})` : headerTitle;
  const peakLine = peak != null ? `PEAK ${formatTick(peak)}${unit ? unit : ''}` : null;
  const ariaChart =
    series === 'psi' ? 'Compressor pressure over time' : 'Compressor outlet temperature over time';

  return (
    <div
      className={`alarm-pane terminal-box compressor-terminal-pane compressor-timeline-pane compressor-timeline-pane--telemetry compressor-timeline-pane--telemetry-${series}`}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>{asciiHeaderLeft(headerTitle)}</span>
            <div className="pane-header-right-actions">
              <PollingStatusLight
                lastUpdatedAt={lastFetchSuccessAt}
                expectedIntervalMs={REFETCH_MS}
                ariaLabel={`Compressor ${headerTitle} chart data freshness`}
                tooltipDetailLines={tooltipLines}
              />
              <span>┐</span>
            </div>
          </div>
        </div>
      </div>

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
                seriesKey={seriesKey}
                color={color}
                startMs={startMs}
                endMs={endMs}
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

      <div className="terminal-box-footer">{asciiFooterLine(42)}</div>
    </div>
  );
};
