import { useWebSocket } from '../hooks/useWebSocket';
import { MachineCard } from '../components/MachineCard';
import { StatusIndicator } from '../components/ui';
import { AddMachineCard } from '../components/AddMachineCard';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';
import './Dashboard.css';
import { useState } from 'react';

const WS_URL = 'ws://localhost:8000/api/ws';
const API_BASE = 'http://localhost:8000/api';

export const Dashboard = () => {
  const { machines, isConnected, removeMachine, addMachine } = useWebSocket(WS_URL);
  const [editMode, setEditMode] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingMachine, setDeletingMachine] = useState<any>(null);

  const onlineCount = machines.filter(m => m.is_online === true).length;
  const runningCount = machines.filter(m => m.is_online === true && m.status?.includes('Running')).length;
  const offlineCount = machines.filter(m => m.is_online !== true).length;

  const handleDeleteMachine = (machine: any) => {
    setDeletingMachine(machine);
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!deletingMachine) return;
    try {
      const machineId = deletingMachine.machine_id || deletingMachine.id;
      console.log('Deleting machine:', { deletingMachine, machineId });
      const response = await fetch(`${API_BASE}/machines/${machineId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setShowDeleteConfirm(false);
        setDeletingMachine(null);
        // Remove machine from frontend state immediately
        removeMachine(machineId);
      } else {
        const error = await response.json().catch(() => ({}));
        console.error('Delete error response:', error);
        alert(`Failed to delete machine: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete machine');
    }
  };

  return (
    <div className="dashboard">
      {/* Fleet Overview */}
      <div className="fleet-overview">
        <span
          className="machines-count clickable"
          onClick={() => setEditMode(!editMode)}
        >
          MACHINES: {machines.length}
          {editMode && <span className="text-warning"> [EDIT MODE]</span>}
        </span>
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
            <p className="text-dim text-sm">
              {editMode ? 'Click [ ADD MACHINE ] to get started' : 'Click "MACHINES: 0" to add a machine'}
            </p>
          </div>
        )}

        {machines.length === 0 && !isConnected && (
          <div className="no-machines">
            <p className="text-warning pulse">CONNECTING TO SERVER...</p>
            <p className="text-dim text-sm">ws://localhost:8000/api/ws</p>
          </div>
        )}

        {machines.map((machine) => (
          <MachineCard
            key={machine.machine_id}
            machine={machine}
            editMode={editMode}
            onDelete={handleDeleteMachine}
          />
        ))}

        {editMode && machines.length > 0 && (
          <AddMachineCard onCancel={() => setEditMode(false)} onAdd={addMachine} />
        )}

        {editMode && machines.length === 0 && isConnected && (
          <AddMachineCard onCancel={() => setEditMode(false)} onAdd={addMachine} />
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        machineName={deletingMachine?.machine_name || ''}
      />

      {/* Footer/Command Line */}
      <div className="dashboard-footer">
        <div className="dashboard-divider">
          ╠{'═'.repeat(100)}╣
        </div>
        <div className="command-line">
          <span className="prompt">&gt;</span>
          <span className="cursor">STATUS: {editMode ? 'EDIT MODE' : 'MONITORING'}</span>
          <span className="separator">│</span>
          <span className="text-dim">REFRESH: 5s</span>
          <span className="separator">│</span>
          <span className="text-dim">{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
};
