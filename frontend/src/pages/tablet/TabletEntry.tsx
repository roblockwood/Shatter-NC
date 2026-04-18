import { Navigate } from 'react-router-dom';
import { useSearchParams } from 'react-router-dom';
import { useMemo } from 'react';
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
 * Handles `/tablet` without path segments: optional `?machineId=` or build-time fallback, else error.
 */
export const TabletEntry = () => {
  const [searchParams] = useSearchParams();

  const targetId = useMemo(() => {
    const fromQuery = parsePositiveInt(searchParams.get('machineId'));
    if (fromQuery !== null) {
      return fromQuery;
    }
    return parsePositiveInt(import.meta.env.VITE_TABLET_MACHINE_ID ?? null);
  }, [searchParams]);

  if (targetId !== null) {
    return (
      <Navigate
        to={`/tablet/${targetId}/${TABLET_DEFAULT_PANE}`}
        replace
      />
    );
  }

  return (
    <div className="tablet-route">
      <div className="tablet-route-state text-error">
        Missing machine id. Use URL path /tablet/ numeric id / pane slug, query ?machineId= on /tablet, or set
        VITE_TABLET_MACHINE_ID.
      </div>
    </div>
  );
};
