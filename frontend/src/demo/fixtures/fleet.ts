import type { MachineStatus, CompressorStatus } from '../../hooks/useWebSocket';
import type { PanelData } from '../../components/machine-detail/PanelPane';
import { DEMO_BOOT_MS, DEMO_NOW } from './demoTime';
import { panelDataForMachine } from './history';

const now = () => DEMO_NOW();

type DemoMachineStatus = MachineStatus & { panel?: PanelData | null };

export function createInitialMachines(): DemoMachineStatus[] {
  const ts = now();
  return [
    {
      machine_id: 1,
      machine_name: 'Mill-01',
      is_online: true,
      status: 'operating',
      program_name: 'O1234.NC',
      mem_mode: 2,
      mem_operation_status: 1,
      cycle_time: '00:04:32',
      power_on_hours: '1247:15',
      counters: [
        { counter_number: 1, count: 142 },
        { counter_number: 2, count: 8 },
        { counter_number: 3, count: 1420 },
      ],
      alarms: [],
      tools: [
        { tool_number: 1, tool_name: '3/8 EM', diameter: 0.375, length: 2.5, pot_number: 1 },
        { tool_number: 2, tool_name: '1/2 EM', diameter: 0.5, length: 3.0, pot_number: 2 },
        { tool_number: 3, tool_name: '1/4 DRILL', diameter: 0.25, length: 1.75, pot_number: 3 },
        { tool_number: 4, tool_name: 'CHAMFER', diameter: 0.375, length: 1.0, pot_number: 4 },
        { tool_number: 5, tool_name: 'SPOT DRILL', diameter: 0.5, length: 1.25, pot_number: 5 },
      ],
      tool_table: [
        { tool_number: 1, tool_name: '3/8 EM', diameter: 0.375, length: 2.5, pot_number: 1 },
        { tool_number: 2, tool_name: '1/2 EM', diameter: 0.5, length: 3.0, pot_number: 2 },
        { tool_number: 3, tool_name: '1/4 DRILL', diameter: 0.25, length: 1.75, pot_number: 3 },
        { tool_number: 10, tool_name: 'PROBE', diameter: 0.125, length: 2.0, pot_number: 10 },
      ],
      current_tool: 1,
      units: 'in',
      control_version: 'D00',
      poll_timestamp: ts,
      last_successful_poll_at: ts,
      ip_address: '192.168.1.101',
      location: 'Bay A — Cell 1',
      enabled: true,
      part_display_mode: 'parts',
      layout_config: null,
      panel: panelDataForMachine(1),
    },
    {
      machine_id: 2,
      machine_name: 'Mill-02',
      is_online: true,
      status: 'standby',
      program_name: 'O2000.NC',
      mem_mode: 2,
      mem_operation_status: 0,
      cycle_time: '00:00:00',
      power_on_hours: '892:42',
      counters: [
        { counter_number: 1, count: 56 },
        { counter_number: 2, count: 3 },
      ],
      alarms: [],
      tools: [
        { tool_number: 1, tool_name: 'FACE MILL', diameter: 2.0, length: 4.0, pot_number: 1 },
        { tool_number: 2, tool_name: '3/4 EM', diameter: 0.75, length: 3.5, pot_number: 2 },
      ],
      tool_table: [
        { tool_number: 1, tool_name: 'FACE MILL', diameter: 2.0, length: 4.0, pot_number: 1 },
      ],
      current_tool: 1,
      units: 'in',
      control_version: 'D00',
      poll_timestamp: ts,
      last_successful_poll_at: ts,
      ip_address: '192.168.1.102',
      location: 'Bay B — Cell 2',
      enabled: true,
      layout_config: null,
      panel: panelDataForMachine(2),
    },
    {
      machine_id: 3,
      machine_name: 'Mill-03',
      is_online: true,
      status: 'error',
      program_name: 'O5500.NC',
      mem_mode: 2,
      mem_operation_status: 2,
      cycle_time: '00:12:08',
      power_on_hours: '2103:07',
      counters: [{ counter_number: 1, count: 31 }],
      error: 'SL3001 Air pressure low',
      alarms: [
        {
          code: 'SL3001',
          message: 'Air pressure low',
          description: 'Shop air below minimum threshold (82 PSI)',
          severity: 'error',
          level_class: 'alarm',
          stop_level: '5',
          reset_level: '1',
          cause: 'Compressor unload / line leak',
          solution: 'Check shop air header and compressor load state',
        },
        {
          code: 'SL2104',
          message: 'Spindle lubrication pressure',
          description: 'Lube pressure below minimum during spindle run',
          severity: 'warning',
          level_class: 'warning',
          stop_level: '3',
          reset_level: '1',
        },
      ],
      tools: [
        { tool_number: 1, tool_name: '1/2 EM', diameter: 0.5, length: 3.0, pot_number: 1 },
      ],
      current_tool: 1,
      units: 'in',
      control_version: 'C00',
      poll_timestamp: ts,
      last_successful_poll_at: ts,
      ip_address: '192.168.1.103',
      location: 'Bay C — Cell 3',
      enabled: true,
      layout_config: null,
      panel: panelDataForMachine(3),
    },
  ];
}

export function createInitialCompressors(): CompressorStatus[] {
  const ts = now();
  return [
    {
      asset_kind: 'compressor',
      compressor_id: 1,
      compressor_name: 'Air-01',
      ip_address: '192.168.1.50',
      enabled: true,
      kaeser_credentials_configured: true,
      poll_interval_seconds: 30,
      is_online: true,
      status: 'running',
      metrics: {
        pressure_psi: 118,
        outlet_temp_f: 72,
        motor_amps: 24.5,
        run_hours: 8420,
      },
      poll_timestamp: ts,
      last_successful_poll_at: ts,
      response_time_ms: 42,
      layout_config: null,
    },
  ];
}

/** Mutable demo state for live-ish ticks. */
export const demoFleetState = {
  operatingCycleSeconds: 4 * 60 + 32,
  partCounter: 142,
  panelTick: 0,
};

export function tickPanelForMachine(
  machineId: number,
  panel?: PanelData | null,
): PanelData {
  demoFleetState.panelTick += 1;
  const t = demoFleetState.panelTick;
  const phase = Math.floor((Date.now() - DEMO_BOOT_MS) / 4000);
  const base = panel ?? panelDataForMachine(machineId);

  if (machineId === 1) {
    const feed = 90 + (phase % 21);
    const spindle = 95 + (phase % 11);
    const chipShower = phase % 30 < 3 ? 1 : 0;
    return {
      ...base,
      mode_and_functions: {
        ...base.mode_and_functions,
        mode: 2,
        screen: 8,
        coolant_pump: 1,
        machine_light: 1,
        table_light: 1,
        chip_shower: chipShower,
        block_skip: phase % 50 === 0 ? 1 : 0,
      },
      overrides: {
        ...base.overrides,
        rapid_traverse_override: 100,
        feedrate_override: feed,
        spindle_override: spindle,
        emergency_stop: 0,
        door_interlock: 1,
        master_on: 1,
        enable: 1,
      },
      doors: { outer_door: 0, inner_door: 0, side_door: 0 },
    };
  }

  if (machineId === 3) {
    const blink = t % 8 < 4 ? 1 : 2;
    return {
      ...base,
      mode_and_functions: {
        ...base.mode_and_functions,
        mode: 2,
        screen: blink,
        coolant_pump: 0,
        machine_light: 1,
      },
      overrides: {
        ...base.overrides,
        feedrate_override: 0,
        spindle_override: 0,
        rapid_traverse_override: 0,
        emergency_stop: 0,
        door_interlock: 0,
      },
      doors: {
        outer_door: 1,
        inner_door: phase % 16 < 2 ? 1 : 0,
        side_door: 0,
      },
    };
  }

  return {
    ...base,
    mode_and_functions: {
      ...base.mode_and_functions,
      mode: 2,
      screen: phase % 20 < 2 ? 4 : 0,
      coolant_pump: 0,
      machine_light: phase % 40 < 1 ? 1 : 0,
    },
    overrides: {
      ...base.overrides,
      feedrate_override: 100,
      spindle_override: 100,
      rapid_traverse_override: 100,
      master_on: 1,
    },
    doors: { outer_door: 0, inner_door: 0, side_door: 0 },
  };
}

export function tickOperatingMachine(machine: DemoMachineStatus): DemoMachineStatus {
  const ts = now();
  const withPanel: DemoMachineStatus = {
    ...machine,
    poll_timestamp: ts,
    last_successful_poll_at: ts,
    panel: tickPanelForMachine(machine.machine_id, machine.panel),
  };

  if (machine.machine_id === 3) {
    return withPanel;
  }

  if (machine.machine_id !== 1 || machine.status !== 'operating') {
    return withPanel;
  }

  demoFleetState.operatingCycleSeconds += 4;
  demoFleetState.partCounter += 1;

  const total = demoFleetState.operatingCycleSeconds;
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const cycle_time = [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');

  return {
    ...withPanel,
    cycle_time,
    counters: [
      { counter_number: 1, count: demoFleetState.partCounter },
      { counter_number: 2, count: 8 },
      { counter_number: 3, count: 1420 + demoFleetState.partCounter },
    ],
  };
}

export function machinesForApiRegistry(): Array<{ id: number; name: string; ip_address: string; path?: string }> {
  return createInitialMachines().map((m) => ({
    id: m.machine_id,
    name: m.machine_name,
    ip_address: m.ip_address ?? '192.168.1.101',
    path: '/',
  }));
}

export function machineConfigById(id: number): Record<string, unknown> | null {
  const m = createInitialMachines().find((x) => x.machine_id === id);
  if (!m) return null;
  return {
    id: m.machine_id,
    name: m.machine_name,
    ip_address: m.ip_address,
    ftp_username: 'demo',
    ftp_port: 21,
    http_port: 80,
    enabled: true,
    poll_interval_seconds: 5,
    tool_poll_interval_seconds: 30,
    location: m.location ?? 'Bay A',
    units: m.units,
    control_version: m.control_version,
    part_display_mode: m.part_display_mode ?? 'cycle',
  };
}
