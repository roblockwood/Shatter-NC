import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ToolListModal } from './ToolListModal';
import { UploadConfirmationModal } from './UploadConfirmationModal';

import { AlarmPane } from './machine-detail/AlarmPane';
import { StatusTimeline } from './machine-detail/StatusTimeline';
import { ToolsPane } from './machine-detail/ToolsPane';
import { CurrentProgramPane } from './machine-detail/CurrentProgramPane';
import { ProductionRunsTimelinePane } from './machine-detail/ProductionRunsTimelinePane';
import { StatusHistoryPane } from './machine-detail/StatusHistoryPane';
import { PanelPane } from './machine-detail/PanelPane';
import { FileManagerPane } from './machine-detail/FileManagerPane';
import { LayoutManager } from './machine-detail/LayoutManager';
import { MachineEditPanel } from './machine-detail/MachineEditPanel';
import { PANE_IDS } from '../types/layout';
import { useExpandedMachine } from '../contexts/ExpandedMachineContext';
import './MachineCard.css';
import { API_BASE_URL } from '../config/api';
import type { Alarm, ValidationResult, MachineStatus, MachineCardProps } from './MachineCardTypes';

/** Fast-poll freshness time for status/alarms/panel: last successful controller poll only (falls back to legacy poll_timestamp if field absent). */
function fastPollLastSuccessAt(machine: MachineStatus): string | null | undefined {
  if (machine.last_successful_poll_at !== undefined) {
    return machine.last_successful_poll_at;
  }
  return machine.poll_timestamp;
}

export const MachineCard: React.FC<MachineCardProps> = ({
  machine,
  editMode = false,
  isExpanded = false,
  isEditing: isEditingProp = false,
  canEdit = true,
  pendingEditSwitch = false,
  pendingCollapse = false,
  onExpand,
  onCollapse,
  onEditStart,
  onEditEnd,
  onRequestEditSwitch,
  onCancelEditSwitch,
  onCancelCollapse,
  onDelete,
  scrollToStatus = false,
  isAnyMachineEditing = false
}) => {
  // Debug: Log machine status for debugging name color (only log when status actually changes)
  // Removed excessive logging - uncomment if needed for debugging
  // console.log(`Machine: ${machine.machine_name}, is_online: ${machine.is_online}, status: "${machine.status}", program_name: "${machine.program_name}"`);

  const [showToolModal, setShowToolModal] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [selectedFilename, setSelectedFilename] = useState('');
  const [fileContent, setFileContent] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  // Use prop if provided (controlled), otherwise use local state (uncontrolled)
  const [isEditingLocal, setIsEditingLocal] = useState(false);
  const isEditing = isEditingProp !== undefined ? isEditingProp : isEditingLocal;
  
  const startEditing = () => {
    if (!canEdit) {
      // Another machine is being edited - request switch
      onRequestEditSwitch?.();
      return;
    }
    if (isEditingProp !== undefined) {
      // Controlled mode - notify parent
      onEditStart?.();
    } else {
      // Uncontrolled mode - use local state
      setIsEditingLocal(true);
    }
  };
  
  const stopEditing = () => {
    if (isEditingProp !== undefined) {
      // Controlled mode - notify parent
      onEditEnd?.();
    } else {
      // Uncontrolled mode - use local state
      setIsEditingLocal(false);
    }
  };
  const { 
    setExpandedMachine,
    setExpandedAssetKind,
    layoutEditMode, 
    setLayoutEditMode, 
    setOnCollapse, 
    setOnToggleLayoutEdit 
  } = useExpandedMachine();
  
  // Create a stable toggle function using useCallback
  const toggleLayoutEdit = useCallback(() => {
    setLayoutEditMode((prev) => !prev);
  }, [setLayoutEditMode]);
  const [cachedAlarms, setCachedAlarms] = useState<Alarm[] | null>(null);
  const [showAlarmHover, setShowAlarmHover] = useState(false);
  const [alarmHoverPosition, setAlarmHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const alarmPaneRef = useRef<HTMLDivElement>(null);
  const alarmHoverRef = useRef<HTMLDivElement>(null);
  const alarmIndicatorRef = useRef<HTMLDivElement>(null);
  const [showToolsHover, setShowToolsHover] = useState(false);
  const [toolsHoverPosition, setToolsHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const toolsPaneRef = useRef<HTMLDivElement>(null);
  const toolsHoverRef = useRef<HTMLDivElement>(null);
  const toolsIndicatorRef = useRef<HTMLDivElement>(null);
  const [showStatusHover, setShowStatusHover] = useState(false);
  const [statusHoverPosition, setStatusHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const statusTimelineRef = useRef<HTMLDivElement>(null);
  const statusHoverRef = useRef<HTMLDivElement>(null);
  const statusIndicatorRef = useRef<HTMLDivElement>(null);
  const [showProgramHover, setShowProgramHover] = useState(false);
  const [programHoverPosition, setProgramHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const currentProgramPaneRef = useRef<HTMLDivElement>(null);
  const programHoverRef = useRef<HTMLDivElement>(null);
  const programIndicatorRef = useRef<HTMLDivElement>(null);
  const cycleHistoryPaneRef = useRef<HTMLDivElement>(null);
  const [showProductionRunsHover, setShowProductionRunsHover] = useState(false);
  const [productionRunsHoverPosition, setProductionRunsHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const productionRunsHoverRef = useRef<HTMLDivElement>(null);
  const productionRunsIndicatorRef = useRef<HTMLDivElement>(null);
  const fileManagerPaneRef = useRef<HTMLDivElement>(null);
  const expandedContentRef = useRef<HTMLDivElement>(null);
  const [currentProgram, setCurrentProgram] = useState<string | null>(null);
  const [latestRun, setLatestRun] = useState<{
    program_no: string | null;
    run_start: string;
    run_end: string;
    cycles: number;
    part_count: number;
    segments: { status: string | null; start_time: string; end_time: string }[];
  } | null>(null);
  const [latestRunLoading, setLatestRunLoading] = useState(false);
  
  // Cache alarms from machine prop to avoid refetching
  useEffect(() => {
    if (machine.alarms) {
      setCachedAlarms(machine.alarms);
    }
  }, [machine.alarms]);

  const getAlarmSeverityLevel = (alarm: Alarm): number => {
    // Mirror AlarmPane: stop_level 5..1 (5 highest). Default to 3 if missing/invalid.
    const raw = alarm.stop_level;
    if (raw !== undefined && raw !== null && String(raw) !== '') {
      const level = parseInt(String(raw), 10);
      if (!isNaN(level) && level >= 1 && level <= 5) {
        return level;
      }
    }
    return 3;
  };


  // Use program_name from machine status (active program from polling)
  // This shows the actual program running on the machine, not just the most recent deployment
  useEffect(() => {
    const programName = machine.program_name;
    // Reduced logging - uncomment if needed for debugging
    // console.log(`[MachineCard] program_name update for ${machine.machine_name}:`, programName, typeof programName);
    
    // Check if program_name is valid (not null, undefined, empty string, "----", or the string "undefined")
    if (programName && 
        programName !== '----' && 
        programName !== 'undefined' && 
        programName !== 'null' &&
        typeof programName === 'string' &&
        programName.trim() !== '') {
      setCurrentProgram(programName);
    } else {
      setCurrentProgram(null);
    }
  }, [machine.program_name, machine.machine_name]);

  // Fetch most recent production run for compact card summary
  useEffect(() => {
    let cancelled = false;
    const fetchLatestRun = async () => {
      try {
        setLatestRunLoading(true);
        const endTime = new Date();
        const startTime = new Date(endTime);
        startTime.setDate(startTime.getDate() - 7);

        const resp = await fetch(
          `${API_BASE_URL}/api/machines/${machine.machine_id}/production-runs-timeline?start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}&limit=1&offset=0`
        );
        if (!resp.ok) {
          if (!cancelled) {
            setLatestRun(null);
          }
          return;
        }
        const data = await resp.json();
        const runs = Array.isArray(data) ? data : [];
        if (!cancelled) {
          setLatestRun(runs[0] || null);
        }
      } catch (_e) {
        if (!cancelled) {
          setLatestRun(null);
        }
      } finally {
        if (!cancelled) {
          setLatestRunLoading(false);
        }
      }
    };

    fetchLatestRun();
    return () => {
      cancelled = true;
    };
  }, [machine.machine_id]);

  // Helper function to find pane element within current card
  const findPaneElement = (paneId: string): HTMLElement | null => {
    if (expandedContentRef.current) {
      return expandedContentRef.current.querySelector(`[data-pane-id="${paneId}"]`) as HTMLElement;
    }
    return document.querySelector(`[data-pane-id="${paneId}"]`) as HTMLElement;
  };

  // Handle scroll to status timeline when requested
  useEffect(() => {
    if (scrollToStatus && isExpanded) {
      setTimeout(() => {
        // Find pane by data attribute (works with LayoutManager)
        const paneElement = findPaneElement(PANE_IDS.STATUS_TIMELINE);
        if (paneElement) {
          paneElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
          paneElement.classList.add('status-pane-highlight');
          setTimeout(() => {
            paneElement.classList.remove('status-pane-highlight');
          }, 2000);
        } else if (statusTimelineRef.current) {
          // Fallback to ref if data attribute not found
          statusTimelineRef.current.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
          statusTimelineRef.current.classList.add('status-pane-highlight');
          setTimeout(() => {
            statusTimelineRef.current?.classList.remove('status-pane-highlight');
          }, 2000);
        }
      }, 300);
    }
  }, [scrollToStatus, isExpanded]);

  // Handle Escape key to collapse expanded card
  useEffect(() => {
    if (!isExpanded || editMode) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCollapse?.();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isExpanded, editMode, onCollapse]);

  // Dismiss all hover panes when card is collapsed
  useEffect(() => {
    if (!isExpanded) {
      setShowStatusHover(false);
      setShowProgramHover(false);
      setShowProductionRunsHover(false);
      setShowToolsHover(false);
      setShowAlarmHover(false);
    }
  }, [isExpanded]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const getStatusType = () => {
    if (!machine.is_online) return 'offline';
    // Normalize actual machine statuses: off, standby, error, operating, stopped
    const status = machine.status?.toLowerCase() || '';
    if (status === 'error' || status.includes('error')) return 'error';
    if (status === 'operating' || status.includes('running')) return 'running';
    if (status === 'standby' || status.includes('idle')) return 'idle';
    if (status === 'stopped' || status === 'off') return 'stopped';
    return 'idle';
  };

  const getStatusDisplay = () => {
    if (!machine.is_online) return 'OFF';
    // Normalize status display to match machine statuses: operating, standby, stopped, error, off
    const status = machine.status?.toLowerCase() || '';
    if (status === 'error' || status.includes('error')) return 'ERROR';
    if (status === 'operating' || status.includes('operating') || status.includes('running')) return 'OPERATING';
    if (status === 'standby' || status.includes('standby') || status.includes('idle')) return 'IDLE';
    if (status === 'stopped' || status.includes('stopped')) return 'STOPPED';
    if (status === 'off' || status.includes('off')) return 'OFF';
    return 'UNKNOWN';
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFilename(file.name);
    setIsValidating(true);

    try {
      const content = await file.text();
      setFileContent(content); // Store for upload

      const response = await fetch(`${API_BASE_URL}/api/programs/machines/${machine.machine_id}/programs/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gcode_content: content }),
      });

      if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
      }

      const result = await response.json();
      setValidationResult(result);
      setShowConfirmationModal(true);
    } catch (error) {
      console.error('Validation error:', error);
      alert(`Validation failed: ${error}`);
      setFileContent('');
    } finally {
      setIsValidating(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't expand if clicking on buttons or inputs
    const target = e.target as HTMLElement;
    if (
      target.closest('button') ||
      target.closest('input') ||
      target.closest('.card-action-btn') ||
      target.closest('.upload-button') ||
      target.closest('.tool-summary') ||
      target.closest('.layout-manager') ||
      target.closest('.react-grid-item') ||
      target.closest('.drag-handle') ||
      target.closest('.react-resizable-handle') ||
      target.closest('.layout-pane-wrapper') ||
      isEditing ||
      editMode ||
      layoutEditMode
    ) {
      return;
    }
    
    if (isExpanded) {
      onCollapse?.();
    } else {
      onExpand?.();
    }
  };

  // Wire this card into the ExpandedMachineContext when expanded so that
  // global layout edit controls (buttons, pane list, etc.) know which
  // machine is active and how to toggle its layout edit mode.
  const hasRegisteredExpandedContextRef = useRef(false);
  useEffect(() => {
    if (!isExpanded || hasRegisteredExpandedContextRef.current) {
      return;
    }

    // Card became expanded – register metadata and handlers once
    setExpandedMachine({ id: machine.machine_id, name: machine.machine_name });
    setExpandedAssetKind('cnc');

    if (onCollapse) {
      setOnCollapse(() => onCollapse);
    }

    setOnToggleLayoutEdit(() => toggleLayoutEdit);
    hasRegisteredExpandedContextRef.current = true;
  }, [isExpanded, machine.machine_id, machine.machine_name, onCollapse, setExpandedAssetKind, setExpandedMachine, setOnCollapse, setOnToggleLayoutEdit, toggleLayoutEdit]);

  // Render edit panel
  if (isEditing) {
    return (
      <MachineEditPanel
        machine={machine}
        pendingEditSwitch={pendingEditSwitch}
        pendingCollapse={pendingCollapse}
        onEditEnd={stopEditing}
        onCancelEditSwitch={onCancelEditSwitch}
        onCancelCollapse={onCancelCollapse}
        onDelete={onDelete}
      />
    );
  }

  // Render expanded view
  if (isExpanded && !editMode) {
    return (
      <div className={`machine-card expanded`} onClick={handleCardClick}>

        <div className="machine-card-expanded-content" ref={expandedContentRef}>
          <LayoutManager
            machineId={machine.machine_id}
            isEditMode={layoutEditMode}
            onEditModeChange={setLayoutEditMode}
            panes={[
              {
                id: PANE_IDS.STATUS_TIMELINE,
                component: (
                  <div ref={statusTimelineRef}>
                    <StatusTimeline 
                      machineId={machine.machine_id} 
                      currentStatus={machine.status} 
                      isOnline={machine.is_online}
                      currentError={machine.error}
                      onExpand={undefined}
                      machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                    />
                  </div>
                ),
              },
              {
                id: PANE_IDS.ALARMS,
                component: (
                  <div ref={alarmPaneRef}>
                    <AlarmPane 
                      machineId={machine.machine_id} 
                      currentAlarms={machine.alarms || cachedAlarms || undefined}
                      onExpand={undefined}
                      pollTimestamp={fastPollLastSuccessAt(machine)}
                      pollIntervalSeconds={machine.poll_interval_seconds ?? 5}
                    />
                  </div>
                ),
              },
              {
                id: PANE_IDS.CURRENT_PROGRAM,
                component: (
                  <div ref={currentProgramPaneRef}>
                    <CurrentProgramPane 
                      machineId={machine.machine_id}
                      machineStatus={machine.status}
                      programName={machine.program_name}
                      onExpand={undefined}
                      machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                    />
                  </div>
                ),
              },
              {
                id: PANE_IDS.TOOLS,
                component: (
                  <div ref={toolsPaneRef}>
            <ToolsPane
              tools={machine.tools || []}
              toolTable={machine.tool_table || []}
              currentTool={machine.current_tool}
              machineId={machine.machine_id}
              units={machine.units ?? 'in'}
              machineStatus={machine.status}
              memMode={machine.mem_mode}
              memOperationStatus={machine.mem_operation_status}
              toolsTimestamp={machine.tools_timestamp ?? undefined}
              toolTableTimestamp={machine.tool_table_timestamp ?? undefined}
              toolPollIntervalSeconds={machine.tool_poll_interval_seconds ?? 30}
              programName={currentProgram ?? undefined}
            />
                  </div>
                ),
              },
              {
                id: PANE_IDS.PRODUCTION_RUNS,
                component: (
                  <div ref={cycleHistoryPaneRef}>
                    <ProductionRunsTimelinePane
                      machineId={machine.machine_id}
                      machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                    />
                  </div>
                ),
              },
              {
                id: PANE_IDS.STATUS_HISTORY,
                component: (
                  <StatusHistoryPane
                    machineId={machine.machine_id}
                    machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                  />
                ),
              },
              {
                id: PANE_IDS.PANEL,
                component: (
                  <PanelPane 
                    panelData={machine.panel}
                    onExpand={undefined}
                    pollTimestamp={fastPollLastSuccessAt(machine)}
                    pollIntervalSeconds={machine.poll_interval_seconds ?? 5}
                  />
                ),
              },
              {
                id: PANE_IDS.FILE_MANAGER,
                component: (
                  <div ref={fileManagerPaneRef}>
                    <FileManagerPane 
                      machineId={machine.machine_id}
                      onExpand={undefined}
                    />
                  </div>
                ),
              },
            ]}
          />
        </div>


        <ToolListModal
          isOpen={showToolModal}
          onClose={() => setShowToolModal(false)}
          tools={machine.tools || []}
          machineName={machine.machine_name}
          units={(machine.units || 'in') as 'in' | 'mm'}
        />

        <UploadConfirmationModal
          isOpen={showConfirmationModal}
          onClose={() => {
            setShowConfirmationModal(false);
            setFileContent('');
            setValidationResult(null);
            setSelectedFilename('');
          }}
          result={validationResult as never}
          filename={selectedFilename}
          machineId={machine.machine_id}
          machineName={machine.machine_name}
          machinePath={machine.path || '/'}
          fileContent={fileContent}
          units={(machine.units || 'in') as 'in' | 'mm'}
        />

        <input
          ref={fileInputRef}
          type="file"
          accept=".nc,.NC,.txt"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
      </div>
    );
  }

  // Render compact view
  return (
    <div className={`machine-card ${isExpanded ? 'expanded' : ''} ${isAnyMachineEditing ? 'hidden-when-editing' : ''}`} onClick={handleCardClick}>
      <div className="machine-card-header">
        <span className={`machine-name ${!machine.is_online ? 'text-error' : (machine.status?.toLowerCase() === 'operating' || machine.status?.toLowerCase().includes('running') ? 'text-glow' : 'text-muted')}`}>{machine.machine_name}</span>
        <div className="machine-header-actions">
        </div>
      </div>

      <div className="machine-card-divider">
        ├{'─'.repeat(30)}┤
      </div>

      <div className="machine-card-content">
          <div 
            ref={statusIndicatorRef}
            className="machine-row machine-row-hoverable"
            onMouseEnter={() => {
              if (statusIndicatorRef.current) {
                const rect = statusIndicatorRef.current.getBoundingClientRect();
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const paneWidth = 600;
                const paneHeight = 300;
                
                let left = rect.right + 8;
                let top = rect.top;
                
                if (left + paneWidth > viewportWidth) {
                  left = rect.left - paneWidth - 8;
                }
                if (top + paneHeight > viewportHeight) {
                  top = Math.max(8, viewportHeight - paneHeight - 8);
                }
                if (top < 8) {
                  top = 8;
                }
                
                setStatusHoverPosition({ top, left });
              }
              setShowStatusHover(true);
            }}
            onMouseLeave={() => setShowStatusHover(false)}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) {
                onExpand?.();
              }
              setTimeout(() => {
                // Find pane by data attribute (works with LayoutManager)
                const paneElement = findPaneElement(PANE_IDS.STATUS_TIMELINE);
                if (paneElement) {
                  paneElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                  paneElement.classList.add('status-pane-highlight');
                  setTimeout(() => {
                    paneElement.classList.remove('status-pane-highlight');
                  }, 2000);
                } else if (statusTimelineRef.current) {
                  // Fallback to ref if data attribute not found
                  statusTimelineRef.current.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                  statusTimelineRef.current.classList.add('status-pane-highlight');
                  setTimeout(() => {
                    statusTimelineRef.current?.classList.remove('status-pane-highlight');
                  }, 2000);
                }
              }, 300);
            }}
            style={{ cursor: 'pointer' }}
          >
            <span className="label">STATUS:</span>
            <span className={`value ${getStatusType() === 'error' ? 'text-error' : 'text-success'}`}>
              {getStatusDisplay()}
            </span>
            {showStatusHover && statusHoverPosition && (
              <div 
                ref={statusHoverRef}
                className="status-hover-pane"
                style={{
                  top: `${statusHoverPosition.top}px`,
                  left: `${statusHoverPosition.left}px`,
                }}
                onMouseEnter={() => setShowStatusHover(true)}
                onMouseLeave={() => setShowStatusHover(false)}
              >
                <StatusTimeline
                  machineId={machine.machine_id}
                  currentStatus={machine.status}
                  isOnline={machine.is_online}
                  currentError={machine.error}
                  machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                />
              </div>
            )}
          </div>

          <div 
            ref={programIndicatorRef}
            className="machine-row machine-row-hoverable"
            onMouseEnter={() => {
              if (programIndicatorRef.current) {
                const rect = programIndicatorRef.current.getBoundingClientRect();
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const paneWidth = 400;
                const paneHeight = 300;
                
                let left = rect.right + 8;
                let top = rect.top;
                
                if (left + paneWidth > viewportWidth) {
                  left = rect.left - paneWidth - 8;
                }
                if (top + paneHeight > viewportHeight) {
                  top = Math.max(8, viewportHeight - paneHeight - 8);
                }
                if (top < 8) {
                  top = 8;
                }
                
                setProgramHoverPosition({ top, left });
              }
              setShowProgramHover(true);
            }}
            onMouseLeave={() => setShowProgramHover(false)}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) {
                onExpand?.();
              }
              setTimeout(() => {
                // Find pane by data attribute (works with LayoutManager)
                const paneElement = findPaneElement(PANE_IDS.CURRENT_PROGRAM);
                if (paneElement) {
                  paneElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                  paneElement.classList.add('program-pane-highlight');
                  setTimeout(() => {
                    paneElement.classList.remove('program-pane-highlight');
                  }, 2000);
                } else if (currentProgramPaneRef.current) {
                  // Fallback to ref if data attribute not found
                  currentProgramPaneRef.current.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                  currentProgramPaneRef.current.classList.add('program-pane-highlight');
                  setTimeout(() => {
                    currentProgramPaneRef.current?.classList.remove('program-pane-highlight');
                  }, 2000);
                }
              }, 300);
            }}
            style={{ cursor: 'pointer' }}
          >
            <span className="label">PROGRAM:</span>
            <span className="value">{currentProgram || 'NONE'}</span>
            {showProgramHover && programHoverPosition && (
              <div 
                ref={programHoverRef}
                className="program-hover-pane"
                style={{
                  top: `${programHoverPosition.top}px`,
                  left: `${programHoverPosition.left}px`,
                }}
                onMouseEnter={() => setShowProgramHover(true)}
                onMouseLeave={() => setShowProgramHover(false)}
              >
                <CurrentProgramPane
                  machineId={machine.machine_id}
                  machineStatus={machine.status}
                  programName={machine.program_name}
                  machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                />
              </div>
            )}
          </div>

          {/* PRODUCTION RUN SUMMARY (replaces legacy CYCLE/PARTS) */}
          <div
            ref={productionRunsIndicatorRef}
            className="machine-row machine-row-hoverable"
            onMouseEnter={() => {
              if (productionRunsIndicatorRef.current) {
                const rect = productionRunsIndicatorRef.current.getBoundingClientRect();
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const paneWidth = 500;
                const paneHeight = 400;

                let left = rect.right + 8;
                let top = rect.top;

                if (left + paneWidth > viewportWidth) {
                  left = rect.left - paneWidth - 8;
                }
                if (top + paneHeight > viewportHeight) {
                  top = Math.max(8, viewportHeight - paneHeight - 8);
                }
                if (top < 8) {
                  top = 8;
                }

                setProductionRunsHoverPosition({ top, left });
              }
              setShowProductionRunsHover(true);
            }}
            onMouseLeave={() => setShowProductionRunsHover(false)}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) {
                onExpand?.();
              }
              setTimeout(() => {
                const paneElement = findPaneElement(PANE_IDS.PRODUCTION_RUNS);
                if (paneElement) {
                  paneElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                  paneElement.classList.add('cycle-pane-highlight');
                  setTimeout(() => {
                    paneElement.classList.remove('cycle-pane-highlight');
                  }, 2000);
                } else if (cycleHistoryPaneRef.current) {
                  cycleHistoryPaneRef.current.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                  cycleHistoryPaneRef.current.classList.add('cycle-pane-highlight');
                  setTimeout(() => {
                    cycleHistoryPaneRef.current?.classList.remove('cycle-pane-highlight');
                  }, 2000);
                }
              }, 300);
            }}
            style={{ cursor: 'pointer' }}
          >
            <span className="label">PRODUCTION RUN:</span>
            <span className="value production-run-summary">
              {latestRunLoading && !latestRun && 'LOADING...'}
              {!latestRunLoading && !latestRun && 'NO RECENT RUNS'}
              {latestRun && (
                <>
                  <span className="production-run-meta">
                    {latestRun.program_no || 'UNKNOWN'} ·{' '}
                    {(machine.part_display_mode || 'parts') === 'cycle'
                      ? `cycles: ${latestRun.cycles}`
                      : `parts: ${latestRun.part_count}`}
                  </span>
                  {(() => {
                    const runStartMs = new Date(latestRun.run_start).getTime();
                    const runEndMs = new Date(latestRun.run_end).getTime();
                    const totalMs = Math.max(1, runEndMs - runStartMs);
                    let activeMs = 0;
                    for (const seg of latestRun.segments || []) {
                      if ((seg.status || '').toLowerCase() !== 'operating') continue;
                      const s0 = new Date(seg.start_time).getTime();
                      const s1 = new Date(seg.end_time).getTime();
                      if (!isNaN(s0) && !isNaN(s1) && s1 >= s0) activeMs += s1 - s0;
                    }
                    const utilPct = Math.min(100, Math.max(0, Math.round((activeMs / totalMs) * 100)));
                    const runStartMs2 = new Date(latestRun.run_start).getTime();
                    const runEndMs2 = new Date(latestRun.run_end).getTime();
                    const span = Math.max(1, runEndMs2 - runStartMs2);
                    return (
                      <span className="production-run-util-row">
                        <span className="production-run-util text-dim" title="Operating time / total run time">
                          util: {utilPct}%
                        </span>
                        <span className="production-run-bar-track">
                          {latestRun.segments.map((seg, idx) => {
                        const sStartMs = new Date(seg.start_time).getTime();
                        const sEndMs = new Date(seg.end_time).getTime();
                        const left = ((sStartMs - runStartMs2) / span) * 100;
                        const width = Math.max(2, ((sEndMs - sStartMs) / span) * 100);
                        const status = (seg.status || '').toLowerCase();
                        const statusClass =
                          status === 'operating'
                            ? 'mini-segment-operating'
                            : status === 'standby'
                            ? 'mini-segment-standby'
                            : status === 'stopped'
                            ? 'mini-segment-stopped'
                            : status === 'error'
                            ? 'mini-segment-error'
                            : status === 'off'
                            ? 'mini-segment-off'
                            : 'mini-segment-standby';
                        return (
                          <span
                            key={idx}
                            className={`production-run-segment ${statusClass}`}
                            style={{ left: `${left}%`, width: `${width}%` }}
                          />
                        );
                          })}
                        </span>
                      </span>
                    );
                  })()}
                </>
              )}
            </span>
            {showProductionRunsHover && productionRunsHoverPosition && (
              <div
                ref={productionRunsHoverRef}
                className="cycle-hover-pane"
                style={{
                  top: `${productionRunsHoverPosition.top}px`,
                  left: `${productionRunsHoverPosition.left}px`,
                }}
                onMouseEnter={() => setShowProductionRunsHover(true)}
                onMouseLeave={() => setShowProductionRunsHover(false)}
              >
                <ProductionRunsTimelinePane
                  machineId={machine.machine_id}
                  machineLastSuccessfulPollAt={fastPollLastSuccessAt(machine)}
                />
              </div>
            )}
          </div>

          {machine.tools && machine.tools.length > 0 && (
            <div
              ref={toolsIndicatorRef}
              className="machine-row machine-row-hoverable"
              onMouseEnter={() => {
                if (toolsIndicatorRef.current) {
                  const rect = toolsIndicatorRef.current.getBoundingClientRect();
                  const viewportWidth = window.innerWidth;
                  const viewportHeight = window.innerHeight;
                  const paneWidth = 560;
                  const paneHeight = 440;
                  
                  let left = rect.right + 8;
                  let top = rect.top;
                  
                  if (left + paneWidth > viewportWidth) {
                    left = rect.left - paneWidth - 8;
                  }
                  if (top + paneHeight > viewportHeight) {
                    top = Math.max(8, viewportHeight - paneHeight - 8);
                  }
                  if (top < 8) {
                    top = 8;
                  }
                  
                  setToolsHoverPosition({ top, left });
                }
                setShowToolsHover(true);
              }}
              onMouseLeave={() => setShowToolsHover(false)}
              onClick={(e) => {
                e.stopPropagation();
                if (!isExpanded) {
                  onExpand?.();
                }
                setTimeout(() => {
                  // Find pane by data attribute (works with LayoutManager)
                  const paneElement = findPaneElement(PANE_IDS.TOOLS);
                  if (paneElement) {
                    paneElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                    paneElement.classList.add('tools-pane-highlight');
                    setTimeout(() => {
                      paneElement.classList.remove('tools-pane-highlight');
                    }, 2000);
                  } else if (toolsPaneRef.current) {
                    // Fallback to ref if data attribute not found
                    toolsPaneRef.current.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                    toolsPaneRef.current.classList.add('tools-pane-highlight');
                    setTimeout(() => {
                      toolsPaneRef.current?.classList.remove('tools-pane-highlight');
                    }, 2000);
                  }
                }, 300);
              }}
              style={{ cursor: 'pointer' }}
            >
              <span className="label">ATC TOOLS:</span>
              <span className="value">{machine.tools.length}</span>
              {showToolsHover && toolsHoverPosition && (
                <div 
                  ref={toolsHoverRef}
                  className="tools-hover-pane"
                  style={{
                    top: `${toolsHoverPosition.top}px`,
                    left: `${toolsHoverPosition.left}px`,
                  }}
                  onMouseEnter={() => setShowToolsHover(true)}
                  onMouseLeave={() => setShowToolsHover(false)}
                >
                  <ToolsPane
                    variant="hover"
                    tools={machine.tools || []}
                    toolTable={machine.tool_table || []}
                    currentTool={machine.current_tool}
                    machineId={machine.machine_id}
                    units={machine.units ?? 'in'}
                    machineStatus={machine.status}
                    toolsTimestamp={machine.tools_timestamp ?? undefined}
                    toolTableTimestamp={machine.tool_table_timestamp ?? undefined}
                    toolPollIntervalSeconds={machine.tool_poll_interval_seconds ?? 30}
                  />
                </div>
              )}
            </div>
          )}

          {machine.current_tool && (
            <div className="machine-row">
              <span className="label">TOOL:</span>
              <span className="value text-info">T{String(machine.current_tool).padStart(2, '0')}</span>
            </div>
          )}

          {(() => {
            const allAlarms = machine.alarms || [];
            const criticalAlarms = allAlarms.filter((a) => getAlarmSeverityLevel(a) >= 4);
            const warningAlarms = allAlarms.filter((a) => getAlarmSeverityLevel(a) < 4);

            const showHoverAt = (el: HTMLElement | null) => {
              if (!el || allAlarms.length === 0) return;
              const rect = el.getBoundingClientRect();
              const viewportWidth = window.innerWidth;
              const viewportHeight = window.innerHeight;
              const paneWidth = 450;
              const paneHeight = 500;

              let left = rect.right + 8;
              let top = rect.top;

              if (left + paneWidth > viewportWidth) {
                left = rect.left - paneWidth - 8;
              }

              if (top + paneHeight > viewportHeight) {
                top = Math.max(8, viewportHeight - paneHeight - 8);
              }

              if (top < 8) top = 8;

              setAlarmHoverPosition({ top, left });
              setShowAlarmHover(true);
            };

            const handleClick = (e: React.MouseEvent) => {
              e.stopPropagation();
              if (!isExpanded) {
                onExpand?.();
              }
              // Scroll to alarm pane after expansion
              setTimeout(() => {
                const paneElement = findPaneElement(PANE_IDS.ALARMS);
                if (paneElement) {
                  paneElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  paneElement.classList.add('alarm-pane-highlight');
                  setTimeout(() => {
                    paneElement.classList.remove('alarm-pane-highlight');
                  }, 2000);
                } else if (alarmPaneRef.current) {
                  alarmPaneRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  alarmPaneRef.current.classList.add('alarm-pane-highlight');
                  setTimeout(() => {
                    alarmPaneRef.current?.classList.remove('alarm-pane-highlight');
                  }, 2000);
                }
              }, 300);
            };

            return (
              <>
                <div
                  ref={alarmIndicatorRef}
                  className="machine-row machine-row-hoverable"
                  onMouseEnter={() => showHoverAt(alarmIndicatorRef.current)}
                  onMouseLeave={() => setShowAlarmHover(false)}
                  onClick={handleClick}
                  style={{ cursor: allAlarms.length > 0 ? 'pointer' : 'default' }}
                >
                  <span className="label">ALARMS/WARN:</span>
                  <span className="value">
                    <span className={criticalAlarms.length > 0 ? 'text-error' : ''}>
                      {criticalAlarms.length}
                    </span>
                    {' / '}
                    <span className={warningAlarms.length > 0 ? 'text-warning' : ''}>
                      {warningAlarms.length}
                    </span>
                  </span>
                </div>

                {showAlarmHover && alarmHoverPosition && allAlarms.length > 0 && (
                  <div
                    ref={alarmHoverRef}
                    className="alarm-hover-pane"
                    style={{
                      top: `${alarmHoverPosition.top}px`,
                      left: `${alarmHoverPosition.left}px`,
                    }}
                    onMouseEnter={() => setShowAlarmHover(true)}
                    onMouseLeave={() => setShowAlarmHover(false)}
                  >
                    <AlarmPane
                      machineId={machine.machine_id}
                      currentAlarms={allAlarms}
                      isExpanded={true}
                      pollTimestamp={fastPollLastSuccessAt(machine)}
                      pollIntervalSeconds={machine.poll_interval_seconds ?? 5}
                    />
                  </div>
                )}
              </>
            );
          })()}

          <div className="machine-card-divider-thin">
            {'─'.repeat(32)}
          </div>

          <div className="machine-actions">
            <button
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isValidating}
            >
              {isValidating ? '[ VALIDATING... ]' : '[ UPLOAD ]'}
            </button>
          </div>

          <div className="machine-card-divider-thin">
            {'─'.repeat(32)}
          </div>

          <div className="machine-footer">
            <button
              className="machine-edit-footer-btn"
              onClick={startEditing}
              title={canEdit ? "Edit machine" : "Switch to edit this machine (will prompt to save current)"}
            >
              [edit]
            </button>
            <div className="machine-timestamp">
              {machine.is_online ? 'LAST UPDATE' : 'LAST SEEN'}: {new Date(machine.poll_timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>

      <ToolListModal
        isOpen={showToolModal}
        onClose={() => setShowToolModal(false)}
        tools={machine.tools || []}
        machineName={machine.machine_name}
        units={(machine.units || 'in') as 'in' | 'mm'}
      />

      <UploadConfirmationModal
        isOpen={showConfirmationModal}
        onClose={() => {
          setShowConfirmationModal(false);
          setFileContent('');
          setValidationResult(null);
          setSelectedFilename('');
        }}
        result={validationResult as never}
        filename={selectedFilename}
        machineId={machine.machine_id}
        machineName={machine.machine_name}
        machinePath={machine.path || '/'}
        fileContent={fileContent}
        units={(machine.units || 'in') as 'in' | 'mm'}
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".nc,.NC,.txt"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </div>
  );
};
