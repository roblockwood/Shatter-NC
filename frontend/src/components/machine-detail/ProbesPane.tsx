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

type RunPhase = 'idle' | 'wizard' | 'complete' | 'error';

type WizardStep = 'write' | 'motion' | 'salt';
type StepUi = 'ready' | 'busy' | 'ok' | 'fail';

const WIZARD_STEPS: WizardStep[] = ['write', 'motion', 'salt'];

function wizardStepTitle(step: WizardStep): string {
  switch (step) {
    case 'write':
      return '1 / 3  WRITE MACROS';
    case 'motion':
      return '2 / 3  START MOTION';
    case 'salt':
      return '3 / 3  COLLECT + SALT';
  }
}

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
  const [wizardStep, setWizardStep] = useState<WizardStep>('write');
  const [stepUi, setStepUi] = useState<StepUi>('ready');
  const [stepLog, setStepLog] = useState<string>('');
  const [macrosWritten, setMacrosWritten] = useState<Record<string, number> | null>(
    null
  );

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
    if (phase !== 'wizard') {
      setPhase('idle');
      setStatusLine('Ready');
      setWizardStep('write');
      setStepUi('ready');
      setStepLog('');
      setMacrosWritten(null);
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

  const controlsDisabled = busy || phase === 'wizard';

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

  function openWizard() {
    setError(null);
    setResults(null);
    setMacrosWritten(null);
    setWizardStep('write');
    setStepUi('ready');
    setStepLog('');
    setPhase('wizard');
    setStatusLine('EXECUTE wizard open — walk each step');
  }

  function abortWizard() {
    if (busy) return;
    setPhase('idle');
    setWizardStep('write');
    setStepUi('ready');
    setStepLog('');
    setStatusLine('Ready');
  }

  function advanceWizard() {
    const idx = WIZARD_STEPS.indexOf(wizardStep);
    if (idx < 0 || idx >= WIZARD_STEPS.length - 1) {
      setPhase('complete');
      setStatusLine('Probe sequence complete');
      return;
    }
    setWizardStep(WIZARD_STEPS[idx + 1]);
    setStepUi('ready');
    setStepLog('');
  }

  async function runWizardStep() {
    if (busy || stepUi === 'busy' || stepUi === 'ok') return;
    setBusy(true);
    setStepUi('busy');
    setStepLog('Working…');
    setError(null);
    try {
      if (wizardStep === 'write') {
        setStatusLine('Wizard: writing macros…');
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
          setStepUi('fail');
          setStepLog(msg);
          setError(msg);
          setStatusLine(`Write failed at ${payload.phase ?? 'unknown'}`);
          return;
        }
        const written = payload.macros_written ?? {};
        setMacrosWritten(written);
        const lines = Object.entries(written)
          .map(([k, v]) => `#${k}=${v}`)
          .join(' · ');
        setStepUi('ok');
        setStepLog(`OK — macros written${lines ? `: ${lines}` : ''}`);
        setStatusLine('Macros written — continue to motion step');
        return;
      }

      if (wizardStep === 'motion') {
        setStatusLine('Wizard: MEMSTRT — machine moving…');
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
          setStepUi('fail');
          setStepLog(msg);
          setError(msg);
          setStatusLine(`Start failed at ${payload.phase ?? 'unknown'}`);
          return;
        }
        const target = payload.target_program ?? modeEntry?.program;
        setStepUi('ok');
        setStepLog(
          `OK — MEMSTRT O${String(target ?? '').padStart(4, '0')} started (${(payload.elapsed_s ?? 0).toFixed(1)}s)`
        );
        setStatusLine(
          `Running O${String(target ?? '').padStart(4, '0')} — continue to collect when ready`
        );
        return;
      }

      // salt = collect + poison
      setStatusLine('Wizard: waiting idle / collect + salt…');
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/collect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poison: true }),
      });
      const payload = await parseProbeResponse(res);
      if (!res.ok || !payload.ok) {
        const msg = payload.error || `Collect failed (HTTP ${res.status})`;
        setStepUi('fail');
        setStepLog(msg);
        setError(msg);
        if (payload.results) setResults(payload.results);
        setStatusLine(`Collect failed at ${payload.phase ?? 'unknown'}`);
        return;
      }
      setResults(payload.results ?? null);
      setStepUi('ok');
      setStepLog(
        `OK — results read · macros salted (${(payload.elapsed_s ?? 0).toFixed(1)}s)`
      );
      setStatusLine(
        `Complete in ${(payload.elapsed_s ?? 0).toFixed(1)}s — macros poisoned`
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      setStepUi('fail');
      setStepLog(msg);
      setError(msg);
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
              {phase === 'wizard' ? ` | WIZARD · ${wizardStepTitle(wizardStep)}` : ''}
              {phase === 'complete' ? ' | COMPLETE' : ''}
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
              className="terminal-button-sm danger"
              disabled={!canRun || busy || phase === 'wizard'}
              onClick={() => {
                if (!canRun || busy || phase === 'wizard') return;
                openWizard();
              }}
              title={
                operating
                  ? 'Machine is operating'
                  : !canRun
                    ? 'Fill valid non-poison params'
                    : 'Open stepped execute wizard'
              }
            >
              [ EXECUTE ]
            </button>
            <button
              type="button"
              className="terminal-button-sm"
              disabled={busy || phase === 'wizard'}
              onClick={() => {
                if (busy || phase === 'wizard') return;
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
              * EXECUTE opens a confirm wizard: write macros → start motion → collect + salt.
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

      {phase === 'wizard' && modeEntry && (
        <div className="probes-confirm-overlay" role="dialog" aria-modal="true">
          <div className="probes-confirm-box probes-wizard-box">
            <div className="probes-confirm-title">{wizardStepTitle(wizardStep)}</div>

            <div className="probes-wizard-progress" aria-hidden="true">
              {WIZARD_STEPS.map((s) => {
                const idx = WIZARD_STEPS.indexOf(s);
                const cur = WIZARD_STEPS.indexOf(wizardStep);
                const done = idx < cur || (idx === cur && stepUi === 'ok');
                const active = idx === cur;
                return (
                  <span
                    key={s}
                    className={`probes-wizard-pip${active ? ' probes-wizard-pip--active' : ''}${done ? ' probes-wizard-pip--done' : ''}`}
                  />
                );
              })}
            </div>

            <div className="probes-confirm-body">
              {wizardStep === 'write' && (
                <>
                  <div>Shatter will write job macros only. No axis motion.</div>
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
                </>
              )}

              {wizardStep === 'motion' && (
                <>
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
                  {macrosWritten && (
                    <div className="probes-confirm-params">
                      {Object.entries(macrosWritten).map(([m, v]) => (
                        <div key={m}>
                          #{m} = {v}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {wizardStep === 'salt' && (
                <>
                  <div>
                    Wait until the machine is idle, then read result macros (#100+) and
                    poison/salt the job macros so a stale cycle cannot re-run.
                  </div>
                  <div>
                    TARGET was O{String(modeEntry.program).padStart(4, '0')} ·{' '}
                    {effectiveMode.toUpperCase()} · {routine?.label ?? routineId}
                  </div>
                </>
              )}

              {stepLog && (
                <div
                  className={`probes-wizard-log probes-wizard-log--${stepUi}`}
                  role="status"
                >
                  {stepUi === 'ok' ? '✓ ' : stepUi === 'fail' ? '✗ ' : ''}
                  {stepLog}
                </div>
              )}
            </div>

            <div className="probes-confirm-actions">
              <button
                type="button"
                className="terminal-button-sm"
                disabled={busy}
                onClick={() => abortWizard()}
              >
                [ ABORT ]
              </button>

              {(stepUi === 'ready' || stepUi === 'fail') && (
                <button
                  type="button"
                  className={`terminal-button-sm${wizardStep === 'motion' ? ' danger' : ''}`}
                  disabled={busy}
                  onClick={() => {
                    if (busy) return;
                    void runWizardStep();
                  }}
                >
                  {stepUi === 'fail'
                    ? '[ RETRY ]'
                    : wizardStep === 'write'
                      ? '[ WRITE MACROS ]'
                      : wizardStep === 'motion'
                        ? '[ START MOTION ]'
                        : '[ COLLECT + SALT ]'}
                </button>
              )}

              {stepUi === 'busy' && (
                <button type="button" className="terminal-button-sm" disabled>
                  [ WORKING… ]
                </button>
              )}

              {stepUi === 'ok' && wizardStep !== 'salt' && (
                <button
                  type="button"
                  className="terminal-button-sm danger"
                  disabled={busy}
                  onClick={() => advanceWizard()}
                >
                  [ NEXT ]
                </button>
              )}

              {stepUi === 'ok' && wizardStep === 'salt' && (
                <button
                  type="button"
                  className="terminal-button-sm"
                  disabled={busy}
                  onClick={() => {
                    setPhase('complete');
                    setStatusLine('Probe sequence complete');
                    setWizardStep('write');
                    setStepUi('ready');
                    setStepLog('');
                  }}
                >
                  [ DONE ]
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
