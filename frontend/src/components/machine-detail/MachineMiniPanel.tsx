import React, { useMemo } from 'react';
import type { PanelData } from './PanelPane';
import { computeHorizontalFeedSpindleSlider, computeHorizontalRapidSlider } from '../../utils/panelOverrideAsciiSlider';
import './MachineMiniPanel.css';

const MODE_LABELS: Record<number, string> = {
  0: 'MANUAL',
  1: 'MDI',
  2: 'MEMORY',
  3: 'EDIT',
  4: 'MDI MANUAL',
  5: 'OP EDIT',
};

const SCREEN_LABELS: Record<number, string> = {
  0: 'OFF',
  1: 'ALARM',
  2: 'DATA BANK',
  3: 'ATC',
  4: 'PROGRAM',
  5: 'MANUAL',
  6: 'POSITION',
  7: 'I/O',
  8: 'MONITOR',
  9: 'GRAPH',
};

function doorTok(v: number | undefined): string {
  if (v === undefined) return '—';
  return v === 1 ? 'OPEN' : 'CLOSED';
}

function doorClass(v: number | undefined): string {
  if (v === undefined) return 'text-dim';
  return v === 1 ? 'text-error' : 'text-success';
}

/** Binary lamp: ● on / ○ off (terminal-style). */
function Lamp({ on, onClassName = 'text-success' }: { on: boolean; onClassName?: string }) {
  return <span className={on ? onClassName : 'text-dim'}>{on ? '●' : '○'}</span>;
}

function MiniHorizontalOverrideSlider({
  label,
  mode,
  value,
}: {
  label: string;
  mode: 'rapid' | 'feed';
  value: number;
}) {
  const model = useMemo(
    () =>
      mode === 'rapid'
        ? computeHorizontalRapidSlider(value)
        : computeHorizontalFeedSpindleSlider(value),
    [mode, value]
  );

  return (
    <div className="machine-mini-hslider-row">
      <div className="machine-mini-hslider-label">{label}</div>
      <div className="machine-mini-hslider-track" aria-hidden>
        <span className="machine-mini-hslider-bracket">[</span>
        <span className="machine-mini-hslider-raster">
          {model.segmentFilled.map((filled, i) => {
            const tone = model.segmentTones[i] ?? 'grey';
            const seg = i + 1;
            const hash = (seg * 73 + 37) % 97;
            const brightnessVariation = 0.96 + (hash / 97) * 0.04;
            return (
              <span
                key={seg}
                className={['machine-mini-hslider-glyph', `slider-segment-${tone}`, filled ? 'filled' : '']
                  .filter(Boolean)
                  .join(' ')}
                style={filled ? { opacity: brightnessVariation, filter: `brightness(${brightnessVariation})` } : undefined}
              >
                {filled ? '#' : '-'}
              </span>
            );
          })}
        </span>
        <span className="machine-mini-hslider-bracket">]</span>
      </div>
      <div className={`machine-mini-hslider-value slider-value-${model.valueBoxTone}`}>{model.displayValue}</div>
    </div>
  );
}

export const MachineMiniPanel: React.FC<{ panelData: PanelData | null | undefined }> = ({ panelData }) => {
  if (!panelData) {
    return <div className="machine-mini-panel machine-mini-panel--empty text-dim">NO PANEL DATA</div>;
  }

  const doors = panelData.doors || {};
  const mf = panelData.mode_and_functions || {};
  const ov = panelData.overrides || {};

  const modeLabel = mf.mode !== undefined ? MODE_LABELS[mf.mode] ?? `M${mf.mode}` : '—';
  const screenLabel =
    mf.screen !== undefined ? SCREEN_LABELS[mf.screen] ?? `S${mf.screen}` : '—';

  const estopHeld = ov.emergency_stop === 0;

  const toggleDefs: { key: string; label: string; v: number | undefined }[] = [
    { key: 'SKIP', label: 'BLK SKIP', v: mf.block_skip },
    { key: 'OPT', label: 'OPT STOP', v: mf.opt_stop },
    { key: 'SGL', label: 'SGL BLK', v: mf.single_block },
    { key: 'DRY', label: 'DRY RUN', v: mf.dry_run },
    { key: 'LOCK', label: 'MACH LOCK', v: mf.machine_lock },
    { key: 'COOL', label: 'COOLANT', v: mf.coolant_pump },
    { key: 'CHIP', label: 'CHIP SHOWER', v: mf.chip_shower },
    { key: 'LITE', label: 'LIGHT', v: mf.machine_light },
  ];
  const toggles = toggleDefs
    .filter((x) => x.v !== undefined)
    .map((x) => ({ key: x.key, label: x.label, on: x.v === 1 }));

  const hasOverrides =
    ov.rapid_traverse_override !== undefined ||
    ov.feedrate_override !== undefined ||
    ov.spindle_override !== undefined;

  const hasSafeBits =
    ov.emergency_stop !== undefined ||
    ov.master_on !== undefined ||
    ov.data_protection !== undefined ||
    ov.door_interlock !== undefined;

  const showSideColumn = hasSafeBits || toggles.length > 0;

  return (
    <div className="machine-mini-panel machine-mini-panel--dense">
      <div className="machine-mini-panel-grid">
        <div className="machine-mini-panel-span machine-mini-panel-top">
          <div className="machine-mini-top-doors">
            <span className="machine-mini-h">DOORS</span>
            <div className="machine-mini-door-spread">
              <span>
                OUTER:<strong className={doorClass(doors.outer_door)}>{doorTok(doors.outer_door)}</strong>
              </span>
              <span>
                INNER:<strong className={doorClass(doors.inner_door)}>{doorTok(doors.inner_door)}</strong>
              </span>
              <span>
                SIDE:<strong className={doorClass(doors.side_door)}>{doorTok(doors.side_door)}</strong>
              </span>
            </div>
          </div>
          <div className="machine-mini-top-mode">
            <span className="machine-mini-h">MODE</span>
            <strong>{modeLabel}</strong>
            <span className="machine-mini-sep text-dim" aria-hidden="true">
              │
            </span>
            <span className="machine-mini-h">SCREEN</span>
            <strong>{screenLabel}</strong>
          </div>
        </div>

        {hasOverrides || showSideColumn ? (
          <div
            className={[
              'machine-mini-panel-span',
              'machine-mini-panel-main',
              !hasOverrides ? 'machine-mini-panel-main--side-only' : '',
              !showSideColumn ? 'machine-mini-panel-main--sliders-only' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {hasOverrides ? (
              <div className="machine-mini-panel-sliders" aria-label="Override sliders">
                {ov.rapid_traverse_override !== undefined ? (
                  <MiniHorizontalOverrideSlider mode="rapid" label="RAPID" value={ov.rapid_traverse_override} />
                ) : null}
                {ov.feedrate_override !== undefined ? (
                  <MiniHorizontalOverrideSlider mode="feed" label="FEED" value={ov.feedrate_override} />
                ) : null}
                {ov.spindle_override !== undefined ? (
                  <MiniHorizontalOverrideSlider mode="feed" label="SPINDLE" value={ov.spindle_override} />
                ) : null}
              </div>
            ) : null}

            {showSideColumn ? (
              <aside className="machine-mini-panel-side" aria-label="Safety and switches">
                {hasSafeBits ? (
                  <div className="machine-mini-ind-row">
                    <span className="machine-mini-h">SAFETY</span>
                    <span className="machine-mini-ind-chips">
                      {ov.emergency_stop !== undefined ? (
                        <span className="machine-mini-ind-pair" title={estopHeld ? 'E-stop asserted' : 'Released'}>
                          <span className="machine-mini-ind-label">E-STOP</span>
                          {estopHeld ? (
                            <span className="text-error">●</span>
                          ) : (
                            <span className="text-success">○</span>
                          )}
                        </span>
                      ) : null}
                      {ov.master_on !== undefined ? (
                        <span className="machine-mini-ind-pair">
                          <span className="machine-mini-ind-label">MASTER</span>
                          <Lamp on={ov.master_on === 1} />
                        </span>
                      ) : null}
                      {ov.data_protection !== undefined ? (
                        <span className="machine-mini-ind-pair" title="Data protection">
                          <span className="machine-mini-ind-label">DATA PROT</span>
                          {ov.data_protection === 1 ? (
                            <span className="text-success">●</span>
                          ) : (
                            <span className="text-warning">○</span>
                          )}
                        </span>
                      ) : null}
                      {ov.door_interlock !== undefined ? (
                        <span className="machine-mini-ind-pair">
                          <span className="machine-mini-ind-label">DOOR IL</span>
                          <Lamp on={ov.door_interlock === 1} />
                        </span>
                      ) : null}
                    </span>
                  </div>
                ) : null}

                {toggles.length > 0 ? (
                  <div className="machine-mini-ind-row">
                    <span className="machine-mini-h">FUNCTIONS</span>
                    <span className="machine-mini-ind-chips machine-mini-ind-chips--wrap">
                      {toggles.map((t) => (
                        <span key={t.key} className="machine-mini-ind-pair">
                          <span className="machine-mini-ind-label">{t.label}</span>
                          <Lamp on={t.on} />
                        </span>
                      ))}
                    </span>
                  </div>
                ) : null}
              </aside>
            ) : null}
          </div>
        ) : null}

        {panelData.control_version ? (
          <div className="machine-mini-panel-span machine-mini-panel-ver text-dim">{panelData.control_version}</div>
        ) : null}
      </div>
    </div>
  );
};
