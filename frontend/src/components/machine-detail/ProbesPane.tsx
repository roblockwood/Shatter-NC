import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Select } from '../ui';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import { API_BASE_URL } from '../../config/api';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
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
import {
  AtcPotSelectGrid,
  buildAtcPotCells,
} from './probe/AtcPotSelectGrid';
import type { UnifiedToolView } from '../../utils/unifiedToolView';
import {
  formatMemMode,
  formatMemOperationStatus,
} from '../../utils/machineMemLabels';
import './ProbesPane.css';

export interface ProbesPaneProps {
  machineId: number;
  macros?: Record<string, number>;
  machineStatus?: string;
  memMode?: number;
  memOperationStatus?: number;
  alarms?: Array<{ code: string; message?: string; stop_level?: string }>;
  pollTimestamp?: string | null;
  pollIntervalSeconds?: number;
  toolsUnified?: UnifiedToolView | null;
  atcPockets?: number;
  onExpand?: () => void;
}

type RunPhase = 'idle' | 'wizard' | 'poison' | 'complete' | 'error';

type WizardStep = 'write' | 'motion' | 'salt';
type StepUi = 'ready' | 'busy' | 'ok' | 'fail';

type ActivityLevel = 'info' | 'ok' | 'warn' | 'fail';

interface ActivityLine {
  id: number;
  at: string;
  msg: string;
  level: ActivityLevel;
}

const WIZARD_STEPS: WizardStep[] = ['write', 'motion', 'salt'];

function wizardStepTitle(step: WizardStep, multi = false): string {
  switch (step) {
    case 'write':
      return multi ? '1 / 3  CONFIRM TOOLS' : '1 / 3  WRITE MACROS';
    case 'motion':
      return multi ? '2 / 3  CONFIRM BATCH' : '2 / 3  START MOTION';
    case 'salt':
      return multi ? '3 / 3  MEASURE BATCH' : '3 / 3  COLLECT + SALT';
  }
}

function formatActivityTime(d = new Date()): string {
  return d.toLocaleTimeString([], {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/** Honest live line from poller fields — not just PRD3 status (often sticky ERROR). */
function formatLiveMachineLine(
  status?: string,
  memMode?: number,
  memOp?: number,
  alarms?: Array<{ code: string; stop_level?: string }>
): string {
  const st = (status || 'unknown').trim().toUpperCase() || 'UNKNOWN';
  const parts = [
    st,
    `MEM ${formatMemMode(memMode)}`,
    `op ${formatMemOperationStatus(memOp)}`,
  ];
  const codes = (alarms || [])
    .map((a) => (a.code || '').trim())
    .filter(Boolean)
    .slice(0, 3);
  if (codes.length) {
    parts.push(`alarms ${codes.join(',')}`);
  } else if (st === 'ERROR') {
    parts.push('PRD3 code 5 (panel may show soft CM alarm)');
  }
  return `Live: ${parts.join(' · ')}`;
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
  memMode,
  memOperationStatus,
  alarms,
  pollTimestamp,
  pollIntervalSeconds = 5,
  toolsUnified = null,
  atcPockets = 21,
}) => {
  const [mode, setMode] = useState<ProbeMode>('probe');
  const [category, setCategory] = useState('corner');
  const routinesInCat = useMemo(
    () => getRoutinesForCategory(category),
    [category]
  );
  const [routineId, setRoutineId] = useState('corner_xyz');
  const [params, setParams] = useState<Record<string, number>>({});
  const [selectedPots, setSelectedPots] = useState<number[]>([]);
  const [phase, setPhase] = useState<RunPhase>('idle');
  const [statusLine, setStatusLine] = useState<string>('Ready');
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, number | null> | null>(null);
  const [busy, setBusy] = useState(false);
  const [wizardStep, setWizardStep] = useState<WizardStep>('write');
  const [stepUi, setStepUi] = useState<StepUi>('ready');
  const [stepLog, setStepLog] = useState<string>('');
  const [activityLog, setActivityLog] = useState<ActivityLine[]>([]);
  const [macrosWritten, setMacrosWritten] = useState<Record<string, number> | null>(
    null
  );
  const activitySeq = useRef(0);
  const activityScrollRef = useRef<HTMLDivElement | null>(null);
  const lastLoggedLive = useRef<string | null>(null);
  const busyStartedAt = useRef<number | null>(null);
  const clientRunIdRef = useRef<string | null>(null);
  const exclusiveHeldRef = useRef(false);
  const gotProbeProgressRef = useRef(false);
  const lastProgressAtRef = useRef(0);
  const lastProgressMsgRef = useRef<string | null>(null);
  const { subscribeProbeProgress } = useWebSocketContext();

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
  const isAtcMulti = routine?.selection === 'atc_multi';
  const potCells = useMemo(
    () => buildAtcPotCells(toolsUnified, atcPockets),
    [toolsUnified, atcPockets]
  );
  const selectedTools = useMemo(() => {
    const tools: number[] = [];
    for (const pot of selectedPots) {
      const cell = potCells.find((c) => c.pot === pot);
      if (cell?.toolNumber != null) tools.push(cell.toolNumber);
    }
    return tools;
  }, [selectedPots, potCells]);

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
    setSelectedPots([]);
    setResults(null);
    setError(null);
    if (phase !== 'wizard' && phase !== 'poison') {
      setPhase('idle');
      setStatusLine('Ready');
      setWizardStep('write');
      setStepUi('ready');
      setStepLog('');
      setActivityLog([]);
      setMacrosWritten(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reset on routine/mode
  }, [routineId, effectiveMode]);

  const freshness = assessMacroFreshness(required, params, macros);
  const operating = (machineStatus || '').toLowerCase() === 'operating';
  const macrosReady =
    !isAtcMulti &&
    required.every((m) => {
      const v = params[m];
      if (v == null || Number.isNaN(v)) return false;
      if (isPoisonValue(m, v)) return false;
      if (m === '900' && !isValidWcs(v)) return false;
      if (m === '900' && !Number.isInteger(v)) return false;
      return true;
    });
  const canRun =
    !busy &&
    !operating &&
    modeEntry != null &&
    (isAtcMulti ? selectedTools.length > 0 : macrosReady);

  const dialogOpen = phase === 'wizard' || phase === 'poison';
  const controlsDisabled = busy || dialogOpen;

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

  const appendActivity = useCallback((msg: string, level: ActivityLevel = 'info') => {
    activitySeq.current += 1;
    const line: ActivityLine = {
      id: activitySeq.current,
      at: formatActivityTime(),
      msg,
      level,
    };
    setActivityLog((prev) => [...prev, line]);
  }, []);

  const endExclusiveHold = useCallback(async () => {
    if (!exclusiveHeldRef.current) return;
    exclusiveHeldRef.current = false;
    clientRunIdRef.current = null;
    try {
      await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/exclusive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: false }),
      });
    } catch {
      // Dialog close must not hang on exclusive end failures.
    }
  }, [machineId]);

  const beginExclusiveHold = useCallback(async () => {
    const runId =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `probe-${Date.now()}`;
    clientRunIdRef.current = runId;
    gotProbeProgressRef.current = false;
    lastProgressAtRef.current = 0;
    lastProgressMsgRef.current = null;
    try {
      await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/exclusive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: true }),
      });
      exclusiveHeldRef.current = true;
      appendActivity('Exclusive telnet hold — fleet polling paused');
    } catch (e) {
      appendActivity(
        `Exclusive hold failed: ${e instanceof Error ? e.message : 'request error'}`,
        'warn'
      );
    }
    return runId;
  }, [machineId, appendActivity]);

  useEffect(() => {
    const el = activityScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [activityLog]);

  // Server probe_progress → ACTIVITY (preferred over poller Live lines).
  useEffect(() => {
    if (!dialogOpen) return;
    return subscribeProbeProgress(machineId, (ev) => {
      const runId = clientRunIdRef.current;
      if (runId && ev.client_run_id && ev.client_run_id !== runId) return;
      gotProbeProgressRef.current = true;
      lastProgressAtRef.current = Date.now();
      let msg = ev.message || `${ev.api_step}/${ev.phase}`;
      if (ev.snap) {
        msg += ` · prd3=${ev.snap.prd3_status ?? '—'} op=${ev.snap.operation_status ?? '—'}`;
      }
      if (typeof ev.elapsed_s === 'number') {
        msg += ` (${ev.elapsed_s.toFixed(1)}s)`;
      }
      if (lastProgressMsgRef.current === msg) return;
      lastProgressMsgRef.current = msg;
      const level: ActivityLevel =
        ev.phase === 'error' ? 'fail' : ev.final && ev.phase === 'complete' ? 'ok' : 'info';
      appendActivity(msg, level);
    });
  }, [dialogOpen, machineId, subscribeProbeProgress, appendActivity]);

  // End exclusive hold when dialog closes; also on unmount.
  useEffect(() => {
    if (dialogOpen) return;
    void endExclusiveHold();
  }, [dialogOpen, endExclusiveHold]);

  useEffect(() => {
    return () => {
      void endExclusiveHold();
    };
  }, [endExclusiveHold]);

  // Fallback poller Live lines only until the first probe_progress event.
  useEffect(() => {
    if (!dialogOpen || stepUi !== 'busy') return;
    if (gotProbeProgressRef.current) return;
    const line = formatLiveMachineLine(
      machineStatus,
      memMode,
      memOperationStatus,
      alarms
    );
    if (lastLoggedLive.current === line) return;
    lastLoggedLive.current = line;
    appendActivity(line);
  }, [
    machineStatus,
    memMode,
    memOperationStatus,
    alarms,
    dialogOpen,
    stepUi,
    appendActivity,
  ]);

  // Thin heartbeat only if WS probe_progress has been silent >3s after first event,
  // or no progress yet after 5s.
  useEffect(() => {
    if (!dialogOpen || stepUi !== 'busy') {
      busyStartedAt.current = null;
      return;
    }
    if (busyStartedAt.current == null) {
      busyStartedAt.current = Date.now();
    }
    let lastBeatAt = 0;
    const id = window.setInterval(() => {
      const started = busyStartedAt.current;
      if (started == null) return;
      const now = Date.now();
      const sec = Math.floor((now - started) / 1000);
      if (gotProbeProgressRef.current) {
        if (now - lastProgressAtRef.current >= 3000 && now - lastBeatAt >= 3000) {
          lastBeatAt = now;
          appendActivity(`Still waiting on server… ${sec}s`);
        }
        return;
      }
      if (sec >= 5 && now - lastBeatAt >= 5000) {
        lastBeatAt = now;
        appendActivity(`Still waiting on server… ${sec}s`);
      }
    }, 1000);
    return () => window.clearInterval(id);
  }, [dialogOpen, stepUi, appendActivity]);

  function seedActivity(banner: string): ActivityLine[] {
    activitySeq.current = 0;
    lastLoggedLive.current = null;
    return [
      {
        id: ++activitySeq.current,
        at: formatActivityTime(),
        msg: banner,
        level: 'info',
      },
    ];
  }

  function openWizard() {
    setError(null);
    setResults(null);
    setMacrosWritten(null);
    setWizardStep('write');
    setStepUi('ready');
    setStepLog('');
    setActivityLog(
      seedActivity(
        isAtcMulti
          ? 'EXECUTE — confirming ATC pot selection'
          : 'EXECUTE — starting write macros'
      )
    );
    setPhase('wizard');
    setStatusLine(
      isAtcMulti ? 'Wizard: confirming tools…' : 'Wizard: writing macros…'
    );
    void (async () => {
      await beginExclusiveHold();
      await runWizardStep('write', { force: true });
    })();
  }

  function openPoisonDialog() {
    setError(null);
    setStepUi('ready');
    setStepLog('');
    setActivityLog(seedActivity('POISON — starting sentinel write'));
    setPhase('poison');
    setStatusLine('Poisoning macros…');
    void (async () => {
      await beginExclusiveHold();
      await runPoison({ force: true });
    })();
  }

  function abortDialog() {
    if (busy) return;
    appendActivity('Aborted by operator', 'warn');
    void endExclusiveHold();
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
    const next = WIZARD_STEPS[idx + 1];
    appendActivity(`—— ${wizardStepTitle(next, isAtcMulti)} ——`);
    setWizardStep(next);
    setStepUi('ready');
    setStepLog('');
    lastLoggedLive.current = null;
    // Salt has no immediate motion — start collect as soon as we land on the step.
    if (next === 'salt') {
      void runWizardStep('salt', { force: true });
    }
  }

  async function runWizardStep(
    stepOverride?: WizardStep,
    opts?: { force?: boolean }
  ) {
    if (busy) return;
    if (!opts?.force && (stepUi === 'busy' || stepUi === 'ok')) return;
    const step = stepOverride ?? wizardStep;
    setBusy(true);
    setStepUi('busy');
    setStepLog('Working…');
    setError(null);
    lastLoggedLive.current = null;
    busyStartedAt.current = Date.now();
    try {
      if (step === 'write') {
        if (isAtcMulti) {
          if (selectedTools.length === 0) {
            const msg = 'Select at least one full ATC pot';
            appendActivity(msg, 'fail');
            setStepUi('fail');
            setStepLog(msg);
            setError(msg);
            return;
          }
          setStatusLine('Wizard: confirming tool list…');
          const summary = selectedPots
            .map((pot) => {
              const cell = potCells.find((c) => c.pot === pot);
              return `P${pot}/T${String(cell?.toolNumber ?? '?').padStart(2, '0')}`;
            })
            .join(' · ');
          appendActivity(`BATCH — ${selectedTools.length} tools selected`);
          appendActivity(`BATCH — ${summary}`);
          appendActivity('BATCH — no macros written yet (O8100 per tool on measure)', 'ok');
          setStepUi('ok');
          setStepLog(`OK — ${selectedTools.length} tools queued`);
          setStatusLine('Tool list ready — continue to confirm batch');
          return;
        }
        setStatusLine('Wizard: writing macros…');
        appendActivity('WRITE — opening telnet session');
        appendActivity('WRITE — safety check (block if operating)');
        appendActivity('WRITE — FLDCHG / then WRTMCNM job macros (no MEMSTRT)');
        const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/write`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: routineId,
            mode: effectiveMode,
            params,
            client_run_id: clientRunIdRef.current,
          }),
        });
        appendActivity(`WRITE — response HTTP ${res.status}`);
        const payload = await parseProbeResponse(res);
        if (!res.ok || !payload.ok) {
          const msg = payload.error || `Write failed (HTTP ${res.status})`;
          appendActivity(
            `WRITE failed @ ${payload.phase ?? 'unknown'}: ${msg}`,
            'fail'
          );
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
        appendActivity(
          `WRITE ok in ${(payload.elapsed_s ?? 0).toFixed(1)}s${lines ? ` — ${lines}` : ''}`,
          'ok'
        );
        setStepUi('ok');
        setStepLog(`OK — macros written${lines ? `: ${lines}` : ''}`);
        setStatusLine('Macros written — continue to motion step');
        return;
      }

      if (step === 'motion') {
        if (isAtcMulti) {
          setStatusLine('Wizard: confirm multi-tool measure…');
          appendActivity(
            `MOTION — will change tools and run O8100 for ${selectedTools.length} tools`,
            'warn'
          );
          appendActivity('MOTION — first failure aborts the rest of the batch', 'warn');
          setStepUi('ok');
          setStepLog(`OK — ready to measure ${selectedTools.length} tools`);
          setStatusLine('Confirmed — continue to measure batch');
          return;
        }
        const targetPad = String(modeEntry?.program ?? '').padStart(4, '0');
        setStatusLine('Wizard: MEMSTRT — machine moving…');
        appendActivity('MOTION — opening telnet session');
        appendActivity('MOTION — safety check + wait idle');
        appendActivity(
          `MOTION — CHGMODE MEM → FLDCHG PROGRAM → MEMSTRT O${targetPad}`
        );
        appendActivity('MOTION — machine will move when MEMSTRT succeeds', 'warn');
        const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: routineId,
            mode: effectiveMode,
            params,
            client_run_id: clientRunIdRef.current,
          }),
        });
        appendActivity(`MOTION — response HTTP ${res.status}`);
        const payload = await parseProbeResponse(res);
        if (!res.ok || !payload.ok) {
          const msg = payload.error || `Start failed (HTTP ${res.status})`;
          appendActivity(
            `MOTION failed @ ${payload.phase ?? 'unknown'}: ${msg}`,
            'fail'
          );
          setStepUi('fail');
          setStepLog(msg);
          setError(msg);
          setStatusLine(`Start failed at ${payload.phase ?? 'unknown'}`);
          return;
        }
        const target = payload.target_program ?? modeEntry?.program;
        appendActivity(
          `MOTION ok — O${String(target ?? '').padStart(4, '0')} started (${(payload.elapsed_s ?? 0).toFixed(1)}s)`,
          'ok'
        );
        setStepUi('ok');
        setStepLog(
          `OK — MEMSTRT O${String(target ?? '').padStart(4, '0')} started (${(payload.elapsed_s ?? 0).toFixed(1)}s)`
        );
        setStatusLine(
          `Running O${String(target ?? '').padStart(4, '0')} — continue to collect when ready`
        );
        return;
      }

      // salt = collect + poison, or multi-tool batch measure
      if (isAtcMulti) {
        setStatusLine('Wizard: measuring tool batch…');
        appendActivity(
          `BATCH — measuring ${selectedTools.length} tools via O8100 (#920 each)`
        );
        const res = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/probe/tool-batch`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              tools: selectedTools,
              client_run_id: clientRunIdRef.current,
            }),
          }
        );
        appendActivity(`BATCH — response HTTP ${res.status}`);
        const body = (await res.json().catch(() => ({}))) as {
          ok?: boolean;
          error?: string;
          phase?: string;
          elapsed_s?: number;
          aborted?: boolean;
          tools?: Array<{
            tool: number;
            ok: boolean;
            detail: string;
            elapsed_s: number;
          }>;
          detail?: {
            ok?: boolean;
            error?: string;
            phase?: string;
            elapsed_s?: number;
            aborted?: boolean;
            tools?: Array<{
              tool: number;
              ok: boolean;
              detail: string;
              elapsed_s: number;
            }>;
          };
        };
        const payload = typeof body.detail === 'object' && body.detail != null
          ? body.detail
          : body;
        for (const item of payload.tools ?? []) {
          appendActivity(
            `T${String(item.tool).padStart(2, '0')} — ${item.ok ? 'ok' : 'FAIL'} · ${item.detail} (${item.elapsed_s.toFixed(1)}s)`,
            item.ok ? 'ok' : 'fail'
          );
        }
        if (!res.ok || payload.ok === false) {
          const msg = payload.error || `Batch failed (HTTP ${res.status})`;
          appendActivity(
            `BATCH failed @ ${payload.phase ?? 'unknown'}: ${msg}`,
            'fail'
          );
          setStepUi('fail');
          setStepLog(msg);
          setError(msg);
          setStatusLine(`Batch failed at ${payload.phase ?? 'unknown'}`);
          return;
        }
        appendActivity(
          `BATCH ok — ${payload.tools?.length ?? 0} tools in ${(payload.elapsed_s ?? 0).toFixed(1)}s`,
          'ok'
        );
        setStepUi('ok');
        setStepLog(
          `OK — measured ${payload.tools?.length ?? 0} tools (${(payload.elapsed_s ?? 0).toFixed(1)}s)`
        );
        setStatusLine('Multi-tool measure complete');
        return;
      }

      setStatusLine('Wizard: waiting idle / collect + salt…');
      appendActivity('SALT — opening telnet session');
      appendActivity(
        'SALT — waiting for cycle complete (server polls MEM/PRD3; may take a while)'
      );
      appendActivity('SALT — then REDMCNM #100–#107, then poison job macros');
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/collect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          poison: true,
          client_run_id: clientRunIdRef.current,
        }),
      });
      appendActivity(`SALT — response HTTP ${res.status}`);
      const payload = await parseProbeResponse(res);
      if (!res.ok || !payload.ok) {
        const msg = payload.error || `Collect failed (HTTP ${res.status})`;
        appendActivity(
          `SALT failed @ ${payload.phase ?? 'unknown'}: ${msg}`,
          'fail'
        );
        if (payload.results) {
          setResults(payload.results);
          appendActivity('Partial results were returned — see RESULTS below', 'warn');
        }
        setStepUi('fail');
        setStepLog(msg);
        setError(msg);
        setStatusLine(`Collect failed at ${payload.phase ?? 'unknown'}`);
        return;
      }
      setResults(payload.results ?? null);
      const resultSummary = Object.entries(payload.results ?? {})
        .map(([k, v]) => `#${k}=${v ?? '──'}`)
        .join(' · ');
      if (resultSummary) {
        appendActivity(`SALT — results ${resultSummary}`);
      }
      const poisoned = Object.keys(payload.macros_written ?? {}).length;
      appendActivity(
        `SALT ok in ${(payload.elapsed_s ?? 0).toFixed(1)}s — salted ${poisoned} macros`,
        'ok'
      );
      setStepUi('ok');
      setStepLog(
        `OK — results read · macros salted (${(payload.elapsed_s ?? 0).toFixed(1)}s)`
      );
      setStatusLine(
        `Complete in ${(payload.elapsed_s ?? 0).toFixed(1)}s — macros poisoned`
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      appendActivity(`Request error: ${msg}`, 'fail');
      setStepUi('fail');
      setStepLog(msg);
      setError(msg);
      setStatusLine('Request error');
    } finally {
      setBusy(false);
    }
  }

  async function runPoison(opts?: { force?: boolean }) {
    if (busy) return;
    if (!opts?.force && (stepUi === 'busy' || stepUi === 'ok')) return;
    setBusy(true);
    setStepUi('busy');
    setStepLog('Working…');
    setError(null);
    lastLoggedLive.current = null;
    busyStartedAt.current = Date.now();
    setStatusLine('Poisoning macros…');
    try {
      appendActivity('POISON — opening telnet session');
      appendActivity('POISON — FLDCHG / then WRTMCNM sentinel values');
      const targets = Object.entries(probeCatalog.poison)
        .map(([k, v]) => `#${k}=${v}`)
        .join(' · ');
      if (targets) {
        appendActivity(`POISON — targets ${targets}`);
      }
      const res = await fetch(`${API_BASE_URL}/api/machines/${machineId}/probe/poison`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_run_id: clientRunIdRef.current,
        }),
      });
      appendActivity(`POISON — response HTTP ${res.status}`);
      const payload = await parseProbeResponse(res);
      if (!res.ok || payload.ok === false) {
        const msg =
          payload.error ||
          `Poison failed (HTTP ${res.status})`;
        appendActivity(
          `POISON failed @ ${payload.phase ?? 'unknown'}: ${msg}`,
          'fail'
        );
        setStepUi('fail');
        setStepLog(msg);
        setError(msg);
        setStatusLine('Poison failed');
        return;
      }
      const written = payload.macros_written ?? {};
      const lines = Object.entries(written)
        .map(([k, v]) => `#${k}=${v}`)
        .join(' · ');
      appendActivity(
        `POISON ok in ${(payload.elapsed_s ?? 0).toFixed(1)}s${lines ? ` — ${lines}` : ''}`,
        'ok'
      );
      setStepUi('ok');
      setStepLog(
        `OK — macros poisoned${lines ? `: ${lines}` : ''} (${(payload.elapsed_s ?? 0).toFixed(1)}s)`
      );
      setStatusLine('Macros poisoned');
      setError(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Poison request failed';
      appendActivity(`Request error: ${msg}`, 'fail');
      setStepUi('fail');
      setStepLog(msg);
      setError(msg);
      setStatusLine('Poison failed');
    } finally {
      setBusy(false);
    }
  }

  const activityPanel = (
    <div className="probes-wizard-activity">
      <div className="probes-wizard-activity-title">ACTIVITY</div>
      <div
        className="probes-wizard-activity-scroll"
        ref={activityScrollRef}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {activityLog.length === 0 ? (
          <div className="probes-wizard-activity-line probes-wizard-activity-line--info">
            — waiting —
          </div>
        ) : (
          activityLog.map((line) => (
            <div
              key={line.id}
              className={`probes-wizard-activity-line probes-wizard-activity-line--${line.level}`}
            >
              <span className="probes-wizard-activity-time">{line.at}</span>
              <span className="probes-wizard-activity-msg">{line.msg}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );

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
              {phase === 'wizard' ? ` | WIZARD · ${wizardStepTitle(wizardStep, isAtcMulti)}` : ''}
              {phase === 'poison' ? ' | POISON' : ''}
              {phase === 'complete' ? ' | COMPLETE' : ''}
            </div>
          )}

          <div className={`probes-main${isAtcMulti ? ' probes-main--atc-multi' : ''}`}>
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
              {isAtcMulti ? (
                <AtcPotSelectGrid
                  unified={toolsUnified}
                  numPockets={atcPockets}
                  selectedPots={selectedPots}
                  disabled={controlsDisabled}
                  onChange={setSelectedPots}
                />
              ) : (
                required.map((macro) => {
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
                        inputMode={macro === '900' ? 'numeric' : 'decimal'}
                        value={params[macro] ?? ''}
                        disabled={controlsDisabled}
                        onChange={(e) => {
                          const n =
                            macro === '900'
                              ? Number.parseInt(e.target.value, 10)
                              : Number.parseFloat(e.target.value);
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
              })
              )}
            </div>

            <ProbeCyclePreview
              routineId={routineId}
              params={params}
              selectedTools={selectedTools}
            />
          </div>

          <div className="probes-actions">
            <button
              type="button"
              className="terminal-button-sm danger"
              disabled={!canRun || busy || dialogOpen}
              onClick={() => {
                if (!canRun || busy || dialogOpen) return;
                openWizard();
              }}
              title={
                operating
                  ? 'Machine is operating'
                  : !canRun
                    ? isAtcMulti
                      ? 'Select at least one full ATC pot'
                      : 'Fill valid non-poison params'
                    : 'Open stepped execute wizard'
              }
            >
              [ EXECUTE ]
            </button>
            <button
              type="button"
              className="terminal-button-sm"
              disabled={busy || dialogOpen}
              onClick={() => {
                if (busy || dialogOpen) return;
                openPoisonDialog();
              }}
              title="Open poison confirm dialog"
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
              *{' '}
              {isAtcMulti
                ? 'EXECUTE confirms pot selection then measures each tool with O8100 (abort on first failure).'
                : 'EXECUTE starts write immediately; motion still needs confirm.'}{' '}
              POISON starts on click.
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
            <div className="probes-confirm-title">
              {wizardStepTitle(wizardStep, isAtcMulti)}
            </div>

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
              {wizardStep === 'write' && isAtcMulti && (
                <>
                  <div>
                    Confirm the ATC pot selection. Shatter will measure each selected
                    tool with O8100 (no macros written yet).
                  </div>
                  <div className="probes-confirm-params">
                    {selectedPots.map((pot) => {
                      const cell = potCells.find((c) => c.pot === pot);
                      return (
                        <div key={pot}>
                          P{pot} → T{String(cell?.toolNumber ?? '?').padStart(2, '0')}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
              {wizardStep === 'write' && !isAtcMulti && (
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
                    {isAtcMulti
                      ? `MACHINE WILL CHANGE TOOLS AND MEASURE ${selectedTools.length} TOOLS (O8100 each).`
                      : `MACHINE WILL MOVE. Shatter will MEMSTRT O${String(modeEntry.program).padStart(4, '0')} now.`}
                  </div>
                  <div>
                    {effectiveMode.toUpperCase()} · {routine?.label ?? routineId}
                  </div>
                  <ProbeCyclePreview
                    routineId={routineId}
                    params={params}
                    selectedTools={selectedTools}
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

              {wizardStep === 'salt' && isAtcMulti && (
                <>
                  <div>
                    Shatter will write #920 and MEMSTRT O8100 for each selected tool,
                    waiting for idle between tools. First failure aborts the rest.
                  </div>
                  <div>{selectedTools.length} tools queued</div>
                </>
              )}
              {wizardStep === 'salt' && !isAtcMulti && (
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

              {activityPanel}

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
                onClick={() => abortDialog()}
              >
                [ ABORT ]
              </button>

              {(stepUi === 'fail' ||
                (stepUi === 'ready' && wizardStep === 'motion')) && (
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
                    : isAtcMulti
                      ? '[ CONFIRM BATCH ]'
                      : '[ START MOTION ]'}
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
                    appendActivity('Sequence complete', 'ok');
                  }}
                >
                  [ DONE ]
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {phase === 'poison' && (
        <div className="probes-confirm-overlay" role="dialog" aria-modal="true">
          <div className="probes-confirm-box probes-wizard-box">
            <div className="probes-confirm-title">POISON MACROS</div>
            <div className="probes-confirm-body">
              <div className="probes-confirm-warn">
                Writes sentinel values so a stale probe cycle cannot re-run. No MEMSTRT /
                no axis motion. Started automatically from [ POISON ].
              </div>
              <div className="probes-confirm-params">
                {Object.entries(probeCatalog.poison).map(([m, v]) => (
                  <div key={m}>
                    #{m} → {v}
                  </div>
                ))}
              </div>

              {activityPanel}

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
              {stepUi !== 'ok' && (
                <button
                  type="button"
                  className="terminal-button-sm"
                  disabled={busy}
                  onClick={() => abortDialog()}
                >
                  [ ABORT ]
                </button>
              )}

              {stepUi === 'fail' && (
                <button
                  type="button"
                  className="terminal-button-sm danger"
                  disabled={busy}
                  onClick={() => {
                    if (busy) return;
                    void runPoison({ force: true });
                  }}
                >
                  [ RETRY ]
                </button>
              )}

              {stepUi === 'busy' && (
                <button type="button" className="terminal-button-sm" disabled>
                  [ WORKING… ]
                </button>
              )}

              {stepUi === 'ok' && (
                <button
                  type="button"
                  className="terminal-button-sm"
                  disabled={busy}
                  onClick={() => {
                    setPhase('idle');
                    setStepUi('ready');
                    setStepLog('');
                    setStatusLine('Macros poisoned');
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
