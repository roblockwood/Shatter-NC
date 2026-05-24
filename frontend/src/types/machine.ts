/** CNC machine types and capability helpers shared across dashboard components. */

export type ControllerType = 'brother' | 'heidenhain';

export type MachineCapability =
  | 'status'
  | 'alarms'
  | 'program'
  | 'statusTimeline'
  | 'tools'
  | 'toolTable'
  | 'panel'
  | 'fileManager'
  | 'counters'
  | 'upload'
  | 'productionRuns';

export const BROTHER_CAPABILITIES: MachineCapability[] = [
  'status',
  'alarms',
  'program',
  'statusTimeline',
  'tools',
  'toolTable',
  'panel',
  'fileManager',
  'counters',
  'upload',
  'productionRuns',
];

export const HEIDENHAIN_V1_CAPABILITIES: MachineCapability[] = [
  'status',
  'alarms',
  'program',
  'statusTimeline',
];

export interface HeidenhainControllerConfig {
  opcua_port?: number;
  opcua_username?: string;
  opcua_password?: string;
  opcua_endpoint_path?: string;
  opcua_endpoint_url?: string;
  opcua_auto_discover?: boolean;
  channel?: string;
}

export interface MachineStatusBase {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  program_name?: string;
  mem_mode?: number;
  mem_operation_status?: number;
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  tools?: Array<{
    pot_number?: string | number;
    tool_number: number;
    tool_name?: string;
    diameter?: number;
    length?: number;
  }>;
  tool_table?: Array<{
    tool_number: number;
    tool_name?: string;
    diameter?: number;
    length?: number;
    pot_number?: string | number;
  }>;
  current_tool?: number;
  alarms?: Array<{
    code: string;
    message: string;
    program?: string;
    line?: string;
    stop_level?: number;
    severity?: string;
    source?: string;
  }>;
  panel?: Record<string, unknown>;
  vendor_data?: Record<string, unknown>;
  error?: string;
  poll_timestamp: string;
  last_successful_poll_at?: string | null;
  tools_timestamp?: string | null;
  tool_table_timestamp?: string | null;
  macros_timestamp?: string | null;
  response_time_ms?: number;
  tool_response_time_ms?: number;
  ip_address?: string;
  ftp_username?: string;
  ftp_password?: string;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  tool_poll_interval_seconds?: number;
  part_display_mode?: 'cycle' | 'parts';
  ftp_sync_enabled?: boolean;
  enabled?: boolean;
  units?: 'in' | 'mm';
  control_version?: 'C00' | 'D00' | null;
  controller_type?: ControllerType;
  controller_config?: HeidenhainControllerConfig | null;
  capabilities?: MachineCapability[];
  model?: string;
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
  layout_config?: Record<string, unknown> | null;
}

export function getCapabilities(machine: {
  capabilities?: MachineCapability[];
  controller_type?: ControllerType;
}): MachineCapability[] {
  if (machine.capabilities?.length) {
    return machine.capabilities;
  }
  if (machine.controller_type === 'heidenhain') {
    return HEIDENHAIN_V1_CAPABILITIES;
  }
  return BROTHER_CAPABILITIES;
}

export function hasCapability(
  machine: { capabilities?: MachineCapability[]; controller_type?: ControllerType },
  cap: MachineCapability,
): boolean {
  return getCapabilities(machine).includes(cap);
}

export function isBrotherMachine(machine: { controller_type?: ControllerType }): boolean {
  return (machine.controller_type ?? 'brother') === 'brother';
}

export function isHeidenhainMachine(machine: { controller_type?: ControllerType }): boolean {
  return machine.controller_type === 'heidenhain';
}

export function defaultModelForController(controllerType: ControllerType): string {
  return controllerType === 'heidenhain' ? 'Heidenhain TNC' : 'Brother CNC';
}
