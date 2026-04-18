import React, { useEffect, useMemo, useState } from 'react';
import type { StatusEvent } from '../../api/summary';
import type { CompressorChartSamplesProfile } from '../../utils/compressorChartSamples';
import {
  buildCompressorStatusSamplesUrl,
  compressorChartRefetchMs,
  fetchCompressorStatusSamples,
  isCompressorChartAbortError,
} from '../../utils/compressorChartSamples';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
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

/** Desktop: plot every sample (path smoothing + beziers handle visual density). */
const OSCILLOSCOPE_DISPLAY_STRIDE = 1;

/** Tablet kiosk: thin dense traces on long windows — keeps StatusOscilloscope responsive. */
function oscilloscopeStrideForProfile(
  range: TimeRange,
  profile: CompressorChartSamplesProfile
): number {
  if (profile !== 'tablet') return OSCILLOSCOPE_DISPLAY_STRIDE;
  switch (range) {
    case '1h':
      return 8;
    case '8h':
      return 36;
    case '24h':
      return 48;
    case '7d':
      return 72;
    default:
      return OSCILLOSCOPE_DISPLAY_STRIDE;
  }
}

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
  samplesProfile?: CompressorChartSamplesProfile;
}

export const CompressorStatusTimelinePane: React.FC<CompressorStatusTimelinePaneProps> = ({
  compressorId,
  liveStatus,
  isOnline,
  pollTimestamp,
  samplesProfile = 'default',
}) => {
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');
  const [samples, setSamples] = useState<SampleRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);

  const chartRefetchMs = compressorChartRefetchMs(samplesProfile);

  useEffect(() => {
    let cancelled = false;
    const abortInitial = new AbortController();
    let pollAbort: AbortController | null = null;
    let pollChainTimeout: ReturnType<typeof setTimeout> | null = null;

    const samplesUrl = () => buildCompressorStatusSamplesUrl(compressorId, timeRange, samplesProfile);

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
      pollChainTimeout = window.setTimeout(() => void runPoll(), chartRefetchMs);
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
      pollChainTimeout = window.setTimeout(() => void runPoll(), chartRefetchMs + jitter);
    });

    return () => {
      cancelled = true;
      abortInitial.abort();
      pollAbort?.abort();
      if (pollChainTimeout !== null) window.clearTimeout(pollChainTimeout);
    };
  }, [compressorId, timeRange, samplesProfile]);

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

  const oscilloscopeStride = oscilloscopeStrideForProfile(timeRange, samplesProfile);

  const sampleHistoryForOscilloscope: StatusEvent[] = useMemo(
    () =>
      decimateSamplesForOscilloscope(
        samplesWithLiveTail.map((s) => ({ time: s.time, status: s.status })),
        oscilloscopeStride
      ),
    [samplesWithLiveTail, oscilloscopeStride]
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
      <PaneTerminalHeader label="STATUS TIMELINE">
        <PollingStatusLight
          lastUpdatedAt={lastFetchSuccessAt}
          expectedIntervalMs={chartRefetchMs}
          ariaLabel="Compressor timeline chart data freshness"
          tooltipDetailLines={statusTooltipLines}
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
                timeAxisStorageKey={`compressor-${compressorId}-status-timeline`}
              />
            </div>
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
