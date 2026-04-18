import { Navigate } from 'react-router-dom';
import { useSearchParams } from 'react-router-dom';
import { useEffect, useMemo } from 'react';
import { TabletSetupPanel } from './TabletSetupPanel';
import { readStoredTabletMachineId, writeStoredTabletMachineId } from './tabletMachineStorage';
import { TABLET_DEFAULT_PANE } from './tabletPaneConfig';
import './tablet.css';

function parsePositiveInt(raw: string | undefined | null): number | null {
  if (raw == null || !String(raw).trim()) {
    return null;
  }
  const n = Number.parseInt(String(raw).trim(), 10);
  if (!Number.isFinite(n) || n <= 0) {
    return null;
  }
  return n;
}

/**
 * `/tablet` — resolve machine id from:
 * 1) ?machineId= (saved to localStorage for next launch)
 * 2) localStorage (per tablet device)
 * 3) optional VITE_TABLET_MACHINE_ID (deploy default)
 * 4) setup form
 */
export const TabletEntry = () => {
  const [searchParams] = useSearchParams();

  const resolution = useMemo(() => {
    const fromQuery = parsePositiveInt(searchParams.get('machineId'));
    const fromStorage = readStoredTabletMachineId();
    const fromEnv = parsePositiveInt(import.meta.env.VITE_TABLET_MACHINE_ID ?? null);
    return { fromQuery, fromStorage, fromEnv };
  }, [searchParams]);

  const targetId = useMemo(() => {
    if (resolution.fromQuery !== null) {
      return resolution.fromQuery;
    }
    if (resolution.fromStorage !== null) {
      return resolution.fromStorage;
    }
    if (resolution.fromEnv !== null) {
      return resolution.fromEnv;
    }
    return null;
  }, [resolution]);

  useEffect(() => {
    if (resolution.fromQuery !== null) {
      writeStoredTabletMachineId(resolution.fromQuery);
    } else if (resolution.fromEnv !== null && resolution.fromStorage === null) {
      writeStoredTabletMachineId(resolution.fromEnv);
    }
  }, [resolution.fromQuery, resolution.fromEnv, resolution.fromStorage]);

  if (targetId !== null) {
    return (
      <Navigate to={`/tablet/${targetId}/${TABLET_DEFAULT_PANE}`} replace />
    );
  }

  return (
    <div className="tablet-route">
      <TabletSetupPanel />
    </div>
  );
};
