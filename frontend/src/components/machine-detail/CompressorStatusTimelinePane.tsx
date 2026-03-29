import React, { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from '../../config/api';
import type { StatusEvent } from '../../api/summary';
import { asciiFooterLine, asciiHeaderLeft } from '../../utils/terminalFrame';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { StatusOscilloscope } from '../ui/StatusOscilloscope';
import './AlarmPane.css';

interface SampleRow {
  time: string;
  compressor_id: number;
  status: string;
  metrics?: Record<string, unknown> | null;
}

type TimeRange = '1h' | '8h' | '24h' | '7d';

/** Chart HTTP refresh — match ~1 Hz compressor_status_samples so the oscilloscope advances smoothly. */
const COMPRESSOR_TIMELINE_REFETCH_MS = 1_000;

/** MQTT samples arrive ~1/s; oscilloscope draws a vertical tick per point — thin unchanged runs. */
const OSCILLOSCOPE_DISPLAY_STRIDE = 5;

function decimateSamplesForOscilloscope<T extends { time: string; status: string }>(
  rows: T[],
  stride: number
): T[] {
  if (rows.length <= 2 || stride < 2) return rows;
  const sorted = [...rows].sort(
    (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
  );
  const out: T[] = [sorted[0]!];
  let sinceLastKept = 0;
  let lastKeptStatus = sorted[0]!.status;
  for (let i = 1; i < sorted.length - 1; i++) {
    const row = sorted[i]!;
    sinceLastKept++;
    const changed = row.status !== lastKeptStatus;
    if (changed || sinceLastKept >= stride) {
      out.push(row);
      lastKeptStatus = row.status;
      sinceLastKept = 0;
    }
  }
  const last = sorted[sorted.length - 1]!;
  if (out[out.length - 1]!.time !== last.time) {
    out.push(last);
  }
  return out;
}

interface CompressorStatusTimelinePaneProps {
  compressorId: number;
  liveStatus?: string;
  isOnline?: boolean;
  /** Last successful compressor poll (ISO) — extends trace to “now” between HTTP refetches. */
  pollTimestamp?: string | null;
}

export const CompressorStatusTimelinePane: React.FC<CompressorStatusTimelinePaneProps> = ({
  compressorId,
  liveStatus,
  isOnline,
  pollTimestamp,
}) => {
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
    }, COMPRESSOR_TIMELINE_REFETCH_MS);

    return () => {
      cancelled = true;
      abortInitial.abort();
      window.clearInterval(intervalId);
    };
  }, [compressorId, timeRange]);

  /** One trailing point from live WS/poll when newer than last API row (fills gap until DB catches up). */
  const samplesWithLiveTail = useMemo(() => {
    const st = liveStatus?.trim();
    if (!st || isOnline === false || pollTimestamp == null || pollTimestamp === '') {
      return samples;
    }
    const tMs = new Date(pollTimestamp).getTime();
    if (!Number.isFinite(tMs)) return samples;
    const lastApiMs = samples.length
      ? new Date(samples[samples.length - 1]!.time).getTime()
      : 0;
    if (tMs <= lastApiMs) return samples;
    const row: SampleRow = {
      time: new Date(tMs).toISOString(),
      compressor_id: compressorId,
      status: st,
      metrics: { source: 'live' },
    };
    return [...samples, row];
  }, [samples, liveStatus, isOnline, pollTimestamp, compressorId]);

  const sampleHistoryForOscilloscope: StatusEvent[] = decimateSamplesForOscilloscope(
    samplesWithLiveTail.map((s) => ({ time: s.time, status: s.status })),
    OSCILLOSCOPE_DISPLAY_STRIDE
  );

  const statusTooltipLines = useMemo(() => {
    const lines: string[] = [
      isOnline === false
        ? 'TELEMETRY: OFFLINE'
        : isOnline === true
          ? 'TELEMETRY: ONLINE'
          : 'TELEMETRY: UNKNOWN',
    ];
    const st = liveStatus?.trim();
    if (st) lines.push(`STATUS: ${st}`);
    return lines;
  }, [isOnline, liveStatus]);

  return (
    <div
      className="alarm-pane terminal-box compressor-terminal-pane compressor-timeline-pane compressor-timeline-pane--oscilloscope"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>{asciiHeaderLeft('Status timeline')}</span>
            <div className="pane-header-right-actions">
              <PollingStatusLight
                lastUpdatedAt={lastFetchSuccessAt}
                expectedIntervalMs={COMPRESSOR_TIMELINE_REFETCH_MS}
                ariaLabel="Compressor timeline chart data freshness"
                tooltipDetailLines={statusTooltipLines}
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

          {loading && <p className="text-dim">LOADING…</p>}
          {error && <p className="compressor-error">{error}</p>}

          {!loading && !error && samples.length > 0 && (
            <div className="compressor-oscilloscope-wrap">
              <StatusOscilloscope
                statusHistory={sampleHistoryForOscilloscope}
                currentStatus={liveStatus}
                timeRange={timeRange}
                variant="compressor"
                isOnline={isOnline}
                fillHeight
              />
            </div>
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
