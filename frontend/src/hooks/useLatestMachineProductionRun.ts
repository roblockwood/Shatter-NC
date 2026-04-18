import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config/api';

export type LatestProductionRunRow = {
  program_no: string | null;
  run_start: string;
  run_end: string;
  cycles: number;
  part_count: number;
  segments: { status: string | null; start_time: string; end_time: string }[];
};

export function useLatestMachineProductionRun(machineId: number): {
  latestRun: LatestProductionRunRow | null;
  latestRunLoading: boolean;
} {
  const [latestRun, setLatestRun] = useState<LatestProductionRunRow | null>(null);
  const [latestRunLoading, setLatestRunLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchLatestRun = async () => {
      try {
        setLatestRunLoading(true);
        const endTime = new Date();
        const startTime = new Date(endTime);
        startTime.setDate(startTime.getDate() - 7);

        const resp = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/production-runs-timeline?start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}&limit=1&offset=0`
        );
        if (!resp.ok) {
          if (!cancelled) setLatestRun(null);
          return;
        }
        const data = await resp.json();
        const runs = Array.isArray(data) ? data : [];
        if (!cancelled) {
          setLatestRun(runs[0] || null);
        }
      } catch {
        if (!cancelled) setLatestRun(null);
      } finally {
        if (!cancelled) setLatestRunLoading(false);
      }
    };

    void fetchLatestRun();
    return () => {
      cancelled = true;
    };
  }, [machineId]);

  return { latestRun, latestRunLoading };
}

/** Recent completed production runs (same API window as dashboard card). */
export function useRecentMachineProductionRuns(
  machineId: number,
  limit: number
): { runs: LatestProductionRunRow[]; runsLoading: boolean } {
  const [runs, setRuns] = useState<LatestProductionRunRow[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchRuns = async () => {
      try {
        setRunsLoading(true);
        const endTime = new Date();
        const startTime = new Date(endTime);
        startTime.setDate(startTime.getDate() - 7);

        const resp = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/production-runs-timeline?start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}&limit=${limit}&offset=0`
        );
        if (!resp.ok) {
          if (!cancelled) setRuns([]);
          return;
        }
        const data = await resp.json();
        const arr = Array.isArray(data) ? data : [];
        if (!cancelled) setRuns(arr);
      } catch {
        if (!cancelled) setRuns([]);
      } finally {
        if (!cancelled) setRunsLoading(false);
      }
    };

    void fetchRuns();
    const t = window.setInterval(fetchRuns, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [machineId, limit]);

  return { runs, runsLoading };
}
