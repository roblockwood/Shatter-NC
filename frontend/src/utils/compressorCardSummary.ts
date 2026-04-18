import type { CompressorStatus } from '../hooks/useWebSocket';
import {
  asRecord,
  readCompressorControllerStatus,
  readOutletTempLine,
  readPressureLine,
} from './compressorTelemetry';

export function compressorCardStatusDisplay(c: CompressorStatus): string {
  if (!c.is_online) return 'OFFLINE';
  const s = (c.status || '').toLowerCase();
  if (s === 'offline') return 'OFFLINE';
  if (s.includes('error')) return 'ERROR';
  return 'ONLINE';
}

export function compressorCardStatusValueClass(c: CompressorStatus): string {
  const d = compressorCardStatusDisplay(c);
  if (d === 'OFFLINE' || d === 'ERROR') return 'text-error';
  return 'text-success';
}

export function compressorCardTelemetryLines(c: CompressorStatus): {
  psiLine: string;
  tempLine: string;
  controllerDetail: string;
} {
  const metrics = c.metrics || {};
  const operational = asRecord(metrics.operational);
  const online = c.is_online;
  return {
    psiLine: online ? readPressureLine(operational) : '—',
    tempLine: online ? readOutletTempLine(operational) : '—',
    controllerDetail: readCompressorControllerStatus(c),
  };
}
