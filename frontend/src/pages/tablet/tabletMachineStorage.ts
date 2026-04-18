/** Persists chosen CNC machine id per browser (multi-tablet / single build). */
export const TABLET_MACHINE_STORAGE_KEY = 'shatter.tablet.machine_id';

export function readStoredTabletMachineId(): number | null {
  try {
    const raw = localStorage.getItem(TABLET_MACHINE_STORAGE_KEY);
    if (raw == null || !String(raw).trim()) {
      return null;
    }
    const n = Number.parseInt(String(raw).trim(), 10);
    if (!Number.isFinite(n) || n <= 0) {
      return null;
    }
    return n;
  } catch {
    return null;
  }
}

export function writeStoredTabletMachineId(machineId: number): void {
  try {
    localStorage.setItem(TABLET_MACHINE_STORAGE_KEY, String(machineId));
  } catch {
    /* quota / private mode */
  }
}

export function clearStoredTabletMachineId(): void {
  try {
    localStorage.removeItem(TABLET_MACHINE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
