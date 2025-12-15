import React, { useState, useRef, useEffect } from 'react';
import { ToolListModal } from './ToolListModal';
import { UploadConfirmationModal } from './UploadConfirmationModal';
import { SaveConfirmModal } from './SaveConfirmModal';
import { Modal } from './ui/Modal';
import { AlarmPane } from './machine-detail/AlarmPane';
import { StatusTimeline } from './machine-detail/StatusTimeline';
import { ToolsPane } from './machine-detail/ToolsPane';
import { CurrentProgramPane } from './machine-detail/CurrentProgramPane';
import { CycleHistoryPane } from './machine-detail/CycleHistoryPane';
import './MachineCard.css';
import { API_BASE_URL } from '../config/api';

interface Tool {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}

interface Alarm {
  code: string;
  message: string;
  severity?: string;
  level_class?: string;
}

interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  tools?: Tool[];
  current_tool?: number;
  alarms?: Alarm[];
  error?: string;
  poll_timestamp: string;
  ip_address?: string;
  ftp_username?: string;
  ftp_password?: string;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  enabled?: boolean;
}

interface MachineCardProps {
  machine: MachineStatus;
  editMode?: boolean;
  isExpanded?: boolean;
  isEditing?: boolean; // Controlled from parent to track which machine is being edited
  canEdit?: boolean; // Whether this machine can be edited (only one at a time)
  pendingEditSwitch?: boolean; // Whether a switch to another machine is pending
  onExpand?: () => void;
  onCollapse?: () => void;
  onEditStart?: () => void; // Called when editing starts
  onEditEnd?: () => void; // Called when editing ends
  onRequestEditSwitch?: () => void; // Called when trying to edit while another machine is being edited
  onCancelEditSwitch?: () => void; // Called when user cancels the edit switch
  onDelete?: (machine: MachineStatus) => void;
  scrollToStatus?: boolean; // Flag to trigger scroll to status timeline
}

export const MachineCard: React.FC<MachineCardProps> = ({ 
  machine, 
  editMode = false, 
  isExpanded = false,
  isEditing: isEditingProp = false,
  canEdit = true,
  pendingEditSwitch = false,
  onExpand,
  onCollapse,
  onEditStart,
  onEditEnd,
  onRequestEditSwitch,
  onCancelEditSwitch,
  onDelete,
  scrollToStatus = false
}) => {
  // Debug: Log machine status for debugging name color
  console.log(`Machine: ${machine.machine_name}, is_online: ${machine.is_online}, status: "${machine.status}"`);

  const [showToolModal, setShowToolModal] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [showSaveConfirmModal, setShowSaveConfirmModal] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
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
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState(false);
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [isEditTesting, setIsEditTesting] = useState(false);
  const [editTestResult, setEditTestResult] = useState<any>(null);
  const [expandedPaneModal, setExpandedPaneModal] = useState<{ type: string; props: any } | null>(null);
  const [expandedPane, setExpandedPane] = useState<string | null>(null);
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
  const [showCycleHover, setShowCycleHover] = useState(false);
  const [cycleHoverPosition, setCycleHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const cycleHistoryPaneRef = useRef<HTMLDivElement>(null);
  const cycleHoverRef = useRef<HTMLDivElement>(null);
  const cycleIndicatorRef = useRef<HTMLDivElement>(null);
  const [currentProgram, setCurrentProgram] = useState<string | null>(null);
  
  // Cache alarms from machine prop to avoid refetching
  useEffect(() => {
    if (machine.alarms) {
      setCachedAlarms(machine.alarms);
    }
  }, [machine.alarms]);

  // Fetch current program name
  useEffect(() => {
    if (machine.is_online && machine.machine_id) {
      const fetchProgram = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/programs/machines/${machine.machine_id}/deployments?current_only=true`);
          if (response.ok) {
            const data = await response.json();
            if (data && data.length > 0) {
              setCurrentProgram(data[0].deployed_filename);
            } else {
              setCurrentProgram(null);
            }
          }
        } catch (error) {
          console.error('Error fetching current program:', error);
          setCurrentProgram(null);
        }
      };
      fetchProgram();
      const interval = setInterval(fetchProgram, 30000);
      return () => clearInterval(interval);
    } else {
      setCurrentProgram(null);
    }
  }, [machine.machine_id, machine.is_online]);

  // Handle scroll to status timeline when requested
  useEffect(() => {
    if (scrollToStatus && isExpanded && statusTimelineRef.current) {
      setTimeout(() => {
        if (statusTimelineRef.current) {
          statusTimelineRef.current.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
          statusTimelineRef.current.classList.add('status-pane-highlight');
          setTimeout(() => {
            statusTimelineRef.current?.classList.remove('status-pane-highlight');
          }, 2000);
        }
      }, 300);
    }
  }, [scrollToStatus, isExpanded]);

  const [editFormData, setEditFormData] = useState({
    ip_address: machine.ip_address || '',
    ftp_username: machine.ftp_username || '',
    ftp_password: machine.ftp_password || '',
    ftp_port: machine.ftp_port || 21,
    http_port: machine.http_port || 80,
    path: machine.path !== undefined && machine.path !== null ? machine.path : '/program',
    poll_interval_seconds: machine.poll_interval_seconds || 5,
    enabled: machine.enabled !== false,
    diameter_tolerance: (machine as any).diameter_tolerance || 0.010,
    length_tolerance_plus: (machine as any).length_tolerance_plus || 0.02,
    length_tolerance_minus: (machine as any).length_tolerance_minus || 0.0,
    tolerance_x: (machine as any).tolerance_x || 0.0394,
    tolerance_y: (machine as any).tolerance_y || 0.0394,
    tolerance_z: (machine as any).tolerance_z || 0.0394,
  });
  const [editMachineName, setEditMachineName] = useState(machine.machine_name || '');
  // Store the original form data when editing starts (from fetched API data)
  const [originalFormData, setOriginalFormData] = useState<typeof editFormData | null>(null);
  const [originalMachineName, setOriginalMachineName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch full machine configuration data on mount
  useEffect(() => {
    const fetchMachineConfig = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`);
        if (response.ok) {
          const fullMachineData = await response.json();
          // Store the fetched data as the original baseline
          const fetchedFormData = {
            ip_address: fullMachineData.ip_address || '',
            ftp_username: fullMachineData.ftp_username || '',
            ftp_password: fullMachineData.ftp_password || '',
            ftp_port: fullMachineData.ftp_port || 21,
            http_port: fullMachineData.http_port || 80,
            path: fullMachineData.path !== undefined && fullMachineData.path !== null ? fullMachineData.path : '/program',
            poll_interval_seconds: fullMachineData.poll_interval_seconds || 5,
            enabled: fullMachineData.enabled !== false,
            diameter_tolerance: fullMachineData.diameter_tolerance || 0.010,
            length_tolerance_plus: fullMachineData.length_tolerance_plus || 0.02,
            length_tolerance_minus: fullMachineData.length_tolerance_minus || 0.0,
            tolerance_x: fullMachineData.tolerance_x || 0.0394,
            tolerance_y: fullMachineData.tolerance_y || 0.0394,
            tolerance_z: fullMachineData.tolerance_z || 0.0394,
          };
          setOriginalFormData(fetchedFormData);
          setOriginalMachineName(fullMachineData.name || '');
          // Update form data with fetched configuration
          setEditMachineName(fullMachineData.name || '');
          setEditFormData(fetchedFormData);
        }
      } catch (error) {
        console.error('Error fetching machine configuration:', error);
      }
    };

    fetchMachineConfig();
  }, [machine.machine_id]);

  const editFormValid = editMachineName && editFormData.ip_address && editFormData.ftp_username && editFormData.ftp_password;

  // Check if there are unsaved changes
  const hasUnsavedChanges = () => {
    if (!isEditing) return false;
    
    // If we don't have original data yet (still loading), assume no changes
    if (!originalFormData || originalMachineName === null) return false;
    
    // Compare machine name against original
    if (editMachineName !== originalMachineName) return true;
    
    // Compare all form fields against original (from fetched API data)
    return JSON.stringify(editFormData) !== JSON.stringify(originalFormData);
  };

  const handleEditSave = async () => {
    if (!editFormValid) {
      setEditError('Please fill in all required fields');
      return;
    }

    setIsEditSaving(true);
    setEditError(null);
    setEditSuccess(false);

    try {
      const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editFormData),
      });

      if (!response.ok) {
        throw new Error(`Update failed: ${response.statusText}`);
      }

      setEditSuccess(true);
      setTimeout(() => {
        stopEditing();
        setEditSuccess(false);
      }, 1500);
    } catch (error) {
      console.error('Edit error:', error);
      setEditError(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsEditSaving(false);
    }
  };

  const performEditCancel = () => {
    stopEditing();
    setEditError(null);
    setEditSuccess(false);
    setEditTestResult(null);
    // Reset to original values (from fetched API data, not machine prop)
    if (originalFormData && originalMachineName !== null) {
      setEditMachineName(originalMachineName);
      setEditFormData(originalFormData);
    } else {
      // Fallback to machine prop if original not loaded yet
      setEditMachineName(machine.machine_name || '');
      setEditFormData({
        ip_address: machine.ip_address || '',
        ftp_username: machine.ftp_username || '',
        ftp_password: machine.ftp_password || '',
        ftp_port: machine.ftp_port || 21,
        http_port: machine.http_port || 80,
        path: machine.path !== undefined && machine.path !== null ? machine.path : '/program',
        poll_interval_seconds: machine.poll_interval_seconds || 5,
        enabled: machine.enabled !== false,
        diameter_tolerance: (machine as any).diameter_tolerance || 0.010,
        length_tolerance_plus: (machine as any).length_tolerance_plus || 0.02,
        length_tolerance_minus: (machine as any).length_tolerance_minus || 0.0,
        tolerance_x: (machine as any).tolerance_x || 0.0394,
        tolerance_y: (machine as any).tolerance_y || 0.0394,
        tolerance_z: (machine as any).tolerance_z || 0.0394,
      });
    }
  };

  const handleEditCancel = () => {
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
      return;
    }
    
    // No unsaved changes, proceed with cancel
    performEditCancel();
  };

  // Trigger save confirmation when edit switch is pending
  useEffect(() => {
    if (!pendingEditSwitch || !isEditing) {
      return;
    }

    // Check for unsaved changes - only show dialog if there are changes
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
    } else {
      // No unsaved changes, just switch directly without confirmation
      performEditCancel();
    }
  }, [pendingEditSwitch, isEditing, editMachineName, editFormData, machine]);

  // Handle Escape key to collapse expanded card or exit edit mode
  useEffect(() => {
    if (isEditing) {
      // In edit mode, Escape should trigger cancel (with confirmation if unsaved)
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          handleEditCancel();
        }
      };

      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    } else if (isExpanded && !editMode) {
      // In expanded view, Escape should collapse
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onCollapse?.();
        }
      };

      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [isExpanded, isEditing, editMode, onCollapse, handleEditCancel]);

  // Dismiss all hover panes when card is collapsed
  useEffect(() => {
    if (!isExpanded) {
      setShowStatusHover(false);
      setShowProgramHover(false);
      setShowCycleHover(false);
      setShowToolsHover(false);
      setShowAlarmHover(false);
    }
  }, [isExpanded]);

  const handleEditTestConnection = async () => {
    if (!editFormData.ip_address) {
      setEditError('IP address required for connection test');
      return;
    }

    setIsEditTesting(true);
    setEditError(null);
    setEditTestResult(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}/test`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();

        // Check if connection actually succeeded
        if (result.overall_status === 'online') {
          setEditTestResult(result);
        } else {
          // Build error message from failed services
          const errors = [];
          if (!result.http?.success) {
            errors.push(`HTTP: ${result.http?.error || 'Connection failed'}`);
          }
          if (!result.ftp?.success) {
            errors.push(`FTP: ${result.ftp?.error || 'Connection failed'}`);
          }
          setEditError(`Connection test failed: ${errors.join(', ')}`);
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setEditError(errorData.detail || 'Connection test failed');
      }
    } catch (err) {
      setEditError(`Test failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsEditTesting(false);
    }
  };

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

  const formatTime = (time: string | undefined) => {
    if (!time || time === '0000:00:00.0') return '00:00:00';
    return time.substring(0, 8); // Remove decimal if present
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
      isEditing ||
      editMode
    ) {
      return;
    }
    
    if (isExpanded) {
      onCollapse?.();
    } else {
      onExpand?.();
    }
  };

  // Render expanded view
  if (isExpanded && !isEditing && !editMode) {
    return (
      <div className={`machine-card expanded`} onClick={handleCardClick}>
        <div className="machine-card-expanded-header">
          <div className="expanded-header-top">
            ╔{'═'.repeat(70)}╗
          </div>
          <div className="expanded-header-title">
            <span className="expanded-machine-name">{machine.machine_name}</span>
            <div className="expanded-header-actions">
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
          </div>
          <div className="expanded-header-bottom">
            ╠{'═'.repeat(70)}╣
          </div>
        </div>

        <div className="machine-card-expanded-content">
          <div className="expanded-pane-full">
            <div ref={statusTimelineRef}>
              <StatusTimeline 
                machineId={machine.machine_id} 
                currentStatus={machine.status} 
                isOnline={machine.is_online}
                currentError={machine.error}
                onExpand={() => setExpandedPaneModal({ type: 'timeline', props: { machineId: machine.machine_id, currentStatus: machine.status, isOnline: machine.is_online, currentError: machine.error } })}
              />
            </div>
          </div>

          <div className="expanded-panes-top">
            <div className="expanded-pane-left">
              <div ref={alarmPaneRef}>
                <AlarmPane 
                  machineId={machine.machine_id} 
                  currentAlarms={machine.alarms || cachedAlarms || undefined}
                  onExpand={() => setExpandedPaneModal({ type: 'alarms', props: { machineId: machine.machine_id, currentAlarms: machine.alarms || cachedAlarms } })}
                />
              </div>
            </div>
            <div className="expanded-pane-right">
              <div ref={currentProgramPaneRef}>
                <CurrentProgramPane 
                  machineId={machine.machine_id}
                  machineStatus={machine.status}
                  onExpand={() => setExpandedPaneModal({ type: 'program', props: { machineId: machine.machine_id, machineStatus: machine.status } })}
                />
              </div>
            </div>
          </div>

          <div className="expanded-panes-bottom">
            <div className="expanded-pane-left">
              <div ref={toolsPaneRef}>
                <ToolsPane 
                  tools={machine.tools || []}
                  currentTool={machine.current_tool}
                  machineId={machine.machine_id}
                  onExpand={() => setExpandedPane(expandedPane === 'tools' ? null : 'tools')}
                  isExpanded={expandedPane === 'tools'}
                  isFullExpanded={expandedPane === 'tools'}
                />
              </div>
            </div>
            <div className="expanded-pane-right">
              <div ref={cycleHistoryPaneRef}>
                <CycleHistoryPane 
                  machineId={machine.machine_id}
                  onExpand={() => setExpandedPaneModal({ type: 'history', props: { machineId: machine.machine_id } })}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Expanded Pane Modals */}
        {expandedPaneModal && (
          <Modal
            isOpen={true}
            onClose={() => setExpandedPaneModal(null)}
            title={expandedPaneModal.type === 'alarms' ? 'ALARMS' :
                   expandedPaneModal.type === 'program' ? 'CURRENT PROGRAM' :
                   expandedPaneModal.type === 'tools' ? 'TOOLS' :
                   expandedPaneModal.type === 'timeline' ? 'STATUS TIMELINE' :
                   expandedPaneModal.type === 'history' ? 'CYCLE HISTORY' : 'EXPANDED VIEW'}
          >
            <div 
              style={{ height: 'auto', overflow: 'visible' }}
              onClick={(e) => e.stopPropagation()}
            >
              {expandedPaneModal.type === 'alarms' && (
                <AlarmPane 
                  machineId={expandedPaneModal.props.machineId} 
                  currentAlarms={expandedPaneModal.props.currentAlarms}
                  onExpand={undefined}
                  isExpanded={true}
                />
              )}
              {expandedPaneModal.type === 'program' && (
                <CurrentProgramPane 
                  machineId={expandedPaneModal.props.machineId}
                  machineStatus={expandedPaneModal.props.machineStatus}
                />
              )}
              {expandedPaneModal.type === 'tools' && (
                <ToolsPane 
                  tools={expandedPaneModal.props.tools}
                  currentTool={expandedPaneModal.props.currentTool}
                  machineId={expandedPaneModal.props.machineId}
                  isExpanded={true}
                />
              )}
              {expandedPaneModal.type === 'timeline' && (
                <StatusTimeline 
                  machineId={expandedPaneModal.props.machineId}
                  currentStatus={expandedPaneModal.props.currentStatus}
                  isOnline={expandedPaneModal.props.isOnline}
                  currentError={expandedPaneModal.props.currentError}
                />
              )}
              {expandedPaneModal.type === 'history' && (
                <CycleHistoryPane 
                  machineId={expandedPaneModal.props.machineId}
                />
              )}
            </div>
          </Modal>
        )}

        <ToolListModal
          isOpen={showToolModal}
          onClose={() => setShowToolModal(false)}
          tools={(machine.tools || []) as any}
          machineName={machine.machine_name}
        />

        <UploadConfirmationModal
          isOpen={showConfirmationModal}
          onClose={() => {
            setShowConfirmationModal(false);
            setFileContent('');
            setValidationResult(null);
            setSelectedFilename('');
          }}
          result={validationResult}
          filename={selectedFilename}
          machineId={machine.machine_id}
          machineName={machine.machine_name}
          machinePath={machine.path || '/PROGRAM'}
          fileContent={fileContent}
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
    <div className={`machine-card ${isExpanded ? 'expanded' : ''}`} onClick={handleCardClick}>
      <div className="machine-card-header">
        {isEditing ? (
          <input
            type="text"
            value={editMachineName}
            onChange={(e) => setEditMachineName(e.target.value)}
            className="machine-name-edit"
            disabled={isEditSaving}
          />
        ) : (
          <span className={`machine-name ${!machine.is_online ? 'text-error' : (machine.status?.toLowerCase() === 'operating' || machine.status?.toLowerCase().includes('running') ? 'text-glow' : 'text-muted')}`}>{machine.machine_name}</span>
        )}
        <div className="machine-header-actions">
          {editMode && !isEditing && (
            <>
              <button
                className="card-action-btn"
                onClick={startEditing}
                title={canEdit ? "Edit machine" : "Switch to edit this machine (will prompt to save current)"}
              >
                [=]
              </button>
              <button
                className="card-action-btn delete"
                onClick={() => onDelete?.(machine)}
                title="Delete machine"
              >
                [X]
              </button>
            </>
          )}
        </div>
      </div>

      <div className="machine-card-divider">
        ├{'─'.repeat(30)}┤
      </div>

      {isEditing ? (
        <div className="machine-edit-form">
          {editError && (
            <div className="form-error text-error">
              {editError}
            </div>
          )}

          {editSuccess && (
            <div className="form-success text-success">
              Machine updated successfully!
            </div>
          )}

          {/* Network Configuration Section */}
          <div className="network-config-section">
            <div className="network-config-header">NETWORK CONFIGURATION</div>

            <div className="form-row">
              <label>IP:</label>
            <input
              type="text"
              value={editFormData.ip_address}
              onChange={(e) => setEditFormData({ ...editFormData, ip_address: e.target.value })}
              placeholder="192.168.1.100"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row">
            <label>FTP USER:</label>
            <input
              type="text"
              value={editFormData.ftp_username}
              onChange={(e) => setEditFormData({ ...editFormData, ftp_username: e.target.value })}
              placeholder="anonymous"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row">
            <label>FTP PASS:</label>
            <input
              type="password"
              value={editFormData.ftp_password}
              onChange={(e) => setEditFormData({ ...editFormData, ftp_password: e.target.value })}
              placeholder="anonymous"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row">
            <label>FTP PATH:</label>
            <input
              type="text"
              value={editFormData.path}
              onChange={(e) => setEditFormData({ ...editFormData, path: e.target.value })}
              placeholder="/program"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row-inline">
            <div>
              <label>FTP PORT:</label>
              <input
                type="number"
                min="1"
                max="65535"
                value={editFormData.ftp_port}
                onChange={(e) => setEditFormData({ ...editFormData, ftp_port: parseInt(e.target.value) })}
                disabled={isEditSaving}
              />
            </div>
            <div>
              <label>HTTP PORT:</label>
              <input
                type="number"
                min="1"
                max="65535"
                value={editFormData.http_port}
                onChange={(e) => setEditFormData({ ...editFormData, http_port: parseInt(e.target.value) })}
                disabled={isEditSaving}
              />
            </div>
          </div>

          <div className="form-row-inline">
            <div>
              <label>POLL INTERVAL:</label>
              <input
                type="number"
                min="1"
                max="300"
                value={editFormData.poll_interval_seconds}
                onChange={(e) => setEditFormData({ ...editFormData, poll_interval_seconds: parseInt(e.target.value) })}
                disabled={isEditSaving}
              />
              <span className="form-hint">seconds</span>
            </div>
            <div className="form-checkbox">
              <input
                type="checkbox"
                id={`enabled-${machine.machine_id}`}
                checked={editFormData.enabled}
                onChange={(e) => setEditFormData({ ...editFormData, enabled: e.target.checked })}
                disabled={isEditSaving}
              />
              <label htmlFor={`enabled-${machine.machine_id}`}>ENABLED</label>
            </div>
          </div>
          </div>

          {/* Tolerances Section */}
          <div className="tolerances-section">
            <div className="tolerances-header">VALIDATION TOLERANCES (inches)</div>

            {/* Tool Diameter Group */}
            <div className="tolerance-group">
              <div className="tolerance-group-label">TOOL DIAMETER</div>
              <div className="tolerance-field tolerance-field-inline">
                <label>(±):</label>
                <input
                  type="number"
                  step="0.00001"
                  value={editFormData.diameter_tolerance}
                  onChange={(e) => setEditFormData({ ...editFormData, diameter_tolerance: parseFloat(e.target.value) })}
                  disabled={isEditSaving}
                />
              </div>
            </div>

            {/* Tool Length Group */}
            <div className="tolerance-group">
              <div className="tolerance-group-label">TOOL LENGTH</div>
              <div className="tolerance-group-row">
                <div className="tolerance-field tolerance-field-inline">
                  <label>(+):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={editFormData.length_tolerance_plus}
                    onChange={(e) => setEditFormData({ ...editFormData, length_tolerance_plus: parseFloat(e.target.value) })}
                    disabled={isEditSaving}
                  />
                </div>
                <div className="tolerance-field tolerance-field-inline">
                  <label>(-):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={editFormData.length_tolerance_minus}
                    onChange={(e) => setEditFormData({ ...editFormData, length_tolerance_minus: parseFloat(e.target.value) })}
                    disabled={isEditSaving}
                  />
                </div>
              </div>
            </div>

            {/* WCS Offset Group */}
            <div className="tolerance-group">
              <div className="tolerance-group-label">WCS OFFSET</div>
              <div className="tolerance-group-row">
                <div className="tolerance-field tolerance-field-inline">
                  <label>X (±):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={editFormData.tolerance_x}
                    onChange={(e) => setEditFormData({ ...editFormData, tolerance_x: parseFloat(e.target.value) })}
                    disabled={isEditSaving}
                  />
                </div>
                <div className="tolerance-field tolerance-field-inline">
                  <label>Y (±):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={editFormData.tolerance_y}
                    onChange={(e) => setEditFormData({ ...editFormData, tolerance_y: parseFloat(e.target.value) })}
                    disabled={isEditSaving}
                  />
                </div>
                <div className="tolerance-field tolerance-field-inline">
                  <label>Z (±):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={editFormData.tolerance_z}
                    onChange={(e) => setEditFormData({ ...editFormData, tolerance_z: parseFloat(e.target.value) })}
                    disabled={isEditSaving}
                  />
                </div>
              </div>
            </div>
          </div>

          {editTestResult && (
            <div className="form-success text-success">
              Connection successful!
            </div>
          )}

          <div className="form-actions">
            <button
              className="form-button test"
              onClick={handleEditTestConnection}
              disabled={!editFormData.ip_address || isEditSaving || isEditTesting}
            >
              {isEditTesting ? '[ TESTING... ]' : '[ TEST CONNECTION ]'}
            </button>
            <button
              className="form-button cancel"
              onClick={handleEditCancel}
              disabled={isEditSaving}
            >
              [ CANCEL ]
            </button>
            <button
              className="form-button save"
              onClick={handleEditSave}
              disabled={!editFormValid || isEditSaving}
            >
              {isEditSaving ? '[ SAVING... ]' : '[ SAVE ]'}
            </button>
          </div>
        </div>
      ) : (
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
                if (statusTimelineRef.current) {
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
                if (currentProgramPaneRef.current) {
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
                />
              </div>
            )}
          </div>

          <div 
            ref={cycleIndicatorRef}
            className="machine-row machine-row-hoverable"
            onMouseEnter={() => {
              if (cycleIndicatorRef.current) {
                const rect = cycleIndicatorRef.current.getBoundingClientRect();
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
                
                setCycleHoverPosition({ top, left });
              }
              setShowCycleHover(true);
            }}
            onMouseLeave={() => setShowCycleHover(false)}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) {
                onExpand?.();
              }
              setTimeout(() => {
                if (cycleHistoryPaneRef.current) {
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
            <span className="label">CYCLE/PARTS:</span>
            <span className="value">
              {formatTime(machine.cycle_time)}
              {machine.counters && machine.counters.length > 0 && `/${machine.counters[0].count}`}
            </span>
            {showCycleHover && cycleHoverPosition && (
              <div 
                ref={cycleHoverRef}
                className="cycle-hover-pane"
                style={{
                  top: `${cycleHoverPosition.top}px`,
                  left: `${cycleHoverPosition.left}px`,
                }}
                onMouseEnter={() => setShowCycleHover(true)}
                onMouseLeave={() => setShowCycleHover(false)}
              >
                <CycleHistoryPane
                  machineId={machine.machine_id}
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
                  const paneWidth = 500;
                  const paneHeight = 500;
                  
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
                  if (toolsPaneRef.current) {
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
                    tools={machine.tools || []}
                    currentTool={machine.current_tool}
                    machineId={machine.machine_id}
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

          {!isEditing && (
            <div 
              ref={alarmIndicatorRef}
              className="machine-row machine-row-hoverable"
              onMouseEnter={() => {
                if (alarmIndicatorRef.current && machine.alarms && machine.alarms.length > 0) {
                  const rect = alarmIndicatorRef.current.getBoundingClientRect();
                  const viewportWidth = window.innerWidth;
                  const viewportHeight = window.innerHeight;
                  const paneWidth = 450; // Approximate width
                  const paneHeight = 500; // Max height
                  
                  // Calculate position - prefer right side, but adjust if needed
                  let left = rect.right + 8;
                  let top = rect.top;
                  
                  // If pane would go off right edge, position to the left
                  if (left + paneWidth > viewportWidth) {
                    left = rect.left - paneWidth - 8;
                  }
                  
                  // If pane would go off bottom, adjust upward
                  if (top + paneHeight > viewportHeight) {
                    top = Math.max(8, viewportHeight - paneHeight - 8);
                  }
                  
                  // Ensure it doesn't go off top
                  if (top < 8) {
                    top = 8;
                  }
                  
                  setAlarmHoverPosition({ top, left });
                }
                if (machine.alarms && machine.alarms.length > 0) {
                  setShowAlarmHover(true);
                }
              }}
              onMouseLeave={() => setShowAlarmHover(false)}
              onClick={(e) => {
                e.stopPropagation();
                if (!isExpanded) {
                  onExpand?.();
                }
                // Scroll to alarm pane after expansion
                setTimeout(() => {
                  if (alarmPaneRef.current) {
                    alarmPaneRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // Highlight briefly
                    alarmPaneRef.current.classList.add('alarm-pane-highlight');
                    setTimeout(() => {
                      alarmPaneRef.current?.classList.remove('alarm-pane-highlight');
                    }, 2000);
                  }
                }, 300);
              }}
              style={{ cursor: machine.alarms && machine.alarms.length > 0 ? 'pointer' : 'default' }}
            >
              <span className="label">ALARMS:</span>
              <span className={`value ${machine.alarms && machine.alarms.length > 0 ? 'text-error' : ''}`}>
                {machine.alarms ? machine.alarms.length : 0}
              </span>
              {showAlarmHover && alarmHoverPosition && machine.alarms && machine.alarms.length > 0 && (
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
                    currentAlarms={machine.alarms}
                    isExpanded={true}
                  />
                </div>
              )}
            </div>
          )}

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

          <div className="machine-timestamp">
            {machine.is_online ? 'LAST UPDATE' : 'LAST SEEN'}: {new Date(machine.poll_timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}

      <ToolListModal
        isOpen={showToolModal}
        onClose={() => setShowToolModal(false)}
        tools={(machine.tools || []) as any}
        machineName={machine.machine_name}
      />

      <UploadConfirmationModal
        isOpen={showConfirmationModal}
        onClose={() => {
          setShowConfirmationModal(false);
          setFileContent('');
          setValidationResult(null);
          setSelectedFilename('');
        }}
        result={validationResult}
        filename={selectedFilename}
        machineId={machine.machine_id}
        machineName={machine.machine_name}
        machinePath={machine.path || '/PROGRAM'}
        fileContent={fileContent}
      />

      <SaveConfirmModal
        isOpen={showSaveConfirmModal}
        onClose={() => {
          setShowSaveConfirmModal(false);
          // If this was triggered by a pending switch, cancel the switch
          if (pendingEditSwitch) {
            onCancelEditSwitch?.();
          }
        }}
        onConfirm={() => {
          setShowSaveConfirmModal(false);
          performEditCancel();
          // Switch will happen via onEditEnd callback
        }}
        onSave={() => {
          setShowSaveConfirmModal(false);
          // Save will trigger onEditEnd which handles the switch
          handleEditSave();
        }}
        machineName={machine.machine_name || 'Unknown'}
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
