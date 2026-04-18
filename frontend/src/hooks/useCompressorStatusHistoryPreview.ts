import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config/api';

export interface CompressorStatusHistoryEventRow {
  time: string;
  compressor_id: number;
  status: string;
  previous_status?: string | null;
  metrics?: Record<string, unknown> | null;
}

export function useCompressorStatusHistoryPreview(
  compressorId: number,
  limit: number
): { events: CompressorStatusHistoryEventRow[]; loading: boolean } {
  const [events, setEvents] = useState<CompressorStatusHistoryEventRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const r = await fetch(
          `${API_BASE_URL}/api/compressors/${compressorId}/status-history?limit=${limit}&offset=0`,
          { cache: 'no-store' }
        );
        if (!r.ok) {
          if (!cancelled) setEvents([]);
          return;
        }
        const data = await r.json();
        if (!cancelled) setEvents(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    const t = window.setInterval(load, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [compressorId, limit]);

  return { events, loading };
}
