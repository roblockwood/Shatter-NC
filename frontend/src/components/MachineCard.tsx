import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ToolListModal } from './ToolListModal';
import { UploadConfirmationModal } from './UploadConfirmationModal';
import { SaveConfirmModal } from './SaveConfirmModal';
import { Select } from './ui/Select';
import { AlarmPane } from './machine-detail/AlarmPane';
import { StatusTimeline } from './machine-detail/StatusTimeline';
import { ToolsPane } from './machine-detail/ToolsPane';
import { CurrentProgramPane } from './machine-detail/CurrentProgramPane';
import { ProductionRunsTimelinePane } from './machine-detail/ProductionRunsTimelinePane';
import { StatusHistoryPane } from './machine-detail/StatusHistoryPane';
import { PanelPane } from './machine-detail/PanelPane';
import { FileManagerPane } from './machine-detail/FileManagerPane';
import { LayoutManager } from './machine-detail/LayoutManager';
import { MachineSyncPanel } from './MachineSyncPanel';
import { PANE_IDS } from '../types/layout';
import { useExpandedMachine } from '../contexts/ExpandedMachineContext';
import './MachineCard.css';
import { API_BASE_URL } from '../config/api';
import { useBetaMode } from '../hooks/useBetaMode';
import { hasCapability } from './MachineCardTypes';
import type { MachineCapability, MachineStatus, MachineCardProps, ValidationResult, ConnectionTestResult } from './MachineCardTypes';
import type { ControllerType } from '../types/machine';
import { defaultModelForController } from '../types/machine';

const PANE_CAPABILITY: Partial<Record<string, MachineCapability>> = {
  [PANE_IDS.STATUS_TIMELINE]: 'statusTimeline',
  [PANE_IDS.ALARMS]: 'alarms',
  [PANE_IDS.CURRENT_PROGRAM]: 'program',
  [PANE_IDS.TOOLS]: 'tools',
  [PANE_IDS.PRODUCTION_RUNS]: 'productionRuns',
  [PANE_IDS.STATUS_HISTORY]: 'statusTimeline',
  [PANE_IDS.PANEL]: 'panel',
  [PANE_IDS.FILE_MANAGER]: 'fileManager',
};

type EditFormData = {
  controller_type: ControllerType;
  ip_address: string;
  ftp_username: string;
  ftp_password: string;
  ftp_port: number;
  path: string;
  poll_interval_seconds: number;
  tool_poll_interval_seconds: number;
  enabled: boolean;
  part_display_mode: string;
  ftp_sync_enabled: boolean;
  diameter_tolerance: number;
  length_tolerance_plus: number;
  length_tolerance_minus: number;
  tolerance_x: number;
  tolerance_y: number;
  tolerance_z: number;
  use_machine_tool_tolerances: boolean;
  use_machine_wcs_tolerances: boolean;
  validate_tool_diameter: boolean;
  validate_tool_length: boolean;
  units: string;
  control_version: 'AUTO' | 'C00' | 'D00';
  opcua_port: number;
  opcua_username: string;
  opcua_password: string;
  opcua_channel: string;
};

function editFormFromMachine(m: MachineStatus): EditFormData {
  const cfg = m.controller_config;
  return {
    controller_type: (m.controller_type ?? 'brother') as ControllerType,
    ip_address: m.ip_address || '',
    ftp_username: m.ftp_username || '',
    ftp_password: m.ftp_password || '',
    ftp_port: m.ftp_port || 21,
    path: m.path !== undefined && m.path !== null ? m.path : '/',
    poll_interval_seconds: m.poll_interval_seconds || 5,
    tool_poll_interval_seconds: m.tool_poll_interval_seconds || 30,
    enabled: m.enabled !== false,
    part_display_mode: m.part_display_mode || 'parts',
    ftp_sync_enabled: m.ftp_sync_enabled === true,
    diameter_tolerance: m.diameter_tolerance || 0.010,
    length_tolerance_plus: m.length_tolerance_plus || 0.02,
    length_tolerance_minus: m.length_tolerance_minus || 0.0,
    tolerance_x: m.tolerance_x || 0.0394,
    tolerance_y: m.tolerance_y || 0.0394,
    tolerance_z: m.tolerance_z || 0.0394,
    use_machine_tool_tolerances: m.use_machine_tool_tolerances || false,
    use_machine_wcs_tolerances: m.use_machine_wcs_tolerances || false,
    validate_tool_diameter: m.validate_tool_diameter !== false,
    validate_tool_length: m.validate_tool_length !== false,
    units: m.units || 'in',
    control_version: (m.control_version ?? 'AUTO') as 'AUTO' | 'C00' | 'D00',
    opcua_port: cfg?.opcua_port ?? 4840,
    opcua_username: cfg?.opcua_username ?? '',
    opcua_password: '',
    opcua_channel: cfg?.channel ?? '0',
  };
}

function editFormFromApi(d: Record<string, unknown>): EditFormData {
  const cfg = (d.controller_config ?? {}) as Record<string, unknown>;
  return {
    controller_type: (d.controller_type ?? 'brother') as ControllerType,
    ip_address: (d.ip_address as string) || '',
    ftp_username: (d.ftp_username as string) || '',
    ftp_password: (d.ftp_password as string) || '',
    ftp_port: (d.ftp_port as number) || 21,
    path: d.path !== undefined && d.path !== null ? (d.path as string) : '/',
    poll_interval_seconds: (d.poll_interval_seconds as number) || 5,
    tool_poll_interval_seconds: (d.tool_poll_interval_seconds as number) || 30,
    enabled: d.enabled !== false,
    part_display_mode: (d.part_display_mode as string) || 'parts',
    ftp_sync_enabled: d.ftp_sync_enabled === true,
    diameter_tolerance: (d.diameter_tolerance as number) || 0.010,
    length_tolerance_plus: (d.length_tolerance_plus as number) || 0.02,
    length_tolerance_minus: (d.length_tolerance_minus as number) || 0.0,
    tolerance_x: (d.tolerance_x as number) || 0.0394,
    tolerance_y: (d.tolerance_y as number) || 0.0394,
    tolerance_z: (d.tolerance_z as number) || 0.0394,
    use_machine_tool_tolerances: (d.use_machine_tool_tolerances as boolean) || false,
    use_machine_wcs_tolerances: (d.use_machine_wcs_tolerances as boolean) || false,
    validate_tool_diameter: d.validate_tool_diameter !== false,
    validate_tool_length: d.validate_tool_length !== false,
    units: (d.units as string) || 'in',
    control_version: ((d.control_version as string) || 'AUTO') as 'AUTO' | 'C00' | 'D00',
    opcua_port: (cfg.opcua_port as number) ?? 4840,
    opcua_username: (cfg.opcua_username as string) ?? '',
    opcua_password: '',
    opcua_channel: (cfg.channel as string) ?? '0',
  };
}

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
  const { isBetaMode } = useBetaMode();
  // Debug: Log machine status for debugging name color (only log when status actually changes)
  // Removed excessive logging - uncomment if needed for debugging
  // console.log(`Machine: ${machine.machine_name}, is_online: ${machine.is_online}, status: "${machine.status}", program_name: "${machine.program_name}"`);

  const [showToolModal, setShowToolModal] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [showSaveConfirmModal, setShowSaveConfirmModal] = useState(false);
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
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState(false);
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [isEditTesting, setIsEditTesting] = useState(false);
  const [editTestResult, setEditTestResult] = useState<ConnectionTestResult | null>(null);
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

  const [editFormData, setEditFormData] = useState<EditFormData>(() => editFormFromMachine(machine));
  const [editMachineName, setEditMachineName] = useState(machine.machine_name || '');
  // Store the original form data when editing starts (from fetched API data)
  const [originalFormData, setOriginalFormData] = useState<EditFormData | null>(null);
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
          const fetchedFormData = editFormFromApi(fullMachineData);
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

  const isEditHeidenhain = editFormData.controller_type === 'heidenhain';
  const editFormValid =
    editMachineName &&
    editFormData.ip_address &&
    (isEditHeidenhain
      ? editFormData.opcua_username
      : editFormData.ftp_username && editFormData.ftp_password);

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
      const payload: Record<string, unknown> = {
        controller_type: editFormData.controller_type,
        model: defaultModelForController(editFormData.controller_type),
        ip_address: editFormData.ip_address,
        poll_interval_seconds: editFormData.poll_interval_seconds,
        enabled: editFormData.enabled,
        units: editFormData.units,
        diameter_tolerance: editFormData.diameter_tolerance,
        length_tolerance_plus: editFormData.length_tolerance_plus,
        length_tolerance_minus: editFormData.length_tolerance_minus,
        tolerance_x: editFormData.tolerance_x,
        tolerance_y: editFormData.tolerance_y,
        tolerance_z: editFormData.tolerance_z,
        use_machine_tool_tolerances: editFormData.use_machine_tool_tolerances,
        use_machine_wcs_tolerances: editFormData.use_machine_wcs_tolerances,
        validate_tool_diameter: editFormData.validate_tool_diameter,
        validate_tool_length: editFormData.validate_tool_length,
      };

      if (isEditHeidenhain) {
        payload.controller_config = {
          opcua_port: editFormData.opcua_port,
          opcua_username: editFormData.opcua_username,
          ...(editFormData.opcua_password ? { opcua_password: editFormData.opcua_password } : {}),
          channel: editFormData.opcua_channel,
        };
      } else {
        Object.assign(payload, {
          ftp_username: editFormData.ftp_username,
          ftp_password: editFormData.ftp_password,
          ftp_port: editFormData.ftp_port,
          path: editFormData.path,
          tool_poll_interval_seconds: editFormData.tool_poll_interval_seconds,
          part_display_mode: editFormData.part_display_mode,
          ftp_sync_enabled: editFormData.ftp_sync_enabled,
          control_version: editFormData.control_version === 'AUTO' ? null : editFormData.control_version,
        });
      }
      const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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
      setEditFormData(editFormFromMachine(machine));
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

  // Trigger save confirmation when collapse is pending
  useEffect(() => {
    if (!pendingCollapse || !isEditing) {
      return;
    }

    // Check for unsaved changes - only show dialog if there are changes
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
    } else {
      // No unsaved changes, proceed with collapse
      performEditCancel();
    }
  }, [pendingCollapse, isEditing, editMachineName, editFormData, machine]);

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
      setShowProductionRunsHover(false);
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
          if (!result.opcua?.success) {
            errors.push(`OPC UA: ${result.opcua?.error || 'Connection failed'}`);
          }
          if (!result.telnet?.success) {
            errors.push(`Telnet: ${result.telnet?.error || 'Connection failed'}`);
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

  // Render expanded view
  if (isExpanded && !isEditing && !editMode) {
    const expandedPanes = [
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
            ].filter((pane) => {
              const cap = PANE_CAPABILITY[pane.id];
              return !cap || hasCapability(machine, cap);
            });

    return (
      <div className={`machine-card expanded`} onClick={handleCardClick}>

        <div className="machine-card-expanded-content" ref={expandedContentRef}>
          <LayoutManager
            machineId={machine.machine_id}
            isEditMode={layoutEditMode}
            onEditModeChange={setLayoutEditMode}
            panes={expandedPanes}
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
    <div className={`machine-card ${isExpanded ? 'expanded' : ''} ${isEditing ? 'edit-mode' : ''} ${isAnyMachineEditing && !isEditing ? 'hidden-when-editing' : ''}`} onClick={handleCardClick}>
      <div className="machine-card-header">
        {isEditing ? (
          <div className="machine-header-edit-row">
            <input
              type="text"
              value={editMachineName}
              onChange={(e) => setEditMachineName(e.target.value)}
              className="machine-name-edit"
              disabled={isEditSaving}
              placeholder="MACHINE NAME"
            />
            <div className="form-checkbox machine-header-checkbox">
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
        ) : (
          <span className={`machine-name ${!machine.is_online ? 'text-error' : (machine.status?.toLowerCase() === 'operating' || machine.status?.toLowerCase().includes('running') ? 'text-glow' : 'text-muted')}`}>{machine.machine_name}</span>
        )}
        <div className="machine-header-actions">
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

          {/* Basic Settings */}
          <div className="form-row-inline">
            <div style={{ flex: '0 0 auto', minWidth: '220px' }}>
              <label>CONTROLLER:</label>
              <Select
                value={editFormData.controller_type}
                onChange={(value) =>
                  setEditFormData({
                    ...editFormData,
                    controller_type: value as ControllerType,
                  })
                }
                disabled={isEditSaving}
                options={[
                  { value: 'brother', label: 'Brother CNC' },
                  { value: 'heidenhain', label: 'Heidenhain TNC (OPC UA)' },
                ]}
              />
            </div>
            <div style={{ flex: '0 0 auto', minWidth: '200px' }}>
              <label>UNITS:</label>
              <Select
                value={editFormData.units}
                onChange={(value) =>
                  setEditFormData({
                    ...editFormData,
                    units: value as 'in' | 'mm',
                  })
                }
                disabled={isEditSaving}
                options={[
                  { value: 'in', label: 'INCHES (in)' },
                  { value: 'mm', label: 'MILLIMETERS (mm)' },
                ]}
              />
            </div>
            {!isEditHeidenhain && (
              <>
                <div style={{ flex: '0 0 auto', minWidth: '260px' }}>
                  <label>CONTROL TYPE:</label>
                  <Select
                    value={editFormData.control_version}
                    onChange={(value) =>
                      setEditFormData({
                        ...editFormData,
                        control_version: value as 'AUTO' | 'C00' | 'D00',
                      })
                    }
                    disabled={isEditSaving}
                    options={[
                      ...((isBetaMode || editFormData.control_version === 'AUTO')
                        ? [{ value: 'AUTO', label: 'AUTO DETECT (beta)' }]
                        : []),
                      { value: 'C00', label: 'C00' },
                      { value: 'D00', label: 'D00' },
                    ]}
                  />
                </div>
                <div style={{ flex: '0 0 auto', minWidth: '260px' }}>
                  <label>PARTS DISPLAY:</label>
                  <Select
                    value={editFormData.part_display_mode}
                    onChange={(value) =>
                      setEditFormData({
                        ...editFormData,
                        part_display_mode: value as 'cycle' | 'parts',
                      })
                    }
                    disabled={isEditSaving}
                    options={[
                      { value: 'parts', label: 'PARTS COUNTER' },
                      { value: 'cycle', label: 'CYCLE COUNT' },
                    ]}
                  />
                </div>
              </>
            )}
          </div>

          {/* Horizontal Form Sections */}
          <div className="form-sections-horizontal">
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

            {isEditHeidenhain ? (
              <>
                <div className="form-row-inline">
                  <div>
                    <label>OPC UA PORT:</label>
                    <input
                      type="number"
                      min="1"
                      max="65535"
                      value={editFormData.opcua_port}
                      onChange={(e) => setEditFormData({ ...editFormData, opcua_port: parseInt(e.target.value) })}
                      disabled={isEditSaving}
                    />
                  </div>
                  <div>
                    <label>CHANNEL:</label>
                    <input
                      type="text"
                      value={editFormData.opcua_channel}
                      onChange={(e) => setEditFormData({ ...editFormData, opcua_channel: e.target.value })}
                      placeholder="0"
                      disabled={isEditSaving}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <label>OPC UA USER:</label>
                  <input
                    type="text"
                    value={editFormData.opcua_username}
                    onChange={(e) => setEditFormData({ ...editFormData, opcua_username: e.target.value })}
                    disabled={isEditSaving}
                  />
                </div>
                <div className="form-row">
                  <label>OPC UA PASS:</label>
                  <input
                    type="password"
                    value={editFormData.opcua_password}
                    onChange={(e) => setEditFormData({ ...editFormData, opcua_password: e.target.value })}
                    placeholder="Leave blank to keep existing"
                    disabled={isEditSaving}
                  />
                </div>
              </>
            ) : (
              <>
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
                    placeholder="/"
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
                    <label>COM PORT:</label>
                    <input
                      type="number"
                      min="1"
                      max="65535"
                      value={10000}
                      disabled={true}
                      title="Telnet communication port (fixed at 10000)"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Polling Intervals - Network Settings */}
            <div className="form-row-inline">
              <div>
                <label>POLL INTERVAL (s):</label>
                <div className="input-with-metric">
                  <input
                    type="number"
                    min="1"
                    max="300"
                    value={editFormData.poll_interval_seconds}
                    onChange={(e) => setEditFormData({ ...editFormData, poll_interval_seconds: parseInt(e.target.value) })}
                    disabled={isEditSaving}
                  />
                  {machine.response_time_ms !== undefined && (
                    <span className="input-metric">{(machine.response_time_ms / 1000).toFixed(1)}s</span>
                  )}
                </div>
              </div>
              {!isEditHeidenhain && (
                <div>
                  <label>TOOL POLL INTERVAL (s):</label>
                  <div className="input-with-metric">
                    <input
                      type="number"
                      min="1"
                      max="600"
                      value={editFormData.tool_poll_interval_seconds}
                      onChange={(e) => setEditFormData({ ...editFormData, tool_poll_interval_seconds: parseInt(e.target.value) })}
                      disabled={isEditSaving}
                    />
                    {machine.tool_response_time_ms !== undefined && (
                      <span className="input-metric">{(machine.tool_response_time_ms / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {isBetaMode && (
              <div className="form-checkbox sync-enable-checkbox">
                <input
                  type="checkbox"
                  id={`ftp-sync-enabled-${machine.machine_id}`}
                  checked={editFormData.ftp_sync_enabled}
                  onChange={(e) => setEditFormData({ ...editFormData, ftp_sync_enabled: e.target.checked })}
                  disabled={isEditSaving}
                />
                <label htmlFor={`ftp-sync-enabled-${machine.machine_id}`}>ENABLE FTP SYNC</label>
              </div>
            )}
            </div>

            {/* Tolerances Section - Brother program validation only */}
            {!isEditHeidenhain && (
            <div className="tolerances-section">
            <div className="tolerances-header">VALIDATION TOLERANCES ({editFormData.units === 'mm' ? 'mm' : 'inches'})</div>

            {/* Tool Tolerances Group */}
            <div className="tolerance-group">
              <div className="tolerance-group-header">
                <div className="tolerance-group-label">TOOL TOLERANCES</div>
                <div className="tolerance-override-toggle" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div>
                    <input
                      type="checkbox"
                      id={`validate-tool-diameter-${machine.machine_id}`}
                      checked={editFormData.validate_tool_diameter}
                      onChange={(e) => setEditFormData({ ...editFormData, validate_tool_diameter: e.target.checked })}
                      disabled={isEditSaving}
                    />
                    <label htmlFor={`validate-tool-diameter-${machine.machine_id}`}>
                      Validate diameter
                    </label>
                  </div>
                  <div>
                    <input
                      type="checkbox"
                      id={`validate-tool-length-${machine.machine_id}`}
                      checked={editFormData.validate_tool_length}
                      onChange={(e) => setEditFormData({ ...editFormData, validate_tool_length: e.target.checked })}
                      disabled={isEditSaving}
                    />
                    <label htmlFor={`validate-tool-length-${machine.machine_id}`}>
                      Validate length
                    </label>
                  </div>
                </div>
                <div className="tolerance-override-toggle">
                  <input
                    type="checkbox"
                    id={`use-machine-tool-tolerances-${machine.machine_id}`}
                    checked={editFormData.use_machine_tool_tolerances}
                    onChange={(e) => setEditFormData({ ...editFormData, use_machine_tool_tolerances: e.target.checked })}
                    disabled={isEditSaving}
                  />
                  <label htmlFor={`use-machine-tool-tolerances-${machine.machine_id}`}>
                    Use machine settings
                  </label>
                </div>
              </div>
              
              <div className={`tolerance-group-content ${!editFormData.use_machine_tool_tolerances ? 'disabled' : ''}`}>
                {/* Tool Diameter Group */}
                <div className="tolerance-subgroup">
                  <div className="tolerance-group-label">TOOL DIAMETER</div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>(±):</label>
                    <input
                      type="number"
                      step="0.00001"
                      value={editFormData.diameter_tolerance}
                      onChange={(e) => setEditFormData({ ...editFormData, diameter_tolerance: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_tool_tolerances}
                    />
                  </div>
                </div>

                {/* Tool Length Group */}
                <div className="tolerance-subgroup">
                  <div className="tolerance-group-label">TOOL LENGTH</div>
                  <div className="tolerance-group-row">
                    <div className="tolerance-field tolerance-field-inline">
                      <label>(+):</label>
                      <input
                        type="number"
                        step="0.0001"
                        value={editFormData.length_tolerance_plus}
                        onChange={(e) => setEditFormData({ ...editFormData, length_tolerance_plus: parseFloat(e.target.value) })}
                        disabled={isEditSaving || !editFormData.use_machine_tool_tolerances}
                      />
                    </div>
                    <div className="tolerance-field tolerance-field-inline">
                      <label>(-):</label>
                      <input
                        type="number"
                        step="0.0001"
                        value={editFormData.length_tolerance_minus}
                        onChange={(e) => setEditFormData({ ...editFormData, length_tolerance_minus: parseFloat(e.target.value) })}
                        disabled={isEditSaving || !editFormData.use_machine_tool_tolerances}
                      />
                    </div>
                  </div>
                </div>
              </div>
              {!editFormData.use_machine_tool_tolerances && (
                <div className="tolerance-hint">
                  Using G-code defaults: diameter must match exactly, length must be ≥ required
                </div>
              )}
            </div>

            {/* WCS Offset Group */}
            <div className="tolerance-group">
              <div className="tolerance-group-header">
                <div className="tolerance-group-label">WCS OFFSET</div>
                <div className="tolerance-override-toggle">
                  <input
                    type="checkbox"
                    id={`use-machine-wcs-tolerances-${machine.machine_id}`}
                    checked={editFormData.use_machine_wcs_tolerances}
                    onChange={(e) => setEditFormData({ ...editFormData, use_machine_wcs_tolerances: e.target.checked })}
                    disabled={isEditSaving}
                  />
                  <label htmlFor={`use-machine-wcs-tolerances-${machine.machine_id}`}>
                    Use machine settings
                  </label>
                </div>
              </div>
              
              <div className={`tolerance-group-content ${!editFormData.use_machine_wcs_tolerances ? 'disabled' : ''}`}>
                <div className="tolerance-group-row">
                  <div className="tolerance-field tolerance-field-inline">
                    <label>X (±):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={editFormData.tolerance_x}
                      onChange={(e) => setEditFormData({ ...editFormData, tolerance_x: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_wcs_tolerances}
                    />
                  </div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>Y (±):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={editFormData.tolerance_y}
                      onChange={(e) => setEditFormData({ ...editFormData, tolerance_y: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_wcs_tolerances}
                    />
                  </div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>Z (±):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={editFormData.tolerance_z}
                      onChange={(e) => setEditFormData({ ...editFormData, tolerance_z: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_wcs_tolerances}
                    />
                  </div>
                </div>
              </div>
              {!editFormData.use_machine_wcs_tolerances && (
                <div className="tolerance-hint">
                  Using G-code E parameter if present in WCS validation macro
                </div>
              )}
            </div>
          </div>
          )}
        </div>

        {isBetaMode && editFormData.ftp_sync_enabled && (
          <div className="machine-sync-section">
            <div className="machine-sync-header">FTP SYNC</div>
            <MachineSyncPanel machineId={machine.machine_id} />
          </div>
        )}

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
              className="form-button delete"
              onClick={() => onDelete?.(machine)}
              disabled={isEditSaving}
            >
              [ DELETE ]
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

          {hasCapability(machine, 'productionRuns') && (
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
          )}

          {hasCapability(machine, 'tools') && machine.tools && machine.tools.length > 0 && (
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

          {hasCapability(machine, 'tools') && machine.current_tool && (
            <div className="machine-row">
              <span className="label">TOOL:</span>
              <span className="value text-info">T{String(machine.current_tool).padStart(2, '0')}</span>
            </div>
          )}

          {!isEditing && (() => {
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

          {hasCapability(machine, 'upload') && (
          <div className="machine-actions">
            <button
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isValidating}
            >
              {isValidating ? '[ VALIDATING... ]' : '[ UPLOAD ]'}
            </button>
          </div>
          )}

          <div className="machine-card-divider-thin">
            {'─'.repeat(32)}
          </div>

          <div className="machine-footer">
            {!isEditing && (
              <button
                className="machine-edit-footer-btn"
                onClick={startEditing}
                title={canEdit ? "Edit machine" : "Switch to edit this machine (will prompt to save current)"}
              >
                [edit]
              </button>
            )}
            <div className="machine-timestamp">
              {machine.is_online ? 'LAST UPDATE' : 'LAST SEEN'}: {new Date(machine.poll_timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>
      )}

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

      <SaveConfirmModal
        isOpen={showSaveConfirmModal}
        onClose={() => {
          setShowSaveConfirmModal(false);
          // If this was triggered by a pending switch, cancel the switch
          if (pendingEditSwitch) {
            onCancelEditSwitch?.();
          }
          // If this was triggered by a pending collapse, cancel the collapse
          if (pendingCollapse) {
            onCancelCollapse?.();
          }
        }}
        onConfirm={() => {
          setShowSaveConfirmModal(false);
          performEditCancel();
          // Switch will happen via onEditEnd callback if pendingEditSwitch
          // Collapse will happen via onEditEnd callback if pendingCollapse
        }}
        onSave={() => {
          setShowSaveConfirmModal(false);
          // Save will trigger onEditEnd which handles the switch or collapse
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
