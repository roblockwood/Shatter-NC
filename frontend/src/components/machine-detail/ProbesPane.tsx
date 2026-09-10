import React, { useEffect, useMemo, useState } from 'react';
import { Select } from '../ui';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import { API_BASE_URL } from '../../config/api';
import {
  assessMacroFreshness,
  fieldLabelFor,
  getRoutine,
  getRoutinesForCategory,
  isPoisonValue,
  isValidWcs,
  probeCatalog,
  requiredMacros,
  resolveProgram,
  type ProbeMode,
  type ProbeRoutine,
} from '../../data/probeCatalog';
import { ProbeGlyph } from './probe/ProbeGlyph';
import { ProbeCyclePreview } from './probe/ProbeCyclePreview';
import './ProbesPane.css';

export interface ProbesPaneProps {
  machineId: number;
  macros?: Record<string, number>;
  machineStatus?: string;
  pollTimestamp?: string | null;
  pollIntervalSeconds?: number;
  onExpand?: () => void;
}

type RunPhase =
  | 'idle'
  | 'confirm'
  | 'running'
  | 'awaiting_m0'
  | 'complete'
  | 'error';

interface ProbeRunResponse {
  ok: boolean;
  program?: number;
  gate_program?: number;
  target_program?: number;
  routine_id?: string;
  mode?: string;
  macros_written?: Record<string, number>;
  results?: Record<string, number | null>;
  phase?: string;
  error?: string;
  elapsed_s?: number;
}

function liveMacro(
  macros: Record<string, number> | undefined,
  num: string
): number | undefined {
  if (!macros) return undefined;
  if (macros[num] != null) return macros[num];
  const asInt = String(Number(num));
  return macros[asInt];
}

function defaultParamsFor(macros: string[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const m of macros) {
    if (m === '900') out[m] = 54;
    else if (m === '920') out[m] = 1;
    else if (m === '904') out[m] = 50;
    else if (m === '905' || m === '906' || m === '907') {
      out[m] = m === '905' ? 0 : m === '906' ? 120 : 240;
    } else out[m] = 10;
  }
  return out;
}

function resultLabel(macro: string): string {
  const map: Record<string, string> = {
    '100': 'X / EDGE X',
    '101': 'Y / EDGE Y',
    '102': 'Z / EDGE Z',
    '103': 'DEV X',
    '104': 'DEV Y',
    '105': 'DEV Z',
    '106': 'SIZE',
    '107': 'SIZE DEV',
  };
  return map[macro] ?? `#${macro}`;
}

function shortCategoryLabel(label: string): string {
  return label
    .replace('TOOL SETTER', 'TOOL')
    .replace('SINGLE FACE', 'FACE')
    .replace('INSIDE + OBSTACLE', 'OBST')
    .replace('3-POINT DIA', '3-PT')
    .replace('DIAMETERS', 'DIA')
    .replace('CORNERS', 'CORNER')
    .replace('WIDTHS', 'WIDTH');
}

export const ProbesPane: React.FC<ProbesPaneProps> = ({
  machineId,
  macros,
  machineStatus,
  pollTimestamp,
  pollIntervalSeconds = 5,
}) => {
  const [mode, setMode] = useState<ProbeMode>('probe');
  const [category, setCategory] = useState('corner');
  const routinesInCat = useMemo(
    () => getRoutinesForCategory(category).filter((r) => r.modes[mode] != null),
    [category, mode]
  );
  const [routineId, setRoutineId] = useState('corner_xyz');
  const [params, setParams] = useState<Record<string, number>>({});
  const [phase, setPhase] = useState<RunPhase>('idle');
  const [statusLine, setStatusLine] = useState<string>('Ready');
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, number | null> | null>(null);
  const [busy, setBusy] = useState(false);

  const routine: ProbeRoutine | undefined = getRoutine(routineId);
  const modeEntry = resolveProgram(routineId, mode);
  const required = requiredMacros(routineId, mode);

  useEffect(() => {
    const list = getRoutinesForCategory(category).filter((r) => r.modes[mode] != null);
    if (!list.length) {
      const fallbackCat = probeCatalog.categories.find((c) =>
        getRoutinesForCategory(c.id).some((r) => r.modes[mode] != null)
      );
      if (fallbackCat && fallbackCat.id !== category) {
        setCategory(fallbackCat.id);
      }
      return;
    }
    if (!list.some((r) => r.id === routineId)) {
      setRoutineId(list[0].id);
    }
  }, [category, mode, routineId]);

  useEffect(() => {
    const macrosNeeded = requiredMacros(routineId, mode);
    setParams(defaultParamsFor(macrosNeeded));
    setResults(null);
    setError(null);
    if (phase !== 'running' && phase !== 'confirm' && phase !== 'awaiting_m0') {
      setPhase('idle');
      setStatusLine('Ready');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reset on routine/mode
  }, [routineId, mode]);

  const freshness = assessMacroFreshness(required, params, macros);
  const operating = (machineStatus || '').toLowerCase() === 'operating';
  const canRun =
    !busy &&
    !operating &&
    modeEntry != null &&
    required.every((m) => {
      const v = params[m];
      if (v == null || Number.isNaN(v)) return false;
      if (isPoisonValue(m, v)) return false;
      if (m === '900' && !isValidWcs(v)) return false;
      return true;
    });

  const categoriesForMode = probeCatalog.categories.filter((c) =>
    getRoutinesForCategory(c.id).some((r) => r.modes[mode] != null)
  );

  const modeOptions = [
    { value: 'probe', label: 'PROBE (SET WCS)' },
    { value: 'measure', label: 'MEASURE (CHECK)' },
  ];

  const modeSelectValue =
    routineId === 'tool_length' && mode === 'measure' ? 'probe' : mode;

  async function armCycle() {
    setBusy(true);
    setPhase('running');
    setError(null);
    setResults(null);
    setStatusLine('Writing macros / starting O8099 gate…');
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: routineId,
          mode: routineId === 'tool_length' ? 'probe' : mode,
          params,
        }),
      });
      const body = (await res.json().catch(() => ({}))) as ProbeRunResponse & {
        detail?: ProbeRunResponse | string;
      };
      const payload: ProbeRunResponse =
        typeof body.detail === 'object' && body.detail != null
          ? body.detail
          : (body as ProbeRunResponse);

      if (!res.ok || !payload.ok) {
        const msg =
          payload.error ||
          (typeof body.detail === 'string' ? body.detail : null) ||
          `Arm failed (HTTP ${res.status})`;
        setError(msg);
        setPhase('error');
        setStatusLine(`Failed at ${payload.phase ?? 'unknown'}`);
        return;
      }

      setPhase('awaiting_m0');
      const gate = payload.gate_program ?? probeCatalog.gate_program ?? 8099;
      const target = payload.target_program ?? modeEntry?.program;
      setStatusLine(
        `ARMED O${String(gate).padStart(4, '0')} → O${String(target ?? '').padStart(4, '0')} — Cycle Start past M0, then COLLECT`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Arm request failed');
      setPhase('error');
      setStatusLine('Request error');
    } finally {
      setBusy(false);
    }
  }

  async function collectResults() {
    setBusy(true);
    setStatusLine('Waiting for idle / reading results…');
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/collect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poison: true }),
      });
      const body = (await res.json().catch(() => ({}))) as ProbeRunResponse & {
        detail?: ProbeRunResponse | string;
      };
      const payload: ProbeRunResponse =
        typeof body.detail === 'object' && body.detail != null
          ? body.detail
          : (body as ProbeRunResponse);

      if (!res.ok || !payload.ok) {
        const msg =
          payload.error ||
          (typeof body.detail === 'string' ? body.detail : null) ||
          `Collect failed (HTTP ${res.status})`;
        setError(msg);
        setPhase('error');
        setStatusLine(`Failed at ${payload.phase ?? 'unknown'}`);
        if (payload.results) setResults(payload.results);
        return;
      }

      setResults(payload.results ?? null);
      setPhase('complete');
      setStatusLine(
        `Complete in ${(payload.elapsed_s ?? 0).toFixed(1)}s — macros poisoned`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Collect request failed');
      setPhase('error');
      setStatusLine('Request error');
    } finally {
      setBusy(false);
    }
  }

  async function poisonMacros() {
    setBusy(true);
    setStatusLine('Poisoning macros…');
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/poison`, {
        method: 'POST',
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = (body as { detail?: { error?: string } | string })?.detail;
        const msg =
          typeof detail === 'string'
            ? detail
            : detail && typeof detail === 'object'
              ? detail.error
              : null;
        setError(msg || `Poison failed (HTTP ${res.status})`);
        setPhase('error');
        setStatusLine('Poison failed');
        return;
      }
      setStatusLine('Macros poisoned');
      setPhase('idle');
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Poison request failed');
      setPhase('error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="probes-pane">
      <div className="terminal-box">
        <PaneTerminalHeader label="PROBES">
          <PollingStatusLight
            lastUpdatedAt={pollTimestamp}
            expectedIntervalMs={pollIntervalSeconds * 1000}
            ariaLabel="Probe pane data freshness"
          />
        </PaneTerminalHeader>

        <div className="terminal-box-content probes-pane-content">
          <div className="probes-row">
            <span className="probes-label">MODE</span>
            <Select
              compact
              value={modeSelectValue}
              onChange={(v) => setMode(v as ProbeMode)}
              options={modeOptions}
              disabled={busy || routineId === 'tool_length'}
            />
          </div>

          <div className="probes-cat-tabs" role="tablist" aria-label="Probe category">
            {categoriesForMode.map((c) => (
              <button
                key={c.id}
                type="button"
                role="tab"
                aria-selected={category === c.id}
                className={`probes-cat-tab${category === c.id ? ' probes-cat-tab--active' : ''}`}
                disabled={busy}
                onClick={() => setCategory(c.id)}
              >
                {shortCategoryLabel(c.label)}
              </button>
            ))}
          </div>

          <div className="probes-glyph-grid" role="listbox" aria-label="Probe type">
            {routinesInCat.map((r) => {
              const selected = r.id === routineId;
              return (
                <button
                  key={r.id}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={`probes-glyph-tile${selected ? ' probes-glyph-tile--selected' : ''}`}
                  disabled={busy}
                  title={r.label}
                  onClick={() => setRoutineId(r.id)}
                >
                  <ProbeGlyph glyphId={r.glyph_id} className="probe-glyph" />
                  <span className="probes-glyph-caption">{r.label.toUpperCase()}</span>
                </button>
              );
            })}
          </div>

          {modeEntry && (
            <div className="probes-meta">
              GATE O{String(probeCatalog.gate_program ?? 8099).padStart(4, '0')}
              {' → '}
              TARGET O{String(modeEntry.program).padStart(4, '0')}
              {' | '}
              <span className={`probes-freshness probes-freshness--${freshness.toLowerCase()}`}>
                {freshness}
              </span>
            </div>
          )}

          <div className="probes-prereq">
            * O8099 gate only. Cycle Start past M0, then COLLECT.
          </div>
          {routine?.prerequisites && (
            <div className="probes-prereq">* {routine.prerequisites}</div>
          )}

          <div className="probes-main">
            <div className="probes-fields">
              {required.map((macro) => {
                const label = routine
                  ? fieldLabelFor(routine, macro)
                  : probeCatalog.fields[macro]?.label ?? `#${macro}`;
                const unit = probeCatalog.fields[macro]?.unit ?? '';
                const live = liveMacro(macros, macro);
                return (
                  <label key={macro} className="probes-field">
                    <span className="probes-field-label">
                      {label}
                      {unit ? ` (${unit})` : ''}
                      <span className="probes-field-macro"> #{macro}</span>
                    </span>
                    <span className="probes-input-wrap">
                      <input
                        className="probes-input"
                        type="number"
                        step={macro === '900' ? 1 : 'any'}
                        value={params[macro] ?? ''}
                        disabled={busy}
                        onChange={(e) => {
                          const n = Number.parseFloat(e.target.value);
                          setParams((prev) => ({
                            ...prev,
                            [macro]: Number.isFinite(n) ? n : 0,
                          }));
                        }}
                      />
                      <span className="probes-spin">
                        <button
                          type="button"
                          className="probes-spin-btn"
                          tabIndex={-1}
                          disabled={busy}
                          aria-label={`Increase ${label}`}
                          onClick={() => {
                            setParams((prev) => ({
                              ...prev,
                              [macro]: (prev[macro] ?? 0) + 1,
                            }));
                          }}
                        >
                          ▲
                        </button>
                        <button
                          type="button"
                          className="probes-spin-btn"
                          tabIndex={-1}
                          disabled={busy}
                          aria-label={`Decrease ${label}`}
                          onClick={() => {
                            setParams((prev) => ({
                              ...prev,
                              [macro]: (prev[macro] ?? 0) - 1,
                            }));
                          }}
                        >
                          ▼
                        </button>
                      </span>
                    </span>
                    <span className="probes-live">
                      LIVE:{' '}
                      {live == null
                        ? '──'
                        : isPoisonValue(macro, live)
                          ? `${live} (POISON)`
                          : live}
                    </span>
                  </label>
                );
              })}
            </div>

            <ProbeCyclePreview routineId={routineId} params={params} />
          </div>

          <div className="probes-actions">
            <button
              type="button"
              className="terminal-button-sm danger"
              disabled={!canRun}
              onClick={() => setPhase('confirm')}
              title={
                operating
                  ? 'Machine is operating'
                  : !canRun
                    ? 'Fill valid non-poison params'
                    : 'Write macros and MEMSTRT O8099 gate only'
              }
            >
              [ WRITE+ARM ]
            </button>
            <button
              type="button"
              className="terminal-button-sm"
              disabled={busy || phase !== 'awaiting_m0'}
              onClick={() => void collectResults()}
              title="After Cycle Start past M0 and probe finishes, read #100+ and poison"
            >
              [ COLLECT ]
            </button>
            <button
              type="button"
              className="terminal-button-sm"
              disabled={busy}
              onClick={() => void poisonMacros()}
            >
              [ POISON ]
            </button>
          </div>

          <div className="probes-status">
            STATUS: {statusLine}
            {operating ? ' | MACHINE OPERATING' : ''}
          </div>
          {error && <div className="probes-error">!! {error}</div>}

          {results && (
            <div className="probes-results">
              <div className="probes-results-title">RESULTS (#100+)</div>
              {Object.entries(results).map(([k, v]) => (
                <div key={k} className="probes-result-row">
                  <span>{resultLabel(k)}</span>
                  <span>{v == null ? '──' : v}</span>
                </div>
              ))}
            </div>
          )}

          {routineId === 'tool_length' && (
            <div className="probes-note">
              Note: ToolsPane also sets #920 as the measurement tool.
            </div>
          )}
        </div>

        <PaneTerminalFooter />
      </div>

      {phase === 'confirm' && modeEntry && (
        <div className="probes-confirm-overlay" role="dialog" aria-modal="true">
          <div className="probes-confirm-box">
            <div className="probes-confirm-title">CONFIRM ARM (O8099 GATE)</div>
            <div className="probes-confirm-body">
              <div>Shatter will ONLY start O8099. No Blum motion until Cycle Start past M0.</div>
              <div>
                GATE O{String(probeCatalog.gate_program ?? 8099).padStart(4, '0')} → TARGET O
                {String(modeEntry.program).padStart(4, '0')} · {mode.toUpperCase()} ·{' '}
                {routine?.label ?? routineId}
              </div>
              <ProbeCyclePreview
                routineId={routineId}
                params={params}
                compact
                className="probes-confirm-preview"
              />
              <div className="probes-confirm-params">
                <div>#908 = {modeEntry.program}</div>
                {required.map((m) => (
                  <div key={m}>
                    #{m} = {params[m]}
                  </div>
                ))}
              </div>
            </div>
            <div className="probes-confirm-actions">
              <button
                type="button"
                className="terminal-button-sm"
                onClick={() => {
                  setPhase('idle');
                  setStatusLine('Ready');
                }}
              >
                [ CANCEL ]
              </button>
              <button
                type="button"
                className="terminal-button-sm danger"
                onClick={() => void armCycle()}
              >
                [ ARM ]
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
