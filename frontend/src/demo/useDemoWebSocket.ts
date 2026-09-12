import { useCallback, useEffect, useRef, useState } from 'react';
import type { MachineStatus, CompressorStatus, ProbeProgressCallback } from '../hooks/useWebSocket';
import {
  createInitialCompressors,
  createInitialMachines,
  tickOperatingMachine,
} from './fixtures/fleet';

const TICK_MS = 4000;

export function useDemoWebSocket() {
  const [machines, setMachines] = useState<Map<number, MachineStatus>>(() => {
    const map = new Map<number, MachineStatus>();
    createInitialMachines().forEach((m) => map.set(m.machine_id, m));
    return map;
  });
  const [compressors, setCompressors] = useState<Map<number, CompressorStatus>>(() => {
    const map = new Map<number, CompressorStatus>();
    createInitialCompressors().forEach((c) => map.set(c.compressor_id, c));
    return map;
  });
  const [isConnected, setIsConnected] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setIsConnected(true);

    intervalRef.current = setInterval(() => {
      setMachines((prev) => {
        const next = new Map(prev);
        for (const [id, machine] of prev) {
          next.set(id, tickOperatingMachine(machine));
        }
        return next;
      });
      setCompressors((prev) => {
        const next = new Map(prev);
        for (const [id, c] of prev) {
          next.set(id, {
            ...c,
            poll_timestamp: new Date().toISOString(),
            last_successful_poll_at: new Date().toISOString(),
          });
        }
        return next;
      });
    }, TICK_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setIsConnected(false);
    };
  }, []);

  const noopRemoveMachine = useCallback((_machineId: number) => {}, []);
  const noopAddMachine = useCallback((_machine: MachineStatus) => {}, []);
  const noopRemoveCompressor = useCallback((_compressorId: number) => {}, []);
  const noopAddCompressor = useCallback((_c: CompressorStatus) => {}, []);
  const noopSubscribeProbeProgress = useCallback(
    (_machineId: number, _cb: ProbeProgressCallback) => () => {},
    []
  );

  return {
    machines: Array.from(machines.values()),
    compressors: Array.from(compressors.values()),
    isConnected,
    removeMachine: noopRemoveMachine,
    addMachine: noopAddMachine,
    removeCompressor: noopRemoveCompressor,
    addCompressor: noopAddCompressor,
    subscribeProbeProgress: noopSubscribeProbeProgress,
  };
}
