import React, { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from '../../config/api';
import { useBetaMode } from '../../hooks/useBetaMode';
import { earlierIsoTimestamp } from '../ui/pollingFreshness';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import './StatusHistoryPane.css';

interface PRD3StatusInterval {
  status: string | null;
  status_code?: number | null;
  program_no?: string | null;
  error_no?: string | null;
  start_time: string;
  end_time: string | null;
  label: string;
  detail?: string | null;
   duration_seconds?: number | null;
}

interface StatusHistoryPaneProps {
  machineId: number;
  /** Last successful fast CNC poll (ISO). Combined with API fetch time for the status light. */
  machineLastSuccessfulPollAt?: string | null;
}

export const StatusHistoryPane: React.FC<StatusHistoryPaneProps> = ({
  machineId,
  machineLastSuccessfulPollAt,
}) => {
  const { isBetaMode } = useBetaMode();
  const [intervals, setIntervals] = useState<PRD3StatusInterval[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilters, setStatusFilters] = useState<Record<string, boolean>>({
    off: true,
    standby: true,
    operating: true,
    stopped: true,
    error: true,
  });
  const [programSearch, setProgramSearch] = useState('');
  const [statusTotals, setStatusTotals] = useState<Record<string, number>>({});
  const [colorMode, setColorMode] = useState<boolean>(() => {
    return localStorage.getItem('statusHistoryColorMode') === 'true';
  });
  const PAGE_SIZE = 100;
  const [page, setPage] = useState(0);
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);
  const statusLightLastUpdatedAt = useMemo(
    () => earlierIsoTimestamp(lastFetchSuccessAt, machineLastSuccessfulPollAt),
    [lastFetchSuccessAt, machineLastSuccessfulPollAt],
  );

  useEffect(() => {
    localStorage.setItem('statusHistoryColorMode', String(colorMode));
  }, [colorMode]);

  useEffect(() => {
    const fetchStatusHistory = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/prd3-status-history?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`
        );
        if (response.ok) {
          const data: PRD3StatusInterval[] = await response.json();
          const arr = Array.isArray(data) ? data : [];
          setIntervals(arr);
          setLastFetchSuccessAt(new Date().toISOString());

          // Aggregate total duration per status over the fetched intervals
          const totals: Record<string, number> = {};
          for (const interval of arr) {
            const key = (interval.status || '').toLowerCase();
            if (!key) continue;
            const dur = interval.duration_seconds ?? 0;
            if (!Number.isFinite(dur)) continue;
            totals[key] = (totals[key] || 0) + dur;
          }
          setStatusTotals(totals);
        } else {
          setIntervals([]);
          setStatusTotals({});
        }
      } catch (err) {
        console.error('Error fetching PRD3 status history:', err);
        setIntervals([]);
        setStatusTotals({});
      } finally {
        setLoading(false);
      }
    };

    fetchStatusHistory();
    const interval = setInterval(fetchStatusHistory, 60000);
    return () => clearInterval(interval);
  }, [machineId, page]);

  const formatDateTime = (value: string | null) => {
    if (!value) return '—';
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleString();
  };

  const formatDuration = (seconds: number | null | undefined) => {
    if (seconds == null || isNaN(seconds)) return '—';
    const total = Math.max(0, Math.floor(seconds));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const toggleStatus = (key: string) => {
    setStatusFilters((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const normalizedSearch = programSearch.trim().toLowerCase();
  const filteredIntervals = intervals.filter((interval) => {
    const statusKey = (interval.status || '').toLowerCase();
    if (statusKey && statusFilters.hasOwnProperty(statusKey) && !statusFilters[statusKey]) {
      return false;
    }
    if (normalizedSearch) {
      const prog = (interval.program_no || '').toLowerCase();
      return prog.includes(normalizedSearch);
    }
    return true;
  });

  const hasPrevPage = page > 0;
  const hasNextPage = intervals.length === PAGE_SIZE;

  return (
    <div
      className="status-history-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label="STATUS HISTORY">
        {isBetaMode && (
          <button
            type="button"
            className={`status-history-color-toggle ${colorMode ? 'active' : ''}`}
            onClick={() => setColorMode((prev) => !prev)}
          >
            [COLOR]
          </button>
        )}
        <PollingStatusLight
          lastUpdatedAt={statusLightLastUpdatedAt}
          expectedIntervalMs={60_000}
          ariaLabel="Status history data freshness"
        />
      </PaneTerminalHeader>
      <div className="terminal-box-content">
        {loading ? (
          <div className="status-history-loading">LOADING...</div>
        ) : intervals.length === 0 ? (
          <div className="status-history-empty">NO PRD3 STATUS DATA</div>
        ) : (
          <div className="status-history-table-wrapper">
            <div className="status-history-summary">
              <div className="status-summary-title">T-7 STATUS TIME</div>
              <div className="status-summary-rows">
                <div className="status-summary-row">
                  <span className="status-summary-label">RUN:</span>
                  <span className="status-summary-value">
                    {formatDuration(statusTotals['operating'] || 0)}
                  </span>
                </div>
                <div className="status-summary-row">
                  <span className="status-summary-label">STANDBY:</span>
                  <span className="status-summary-value">
                    {formatDuration(statusTotals['standby'] || 0)}
                  </span>
                </div>
                <div className="status-summary-row">
                  <span className="status-summary-label">STOPPED:</span>
                  <span className="status-summary-value">
                    {formatDuration(statusTotals['stopped'] || 0)}
                  </span>
                </div>
                <div className="status-summary-row">
                  <span className="status-summary-label">OFF:</span>
                  <span className="status-summary-value">
                    {formatDuration(statusTotals['off'] || 0)}
                  </span>
                </div>
                <div className="status-summary-row">
                  <span className="status-summary-label">ERROR:</span>
                  <span className="status-summary-value">
                    {formatDuration(statusTotals['error'] || 0)}
                  </span>
                </div>
              </div>
            </div>
            <div className="status-history-controls">
              <div className="status-filter-group">
                {[
                  { key: 'operating', label: 'RUN' },
                  { key: 'standby', label: 'STANDBY' },
                  { key: 'stopped', label: 'STOPPED' },
                  { key: 'off', label: 'OFF' },
                  { key: 'error', label: 'ERROR' },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    type="button"
                    className={`status-filter-pill ${
                      statusFilters[key] ? 'status-filter-on' : 'status-filter-off'
                    }`}
                    onClick={() => toggleStatus(key)}
                  >
                    [{label}]
                  </button>
                ))}
              </div>
              <div className="status-search">
                <span className="status-search-label">PROGRAM:</span>
                <input
                  type="text"
                  value={programSearch}
                  onChange={(e) => setProgramSearch(e.target.value)}
                  placeholder="0004"
                  className="status-search-input"
                />
              </div>
            </div>
            <table className="status-history-table">
              <thead>
                <tr className="status-history-header-row">
                  <th>STATUS</th>
                  <th>START</th>
                  <th>END</th>
                  <th>DURATION</th>
                  <th>DETAIL</th>
                </tr>
              </thead>
              <tbody>
                {filteredIntervals.map((interval, idx) => (
                  <tr
                    key={`${interval.start_time}-${idx}`}
                    className={`status-history-row status-${(interval.status || '').toLowerCase()} ${
                      isBetaMode && colorMode ? 'status-colored' : ''
                    }`}
                  >
                    <td>{interval.label || interval.status || 'UNKNOWN'}</td>
                    <td>{formatDateTime(interval.start_time)}</td>
                    <td>{formatDateTime(interval.end_time)}</td>
                    <td>{formatDuration(interval.duration_seconds ?? undefined)}</td>
                    <td>{interval.detail ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
          </div>
        )}
      </div>
      <PaneTerminalFooter />
    </div>
  );
};

