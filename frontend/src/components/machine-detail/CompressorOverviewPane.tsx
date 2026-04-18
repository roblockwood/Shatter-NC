import React, { useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import type { CompressorStatus } from '../../hooks/useWebSocket';
import { useCompressorStatusHistoryPreview } from '../../hooks/useCompressorStatusHistoryPreview';
import {
  compressorCardStatusDisplay,
  compressorCardStatusValueClass,
  compressorCardTelemetryLines,
} from '../../utils/compressorCardSummary';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import '../MachineCard.css';
import './AlarmPane.css';
import './MachineOverviewPane.css';

export interface CompressorOverviewPaneProps {
  compressor: CompressorStatus;
  /** When set (tablet kiosk), summary rows navigate to sibling panes under this base path. Dashboard embed omits this. */
  tabletRouteBase?: string;
}

function shortEventTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function truncateText(s: string, maxLen: number): string {
  const t = s.trim();
  if (t.length <= maxLen) return t;
  return `${t.slice(0, Math.max(0, maxLen - 1))}…`;
}

export const CompressorOverviewPane: React.FC<CompressorOverviewPaneProps> = ({
  compressor,
  tabletRouteBase,
}) => {
  const navigate = useNavigate();
  const pollTs = compressor.last_successful_poll_at || compressor.poll_timestamp;

  const { psiLine, tempLine, controllerDetail } = useMemo(
    () => compressorCardTelemetryLines(compressor),
    [compressor]
  );

  const alarmCount = compressor.alarms?.length ?? 0;
  const alarms = compressor.alarms ?? [];
  const { events: recentStatusEvents, loading: historyLoading } = useCompressorStatusHistoryPreview(
    compressor.compressor_id,
    10
  );

  const go = useCallback(
    (slug: string) => {
      if (!tabletRouteBase) return;
      navigate(`${tabletRouteBase}/${slug}`);
    },
    [navigate, tabletRouteBase]
  );

  const Row = ({
    slug,
    label,
    valueClassName,
    children,
  }: {
    slug: string;
    label: string;
    valueClassName?: string;
    children: React.ReactNode;
  }) => {
    const inner = (
      <>
        <span className="label">{label}</span>
        <span className={`value ${valueClassName ?? ''}`.trim()}>{children}</span>
      </>
    );

    if (tabletRouteBase) {
      return (
        <button
          type="button"
          className="compressor-overview-nav-row machine-row machine-row-hoverable"
          onClick={() => go(slug)}
        >
          {inner}
        </button>
      );
    }

    return (
      <div className="machine-row">
        <span className="label">{label}</span>
        <span className={`value ${valueClassName ?? ''}`.trim()}>{children}</span>
      </div>
    );
  };

  return (
    <div
      className="alarm-pane terminal-box compressor-terminal-pane compressor-overview-pane machine-overview-pane"
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label="COMPRESSOR OVERVIEW">
        <PollingStatusLight
          lastUpdatedAt={pollTs}
          expectedIntervalMs={Math.max((compressor.poll_interval_seconds ?? 5) * 1000, 1000)}
          ariaLabel="Compressor telemetry freshness"
        />
      </PaneTerminalHeader>

      <div className="terminal-box-content">
        <div className="machine-overview-pane-body machine-card-content">
          <section className="machine-overview-section" aria-labelledby="cov-summary-h">
            {tabletRouteBase ? (
              <button
                id="cov-summary-h"
                type="button"
                className="machine-overview-section-head"
                onClick={() => go('panel')}
              >
                [ SUMMARY ]
              </button>
            ) : (
              <div id="cov-summary-h" className="machine-overview-section-head" style={{ cursor: 'default' }}>
                [ SUMMARY ]
              </div>
            )}
            <div className="machine-overview-detail">
              <Row slug="panel" label="STATUS:" valueClassName={compressorCardStatusValueClass(compressor)}>
                {compressorCardStatusDisplay(compressor)}
              </Row>

              <Row slug="status" label="OPERATION:" valueClassName="compressor-card-operation-value">
                {controllerDetail || '—'}
              </Row>

              <Row slug="psi" label="PSI:">
                {psiLine}
              </Row>

              <Row slug="temp" label="TEMP:">
                {tempLine}
              </Row>

              <Row slug="alarms" label="ALARMS:">
                {alarmCount}
              </Row>
            </div>
          </section>

          <section className="machine-overview-section" aria-labelledby="cov-hist-h">
            {tabletRouteBase ? (
              <button
                id="cov-hist-h"
                type="button"
                className="machine-overview-section-head"
                onClick={() => go('history')}
              >
                [ RECENT STATE ]
              </button>
            ) : (
              <div id="cov-hist-h" className="machine-overview-section-head" style={{ cursor: 'default' }}>
                [ RECENT STATE ]
              </div>
            )}
            <div className="machine-overview-detail">
              {historyLoading && recentStatusEvents.length === 0 && (
                <div className="machine-overview-detail-muted">Loading history…</div>
              )}
              {!historyLoading && recentStatusEvents.length === 0 && (
                <div className="machine-overview-detail-muted">No transitions recorded.</div>
              )}
              {recentStatusEvents.slice(0, 8).map((ev, idx) => (
                <div key={`${ev.time}-${idx}`} className="machine-overview-prd3-line">
                  <span className="machine-overview-prd3-time">{shortEventTime(ev.time)}</span>
                  <span className="machine-overview-prd3-status text-success">{ev.status}</span>
                  {ev.previous_status ? (
                    <span className="machine-overview-prd3-prog text-dim" title={`was: ${ev.previous_status}`}>
                      ← {ev.previous_status}
                    </span>
                  ) : null}
                </div>
              ))}
              <div className="machine-overview-detail-muted" style={{ marginTop: 'var(--spacing-xs)' }}>
                Updates every minute.
              </div>
            </div>
          </section>

          {alarms.length > 0 ? (
            <section className="machine-overview-section" aria-labelledby="cov-alarm-detail-h">
              {tabletRouteBase ? (
                <button
                  id="cov-alarm-detail-h"
                  type="button"
                  className="machine-overview-section-head"
                  onClick={() => go('alarms')}
                >
                  [ ALARM DETAIL ]
                </button>
              ) : (
                <div id="cov-alarm-detail-h" className="machine-overview-section-head" style={{ cursor: 'default' }}>
                  [ ALARM DETAIL ]
                </div>
              )}
              <div className="machine-overview-detail">
                {alarms.map((a, idx) => (
                  <div key={`${a.code}-${idx}`} className="machine-overview-alarm-line">
                    <span className={a.severity?.toLowerCase().includes('crit') ? 'text-error' : 'text-warning'}>
                      <strong>{a.code}</strong>
                      {' · '}
                      {truncateText(a.message || '—', 96)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <div className="machine-footer" style={{ marginTop: 'var(--spacing-sm)' }}>
        <div className="machine-timestamp" style={{ width: '100%', textAlign: 'right' }}>
          {compressor.is_online ? 'LAST UPDATE' : 'LAST SEEN'}: {new Date(pollTs).toLocaleTimeString()}
        </div>
      </div>

      <PaneTerminalFooter />
    </div>
  );
};
