import { useWebSocketContext } from '../contexts/WebSocketContext';
import { MachineCard } from '../components/MachineCard';
import { StatusIndicator } from '../components/ui';
import { AddMachineCard } from '../components/AddMachineCard';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';
import { SummaryModal } from '../components/modals/SummaryModal';
import { SummaryPopup } from '../components/modals/SummaryPopup';
import { AsciiLoadingScreen } from '../components/AsciiLoadingScreen';
import { AsciiEmptyState } from '../components/AsciiEmptyState';
import './Dashboard.css';
import { useState, useRef, useEffect } from 'react';
import { API_BASE } from '../config/api';

export const Dashboard = () => {
  const { machines, isConnected, removeMachine, addMachine } = useWebSocketContext();
  const [editMode, setEditMode] = useState(false);
  const [expandedMachineId, setExpandedMachineId] = useState<number | null>(null);
  const [editingMachineId, setEditingMachineId] = useState<number | null>(null);
  const [pendingEditMachineId, setPendingEditMachineId] = useState<number | null>(null);
  const [scrollToStatusMachineId, setScrollToStatusMachineId] = useState<number | null>(null);
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

  // Handle Escape key to exit edit mode (only if no machine is being edited)
  useEffect(() => {
    if (!editMode) {
      return;
    }

    // Don't exit edit mode if a machine is being edited - let MachineCard handle it first
    if (editingMachineId !== null) {
      return;
    }

    // Don't exit edit mode if a modal or popup is open
    if (showDeleteConfirm || summaryModal.isOpen || summaryPopup.isOpen) {
      return;
    }

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setEditMode(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [editMode, editingMachineId, showDeleteConfirm, summaryModal.isOpen, summaryPopup.isOpen]);

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
  const runningCount = machines.filter(m => m.is_online === true && (m.status?.toLowerCase() === 'operating' || m.status?.toLowerCase().includes('running'))).length;

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
          onClick={() => {
            // Collapse all cards and reset edit state
            setExpandedMachineId(null);
            setEditingMachineId(null);
            setPendingEditMachineId(null);
            setScrollToStatusMachineId(null);
          }}
        >
          MACHINES: {machines.length}
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
      </div>

      {/* Machine Grid */}
      <div className="machine-grid">
        {machines.length === 0 && !isConnected && (
          <AsciiLoadingScreen />
        )}

        {/* When a machine is expanded, only show that machine card */}
        {expandedMachineId !== null ? (
          machines
            .filter((machine) => machine.machine_id === expandedMachineId)
            .map((machine) => (
              <MachineCard
                key={machine.machine_id}
                machine={machine}
                editMode={editMode}
                isExpanded={expandedMachineId === machine.machine_id}
                isEditing={editingMachineId === machine.machine_id}
                canEdit={editingMachineId === null || editingMachineId === machine.machine_id}
                pendingEditSwitch={editingMachineId === machine.machine_id && pendingEditMachineId !== null}
                onExpand={() => setExpandedMachineId(machine.machine_id)}
                onCollapse={() => {
                  setExpandedMachineId(null);
                  setScrollToStatusMachineId(null);
                }}
                onEditStart={() => setEditingMachineId(machine.machine_id)}
                onEditEnd={() => {
                  setEditingMachineId(null);
                  // If there's a pending edit, start it now
                  if (pendingEditMachineId !== null) {
                    setEditingMachineId(pendingEditMachineId);
                    setPendingEditMachineId(null);
                  }
                }}
                onRequestEditSwitch={() => {
                  // Request to switch to this machine - trigger save confirmation on current
                  setPendingEditMachineId(machine.machine_id);
                }}
                onCancelEditSwitch={() => {
                  // User cancelled the switch - clear pending
                  setPendingEditMachineId(null);
                }}
                onDelete={handleDeleteMachine}
                scrollToStatus={scrollToStatusMachineId === machine.machine_id}
              />
            ))
        ) : (
          // When no machine is expanded, show all machine cards
          machines.map((machine) => (
            <MachineCard
              key={machine.machine_id}
              machine={machine}
              editMode={editMode}
              isExpanded={expandedMachineId === machine.machine_id}
              isEditing={editingMachineId === machine.machine_id}
              canEdit={editingMachineId === null || editingMachineId === machine.machine_id}
              pendingEditSwitch={editingMachineId === machine.machine_id && pendingEditMachineId !== null}
              onExpand={() => setExpandedMachineId(machine.machine_id)}
              onCollapse={() => {
                setExpandedMachineId(null);
                setScrollToStatusMachineId(null);
              }}
              onEditStart={() => setEditingMachineId(machine.machine_id)}
              onEditEnd={() => {
                setEditingMachineId(null);
                // If there's a pending edit, start it now
                if (pendingEditMachineId !== null) {
                  setEditingMachineId(pendingEditMachineId);
                  setPendingEditMachineId(null);
                }
              }}
              onRequestEditSwitch={() => {
                // Request to switch to this machine - trigger save confirmation on current
                setPendingEditMachineId(machine.machine_id);
              }}
              onCancelEditSwitch={() => {
                // User cancelled the switch - clear pending
                setPendingEditMachineId(null);
              }}
              onDelete={handleDeleteMachine}
              scrollToStatus={scrollToStatusMachineId === machine.machine_id}
            />
          ))
        )}

        {/* Always show AddMachineCard when no machine is expanded */}
        {expandedMachineId === null && (
          <AddMachineCard onCancel={() => {}} onAdd={addMachine} />
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
          onMachineClick={(machineId) => {
            setExpandedMachineId(machineId);
            setScrollToStatusMachineId(machineId);
            setSummaryPopup({ isOpen: false, type: null });
            // Reset scroll flag after a delay to allow re-triggering
            setTimeout(() => {
              setScrollToStatusMachineId(null);
            }, 1000);
          }}
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
          <span className="separator">│</span>
          <StatusIndicator
            status={isConnected ? 'online' : 'offline'}
            label={isConnected ? 'WS CONNECTED' : 'WS DISCONNECTED'}
          />
        </div>
      </div>
    </div>
  );
};
