// Shared types for MachineCard and its sub-components

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
}

export interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  program_name?: string;  // Active program O-number from machine (e.g., "O2045")
  mem_mode?: number;  // MEM mode: 0=Manual, 1=MDI, 2=Memory, 3=Edit, 4=MDI manual, 5=Memory edit
  mem_operation_status?: number;  // MEM operation_status: 0=Reset, 1=Operation, 2=Temporary stop, 3=Block stop
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  tools?: Tool[];  // ATC data
  tool_table?: Tool[];  // TABLE data (TOLN)
  current_tool?: number;
  alarms?: Alarm[];
  panel?: PanelData;  // Panel data (doors, mode, overrides)
  error?: string;
  poll_timestamp: string;
  /** When the last successful fast (status) poll completed; does not advance on failed attempts. */
  last_successful_poll_at?: string | null;
  tools_timestamp?: string | null;
  tool_table_timestamp?: string | null;
  macros_timestamp?: string | null;
  response_time_ms?: number;
  tool_response_time_ms?: number;
  ip_address?: string;
  ftp_username?: string;
  ftp_credentials_configured?: boolean;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  tool_poll_interval_seconds?: number;
  part_display_mode?: 'cycle' | 'parts';
  enabled?: boolean;
  units?: 'in' | 'mm';
  control_version?: 'C00' | 'D00' | null;
  diameter_tolerance?: number;
  length_tolerance_plus?: number;
  length_tolerance_minus?: number;
  tolerance_x?: number;
  tolerance_y?: number;
  tolerance_z?: number;
  use_machine_tool_tolerances?: boolean;
  use_machine_wcs_tolerances?: boolean;
  validate_tool_diameter?: boolean;
  validate_tool_length?: boolean;
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
