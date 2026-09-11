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
  | 'confirm_write'
  | 'written'
  | 'confirm_motion'
  | 'running'
  | 'complete'
  | 'error';

interface ProbeRunResponse {
  ok: boolean;
  program?: number;
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
    () => getRoutinesForCategory(category),
    [category]
  );
  const [routineId, setRoutineId] = useState('corner_xyz');
  const [params, setParams] = useState<Record<string, number>>({});
  const [phase, setPhase] = useState<RunPhase>('idle');
  const [statusLine, setStatusLine] = useState<string>('Ready');
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, number | null> | null>(null);
  const [busy, setBusy] = useState(false);

  const routine: ProbeRoutine | undefined = getRoutine(routineId);
  const availableModes = useMemo((): ProbeMode[] => {
    if (!routine) return ['probe'];
    return (['probe', 'measure'] as ProbeMode[]).filter((m) => routine.modes[m] != null);
  }, [routine]);
  const showModeSelect = availableModes.length > 1;
  const effectiveMode: ProbeMode =
    routine?.modes[mode] != null ? mode : availableModes[0] ?? 'probe';
  const modeEntry = resolveProgram(routineId, effectiveMode);
  const required = requiredMacros(routineId, effectiveMode);

  // Category change may leave routine elsewhere — pick first in category only
  useEffect(() => {
    const list = getRoutinesForCategory(category);
    if (!list.some((r) => r.id === routineId) && list[0]) {
      setRoutineId(list[0].id);
    }
  }, [category, routineId]);

  // If the selected routine does not support the current mode, snap mode
  // (never change the routine underneath the user).
  useEffect(() => {
    if (!routine) return;
    if (routine.modes[mode] == null && availableModes[0]) {
      setMode(availableModes[0]);
    }
  }, [routine, mode, availableModes]);

  useEffect(() => {
    const macrosNeeded = requiredMacros(routineId, effectiveMode);
    setParams(defaultParamsFor(macrosNeeded));
    setResults(null);
    setError(null);
    if (phase !== 'running' && phase !== 'confirm_write' && phase !== 'confirm_motion') {
      setPhase('idle');
      setStatusLine('Ready');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reset on routine/mode
  }, [routineId, effectiveMode]);

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

  const controlsDisabled = busy;

  const modeOptions = availableModes.map((m) => ({
    value: m,
    label: m === 'probe' ? 'PROBE · SET WCS' : 'MEASURE · CHECK',
  }));

  async function parseProbeResponse(res: Response): Promise<ProbeRunResponse> {
    const body = (await res.json().catch(() => ({}))) as ProbeRunResponse & {
      detail?: ProbeRunResponse | string;
    };
    return typeof body.detail === 'object' && body.detail != null
      ? body.detail
      : (body as ProbeRunResponse);
  }

  async function writeMacros() {
    setBusy(true);
    setError(null);
    setResults(null);
    setStatusLine('Writing job macros (no motion)…');
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: routineId,
          mode: effectiveMode,
          params,
        }),
      });
      const payload = await parseProbeResponse(res);
      if (!res.ok || !payload.ok) {
        const msg = payload.error || `Write failed (HTTP ${res.status})`;
        setError(msg);
        setPhase('error');
        setStatusLine(`Failed at ${payload.phase ?? 'unknown'}`);
        return;
      }
      setPhase('written');
      const target = payload.target_program ?? modeEntry?.program;
      setStatusLine(
        `MACROS WRITTEN · target O${String(target ?? '').padStart(4, '0')} — confirm START MOTION when ready`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Write request failed');
      setPhase('error');
      setStatusLine('Request error');
    } finally {
      setBusy(false);
    }
  }

  async function startMotion() {
    setBusy(true);
    setError(null);
    setStatusLine('MEMSTRT — machine will move…');
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: routineId,
          mode: effectiveMode,
          params,
        }),
      });
      const payload = await parseProbeResponse(res);
      if (!res.ok || !payload.ok) {
        const msg = payload.error || `Start failed (HTTP ${res.status})`;
        setError(msg);
        setPhase('error');
        setStatusLine(`Failed at ${payload.phase ?? 'unknown'}`);
        return;
      }
      setPhase('running');
      const target = payload.target_program ?? modeEntry?.program;
      setStatusLine(
        `RUNNING O${String(target ?? '').padStart(4, '0')} — when idle, COLLECT results`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Start request failed');
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
      const payload = await parseProbeResponse(res);

      if (!res.ok || !payload.ok) {
        const msg =
          payload.error ||
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
          <div className="probes-cat-tabs" role="tablist" aria-label="Probe category">
            {probeCatalog.categories.map((c) => (
              <button
                key={c.id}
                type="button"
                role="tab"
                aria-selected={category === c.id}
                className={`probes-cat-tab${category === c.id ? ' probes-cat-tab--active' : ''}`}
                disabled={controlsDisabled}
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
                  disabled={controlsDisabled}
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
              TARGET O{String(modeEntry.program).padStart(4, '0')}
              {' | '}
              <span className={`probes-freshness probes-freshness--${freshness.toLowerCase()}`}>
                {freshness}
              </span>
              {phase === 'written' ? ' | MACROS READY' : ''}
              {phase === 'running' ? ' | MOTION ARMED/RUNNING' : ''}
            </div>
          )}

          <div className="probes-main">
            <div className="probes-fields">
              {showModeSelect && (
                <label className="probes-field probes-field--mode">
                  <span className="probes-field-label">MODE</span>
                  <Select
                    compact
                    className="probes-mode-select"
                    value={effectiveMode}
                    onChange={(v) => setMode(v as ProbeMode)}
                    options={modeOptions}
                    disabled={controlsDisabled}
                  />
                </label>
              )}
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
                        disabled={controlsDisabled}
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
                          disabled={controlsDisabled}
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
                          disabled={controlsDisabled}
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
              className="terminal-button-sm"
              disabled={!canRun || busy}
              onClick={() => {
                if (!canRun || busy) return;
                setPhase('confirm_write');
              }}
              title={
                operating
                  ? 'Machine is operating'
                  : !canRun
                    ? 'Fill valid non-poison params'
                    : 'Write job macros only — no motion'
              }
            >
              [ 1 WRITE MACROS ]
            </button>
            <button
              type="button"
              className="terminal-button-sm danger"
              disabled={busy || phase !== 'written'}
              onClick={() => {
                if (busy || phase !== 'written') return;
                setPhase('confirm_motion');
              }}
              title={
                phase !== 'written'
                  ? 'Write macros first'
                  : 'MEMSTRT target program — MACHINE WILL MOVE'
              }
            >
              [ 2 START MOTION ]
            </button>
            <button
              type="button"
              className="terminal-button-sm"
              disabled={busy || phase !== 'running'}
              onClick={() => {
                if (busy || phase !== 'running') return;
                void collectResults();
              }}
              title={
                phase !== 'running'
                  ? 'Start motion first'
                  : 'Wait for idle, read #100+, poison'
              }
            >
              [ 3 COLLECT ]
            </button>
            <button
              type="button"
              className="terminal-button-sm"
              disabled={busy}
              onClick={() => {
                if (busy) return;
                void poisonMacros();
              }}
              title="Poison probe macros"
            >
              [ POISON ]
            </button>
          </div>

          <div className="probes-footer">
            <div className="probes-status">
              STATUS: {statusLine}
              {operating ? ' | MACHINE OPERATING' : ''}
            </div>
            <div className="probes-prereq">
              * Stepped run: WRITE (no motion) → START MOTION (MEMSTRT) → COLLECT.
              {routine?.prerequisites ? ` · ${routine.prerequisites}` : ''}
            </div>
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
        </div>

        <PaneTerminalFooter />
      </div>

      {phase === 'confirm_write' && modeEntry && (
        <div className="probes-confirm-overlay" role="dialog" aria-modal="true">
          <div className="probes-confirm-box">
            <div className="probes-confirm-title">STEP 1 — WRITE MACROS</div>
            <div className="probes-confirm-body">
              <div>No axis motion. Shatter will write job macros only.</div>
              <div>
                TARGET O{String(modeEntry.program).padStart(4, '0')} ·{' '}
                {effectiveMode.toUpperCase()} · {routine?.label ?? routineId}
              </div>
              <div className="probes-confirm-params">
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
                disabled={busy}
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
                disabled={busy}
                onClick={() => {
                  if (busy) return;
                  void writeMacros();
                }}
              >
                [ WRITE ]
              </button>
            </div>
          </div>
        </div>
      )}

      {phase === 'confirm_motion' && modeEntry && (
        <div className="probes-confirm-overlay" role="dialog" aria-modal="true">
          <div className="probes-confirm-box">
            <div className="probes-confirm-title">STEP 2 — START MOTION</div>
            <div className="probes-confirm-body">
              <div className="probes-confirm-warn">
                MACHINE WILL MOVE. Shatter will MEMSTRT O
                {String(modeEntry.program).padStart(4, '0')} now.
              </div>
              <div>
                {effectiveMode.toUpperCase()} · {routine?.label ?? routineId}
              </div>
              <ProbeCyclePreview
                routineId={routineId}
                params={params}
                compact
                className="probes-confirm-preview"
              />
              <div className="probes-confirm-params">
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
                disabled={busy}
                onClick={() => {
                  setPhase('written');
                  setStatusLine(
                    `MACROS WRITTEN · target O${String(modeEntry.program).padStart(4, '0')} — confirm START MOTION when ready`
                  );
                }}
              >
                [ CANCEL ]
              </button>
              <button
                type="button"
                className="terminal-button-sm danger"
                disabled={busy}
                onClick={() => {
                  if (busy) return;
                  void startMotion();
                }}
              >
                [ GO — MEMSTRT ]
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
