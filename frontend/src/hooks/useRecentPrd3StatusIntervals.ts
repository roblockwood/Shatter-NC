import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config/api';

export interface Prd3StatusIntervalRow {
  status: string | null;
  status_code?: number | null;
  program_no?: string | null;
  error_no?: string | null;
  start_time: string;
  end_time: string | null;
  label: string;
  detail?: string | null;
  duration_seconds?: number | null;
}

export function useRecentPrd3StatusIntervals(
  machineId: number,
  limit: number
): { intervals: Prd3StatusIntervalRow[]; loading: boolean } {
  const [intervals, setIntervals] = useState<Prd3StatusIntervalRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchIntervals = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/prd3-status-history?limit=${limit}&offset=0`
        );
        if (!response.ok) {
          if (!cancelled) setIntervals([]);
          return;
        }
        const data: Prd3StatusIntervalRow[] = await response.json();
        if (!cancelled) setIntervals(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setIntervals([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void fetchIntervals();
    const t = window.setInterval(fetchIntervals, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [machineId, limit]);

  return { intervals, loading };
}
