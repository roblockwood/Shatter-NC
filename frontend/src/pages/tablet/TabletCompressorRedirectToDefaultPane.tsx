import { Navigate, useParams } from 'react-router-dom';
import { TABLET_DEFAULT_COMPRESSOR_PANE } from './tabletCompressorPaneConfig';
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

/** `/tablet/compressor/:compressorId` → canonical pane URL */
export const TabletCompressorRedirectToDefaultPane = () => {
  const { compressorId } = useParams<{ compressorId: string }>();
  const id = parsePositiveInt(compressorId);

  if (id === null) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">Invalid compressor id in URL.</div>
      </div>
    );
  }

  return (
    <Navigate to={`/tablet/compressor/${id}/${TABLET_DEFAULT_COMPRESSOR_PANE}`} replace />
  );
};
