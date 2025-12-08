import { useWebSocket } from '../hooks/useWebSocket';
import { MachineCard } from '../components/MachineCard';
import { StatusIndicator } from '../components/ui';
import { AddMachineCard } from '../components/AddMachineCard';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';
import { SummaryModal } from '../components/modals/SummaryModal';
import { SummaryPopup } from '../components/modals/SummaryPopup';
import './Dashboard.css';
import { useState, useRef } from 'react';
import { WS_URL, API_BASE } from '../config/api';

export const Dashboard = () => {
  const { machines, isConnected, removeMachine, addMachine } = useWebSocket(WS_URL);
  const [editMode, setEditMode] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingMachine, setDeletingMachine] = useState<any>(null);
  const [summaryModal, setSummaryModal] = useState<{
    isOpen: boolean;
    type: 'running' | 'online' | 'offline' | null;
  }>({ isOpen: false, type: null });
  const [summaryPopup, setSummaryPopup] = useState<{
    isOpen: boolean;
    type: 'online' | 'offline' | 'running' | 'machines' | null;
  }>({ isOpen: false, type: null });

  const runningRef = useRef<HTMLSpanElement>(null);
  const machinesRef = useRef<HTMLSpanElement>(null);
  const popupCloseTimerRef = useRef<number | null>(null);

  const handlePopupMouseEnter = (type: 'machines' | 'running') => {
    if (popupCloseTimerRef.current) {
      clearTimeout(popupCloseTimerRef.current);
      popupCloseTimerRef.current = null;
    }
    setSummaryPopup({ isOpen: true, type });
  };

  const handlePopupMouseLeave = () => {
    popupCloseTimerRef.current = setTimeout(() => {
      setSummaryPopup({ isOpen: false, type: null });
    }, 200);
  };

  const onlineCount = machines.filter(m => m.is_online === true).length;
  const runningCount = machines.filter(m => m.is_online === true && m.status?.includes('Running')).length;

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
        <span
          ref={runningRef}
          className="clickable"
          onClick={() => setSummaryModal({ isOpen: true, type: 'running' })}
          onMouseEnter={() => handlePopupMouseEnter('running')}
          onMouseLeave={handlePopupMouseLeave}
        >
          RUNNING: <span className="text-success">{runningCount}</span>
        </span>
        <span className="separator">│</span>
        <span
          ref={machinesRef}
          className="clickable"
          onMouseEnter={() => handlePopupMouseEnter('machines')}
          onMouseLeave={handlePopupMouseLeave}
        >
          ONLINE: <span className="text-info">{onlineCount}</span><span className="text-dim">/</span><span className="text-info">{machines.length}</span>
        </span>
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
            <p className="text-dim text-sm">{WS_URL}</p>
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

      {/* Summary Modal (for Running only) */}
      {summaryModal.isOpen && summaryModal.type === 'running' && (
        <SummaryModal
          isOpen={summaryModal.isOpen}
          onClose={() => setSummaryModal({ isOpen: false, type: null })}
          summaryType={summaryModal.type}
        />
      )}

      {/* Summary Popup (for Machines/Running hover) */}
      {summaryPopup.isOpen && summaryPopup.type && (
        <SummaryPopup
          summaryType={summaryPopup.type}
          anchorRef={
            summaryPopup.type === 'machines' ? machinesRef :
            runningRef
          }
          onClose={() => setSummaryPopup({ isOpen: false, type: null })}
          onMouseEnter={() => handlePopupMouseEnter(summaryPopup.type as 'machines' | 'running')}
          onMouseLeave={handlePopupMouseLeave}
        />
      )}

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
