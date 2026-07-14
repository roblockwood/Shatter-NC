import { useWebSocketContext } from '../contexts/WebSocketContext';
import { MachineCard } from '../components/MachineCard';
import { CompressorCard } from '../components/CompressorCard';
import { StatusIndicator } from '../components/ui';
import { AddMachineCard } from '../components/AddMachineCard';
import { AddCompressorCard } from '../components/AddCompressorCard';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';
import { SummaryModal } from '../components/modals/SummaryModal';
import { SummaryPopup } from '../components/modals/SummaryPopup';
import { AsciiLoadingScreen } from '../components/AsciiLoadingScreen';
import { useExpandedMachine } from '../contexts/ExpandedMachineContext';
import './Dashboard.css';
import { useState, useRef, useEffect, useCallback } from 'react';
import { API_BASE, getApiErrorMessage } from '../config/api';
import type { CompressorStatus } from '../hooks/useWebSocket';

type DeleteTarget =
  | { kind: 'cnc'; data: { machine_id: number; machine_name: string } }
  | { kind: 'compressor'; data: CompressorStatus };

export const Dashboard = () => {
  const { machines, compressors, isConnected, removeMachine, addMachine, removeCompressor, addCompressor } =
    useWebSocketContext();
  const [editMode, setEditMode] = useState(false);
  const [expandedMachineId, setExpandedMachineId] = useState<number | null>(null);
  const [expandedCompressorId, setExpandedCompressorId] = useState<number | null>(null);
  const [editingMachineId, setEditingMachineId] = useState<number | null>(null);
  const [editingCompressorId, setEditingCompressorId] = useState<number | null>(null);
  const [pendingEditMachineId, setPendingEditMachineId] = useState<number | null>(null);
  const [pendingCollapseMachineId, setPendingCollapseMachineId] = useState<number | null>(null);
  const [pendingCollapseCompressorId, setPendingCollapseCompressorId] = useState<number | null>(null);
  const [scrollToStatusMachineId, setScrollToStatusMachineId] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingTarget, setDeletingTarget] = useState<DeleteTarget | null>(null);
  const [summaryModal, setSummaryModal] = useState<{
    isOpen: boolean;
    type: 'running' | 'online' | 'offline' | null;
  }>({ isOpen: false, type: null });
  const [summaryPopup, setSummaryPopup] = useState<{
    isOpen: boolean;
    type: 'online' | 'offline' | 'running' | 'machines' | null;
  }>({ isOpen: false, type: null });
  const [isAddingMachine, setIsAddingMachine] = useState(false);
  const [isAddingCompressor, setIsAddingCompressor] = useState(false);

  const runningRef = useRef<HTMLSpanElement>(null);
  const machinesRef = useRef<HTMLSpanElement>(null);
  const popupCloseTimerRef = useRef<number | null>(null);

  const {
    expandedMachine,
    setExpandedMachine,
    setExpandedAssetKind,
    layoutEditMode,
    setLayoutEditMode,
    onCollapse,
    onToggleLayoutEdit,
    showPaneList,
    setShowPaneList,
    onResetToDefault,
  } = useExpandedMachine();

  const clearExpansionChrome = useCallback(() => {
    setExpandedMachine(null);
    setExpandedAssetKind(null);
    setLayoutEditMode(false);
  }, [setExpandedAssetKind, setExpandedMachine, setLayoutEditMode]);

  const isAnyAssetEditing =
    editingMachineId !== null || editingCompressorId !== null || isAddingMachine || isAddingCompressor;

  // Handle Escape key to exit edit mode (only if no asset is being edited in a card)
  useEffect(() => {
    if (!editMode) {
      return;
    }

    if (editingMachineId !== null || editingCompressorId !== null) {
      return;
    }

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
  }, [editMode, editingMachineId, editingCompressorId, showDeleteConfirm, summaryModal.isOpen, summaryPopup.isOpen]);

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

  const onlineCount = machines.filter((m) => m.is_online === true).length;
  const runningCount = machines.filter(
    (m) => m.is_online === true && (m.status?.toLowerCase() === 'operating' || m.status?.toLowerCase().includes('running'))
  ).length;
  const compressorsOnlineCount = compressors.filter((c) => c.is_online === true).length;
  /** Fleet totals: compressors count toward machine/online totals (RUNNING stays CNC-only). */
  const fleetAssetCount = machines.length + compressors.length;
  const fleetOnlineCount = onlineCount + compressorsOnlineCount;

  const handleDeleteMachine = (machine: { machine_id: number; machine_name: string }) => {
    setDeletingTarget({ kind: 'cnc', data: machine });
    setShowDeleteConfirm(true);
  };

  const handleDeleteCompressor = (compressor: CompressorStatus) => {
    setDeletingTarget({ kind: 'compressor', data: compressor });
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!deletingTarget) return;
    try {
      if (deletingTarget.kind === 'cnc') {
        const machineId = deletingTarget.data.machine_id;
        const response = await fetch(`${API_BASE}/machines/${machineId}`, {
          method: 'DELETE',
        });
        if (response.ok) {
          setShowDeleteConfirm(false);
          setDeletingTarget(null);
          removeMachine(machineId);
        } else {
          const error = await response.json().catch(() => ({}));
          alert(`Failed to delete machine: ${getApiErrorMessage(error.detail) || 'Unknown error'}`);
        }
      } else {
        const id = deletingTarget.data.compressor_id;
        const response = await fetch(`${API_BASE}/compressors/${id}`, {
          method: 'DELETE',
        });
        if (response.ok) {
          setShowDeleteConfirm(false);
          setDeletingTarget(null);
          removeCompressor(id);
          if (expandedCompressorId === id) {
            setExpandedCompressorId(null);
            clearExpansionChrome();
          }
        } else {
          const error = await response.json().catch(() => ({}));
          alert(`Failed to delete compressor: ${getApiErrorMessage(error.detail) || 'Unknown error'}`);
        }
      }
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Delete failed');
    }
  };

  const deleteModalName =
    deletingTarget?.kind === 'cnc'
      ? deletingTarget.data.machine_name
      : deletingTarget?.kind === 'compressor'
        ? deletingTarget.data.compressor_name
        : '';

  const collapseAllExpanded = () => {
    setExpandedMachineId(null);
    setExpandedCompressorId(null);
    setScrollToStatusMachineId(null);
    clearExpansionChrome();
  };

  return (
    <div className="dashboard">
      <div className="fleet-overview">
        <div className="fleet-overview-left">
          <span
            className="machines-count clickable"
            onClick={() => {
              if (editingMachineId !== null) {
                setPendingCollapseMachineId(editingMachineId);
              } else if (editingCompressorId !== null) {
                setPendingCollapseCompressorId(editingCompressorId);
              } else {
                collapseAllExpanded();
              }
            }}
          >
            MACHINES: {fleetAssetCount}
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
            ONLINE: <span className="text-info">{fleetOnlineCount}</span>
            <span className="text-dim">/</span>
            <span className="text-info">{fleetAssetCount}</span>
          </span>
        </div>
        {expandedMachine && (
          <div className="fleet-overview-right">
            <span className="expanded-machine-name">{expandedMachine.name}</span>
            {layoutEditMode && (
              <>
                <button
                  className="card-action-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowPaneList(!showPaneList);
                  }}
                  title={showPaneList ? 'Hide pane list' : 'Show pane list'}
                >
                  {showPaneList ? '[HIDE PANE LIST]' : '[SHOW PANE LIST]'}
                </button>
                <button
                  className="card-action-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onResetToDefault?.();
                  }}
                  title="Reset to default layout"
                >
                  [RESET TO DEFAULT]
                </button>
              </>
            )}
            <button
              className="card-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onToggleLayoutEdit?.();
              }}
              title={layoutEditMode ? 'Exit layout edit mode' : 'Customize layout'}
            >
              {layoutEditMode ? '[EXIT EDIT]' : '[CUSTOMIZE LAYOUT]'}
            </button>
            <button
              className="card-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onCollapse?.();
              }}
              title="Collapse"
            >
              [COLLAPSE]
            </button>
          </div>
        )}
      </div>

      <div className="machine-grid">
        {machines.length === 0 && compressors.length === 0 && !isConnected && <AsciiLoadingScreen />}

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
                canEdit={
                  editingCompressorId === null && (editingMachineId === null || editingMachineId === machine.machine_id)
                }
                pendingEditSwitch={editingMachineId === machine.machine_id && pendingEditMachineId !== null}
                isAnyMachineEditing={isAnyAssetEditing}
                onExpand={() => {
                  setExpandedMachineId(machine.machine_id);
                  setExpandedCompressorId(null);
                }}
                onCollapse={() => {
                  setExpandedMachineId(null);
                  setScrollToStatusMachineId(null);
                  clearExpansionChrome();
                }}
                onEditStart={() => {
                  setEditingMachineId(machine.machine_id);
                  setEditingCompressorId(null);
                }}
                onEditEnd={() => {
                  setEditingMachineId(null);
                  if (pendingCollapseMachineId === machine.machine_id) {
                    collapseAllExpanded();
                    setPendingCollapseMachineId(null);
                    return;
                  }
                  if (pendingEditMachineId !== null) {
                    setEditingMachineId(pendingEditMachineId);
                    setPendingEditMachineId(null);
                  }
                }}
                onRequestEditSwitch={() => {
                  setPendingEditMachineId(machine.machine_id);
                }}
                onCancelEditSwitch={() => {
                  setPendingEditMachineId(null);
                }}
                pendingCollapse={pendingCollapseMachineId === machine.machine_id}
                onCancelCollapse={() => {
                  setPendingCollapseMachineId(null);
                }}
                onDelete={handleDeleteMachine}
                scrollToStatus={scrollToStatusMachineId === machine.machine_id}
              />
            ))
        ) : expandedCompressorId !== null ? (
          compressors
            .filter((c) => c.compressor_id === expandedCompressorId)
            .map((c) => (
              <CompressorCard
                key={c.compressor_id}
                compressor={c}
                editMode={editMode}
                isExpanded
                isEditing={editingCompressorId === c.compressor_id}
                canEdit={
                  editingMachineId === null &&
                  (editingCompressorId === null || editingCompressorId === c.compressor_id)
                }
                isAnyAssetEditing={isAnyAssetEditing}
                onExpand={() => {
                  setExpandedCompressorId(c.compressor_id);
                  setExpandedMachineId(null);
                }}
                onCollapse={() => {
                  setExpandedCompressorId(null);
                  clearExpansionChrome();
                }}
                onEditStart={() => {
                  setEditingCompressorId(c.compressor_id);
                  setEditingMachineId(null);
                }}
                onEditEnd={() => {
                  setEditingCompressorId(null);
                  if (pendingCollapseCompressorId === c.compressor_id) {
                    collapseAllExpanded();
                    setPendingCollapseCompressorId(null);
                  }
                }}
                pendingCollapse={pendingCollapseCompressorId === c.compressor_id}
                onCancelCollapse={() => {
                  setPendingCollapseCompressorId(null);
                }}
                onDelete={handleDeleteCompressor}
              />
            ))
        ) : (
          <>
            {machines.map((machine) => (
              <MachineCard
                key={machine.machine_id}
                machine={machine}
                editMode={editMode}
                isExpanded={false}
                isEditing={editingMachineId === machine.machine_id}
                canEdit={
                  editingCompressorId === null && (editingMachineId === null || editingMachineId === machine.machine_id)
                }
                pendingEditSwitch={editingMachineId === machine.machine_id && pendingEditMachineId !== null}
                isAnyMachineEditing={isAnyAssetEditing}
                onExpand={() => {
                  setExpandedMachineId(machine.machine_id);
                  setExpandedCompressorId(null);
                }}
                onCollapse={() => {
                  setExpandedMachineId(null);
                  setScrollToStatusMachineId(null);
                  clearExpansionChrome();
                }}
                onEditStart={() => {
                  setEditingMachineId(machine.machine_id);
                  setEditingCompressorId(null);
                }}
                onEditEnd={() => {
                  setEditingMachineId(null);
                  if (pendingCollapseMachineId === machine.machine_id) {
                    collapseAllExpanded();
                    setPendingCollapseMachineId(null);
                    return;
                  }
                  if (pendingEditMachineId !== null) {
                    setEditingMachineId(pendingEditMachineId);
                    setPendingEditMachineId(null);
                  }
                }}
                onRequestEditSwitch={() => {
                  setPendingEditMachineId(machine.machine_id);
                }}
                onCancelEditSwitch={() => {
                  setPendingEditMachineId(null);
                }}
                pendingCollapse={pendingCollapseMachineId === machine.machine_id}
                onCancelCollapse={() => {
                  setPendingCollapseMachineId(null);
                }}
                onDelete={handleDeleteMachine}
                scrollToStatus={scrollToStatusMachineId === machine.machine_id}
              />
            ))}
            {compressors.map((c) => (
              <CompressorCard
                key={c.compressor_id}
                compressor={c}
                editMode={editMode}
                isExpanded={false}
                isEditing={editingCompressorId === c.compressor_id}
                canEdit={
                  editingMachineId === null &&
                  (editingCompressorId === null || editingCompressorId === c.compressor_id)
                }
                isAnyAssetEditing={isAnyAssetEditing}
                onExpand={() => {
                  setExpandedCompressorId(c.compressor_id);
                  setExpandedMachineId(null);
                }}
                onCollapse={() => {
                  setExpandedCompressorId(null);
                  clearExpansionChrome();
                }}
                onEditStart={() => {
                  setEditingCompressorId(c.compressor_id);
                  setEditingMachineId(null);
                }}
                onEditEnd={() => {
                  setEditingCompressorId(null);
                  if (pendingCollapseCompressorId === c.compressor_id) {
                    collapseAllExpanded();
                    setPendingCollapseCompressorId(null);
                  }
                }}
                pendingCollapse={pendingCollapseCompressorId === c.compressor_id}
                onCancelCollapse={() => {
                  setPendingCollapseCompressorId(null);
                }}
                onDelete={handleDeleteCompressor}
              />
            ))}
            {(machines.length > 0 || compressors.length > 0 || isConnected) &&
              editingMachineId === null &&
              editingCompressorId === null && (
                <>
                  {!isAddingCompressor && (
                    <AddMachineCard
                      onCancel={() => {}}
                      onAdd={(m) => addMachine(m as never)}
                      onActiveChange={setIsAddingMachine}
                      showCompressorOption={!isAddingMachine}
                      onStartAddCompressor={() => setIsAddingCompressor(true)}
                    />
                  )}
                  {isAddingCompressor && (
                    <AddCompressorCard
                      startActive
                      onCancel={() => setIsAddingCompressor(false)}
                      onAdd={addCompressor}
                      onActiveChange={setIsAddingCompressor}
                    />
                  )}
                </>
              )}
          </>
        )}
      </div>

      <DeleteConfirmModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        machineName={deleteModalName}
      />

      {summaryModal.isOpen && summaryModal.type === 'running' && (
        <SummaryModal
          isOpen={summaryModal.isOpen}
          onClose={() => setSummaryModal({ isOpen: false, type: null })}
          summaryType={summaryModal.type}
        />
      )}

      {summaryPopup.isOpen && summaryPopup.type && (
        <SummaryPopup
          summaryType={summaryPopup.type}
          anchorRef={summaryPopup.type === 'machines' ? machinesRef : runningRef}
          onClose={() => setSummaryPopup({ isOpen: false, type: null })}
          onMouseEnter={() => handlePopupMouseEnter(summaryPopup.type as 'machines' | 'running')}
          onMouseLeave={handlePopupMouseLeave}
          onMachineClick={(machineId) => {
            setExpandedMachineId(machineId);
            setExpandedCompressorId(null);
            setScrollToStatusMachineId(machineId);
            setSummaryPopup({ isOpen: false, type: null });
            setTimeout(() => {
              setScrollToStatusMachineId(null);
            }, 1000);
          }}
        />
      )}

      <div className="dashboard-footer">
        <div className="dashboard-divider">╠{'═'.repeat(100)}╣</div>
        <div className="command-line">
          <span className="prompt">&gt;</span>
          <span className="cursor">STATUS: {editMode ? 'EDIT MODE' : 'MONITORING'}</span>
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
