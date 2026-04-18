import { Navigate, useParams } from 'react-router-dom';
import { TABLET_DEFAULT_PANE } from './tabletPaneConfig';
import './tablet.css';

function parsePositiveInt(raw: string | undefined): number | null {
  if (raw == null || !String(raw).trim()) {
    return null;
  }
  const n = Number.parseInt(String(raw).trim(), 10);
  if (!Number.isFinite(n) || n <= 0) {
    return null;
  }
  return n;
}

/** `/tablet/:machineId` → canonical `/tablet/:machineId/status` */
export const TabletRedirectToDefaultPane = () => {
  const { machineId } = useParams<{ machineId: string }>();
  const id = parsePositiveInt(machineId);

  if (id === null) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">Invalid machine id in URL.</div>
      </div>
    );
  }

  return <Navigate to={`/tablet/${id}/${TABLET_DEFAULT_PANE}`} replace />;
};
