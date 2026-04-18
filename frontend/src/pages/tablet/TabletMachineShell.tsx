import type { ComponentProps } from 'react';
import { useEffect, useState } from 'react';
import { Link, Navigate, NavLink, useParams } from 'react-router-dom';
import { AsciiLoadingScreen } from '../../components/AsciiLoadingScreen';
import { AlarmPane } from '../../components/machine-detail/AlarmPane';
import { CurrentProgramPane } from '../../components/machine-detail/CurrentProgramPane';
import { FileManagerPane } from '../../components/machine-detail/FileManagerPane';
import { MachineOverviewPane } from '../../components/machine-detail/MachineOverviewPane';
import { PanelPane } from '../../components/machine-detail/PanelPane';
import { ProductionRunsTimelinePane } from '../../components/machine-detail/ProductionRunsTimelinePane';
import { StatusHistoryPane } from '../../components/machine-detail/StatusHistoryPane';
import { StatusTimeline } from '../../components/machine-detail/StatusTimeline';
import { ToolsPane } from '../../components/machine-detail/ToolsPane';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import type { MachineStatus } from '../../hooks/useWebSocket';
import { fastPollLastSuccessAt } from '../../utils/machinePollFreshness';
import {
  isTabletPaneSlug,
  TABLET_DEFAULT_PANE,
  TABLET_NAV_ITEMS,
  type TabletPaneSlug,
} from './tabletPaneConfig';
import { writeStoredTabletMachineId } from './tabletMachineStorage';
import { TabletScreensaver } from './TabletScreensaver';
import { useTabletPaneSwipe } from './useTabletPaneSwipe';
import { useTabletScreensaverIdleMs } from './useTabletScreensaverIdleMs';
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

function TabletPaneContent({
  slug,
  machine,
}: {
  slug: TabletPaneSlug;
  machine: MachineStatus;
}) {
  const pollAt = fastPollLastSuccessAt(machine);

  switch (slug) {
    case 'overview':
      return (
        <div className="tablet-pane-root">
          <MachineOverviewPane machine={machine} />
        </div>
      );
    case 'status':
      return (
        <div className="tablet-pane-root">
          <StatusTimeline
            machineId={machine.machine_id}
            currentStatus={machine.status}
            isOnline={machine.is_online}
            currentError={machine.error}
            onExpand={undefined}
            machineLastSuccessfulPollAt={pollAt}
          />
        </div>
      );
    case 'alarms':
      return (
        <div className="tablet-pane-root">
          <AlarmPane
            machineId={machine.machine_id}
            currentAlarms={machine.alarms || undefined}
            onExpand={undefined}
            pollTimestamp={pollAt}
            pollIntervalSeconds={machine.poll_interval_seconds ?? 5}
          />
        </div>
      );
    case 'program':
      return (
        <div className="tablet-pane-root">
          <CurrentProgramPane
            machineId={machine.machine_id}
            machineStatus={machine.status}
            programName={machine.program_name}
            onExpand={undefined}
            machineLastSuccessfulPollAt={pollAt}
          />
        </div>
      );
    case 'tools':
      return (
        <div className="tablet-pane-root">
          <ToolsPane
            tools={machine.tools || []}
            toolTable={machine.tool_table || []}
            currentTool={machine.current_tool}
            machineId={machine.machine_id}
            units={machine.units || 'in'}
            machineStatus={machine.status}
            memMode={machine.mem_mode}
            memOperationStatus={machine.mem_operation_status}
            toolsTimestamp={machine.tools_timestamp ?? undefined}
            toolTableTimestamp={machine.tool_table_timestamp ?? undefined}
            toolPollIntervalSeconds={machine.tool_poll_interval_seconds ?? 30}
          />
        </div>
      );
    case 'runs':
      return (
        <div className="tablet-pane-root">
          <ProductionRunsTimelinePane
            machineId={machine.machine_id}
            machineLastSuccessfulPollAt={pollAt}
          />
        </div>
      );
    case 'history':
      return (
        <div className="tablet-pane-root">
          <StatusHistoryPane machineId={machine.machine_id} machineLastSuccessfulPollAt={pollAt} />
        </div>
      );
    case 'panel':
      return (
        <div className="tablet-pane-root">
          <PanelPane
            panelData={(machine as MachineStatus & {
              panel?: ComponentProps<typeof PanelPane>['panelData'];
            }).panel}
            onExpand={undefined}
            pollTimestamp={pollAt}
            pollIntervalSeconds={machine.poll_interval_seconds ?? 5}
          />
        </div>
      );
    case 'files':
      return (
        <div className="tablet-pane-root">
          <FileManagerPane machineId={machine.machine_id} onExpand={undefined} />
        </div>
      );
  }
}

function TabletMachineShellLoaded({
  machine,
  slug,
}: {
  machine: MachineStatus;
  slug: TabletPaneSlug;
}) {
  const [screensaver, setScreensaver] = useState(false);
  const screensaverIdleMs = useTabletScreensaverIdleMs();
  const swipeNav = useTabletPaneSwipe(machine.machine_id, slug);
  const base = `/tablet/${machine.machine_id}`;

  return (
    <>
      <TabletScreensaver
        active={screensaver}
        onActiveChange={setScreensaver}
        idleMs={screensaverIdleMs}
      />
      <div className="tablet-machine-shell">
      <header className="tablet-machine-shell-header">
        <button
          type="button"
          className="tablet-machine-shell-title"
          onClick={() => setScreensaver(true)}
          title="Screensaver"
        >
          {machine.machine_name}
        </button>
        <div className="tablet-machine-shell-header-aside">
          <span className="tablet-machine-shell-meta">
            ID {machine.machine_id}
            {' · '}
            {machine.is_online ? 'ONLINE' : 'OFFLINE'}
          </span>
          <Link to="/tablet/setup" className="tablet-shell-link">
            [ CHANGE ASSET ]
          </Link>
        </div>
      </header>

      <div
        className="tablet-machine-shell-body tablet-machine-shell-body--swipe"
        {...swipeNav}
      >
        <TabletPaneContent slug={slug} machine={machine} />
      </div>

      <nav className="tablet-bottom-nav" aria-label="Machine detail panes">
        {TABLET_NAV_ITEMS.map(({ slug: navSlug, label }) => (
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

export const TabletMachineShell = () => {
  const { machineId: midStr, paneSlug } = useParams<{ machineId: string; paneSlug: string }>();
  const machineIdNum = parsePositiveInt(midStr);

  const { machines, isConnected } = useWebSocketContext();

  const machine =
    machineIdNum !== null ? machines.find((m) => m.machine_id === machineIdNum) : undefined;

  useEffect(() => {
    if (machineIdNum !== null && machine) {
      writeStoredTabletMachineId(machine.machine_id);
    }
  }, [machineIdNum, machine?.machine_id]);

  if (machineIdNum === null) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">Invalid machine id in URL.</div>
      </div>
    );
  }

  if (!paneSlug || !isTabletPaneSlug(paneSlug)) {
    return <Navigate to={`/tablet/${machineIdNum}/${TABLET_DEFAULT_PANE}`} replace />;
  }

  const slug: TabletPaneSlug = paneSlug;

  if (!isConnected) {
    return (
      <div className="tablet-route">
        <AsciiLoadingScreen />
      </div>
    );
  }

  if (machines.length === 0) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">
          No CNC machines reported by the server yet.
        </div>
      </div>
    );
  }

  if (!machine) {
    return (
      <div className="tablet-route">
        <div className="tablet-route-state text-error">
          Machine id {machineIdNum} not found in fleet data. Check the id or WebSocket connection.
        </div>
      </div>
    );
  }

  return <TabletMachineShellLoaded machine={machine} slug={slug} />;
};
