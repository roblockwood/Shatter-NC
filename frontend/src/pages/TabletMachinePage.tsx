import { useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { MachineCard } from '../components/MachineCard';
import { AsciiLoadingScreen } from '../components/AsciiLoadingScreen';
import { useWebSocketContext } from '../contexts/WebSocketContext';
import './TabletMachinePage.css';

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

export const TabletMachinePage = () => {
  const { machineId: machineIdSegment } = useParams<{ machineId?: string }>();
  const [searchParams] = useSearchParams();

  const targetMachineId = useMemo(() => {
    const fromPath = parsePositiveInt(machineIdSegment);
    if (fromPath !== null) {
      return fromPath;
    }
    const fromQuery = parsePositiveInt(searchParams.get('machineId'));
    if (fromQuery !== null) {
      return fromQuery;
    }
    return parsePositiveInt(import.meta.env.VITE_TABLET_MACHINE_ID ?? null);
  }, [machineIdSegment, searchParams]);

  const { machines, isConnected } = useWebSocketContext();

  const machine =
    targetMachineId !== null
      ? machines.find((m) => m.machine_id === targetMachineId)
      : undefined;

  if (targetMachineId === null) {
    return (
      <div className="tablet-machine-page">
        <div className="tablet-machine-page-state text-error">
          Missing machine id. Use path /tablet/ followed by the numeric id, query ?machineId=, or set
          VITE_TABLET_MACHINE_ID.
        </div>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="tablet-machine-page">
        <AsciiLoadingScreen />
      </div>
    );
  }

  if (machines.length === 0) {
    return (
      <div className="tablet-machine-page">
        <div className="tablet-machine-page-state text-error">
          No CNC machines reported by the server yet.
        </div>
      </div>
    );
  }

  if (!machine) {
    return (
      <div className="tablet-machine-page">
        <div className="tablet-machine-page-state text-error">
          Machine id {targetMachineId} not found in fleet data. Check the id or WebSocket connection.
        </div>
      </div>
    );
  }

  return (
    <div className="tablet-machine-page">
      <div className="tablet-machine-inner">
        <MachineCard
          machine={machine}
          editMode={false}
          isExpanded
          canEdit={false}
          isAnyMachineEditing={false}
          onCollapse={undefined}
        />
      </div>
    </div>
  );
};
