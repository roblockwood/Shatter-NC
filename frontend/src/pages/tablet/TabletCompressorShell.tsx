import { useEffect, useState } from 'react';
import { Link, Navigate, NavLink, useParams } from 'react-router-dom';
import { AsciiLoadingScreen } from '../../components/AsciiLoadingScreen';
import { AlarmPane } from '../../components/machine-detail/AlarmPane';
import { CompressorOverviewPane } from '../../components/machine-detail/CompressorOverviewPane';
import { CompressorPanelPane } from '../../components/machine-detail/CompressorPanelPane';
import { CompressorStatusHistoryPane } from '../../components/machine-detail/CompressorStatusHistoryPane';
import { CompressorStatusTimelinePane } from '../../components/machine-detail/CompressorStatusTimelinePane';
import { CompressorTelemetrySeriesPane } from '../../components/machine-detail/CompressorTelemetrySeriesPane';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import type { CompressorStatus } from '../../hooks/useWebSocket';
import { asRecord } from '../../utils/compressorTelemetry';
import {
  isTabletCompressorPaneSlug,
  TABLET_COMPRESSOR_NAV_ITEMS,
  TABLET_DEFAULT_COMPRESSOR_PANE,
  type TabletCompressorPaneSlug,
} from './tabletCompressorPaneConfig';
import { writeStoredTabletCompressorId } from './tabletCompressorStorage';
import { TabletScreensaver } from './TabletScreensaver';
import { useTabletCompressorPaneSwipe } from './useTabletCompressorPaneSwipe';
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

function TabletCompressorPaneContent({
  slug,
  compressor,
}: {
  slug: TabletCompressorPaneSlug;
  compressor: CompressorStatus;
}) {
  const pollTs = compressor.last_successful_poll_at || compressor.poll_timestamp;

  switch (slug) {
    case 'panel':
      return (
        <div className="tablet-pane-root">
          <CompressorPanelPane compressor={compressor} />
        </div>
      );
    case 'overview':
      return (
        <div className="tablet-pane-root">
          <CompressorOverviewPane compressor={compressor} />
        </div>
      );
    case 'alarms':
      return (
        <div className="tablet-pane-root">
          <AlarmPane
            machineId={compressor.compressor_id}
            currentAlarms={compressor.alarms}
            pollTimestamp={pollTs}
            pollIntervalSeconds={compressor.poll_interval_seconds ?? 5}
          />
        </div>
      );
    case 'status':
      return (
        <div className="tablet-pane-root">
          <CompressorStatusTimelinePane
            compressorId={compressor.compressor_id}
            liveStatus={compressor.status}
            isOnline={compressor.is_online}
            pollTimestamp={pollTs}
          />
        </div>
      );
    case 'psi':
      return (
        <div className="tablet-pane-root">
          <CompressorTelemetrySeriesPane
            series="psi"
            compressorId={compressor.compressor_id}
            liveOperational={asRecord(compressor.metrics?.operational)}
            isOnline={compressor.is_online}
            pollTimestamp={pollTs}
          />
        </div>
      );
    case 'temp':
      return (
        <div className="tablet-pane-root">
          <CompressorTelemetrySeriesPane
            series="temp"
            compressorId={compressor.compressor_id}
            liveOperational={asRecord(compressor.metrics?.operational)}
            isOnline={compressor.is_online}
            pollTimestamp={pollTs}
          />
        </div>
      );
    case 'history':
      return (
        <div className="tablet-pane-root">
          <CompressorStatusHistoryPane
            compressorId={compressor.compressor_id}
            liveStatus={compressor.status}
            isOnline={compressor.is_online}
          />
        </div>
      );
  }
}

function TabletCompressorShellLoaded({
  compressor,
  slug,
}: {
  compressor: CompressorStatus;
  slug: TabletCompressorPaneSlug;
}) {
  const [screensaver, setScreensaver] = useState(false);
  const swipeNav = useTabletCompressorPaneSwipe(compressor.compressor_id, slug);
  const base = `/tablet/compressor/${compressor.compressor_id}`;

  return (
    <>
      <TabletScreensaver active={screensaver} onActiveChange={setScreensaver} />
      <div className="tablet-machine-shell">
      <header className="tablet-machine-shell-header">
        <button
          type="button"
          className="tablet-machine-shell-title"
          onClick={() => setScreensaver(true)}
          title="Screensaver"
        >
          {compressor.compressor_name}
        </button>
        <div className="tablet-machine-shell-header-aside">
          <span className="tablet-machine-shell-meta">
            ID {compressor.compressor_id}
            {' · '}
            {compressor.is_online ? 'ONLINE' : 'OFFLINE'}
          </span>
          <Link to="/tablet/setup" className="tablet-shell-link">
            [ CHANGE ASSET ]
          </Link>
        </div>
      </header>

      <div className="tablet-machine-shell-body tablet-machine-shell-body--swipe" {...swipeNav}>
        <TabletCompressorPaneContent slug={slug} compressor={compressor} />
      </div>

      <nav className="tablet-bottom-nav" aria-label="Compressor detail panes">
        {TABLET_COMPRESSOR_NAV_ITEMS.map(({ slug: navSlug, label }) => (
          <NavLink
            key={navSlug}
            to={`${base}/${navSlug}`}
            className={({ isActive }) => `tablet-nav-link ${isActive ? 'active' : ''}`}
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
    </>
  );
}

export const TabletCompressorShell = () => {
  const { compressorId: cidStr, paneSlug } = useParams<{ compressorId: string; paneSlug: string }>();
  const compressorIdNum = parsePositiveInt(cidStr);

  const { compressors, isConnected } = useWebSocketContext();

  const compressor =
    compressorIdNum !== null ? compressors.find((c) => c.compressor_id === compressorIdNum) : undefined;

  useEffect(() => {
    if (compressorIdNum !== null && compressor) {
      writeStoredTabletCompressorId(compressor.compressor_id);
    }
  }, [compressorIdNum, compressor?.compressor_id]);

  if (compressorIdNum === null) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">Invalid compressor id in URL.</div>
      </div>
    );
  }

  if (!paneSlug || !isTabletCompressorPaneSlug(paneSlug)) {
    return (
      <Navigate to={`/tablet/compressor/${compressorIdNum}/${TABLET_DEFAULT_COMPRESSOR_PANE}`} replace />
    );
  }

  const slug: TabletCompressorPaneSlug = paneSlug;

  if (!isConnected) {
    return (
      <div className="tablet-route">
        <AsciiLoadingScreen />
      </div>
    );
  }

  if (compressors.length === 0) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">
          No compressors reported by the server yet.
        </div>
      </div>
    );
  }

  if (!compressor) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">
          Compressor id {compressorIdNum} not found in fleet data. Check the id or WebSocket connection.
        </div>
      </div>
    );
  }

  return <TabletCompressorShellLoaded compressor={compressor} slug={slug} />;
};
