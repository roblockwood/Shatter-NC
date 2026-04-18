import React, { useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { MachineStatus } from '../../hooks/useWebSocket';
import type { PanelData } from './PanelPane';
import { MachineMiniPanel } from './MachineMiniPanel';
import {
  useRecentMachineProductionRuns,
  type LatestProductionRunRow,
} from '../../hooks/useLatestMachineProductionRun';
import { useRecentPrd3StatusIntervals } from '../../hooks/useRecentPrd3StatusIntervals';
import { fastPollLastSuccessAt } from '../../utils/machinePollFreshness';
import {
  activeProgramNameFromMachine,
  machineSummaryStatusDisplay,
  machineSummaryStatusValueClass,
} from '../../utils/machineSummaryStatus';
import { alarmStopLevel } from '../../utils/alarmStopLevel';
import { formatDurationHMS } from '../../utils/formatDuration';
import { formatMemMode, formatMemOperationStatus } from '../../utils/machineMemLabels';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import { ProductionRunCompactSummary } from './ProductionRunCompactSummary';
import '../MachineCard.css';
import './AlarmPane.css';
import './MachineOverviewPane.css';

interface MachineOverviewPaneProps {
  machine: MachineStatus;
}

function prd3LineStatusClass(status: string | null): string {
  const s = (status || '').toLowerCase();
  if (s === 'operating') return 'text-success';
  if (s === 'error') return 'text-error';
  if (s === 'stopped' || s === 'off') return 'text-dim';
  if (s === 'standby') return 'text-warning';
  return '';
}

function shortTime(iso: string): string {
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

function alarmLineClass(alarm: { stop_level?: string }): string {
  const lvl = alarmStopLevel(alarm);
  if (lvl >= 4) return 'text-error';
  if (lvl >= 3) return 'text-warning';
  return 'text-dim';
}

export const MachineOverviewPane: React.FC<MachineOverviewPaneProps> = ({ machine }) => {
  const navigate = useNavigate();
  const base = `/tablet/${machine.machine_id}`;
  const pollAt = fastPollLastSuccessAt(machine);
  const { runs, runsLoading } = useRecentMachineProductionRuns(machine.machine_id, 4);
  const { intervals: prd3Intervals, loading: prd3Loading } = useRecentPrd3StatusIntervals(
    machine.machine_id,
    8
  );
  const programLine = activeProgramNameFromMachine(machine);
  const allAlarms = machine.alarms || [];
  const criticalAlarms = allAlarms.filter((a) => alarmStopLevel(a) >= 4);
  const warningAlarms = allAlarms.filter((a) => alarmStopLevel(a) < 4);
  const sortedAlarms = useMemo(
    () => [...allAlarms].sort((a, b) => alarmStopLevel(b) - alarmStopLevel(a)),
    [allAlarms]
  );

  const go = useCallback(
    (slug: string) => {
      navigate(`${base}/${slug}`);
    },
    [navigate, base]
  );

  const partMode = machine.part_display_mode || 'parts';
  const panelData = (machine as MachineStatus & { panel?: PanelData | null }).panel;

  return (
    <div
      className="alarm-pane terminal-box machine-overview-pane"
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label="OVERVIEW">
        <PollingStatusLight
          lastUpdatedAt={pollAt}
          expectedIntervalMs={Math.max((machine.poll_interval_seconds ?? 5) * 1000, 1000)}
          ariaLabel="Machine data freshness"
        />
      </PaneTerminalHeader>

      <div className="terminal-box-content">
        <div className="machine-overview-pane-body machine-card-content">
          <section className="machine-overview-section" aria-labelledby="mov-status-h">
            <button
              id="mov-status-h"
              type="button"
              className="machine-overview-section-head"
              onClick={() => go('status')}
            >
              [ STATUS ]
            </button>
            <div className="machine-overview-detail">
              <div className="machine-row">
                <span className="label">NOW:</span>
                <span className={`value ${machineSummaryStatusValueClass(machine)}`}>
                  {machineSummaryStatusDisplay(machine)}
                </span>
              </div>
              {prd3Loading && prd3Intervals.length === 0 && (
                <div className="machine-overview-detail-muted">Loading PRD3 history…</div>
              )}
              {!prd3Loading && prd3Intervals.length === 0 && (
                <div className="machine-overview-detail-muted">No PRD3 intervals in window.</div>
              )}
              {prd3Intervals.map((iv, idx) => (
                <div key={`${iv.start_time}-${idx}`} className="machine-overview-prd3-line">
                  <span className="machine-overview-prd3-time">{shortTime(iv.start_time)}</span>
                  <span className={`machine-overview-prd3-status ${prd3LineStatusClass(iv.status)}`}>
                    {(iv.status || iv.label || '—').toUpperCase()}
                  </span>
                  <span className="machine-overview-prd3-dur">{formatDurationHMS(iv.duration_seconds)}</span>
                  {iv.program_no ? (
                    <span className="machine-overview-prd3-prog" title={iv.program_no}>
                      {truncateText(iv.program_no, 28)}
                    </span>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          <section className="machine-overview-section" aria-labelledby="mov-panel-h">
            <button
              id="mov-panel-h"
              type="button"
              className="machine-overview-section-head"
              onClick={() => go('panel')}
            >
              [ PANEL ]
            </button>
            <div className="machine-overview-detail">
              <MachineMiniPanel panelData={panelData} />
            </div>
          </section>

          <section className="machine-overview-section" aria-labelledby="mov-program-h">
            <button
              id="mov-program-h"
              type="button"
              className="machine-overview-section-head"
              onClick={() => go('program')}
            >
              [ PROGRAM ]
            </button>
            <div className="machine-overview-detail">
              <div className="terminal-kv-row">
                <span className="terminal-kv-label">ACTIVE</span>
                <span className="terminal-kv-value">{programLine || 'NONE'}</span>
              </div>
              <div className="terminal-kv-row">
                <span className="terminal-kv-label">CYCLE TIME</span>
                <span className="terminal-kv-value">{machine.cycle_time?.trim() ? machine.cycle_time : '—'}</span>
              </div>
              <div className="terminal-kv-row">
                <span className="terminal-kv-label">MEM MODE</span>
                <span className="terminal-kv-value">{formatMemMode(machine.mem_mode)}</span>
              </div>
              <div className="terminal-kv-row">
                <span className="terminal-kv-label">MEM OP</span>
                <span className="terminal-kv-value">{formatMemOperationStatus(machine.mem_operation_status)}</span>
              </div>
              {machine.power_on_hours?.trim() ? (
                <div className="terminal-kv-row">
                  <span className="terminal-kv-label">POWER ON</span>
                  <span className="terminal-kv-value text-dim">{machine.power_on_hours}</span>
                </div>
              ) : null}
            </div>
          </section>

          <section className="machine-overview-section" aria-labelledby="mov-runs-h">
            <button
              id="mov-runs-h"
              type="button"
              className="machine-overview-section-head"
              onClick={() => go('runs')}
            >
              [ PRODUCTION RUNS ]
            </button>
            <div className="machine-overview-detail">
              {runsLoading && runs.length === 0 && (
                <div className="machine-overview-detail-muted">Loading runs…</div>
              )}
              {!runsLoading && runs.length === 0 && (
                <div className="machine-overview-detail-muted">No recent runs (7d window).</div>
              )}
              {runs.map((run: LatestProductionRunRow, idx) => (
                <div key={`${run.run_start}-${run.run_end}-${idx}`} className="machine-overview-run-block">
                  <div className="production-run-summary" style={{ width: '100%' }}>
                    <ProductionRunCompactSummary
                      latestRun={run}
                      latestRunLoading={false}
                      partDisplayMode={partMode}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="machine-overview-section" aria-labelledby="mov-alarm-h">
            <button
              id="mov-alarm-h"
              type="button"
              className="machine-overview-section-head"
              onClick={() => go('alarms')}
            >
              [ ALARMS ]
            </button>
            <div className="machine-overview-detail">
              <div className="machine-row" style={{ padding: '2px 0', marginBottom: 'var(--spacing-xs)' }}>
                <span className="label">COUNT CRIT / WARN:</span>
                <span className="value">
                  <span className={criticalAlarms.length > 0 ? 'text-error' : ''}>{criticalAlarms.length}</span>
                  {' / '}
                  <span className={warningAlarms.length > 0 ? 'text-warning' : ''}>{warningAlarms.length}</span>
                </span>
              </div>
              {sortedAlarms.length === 0 ? (
                <div className="machine-overview-detail-muted">No active alarms.</div>
              ) : (
                sortedAlarms.map((alarm, idx) => (
                  <div key={`${alarm.code}-${idx}`} className="machine-overview-alarm-line">
                    <span className={alarmLineClass(alarm)}>
                      <strong>{alarm.code}</strong>
                      {' · '}
                      {truncateText(alarm.message || alarm.description || '—', 96)}
                    </span>
                  </div>
                ))
              )}
            </div>
          </section>

          <div className="machine-overview-link-row" role="group" aria-label="Tools and file manager">
            <button
              type="button"
              className="machine-overview-section-head machine-overview-section-head--inline"
              onClick={() => go('tools')}
            >
              [ TOOLS ]
            </button>
            <button
              type="button"
              className="machine-overview-section-head machine-overview-section-head--inline"
              onClick={() => go('files')}
            >
              [ FILES ]
            </button>
          </div>

          {machine.error ? (
            <section className="machine-overview-section machine-overview-span-full">
              <div className="machine-overview-detail text-error" style={{ fontSize: 'var(--font-xs)' }}>
                POLL ERROR: {truncateText(machine.error, 200)}
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <PaneTerminalFooter />
    </div>
  );
};
