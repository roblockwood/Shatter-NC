import React, { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from '../../config/api';
import { asciiFooterLine, asciiHeaderLeft } from '../../utils/terminalFrame';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import './AlarmPane.css';
import './StatusHistoryPane.css';

interface StatusEventRow {
  time: string;
  compressor_id: number;
  status: string;
  previous_status?: string | null;
  metrics?: Record<string, unknown> | null;
}

const PAGE_SIZE = 100;
const COMPRESSOR_HISTORY_REFETCH_MS = 60_000;

interface CompressorStatusHistoryPaneProps {
  compressorId: number;
  liveStatus?: string;
  isOnline?: boolean;
}

export const CompressorStatusHistoryPane: React.FC<CompressorStatusHistoryPaneProps> = ({
  compressorId,
  liveStatus,
  isOnline,
}) => {
  const [page, setPage] = useState(0);
  const [events, setEvents] = useState<StatusEventRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);

  useEffect(() => {
    setPage(0);
  }, [compressorId]);

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

  useEffect(() => {
    let cancelled = false;
    const abortInitial = new AbortController();

    const historyUrl = () =>
      `${API_BASE_URL}/api/compressors/${compressorId}/status-history?limit=${PAGE_SIZE}&offset=${
        page * PAGE_SIZE
      }`;

    const load = (signal: AbortSignal, showLoading: boolean) => {
      if (showLoading) {
        setLoading(true);
        setError(null);
      }
      fetch(historyUrl(), { signal, cache: 'no-store' })
        .then((r) => {
          if (!r.ok) throw new Error(r.statusText);
          return r.json();
        })
        .then((hist) => {
          if (cancelled) return;
          setEvents(Array.isArray(hist) ? hist : []);
          setLastFetchSuccessAt(new Date().toISOString());
          setError(null);
        })
        .catch((e) => {
          if (e.name === 'AbortError' || cancelled) return;
          if (showLoading) {
            setError(e.message || 'Failed to load history');
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
    }, COMPRESSOR_HISTORY_REFETCH_MS);

    return () => {
      cancelled = true;
      abortInitial.abort();
      window.clearInterval(intervalId);
    };
  }, [compressorId, page]);

  const hasPrevPage = page > 0;
  const hasNextPage = events.length === PAGE_SIZE;

  return (
    <div
      className="alarm-pane terminal-box compressor-terminal-pane compressor-timeline-pane"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>{asciiHeaderLeft('Status history')}</span>
            <div className="pane-header-right-actions">
              <PollingStatusLight
                lastUpdatedAt={lastFetchSuccessAt}
                expectedIntervalMs={COMPRESSOR_HISTORY_REFETCH_MS}
                ariaLabel="Compressor status history data freshness"
                tooltipDetailLines={statusTooltipLines}
              />
              <span>┐</span>
            </div>
          </div>
        </div>
      </div>

      <div className="terminal-box-content">
        <div className="compressor-timeline-pane-inner compressor-history-pane-inner">
          {loading && <p className="text-dim">LOADING…</p>}
          {error && <p className="compressor-error">{error}</p>}

          {!loading && !error && events.length === 0 && (
            <p className="text-dim">No status transitions on this page.</p>
          )}

          {!loading && !error && events.length > 0 && (
            <>
              <ul className="compressor-timeline-list compressor-history-list">
                {events.map((ev, idx) => (
                  <li key={`${ev.time}-${idx}`}>
                    <span className="compressor-timeline-time">{new Date(ev.time).toLocaleString()}</span>
                    <span className="compressor-timeline-status">
                      {ev.previous_status != null ? `${ev.previous_status} → ` : ''}
                      {ev.status}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="status-history-pagination">
                <button
                  type="button"
                  className="status-page-btn"
                  disabled={!hasPrevPage || loading}
                  onClick={(e) => {
                    e.stopPropagation();
                    setPage((p) => Math.max(0, p - 1));
                  }}
                >
                  [PREV {PAGE_SIZE}]
                </button>
                <span className="status-page-info">PAGE {page + 1}</span>
                <button
                  type="button"
                  className="status-page-btn"
                  disabled={!hasNextPage || loading}
                  onClick={(e) => {
                    e.stopPropagation();
                    setPage((p) => p + 1);
                  }}
                >
                  [NEXT {PAGE_SIZE}]
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="terminal-box-footer">{asciiFooterLine(42)}</div>
    </div>
  );
};
