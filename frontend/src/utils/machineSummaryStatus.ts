import type { MachineStatus } from '../hooks/useWebSocket';

export function machineSummaryStatusDisplay(machine: MachineStatus): string {
  if (!machine.is_online) return 'OFF';
  const status = machine.status?.toLowerCase() || '';
  if (status === 'error' || status.includes('error')) return 'ERROR';
  if (status === 'operating' || status.includes('operating') || status.includes('running')) return 'OPERATING';
  if (status === 'standby' || status.includes('standby') || status.includes('idle')) return 'IDLE';
  if (status === 'stopped' || status.includes('stopped')) return 'STOPPED';
  if (status === 'off' || status.includes('off')) return 'OFF';
  return 'UNKNOWN';
}

export function machineSummaryStatusValueClass(machine: MachineStatus): string {
  if (!machine.is_online) return 'text-error';
  const status = machine.status?.toLowerCase() || '';
  if (status === 'error' || status.includes('error')) return 'text-error';
  return 'text-success';
}

export function activeProgramNameFromMachine(machine: MachineStatus): string | null {
  const programName = machine.program_name;
  if (
    programName &&
    programName !== '----' &&
    programName !== 'undefined' &&
    programName !== 'null' &&
    typeof programName === 'string' &&
    programName.trim() !== ''
  ) {
    return programName;
  }
  return null;
}
