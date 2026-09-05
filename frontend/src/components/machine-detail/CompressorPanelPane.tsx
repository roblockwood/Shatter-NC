import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import type { CompressorStatus } from '../../hooks/useWebSocket';
import {
  asRecord,
  readLedData,
  readOutletTempLine,
  readPressureLine,
  readSigmaPanel,
} from '../../utils/compressorTelemetry';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import './AlarmPane.css';
import './CompressorPanelPane.css';

interface CompressorPanelPaneProps {
  compressor: CompressorStatus;
}

type LedTone = 'green' | 'amber' | 'red' | 'blue';

type TileIconId =
  | 'fault'
  | 'com'
  | 'maint'
  | 'power'
  | 'volt'
  | 'load'
  | 'idle'
  | 'remote'
  | 'clock'
  | 'link';

/** LED false = healthy, true = fault; undefined = no data yet (dim). */
function healthOkWhenClear(isFault: boolean | undefined): boolean | undefined {
  if (isFault === true) return false;
  if (isFault === false) return true;
  return undefined;
}

/** Maintenance: false = OK, true = due; undefined = unknown. */
function healthOkWhenNotDue(due: boolean | undefined): boolean | undefined {
  if (due === true) return false;
  if (due === false) return true;
  return undefined;
}

/** Flat SVG glyphs (currentColor); sized by .cp-svg-icon */
function TileIcon({ id }: { id: TileIconId }) {
  const c = 'cp-svg-icon';
  switch (id) {
    case 'fault':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <polyline
            points="2,16 6,8 10,14 14,6 18,12 22,9"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinejoin="miter"
            strokeLinecap="square"
          />
        </svg>
      );
    case 'com':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <polyline
            points="2,14 5,9 8,12 11,7 14,11 17,9 22,12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="miter"
          />
          <line x1="2" y1="17" x2="22" y2="17" stroke="currentColor" strokeWidth="2" />
        </svg>
      );
    case 'maint':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <path
            fill="currentColor"
            d="M14.7 3 L16.2 4.5 L13.5 7.2 L15 8.7 L17.7 6 L19.2 7.5 L11.2 15.5 C10.4 16.3 9 16.3 8.2 15.5 L7.5 14.8 C6.7 14 6.7 12.6 7.5 11.8 L14.7 3 Z M5 19 L9 15 L11 17 L7 21 L5 19 Z"
          />
        </svg>
      );
    case 'power':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <path fill="currentColor" d="M13 2 L10 12 L14 12 L11 22 L18 9 L13 9 L13 2 Z" />
        </svg>
      );
    case 'volt':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="2" />
          <line x1="6" y1="12" x2="18" y2="12" stroke="currentColor" strokeWidth="2" />
        </svg>
      );
    case 'load':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <rect x="4" y="14" width="4" height="6" fill="currentColor" />
          <rect x="10" y="10" width="4" height="10" fill="currentColor" />
          <rect x="16" y="6" width="4" height="14" fill="currentColor" />
        </svg>
      );
    case 'idle':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="2" />
          <line x1="8" y1="12" x2="16" y2="12" stroke="currentColor" strokeWidth="2" />
        </svg>
      );
    case 'remote':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <rect x="5" y="7" width="14" height="12" fill="none" stroke="currentColor" strokeWidth="2" />
          <path fill="currentColor" d="M12 9 L8 13 H16 L12 9 Z" />
        </svg>
      );
    case 'clock':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2" />
          <line x1="12" y1="12" x2="12" y2="7" stroke="currentColor" strokeWidth="2" />
          <line x1="12" y1="12" x2="16" y2="12" stroke="currentColor" strokeWidth="2" />
        </svg>
      );
    case 'link':
      return (
        <svg className={c} viewBox="0 0 24 24" aria-hidden>
          <path
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            d="M8 8v8M16 8v8M11 12H8M16 12h3"
          />
        </svg>
      );
    default:
      return null;
  }
}

type TileVisual =
  /** Green when OK, colored when not; dim when unknown (no LED data yet). */
  | { mode: 'health'; ok: boolean | undefined; badTone: LedTone }
  /** Lit with tone only when active; dim when off (e.g. power, load). */
  | { mode: 'active'; active: boolean; tone: LedTone };

type IconTone = 'off' | LedTone;

function statusTileLedClass(visual: TileVisual): { ledClass: string; iconTone: IconTone } {
  if (visual.mode === 'health') {
    if (visual.ok === true) {
      return {
        ledClass: 'cp-tile-led cp-tile-led--on cp-tile-led--tone-green',
        iconTone: 'green',
      };
    }
    if (visual.ok === false) {
      return {
        ledClass: `cp-tile-led cp-tile-led--on cp-tile-led--tone-${visual.badTone}`,
        iconTone: visual.badTone,
      };
    }
    return { ledClass: 'cp-tile-led cp-tile-led--off', iconTone: 'off' };
  }
  if (visual.active) {
    return {
      ledClass: `cp-tile-led cp-tile-led--on cp-tile-led--tone-${visual.tone}`,
      iconTone: visual.tone,
    };
  }
  return { ledClass: 'cp-tile-led cp-tile-led--off', iconTone: 'off' };
}

const CP_TILE_TOOLTIP_SHOW_MS = 80;

function StatusTile({
  icon,
  label,
  tooltip,
  visual,
}: {
  icon: TileIconId;
  label: string;
  /** Shown in themed hover popover (split on " — " into title + body when present). */
  tooltip: string;
  visual: TileVisual;
}) {
  const { ledClass, iconTone } = statusTileLedClass(visual);
  const anchorRef = useRef<HTMLDivElement>(null);
  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [hoverOpen, setHoverOpen] = useState(false);
  const [tipPos, setTipPos] = useState<{ top: number; left: number; flip: boolean } | null>(null);
  const tipId = useId();

  const dashSep = ' — ';
  const sepIdx = tooltip.indexOf(dashSep);
  const tipTitle = sepIdx >= 0 ? tooltip.slice(0, sepIdx) : label;
  const tipBody = sepIdx >= 0 ? tooltip.slice(sepIdx + dashSep.length) : tooltip;

  const clearShowTimer = () => {
    if (showTimerRef.current != null) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
  };

  useLayoutEffect(() => {
    if (!hoverOpen) return;
    const update = () => {
      const el = anchorRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const flip = r.top < 100;
      setTipPos({
        top: flip ? r.bottom : r.top,
        left: r.left + r.width / 2,
        flip,
      });
    };
    update();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [hoverOpen, tooltip]);

  useEffect(() => {
    if (!hoverOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setHoverOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [hoverOpen]);

  useEffect(() => () => clearShowTimer(), []);

  const handleShow = () => {
    clearShowTimer();
    showTimerRef.current = setTimeout(() => setHoverOpen(true), CP_TILE_TOOLTIP_SHOW_MS);
  };

  const handleHide = () => {
    clearShowTimer();
    setHoverOpen(false);
  };

  const displayTipPos = hoverOpen ? tipPos : null;

  const tooltipEl =
    hoverOpen && displayTipPos != null ? (
      <div
        id={tipId}
        role="tooltip"
        className="cp-tile-tooltip"
        style={{
          position: 'fixed',
          top: displayTipPos.top,
          left: displayTipPos.left,
          transform: displayTipPos.flip
            ? 'translate(-50%, 8px)'
            : 'translate(-50%, calc(-100% - 8px))',
        }}
      >
        <div className="cp-tile-tooltip__title">{tipTitle}</div>
        <div className="cp-tile-tooltip__body">{tipBody}</div>
      </div>
    ) : null;

  return (
    <>
      <div
        ref={anchorRef}
        className="cp-tile cp-tile--hint"
        data-cp-icon-tone={iconTone}
        tabIndex={0}
        aria-label={label}
        aria-describedby={hoverOpen && tipPos != null ? tipId : undefined}
        onMouseEnter={handleShow}
        onMouseLeave={handleHide}
        onFocus={handleShow}
        onBlur={handleHide}
      >
        <span className={ledClass} aria-hidden />
        <span className="cp-tile-icon-wrap">
          <TileIcon id={icon} />
        </span>
        <span className="cp-tile-label">{label}</span>
      </div>
      {tooltipEl != null ? createPortal(tooltipEl, document.body) : null}
    </>
  );
}

export const CompressorPanelPane: React.FC<CompressorPanelPaneProps> = ({ compressor }) => {
  const metrics = compressor.metrics || {};
  const operational = asRecord(metrics.operational);
  const sigma = readSigmaPanel(operational);
  const led = readLedData(metrics.led_data);

  const pollTs = compressor.last_successful_poll_at || compressor.poll_timestamp;
  const intervalS = compressor.poll_interval_seconds ?? 30;

  const pressure = readPressureLine(operational);
  const temp = readOutletTempLine(operational);
  const clock = sigma.panelClock?.trim() || '—';

  const statusLine =
    sigma.systemStatusDisplay?.trim() ||
    (typeof operational?.compressorState === 'string' ? operational.compressorState : '') ||
    compressor.status ||
    '—';

  const kl = sigma.keyLabel?.trim() || 'Key';
  const kt = sigma.keyToggle?.trim() || '—';
  const keyCode = sigma.keyCode?.trim() || '—';
  const keyRight = sigma.keyRight?.trim() || '—';

  const runH = sigma.runHoursDisplay?.trim();
  const loadH = sigma.loadHoursDisplay?.trim();
  const maintH = sigma.maintenanceHoursDisplay?.trim();

  const telemetryOk: boolean | undefined = compressor.is_online;

  const dash = '─'.repeat(28);

  return (
    <div
      className="alarm-pane terminal-box compressor-terminal-pane compressor-panel-pane"
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label="COMPRESSOR PANEL">
        <PollingStatusLight
          lastUpdatedAt={pollTs}
          expectedIntervalMs={Math.max(intervalS, 10) * 1000}
          ariaLabel="Compressor panel data freshness"
        />
      </PaneTerminalHeader>

      <div className="terminal-box-content">
        <div className="compressor-panel-body">
        <div className="compressor-panel-lcd-bezel">
          <div className="cp-lcd-header">
            <span className="cp-lcd-header-metric">{pressure}</span>
            <span className="cp-lcd-header-metric">{clock}</span>
            <span className="cp-lcd-header-metric">{temp}</span>
          </div>
          <div className="cp-lcd-body" aria-label="Compressor display">
            <div className="cp-lcd-section">
              <p className="cp-lcd-status-word">{statusLine}</p>
            </div>
            <pre className="cp-lcd-dash">{dash}</pre>
            <div className="cp-lcd-section cp-lcd-split">
              <div className="cp-lcd-split-col">
                {kl} - {kt}
              </div>
              <div className="cp-lcd-split-col cp-lcd-split-col--right">
                {keyCode} - {keyRight}
              </div>
            </div>
            <pre className="cp-lcd-dash">{dash}</pre>
            <div className="cp-lcd-hours-row" aria-label="Run, load, and maintenance hours">
              <span className="cp-lcd-hours-col cp-lcd-hours-col--left">
                {runH ? `Run ${runH}` : '—'}
              </span>
              <span className="cp-lcd-hours-col cp-lcd-hours-col--center">
                {loadH ? `Load ${loadH}` : '—'}
              </span>
              <span className="cp-lcd-hours-col cp-lcd-hours-col--right">
                {maintH ? `Maint in ${maintH}` : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="cp-icon-strip" aria-label="Status indicators">
          <StatusTile
            icon="fault"
            label="FLT"
            tooltip="Fault (FLT) — Kaeser SC2 fault LED. Green: no fault. Red: controller reports a fault."
            visual={{ mode: 'health', ok: healthOkWhenClear(led.error), badTone: 'red' }}
          />
          <StatusTile
            icon="com"
            label="COM"
            tooltip="Communication (COM) — SC2 comm-error LED. Green: OK. Red: communication fault reported."
            visual={{ mode: 'health', ok: healthOkWhenClear(led.comError), badTone: 'red' }}
          />
          <StatusTile
            icon="maint"
            label="SVC"
            tooltip="Service (SVC) — Maintenance / service due LED. Green: not due. Amber: maintenance due."
            visual={{ mode: 'health', ok: healthOkWhenNotDue(led.maintenanceDue), badTone: 'amber' }}
          />
          <StatusTile
            icon="power"
            label="PWR"
            tooltip="Power (PWR) — SC2 power-on LED. Green: power on. Dim: power off or LED state unknown."
            visual={{ mode: 'active', active: !!led.powerOn, tone: 'green' }}
          />
          <StatusTile
            icon="volt"
            label="VLT"
            tooltip="Voltage (VLT) — Supply / voltage fault LED (not a live voltage readout). Green: OK. Amber: voltage fault."
            visual={{ mode: 'health', ok: healthOkWhenClear(led.errorVoltage), badTone: 'amber' }}
          />
          <StatusTile
            icon="load"
            label="LOAD"
            tooltip="Load (LOAD) — Compressor on load (SC2 load LED). Amber: signaling load. Dim: not on load."
            visual={{ mode: 'active', active: !!led.load, tone: 'amber' }}
          />
          <StatusTile
            icon="idle"
            label="IDLE"
            tooltip="Idle (IDLE) — SC2 idle LED. Blue: idle. Dim: not idle."
            visual={{ mode: 'active', active: !!led.idle, tone: 'blue' }}
          />
          <StatusTile
            icon="remote"
            label="REM"
            tooltip="Remote (REM) — Remote operation enabled (SC2 remote LED). Green: remote on. Dim: off or unknown."
            visual={{ mode: 'active', active: !!led.remoteEnabled, tone: 'green' }}
          />
          <StatusTile
            icon="clock"
            label="CLK"
            tooltip="Clock (CLK) — SC2 clock LED (per controller/HMI mapping). Green: active. Dim: off or unknown."
            visual={{ mode: 'active', active: !!led.clockEnabled, tone: 'green' }}
          />
          <StatusTile
            icon="link"
            label="NET"
            tooltip="Telemetry (NET) — Shatter link: receiving compressor status from the backend (not a physical machine LED). Green: online. Red: offline."
            visual={{
              mode: 'health',
              ok: telemetryOk === true ? true : telemetryOk === false ? false : undefined,
              badTone: 'red',
            }}
          />
        </div>
        </div>

        {metrics.mqtt_stale === true && (
          <p className="compressor-panel-foot text-dim" style={{ margin: 0, fontSize: 'var(--font-xs)' }}>
            MQTT operational snapshot stale; REST merge may lag.
          </p>
        )}
      </div>

      <PaneTerminalFooter />
    </div>
  );
};
