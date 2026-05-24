// Shared types for MachineCard and its sub-components (MachineEditPanel, etc.)

import type { MachineStatusBase } from '../types/machine';

export type { MachineCapability, ControllerType } from '../types/machine';
export { getCapabilities, hasCapability, isBrotherMachine, isHeidenhainMachine } from '../types/machine';

export interface Tool {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}

export interface Alarm {
  code: string;
  message: string;
  severity?: string;
  level_class?: string;
  stop_level?: string;
}

export interface PanelData {
  doors?: Record<string, unknown>;
  mode?: unknown;
  overrides?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ValidationResult {
  valid: boolean;
  tools: Record<number, unknown>;
  wcs_offset: unknown;
  warnings: string[];
  errors: string[];
  metadata: {
    posted_date?: string;
    estimated_runtime_seconds?: number;
    tool_count: number;
    line_count: number;
    file_size: number;
  };
}

export interface ConnectionTestResult {
  overall_status: string;
  telnet?: { success: boolean; error?: string };
  ftp?: { success: boolean; error?: string };
  opcua?: { success: boolean; error?: string; nc_state?: string };
}

export interface MachineStatus extends MachineStatusBase {
  tools?: Tool[];
  tool_table?: Tool[];
  alarms?: Alarm[];
  panel?: PanelData;
}

export interface MachineCardProps {
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
  pendingCollapse?: boolean; // Whether a collapse is pending (will check for unsaved changes)
  onCancelCollapse?: () => void; // Called when user cancels the collapse
  onDelete?: (machine: MachineStatus) => void;
  scrollToStatus?: boolean; // Flag to trigger scroll to status timeline
  isAnyMachineEditing?: boolean; // Whether any machine is currently being edited
}
