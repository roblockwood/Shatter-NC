import { useWebSocket } from '../hooks/useWebSocket';
import { MachineCard } from '../components/MachineCard';
import { StatusIndicator } from '../components/ui';
import './Dashboard.css';

const WS_URL = 'ws://localhost:8000/api/ws';

export const Dashboard = () => {
  const { machines, isConnected } = useWebSocket(WS_URL);

  const onlineCount = machines.filter(m => m.is_online).length;
  const runningCount = machines.filter(m => m.is_online && m.status?.includes('Running')).length;
  const offlineCount = machines.filter(m => !m.is_online).length;

  return (
    <div className="dashboard">
      {/* Fleet Overview */}
      <div className="fleet-overview">
        <span>MACHINES: {machines.length}</span>
        <span className="separator">│</span>
        <span>RUNNING: <span className="text-success">{runningCount}</span></span>
        <span className="separator">│</span>
        <span>ONLINE: <span className="text-info">{onlineCount}</span></span>
        <span className="separator">│</span>
        <span>OFFLINE: <span className="text-error">{offlineCount}</span></span>
        <span className="separator">│</span>
        <StatusIndicator
          status={isConnected ? 'online' : 'offline'}
          label={isConnected ? 'WS CONNECTED' : 'WS DISCONNECTED'}
        />
      </div>

      {/* Machine Grid */}
      <div className="machine-grid">
        {machines.length === 0 && isConnected && (
          <div className="no-machines">
            <p className="text-muted">NO MACHINES CONFIGURED</p>
            <p className="text-dim text-sm">Waiting for machine data...</p>
          </div>
        )}

        {machines.length === 0 && !isConnected && (
          <div className="no-machines">
            <p className="text-warning pulse">CONNECTING TO SERVER...</p>
            <p className="text-dim text-sm">ws://localhost:8000/api/ws</p>
          </div>
        )}

        {machines.map((machine) => (
          <MachineCard key={machine.machine_id} machine={machine} />
        ))}
      </div>

      {/* Footer/Command Line */}
      <div className="dashboard-footer">
        <div className="dashboard-divider">
          ╠{'═'.repeat(100)}╣
        </div>
        <div className="command-line">
          <span className="prompt">&gt;</span>
          <span className="cursor">STATUS: MONITORING</span>
          <span className="separator">│</span>
          <span className="text-dim">REFRESH: 5s</span>
          <span className="separator">│</span>
          <span className="text-dim">{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
};
