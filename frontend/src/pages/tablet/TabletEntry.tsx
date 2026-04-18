import { Navigate } from 'react-router-dom';
import { useSearchParams } from 'react-router-dom';
import { useEffect, useMemo } from 'react';
import { TabletSetupPanel } from './TabletSetupPanel';
import { readStoredTabletCompressorId, writeStoredTabletCompressorId } from './tabletCompressorStorage';
import { TABLET_DEFAULT_COMPRESSOR_PANE } from './tabletCompressorPaneConfig';
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
 * `/tablet` — resolve asset from:
 * 1) ?machineId= / ?compressorId= (saved to localStorage for next launch)
 * 2) localStorage (per tablet device)
 * 3) optional VITE_TABLET_MACHINE_ID / VITE_TABLET_COMPRESSOR_ID
 * 4) setup form
 *
 * Query params beat storage. Between storages: CNC machine id first, then compressor id.
 */
export const TabletEntry = () => {
  const [searchParams] = useSearchParams();

  const resolution = useMemo(() => {
    const qMachine = parsePositiveInt(searchParams.get('machineId'));
    const qCompressor = parsePositiveInt(searchParams.get('compressorId'));
    const fromStorageMachine = readStoredTabletMachineId();
    const fromStorageCompressor = readStoredTabletCompressorId();
    const fromEnvMachine = parsePositiveInt(import.meta.env.VITE_TABLET_MACHINE_ID ?? null);
    const fromEnvCompressor = parsePositiveInt(import.meta.env.VITE_TABLET_COMPRESSOR_ID ?? null);
    return {
      qMachine,
      qCompressor,
      fromStorageMachine,
      fromStorageCompressor,
      fromEnvMachine,
      fromEnvCompressor,
    };
  }, [searchParams]);

  const target = useMemo(() => {
    const r = resolution;
    if (r.qMachine !== null) {
      return { kind: 'machine' as const, id: r.qMachine };
    }
    if (r.qCompressor !== null) {
      return { kind: 'compressor' as const, id: r.qCompressor };
    }
    if (r.fromStorageMachine !== null) {
      return { kind: 'machine' as const, id: r.fromStorageMachine };
    }
    if (r.fromStorageCompressor !== null) {
      return { kind: 'compressor' as const, id: r.fromStorageCompressor };
    }
    if (r.fromEnvMachine !== null) {
      return { kind: 'machine' as const, id: r.fromEnvMachine };
    }
    if (r.fromEnvCompressor !== null) {
      return { kind: 'compressor' as const, id: r.fromEnvCompressor };
    }
    return null;
  }, [resolution]);

  useEffect(() => {
    const r = resolution;
    if (r.qMachine !== null) {
      writeStoredTabletMachineId(r.qMachine);
    } else if (r.qCompressor !== null) {
      writeStoredTabletCompressorId(r.qCompressor);
    } else if (r.fromEnvMachine !== null && r.fromStorageMachine === null) {
      writeStoredTabletMachineId(r.fromEnvMachine);
    } else if (r.fromEnvCompressor !== null && r.fromStorageCompressor === null) {
      writeStoredTabletCompressorId(r.fromEnvCompressor);
    }
  }, [
    resolution.qMachine,
    resolution.qCompressor,
    resolution.fromEnvMachine,
    resolution.fromEnvCompressor,
    resolution.fromStorageMachine,
    resolution.fromStorageCompressor,
  ]);

  if (target !== null) {
    if (target.kind === 'machine') {
      return <Navigate to={`/tablet/${target.id}/${TABLET_DEFAULT_PANE}`} replace />;
    }
    return (
      <Navigate
        to={`/tablet/compressor/${target.id}/${TABLET_DEFAULT_COMPRESSOR_PANE}`}
        replace
      />
    );
  }

  return (
    <div className="tablet-route tablet-setup-page">
      <section className="tablet-setup-section" aria-labelledby="tablet-entry-cnc-heading">
        <h2 id="tablet-entry-cnc-heading" className="tablet-setup-section-heading">
          CNC machine
        </h2>
        <TabletSetupPanel kind="machine" />
      </section>
      <section className="tablet-setup-section" aria-labelledby="tablet-entry-comp-heading">
        <h2 id="tablet-entry-comp-heading" className="tablet-setup-section-heading">
          Air compressor
        </h2>
        <TabletSetupPanel kind="compressor" />
      </section>
    </div>
  );
};
