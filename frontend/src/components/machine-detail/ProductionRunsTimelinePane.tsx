import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { API_BASE_URL } from '../../config/api';
import { earlierIsoTimestamp } from '../ui/pollingFreshness';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import './ProductionRunsTimelinePane.css';

interface RunSegment {
  status: string | null;
  status_code?: number | null;
  start_time: string;
  end_time: string;
  error_no?: string | null;
}

interface ProductionRun {
  program_no: string | null;
  run_start: string;
  run_end: string;
  cycles: number;
  segments: RunSegment[];
  part_count: number;
}

interface ProductionRunsTimelinePaneProps {
  machineId: number;
  /** Last successful fast CNC poll (ISO). Combined with API fetch time for the status light. */
  machineLastSuccessfulPollAt?: string | null;
}

type TimeRange = '1h' | '8h' | '24h' | '7d';

const SEGMENT_TOOLTIP_DELAY_MS = 100;

export const ProductionRunsTimelinePane: React.FC<ProductionRunsTimelinePaneProps> = ({
  machineId,
  machineLastSuccessfulPollAt,
}) => {
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);
  const statusLightLastUpdatedAt = useMemo(
    () => earlierIsoTimestamp(lastFetchSuccessAt, machineLastSuccessfulPollAt),
    [lastFetchSuccessAt, machineLastSuccessfulPollAt],
  );
  const [segmentTooltip, setSegmentTooltip] = useState<{ text: string; x: number; y: number } | null>(null);
  const segmentTooltipRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (segmentTooltipRef.current) {
        clearTimeout(segmentTooltipRef.current);
        segmentTooltipRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        setLoading(true);
        const endTime = new Date();
        const startTime = new Date(endTime);

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

        const resp = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/production-runs-timeline?start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}&limit=500&offset=0`
        );
        if (resp.ok) {
          const data: ProductionRun[] = await resp.json();
          const arr = Array.isArray(data) ? data : [];
          arr.sort((a, b) => new Date(b.run_start).getTime() - new Date(a.run_start).getTime());
          setRuns(arr);
          setLastFetchSuccessAt(new Date().toISOString());
        } else {
          setRuns([]);
        }
      } catch (e) {
        console.error('Error fetching production runs timeline:', e);
        setRuns([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRuns();
  }, [machineId, timeRange]);

  const formatTime = (value: string) => {
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleTimeString();
  };

  // Compute global min/max to normalize X positions
  const allTimes = runs.flatMap((r) => [new Date(r.run_start).getTime(), new Date(r.run_end).getTime()]);
  const minTime = allTimes.length ? Math.min(...allTimes) : 0;
  const maxTime = allTimes.length ? Math.max(...allTimes) : 1;
  const span = Math.max(1, maxTime - minTime);

  const getStatusClass = (status: string | null) => {
    const s = (status || '').toLowerCase();
    if (s === 'operating') return 'segment-operating';
    if (s === 'standby') return 'segment-standby';
    if (s === 'stopped') return 'segment-stopped';
    if (s === 'error') return 'segment-error';
    if (s === 'off') return 'segment-off';
    return 'segment-standby';
  };

  return (
    <div
      className="production-runs-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label="PRODUCTION RUNS">
        <PollingStatusLight
          lastUpdatedAt={statusLightLastUpdatedAt}
          expectedIntervalMs={120_000}
          ariaLabel="Production runs data freshness"
        />
      </PaneTerminalHeader>
      <div className="terminal-box-content">
        <div className="runs-controls">
          <div className="runs-range-controls">
            <button
              type="button"
              className={`runs-range-btn ${timeRange === '1h' ? 'active' : ''}`}
              onClick={() => setTimeRange('1h')}
            >
              [1H]
            </button>
            <button
              type="button"
              className={`runs-range-btn ${timeRange === '8h' ? 'active' : ''}`}
              onClick={() => setTimeRange('8h')}
            >
              [8H]
            </button>
            <button
              type="button"
              className={`runs-range-btn ${timeRange === '24h' ? 'active' : ''}`}
              onClick={() => setTimeRange('24h')}
            >
              [24H]
            </button>
            <button
              type="button"
              className={`runs-range-btn ${timeRange === '7d' ? 'active' : ''}`}
              onClick={() => setTimeRange('7d')}
            >
              [7D]
            </button>
          </div>
        </div>
        {loading ? (
          <div className="runs-loading">LOADING...</div>
        ) : runs.length === 0 ? (
          <div className="runs-empty">NO PRODUCTION RUNS</div>
        ) : (
          <div className="runs-timeline-wrapper">
            {runs.map((run, idx) => {
              const runStartMs = new Date(run.run_start).getTime();
              const runEndMs = new Date(run.run_end).getTime();
              const left = ((runStartMs - minTime) / span) * 100;
              const width = Math.max(2, ((runEndMs - runStartMs) / span) * 100);

              return (
                <div key={`${run.run_start}-${idx}`} className="run-row">
                  <div className="run-label">
                    <span className="run-program">{run.program_no || 'UNKNOWN'}</span>
                    <span className="run-meta">
                      {formatTime(run.run_start)} → {formatTime(run.run_end)} · {run.part_count} parts · {run.cycles} cycles
                    </span>
                  </div>
                  <div className="run-bar-track">
                    <div
                      className="run-bar"
                      style={{ left: `${left}%`, width: `${width}%` }}
                    >
                      {run.segments.map((seg, sIdx) => {
                        const sStartMs = new Date(seg.start_time).getTime();
                        const sEndMs = new Date(seg.end_time).getTime();
                        const sLeft = ((sStartMs - runStartMs) / (runEndMs - runStartMs || 1)) * 100;
                        const sWidth = Math.max(1, ((sEndMs - sStartMs) / (runEndMs - runStartMs || 1)) * 100);
                        const tooltipText = `${seg.status || 'unknown'} ${formatTime(seg.start_time)} → ${formatTime(seg.end_time)}`;
                        return (
                          <div
                            key={sIdx}
                            className={`run-segment ${getStatusClass(seg.status)}`}
                            style={{ left: `${sLeft}%`, width: `${sWidth}%` }}
                            title={tooltipText}
                            onMouseEnter={(e) => {
                              if (segmentTooltipRef.current) clearTimeout(segmentTooltipRef.current);
                              const target = e.currentTarget;
                              segmentTooltipRef.current = setTimeout(() => {
                                const rect = target.getBoundingClientRect();
                                setSegmentTooltip({
                                  text: tooltipText,
                                  x: rect.left + rect.width / 2,
                                  y: rect.top,
                                });
                              }, SEGMENT_TOOLTIP_DELAY_MS);
                            }}
                            onMouseLeave={() => {
                              if (segmentTooltipRef.current) {
                                clearTimeout(segmentTooltipRef.current);
                                segmentTooltipRef.current = null;
                              }
                              if (segmentTooltip) {
                                setSegmentTooltip(null);
                              }
                            }}
                          />
                        );
                      })}
                      <div className="run-bar-parts">
                        {run.part_count > 0 ? `${run.part_count} pcs` : ''}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      {segmentTooltip &&
        typeof document !== 'undefined' &&
        document.body &&
        createPortal(
          <div
            className="runs-segment-tooltip"
            style={{
              left: segmentTooltip.x,
              top: segmentTooltip.y,
            }}
          >
            {segmentTooltip.text}
          </div>,
          document.body
        )}
      <PaneTerminalFooter />
    </div>
  );
};

