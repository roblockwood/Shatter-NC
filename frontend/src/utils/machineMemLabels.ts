/** MEM mode from CNC poll (`mem_mode`). */
export function formatMemMode(mode: number | undefined): string {
  if (mode === undefined || mode === null || Number.isNaN(Number(mode))) return '—';
  const labels = ['MANUAL', 'MDI', 'MEMORY', 'EDIT', 'MDI MAN', 'MEM EDIT'] as const;
  const i = Math.floor(Number(mode));
  if (i >= 0 && i < labels.length) return labels[i];
  return `MODE ${mode}`;
}

/** MEM operation_status from CNC poll (`mem_operation_status`). */
export function formatMemOperationStatus(status: number | undefined): string {
  if (status === undefined || status === null || Number.isNaN(Number(status))) return '—';
  const labels = ['RESET', 'OPERATION', 'TEMP STOP', 'BLOCK STOP'] as const;
  const i = Math.floor(Number(status));
  if (i >= 0 && i < labels.length) return labels[i];
  return `OP ${status}`;
}
