import type { CompressorStatus } from '../hooks/useWebSocket';

export function asRecord(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : undefined;
}

export interface SigmaPanelFields {
  panelClock?: string;
  systemStatusDisplay?: string;
  keyLabel?: string;
  keyToggle?: string;
  keyCode?: string;
  keyRight?: string;
  runHoursDisplay?: string;
  loadHoursDisplay?: string;
  maintenanceHoursDisplay?: string;
}

export interface LedDataLike {
  powerOn?: boolean;
  idle?: boolean;
  load?: boolean;
  error?: boolean;
  errorVoltage?: boolean;
  comError?: boolean;
  maintenanceDue?: boolean;
  remoteEnabled?: boolean;
  clockEnabled?: boolean;
}

export function readSigmaPanel(operational: Record<string, unknown> | undefined): SigmaPanelFields {
  const sp = asRecord(operational?.sigmaPanel);
  if (!sp) return {};
  return {
    panelClock: typeof sp.panelClock === 'string' ? sp.panelClock : undefined,
    systemStatusDisplay: typeof sp.systemStatusDisplay === 'string' ? sp.systemStatusDisplay : undefined,
    keyLabel: typeof sp.keyLabel === 'string' ? sp.keyLabel : undefined,
    keyToggle: typeof sp.keyToggle === 'string' ? sp.keyToggle : undefined,
    keyCode: typeof sp.keyCode === 'string' ? sp.keyCode : undefined,
    keyRight: typeof sp.keyRight === 'string' ? sp.keyRight : undefined,
    runHoursDisplay: typeof sp.runHoursDisplay === 'string' ? sp.runHoursDisplay : undefined,
    loadHoursDisplay: typeof sp.loadHoursDisplay === 'string' ? sp.loadHoursDisplay : undefined,
    maintenanceHoursDisplay:
      typeof sp.maintenanceHoursDisplay === 'string' ? sp.maintenanceHoursDisplay : undefined,
  };
}

export function readLedData(raw: unknown): LedDataLike {
  const top = asRecord(raw);
  if (!top) return {};
  const inner = asRecord(top['led-data']) ?? top;
  return inner as LedDataLike;
}

export function readPressureLine(operational: Record<string, unknown> | undefined): string {
  const p = asRecord(operational?.pressure);
  if (!p) return '—';
  const v = p.value;
  const u = p.unit;
  const num = typeof v === 'number' ? v : Number(v);
  const unit = typeof u === 'string' ? u : '';
  if (Number.isFinite(num)) {
    return `${Math.round(num * 10) / 10}${unit ? unit : ''}`.trim();
  }
  return '—';
}

export function readOutletTempLine(operational: Record<string, unknown> | undefined): string {
  const t = asRecord(operational?.outletTemp);
  if (!t) return '—';
  const v = t.value;
  const u = t.unit;
  const num = typeof v === 'number' ? v : Number(v);
  const unit = typeof u === 'string' ? u : '';
  if (Number.isFinite(num)) {
    return `${Math.round(num)}${unit ? unit : ''}`.trim();
  }
  return '—';
}

export interface NumericPressureTemp {
  psi: number | null;
  psiUnit: string | null;
  outletTemp: number | null;
  tempUnit: string | null;
}

/** Numeric values for charts / live tail (matches backend sample metrics keys when sourced from operational). */
export function readNumericPressureTemp(operational: Record<string, unknown> | undefined): NumericPressureTemp {
  const p = asRecord(operational?.pressure);
  const t = asRecord(operational?.outletTemp);
  const pv = p?.value;
  const tv = t?.value;
  const psiNum = typeof pv === 'number' ? pv : typeof pv === 'string' ? Number(pv) : NaN;
  const tempNum = typeof tv === 'number' ? tv : typeof tv === 'string' ? Number(tv) : NaN;
  const pu = p?.unit;
  const tu = t?.unit;
  return {
    psi: Number.isFinite(psiNum) ? psiNum : null,
    psiUnit: typeof pu === 'string' && pu.trim() ? pu.trim() : null,
    outletTemp: Number.isFinite(tempNum) ? tempNum : null,
    tempUnit: typeof tu === 'string' && tu.trim() ? tu.trim() : null,
  };
}

/** Human-readable controller / HMI status line (matches panel LCD priority). */
export function readCompressorControllerStatus(compressor: CompressorStatus): string {
  const metrics = compressor.metrics || {};
  const operational = asRecord(metrics.operational);
  const sigma = readSigmaPanel(operational);
  return (
    sigma.systemStatusDisplay?.trim() ||
    (typeof operational?.compressorState === 'string' ? operational.compressorState : '') ||
    compressor.status?.trim() ||
    ''
  );
}

/** LOAD / IDLE from SC2 LEDs, with fallback to status string keywords. */
export function formatLoadIdle(led: LedDataLike, compressorStatus?: string): string {
  if (led.load === true) return 'LOAD';
  if (led.idle === true) return 'IDLE';
  const s = (compressorStatus || '').toLowerCase();
  if (s.includes('load') && !s.includes('unload')) return 'LOAD';
  if (s.includes('idle') || s.includes('standby')) return 'IDLE';
  return '—';
}
