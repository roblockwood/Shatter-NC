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
    else out[m] = 1;
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

export const ProbesPane: React.FC<ProbesPaneProps> = ({
  machineId,
  macros,
  machineStatus,
  pollTimestamp,
  pollIntervalSeconds = 5,
}) => {
  const [mode, setMode] = useState<ProbeMode>('probe');
  const [category, setCategory] = useState(probeCatalog.categories[0]?.id ?? 'corner');
  const routinesInCat = useMemo(
    () => getRoutinesForCategory(category).filter((r) => r.modes[mode] != null),
    [category, mode]
  );
  const [routineId, setRoutineId] = useState(
    () => getRoutinesForCategory(probeCatalog.categories[0]?.id ?? 'corner')[0]?.id ?? 'corner_xyz'
  );
  const [params, setParams] = useState<Record<string, number>>({});
  const [phase, setPhase] = useState<RunPhase>('idle');
  const [statusLine, setStatusLine] = useState<string>('Ready');
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, number | null> | null>(null);
  const [busy, setBusy] = useState(false);

  const routine: ProbeRoutine | undefined = getRoutine(routineId);
  const modeEntry = resolveProgram(routineId, mode);
  const required = requiredMacros(routineId, mode);

  // When mode/category changes, keep a valid routine selected
  useEffect(() => {
    const list = getRoutinesForCategory(category).filter((r) => r.modes[mode] != null);
    if (!list.length) {
      // Prefer first category that has routines for this mode
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

  // Reset form defaults when routine/mode changes
  useEffect(() => {
    const macrosNeeded = requiredMacros(routineId, mode);
    setParams(defaultParamsFor(macrosNeeded));
    setResults(null);
    setError(null);
    if (phase !== 'running' && phase !== 'confirm') {
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

  const categoryOptions = probeCatalog.categories
    .filter((c) => getRoutinesForCategory(c.id).some((r) => r.modes[mode] != null))
    .map((c) => ({ value: c.id, label: c.label }));

  const routineOptions = routinesInCat.map((r) => ({
    value: r.id,
    label: r.label.toUpperCase(),
  }));

  const modeOptions = [
    { value: 'probe', label: 'PROBE (SET WCS)' },
    { value: 'measure', label: 'MEASURE (CHECK)' },
  ];

  // Tool length only supports probe — coerce mode display
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
        `ARMED O${String(gate).padStart(4, '0')} → target O${String(target ?? '').padStart(4, '0')} — Cycle Start past M0 on machine, then COLLECT`
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
        const msg =
          (body as { detail?: { error?: string } | string })?.detail &&
          typeof (body as { detail: unknown }).detail === 'object'
            ? ((body as { detail: { error?: string } }).detail.error ?? 'Poison failed')
            : 'Poison failed';
        setError(msg);
        setPhase('error');
        return;
      }
      setStatusLine('Macros poisoned');
      setPhase('idle');
      setResults(null);
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

          <div className="probes-row">
            <span className="probes-label">CATEGORY</span>
            <Select
              compact
              value={category}
              onChange={setCategory}
              options={categoryOptions}
              disabled={busy}
            />
          </div>

          <div className="probes-row">
            <span className="probes-label">TYPE</span>
            <Select
              compact
              value={routineId}
              onChange={setRoutineId}
              options={routineOptions}
              disabled={busy || routineOptions.length === 0}
            />
          </div>

          {modeEntry && (
            <div className="probes-meta">
              GATE O{String(probeCatalog.gate_program ?? 8099).padStart(4, '0')}
              {' → '}
              TARGET O{String(modeEntry.program).padStart(4, '0')}
              {' | '}
              #908={modeEntry.program}
              {' | '}
              MACROS {required.map((m) => `#${m}`).join(' ')}
              {' | '}
              <span className={`probes-freshness probes-freshness--${freshness.toLowerCase()}`}>
                {freshness}
              </span>
            </div>
          )}

          <div className="probes-prereq">
            * Shatter only starts O8099 (preview + M0). Load O8099 on the machine. Cycle Start
            past M0 runs the target helper; then COLLECT.
          </div>
          {routine?.prerequisites && (
            <div className="probes-prereq">* {routine.prerequisites}</div>
          )}

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
                  <input
                    className="probes-input"
                    type="number"
                    step="any"
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
              <div>Shatter will ONLY start O8099. No Blum motion until you Cycle Start past M0.</div>
              <div>
                GATE O{String(probeCatalog.gate_program ?? 8099).padStart(4, '0')} → TARGET O
                {String(modeEntry.program).padStart(4, '0')} · {mode.toUpperCase()} ·{' '}
                {routine?.label ?? routineId}
              </div>
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
