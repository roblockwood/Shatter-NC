import { DEFAULT_LAYOUT } from '../../types/layout';
import type { PanelData } from '../../components/machine-detail/PanelPane';
import { daysAgo, durationSeconds, hoursAgo } from './demoTime';

export const DEMO_FORBIDDEN = { detail: 'Demo mode — changes are disabled.' };

export function panelDataForMachine(machineId: number): PanelData {
  if (machineId === 1) {
    return {
      control_version: 'D00',
      doors: { outer_door: 0, inner_door: 0, side_door: 0 },
      mode_and_functions: {
        mode: 2,
        screen: 8,
        block_skip: 0,
        opt_stop: 0,
        single_block: 0,
        dry_run: 0,
        machine_lock: 0,
        coolant_pump: 1,
        chip_shower: 0,
        machine_light: 1,
        table_light: 1,
        pallet_select_key: 0,
      },
      overrides: {
        rapid_traverse_override: 100,
        feedrate_override: 100,
        spindle_override: 100,
        emergency_stop: 0,
        door_interlock: 1,
        master_on: 1,
        enable: 1,
      },
    };
  }
  if (machineId === 3) {
    return {
      control_version: 'C00',
      doors: { outer_door: 1, inner_door: 0, side_door: 0 },
      mode_and_functions: {
        mode: 2,
        screen: 1,
        block_skip: 0,
        opt_stop: 0,
        single_block: 0,
        dry_run: 0,
        machine_lock: 0,
        coolant_pump: 0,
        chip_shower: 0,
        machine_light: 1,
        table_light: 0,
      },
      overrides: {
        rapid_traverse_override: 0,
        feedrate_override: 0,
        spindle_override: 0,
        emergency_stop: 0,
        door_interlock: 0,
        master_on: 1,
      },
    };
  }
  return {
    control_version: 'D00',
    doors: { outer_door: 0, inner_door: 0, side_door: 0 },
    mode_and_functions: {
      mode: 2,
      screen: 0,
      block_skip: 0,
      opt_stop: 0,
      single_block: 0,
      dry_run: 0,
      machine_lock: 0,
      coolant_pump: 0,
      chip_shower: 0,
      machine_light: 0,
      table_light: 0,
    },
    overrides: {
      feedrate_override: 100,
      spindle_override: 100,
      rapid_traverse_override: 100,
      master_on: 1,
      door_interlock: 1,
    },
  };
}

export function machineLayoutResponse() {
  return { layout_config: { panes: DEFAULT_LAYOUT, gridCols: 24 } };
}

export function compressorLayoutResponse() {
  return { layout_config: null };
}

function buildPollingHistory(hours: number, successRate = 0.99) {
  const points = [];
  const step = (hours * 3600 * 1000) / 48;
  for (let i = 48; i >= 0; i--) {
    points.push({
      time: new Date(Date.now() - i * step).toISOString(),
      success: Math.random() < successRate,
      response_time_ms: 35 + Math.floor(Math.random() * 40),
    });
  }
  return points;
}

export function runningSummary() {
  return {
    time_range: '24h',
    total_machines: 3,
    machines: [
      {
        machine_id: 1,
        machine_name: 'Mill-01',
        current_status: 'operating',
        total_run_time_seconds: Math.round(6.5 * 3600),
        total_run_time_formatted: '6h 30m',
        run_percentage: 68,
        active_runs_count: 1,
        last_run_start: hoursAgo(4.5),
        current_program: 'O1234.NC',
        status_history: [
          { time: hoursAgo(22), status: 'off' },
          { time: hoursAgo(18), status: 'standby' },
          { time: hoursAgo(16), status: 'operating' },
          { time: hoursAgo(12), status: 'stopped' },
          { time: hoursAgo(11.5), status: 'operating' },
        ],
      },
      {
        machine_id: 2,
        machine_name: 'Mill-02',
        current_status: 'standby',
        total_run_time_seconds: Math.round(2.25 * 3600),
        total_run_time_formatted: '2h 15m',
        run_percentage: 22,
        active_runs_count: 0,
        current_program: 'O2000.NC',
        status_history: [
          { time: hoursAgo(20), status: 'operating' },
          { time: hoursAgo(8), status: 'standby' },
        ],
      },
      {
        machine_id: 3,
        machine_name: 'Mill-03',
        current_status: 'error',
        total_run_time_seconds: Math.round(1.5 * 3600),
        total_run_time_formatted: '1h 30m',
        run_percentage: 12,
        active_runs_count: 0,
        current_program: 'O5500.NC',
        status_history: [
          { time: hoursAgo(14), status: 'operating' },
          { time: hoursAgo(2), status: 'error' },
        ],
      },
    ],
  };
}

export function machinesSummary() {
  return {
    total_machines: 4,
    online_count: 4,
    offline_count: 0,
    machines: [
      {
        machine_id: 1,
        machine_name: 'Mill-01',
        asset_kind: 'cnc',
        is_online: true,
        uptime_8h_percent: 82,
        current_status: 'operating',
        connection_health: 'healthy',
        online_duration_formatted: '7h 45m',
        offline_duration_formatted: '15m',
        status_changed_at: hoursAgo(4.5),
        polling_history_8h: buildPollingHistory(8, 0.995),
        polling_summary: {
          total_polls: 5760,
          successful_polls: 5742,
          failed_polls: 18,
          success_rate: 99.7,
          avg_response_time_ms: 42,
          current_streak: 240,
        },
      },
      {
        machine_id: 2,
        machine_name: 'Mill-02',
        asset_kind: 'cnc',
        is_online: true,
        uptime_8h_percent: 71,
        current_status: 'standby',
        connection_health: 'healthy',
        online_duration_formatted: '8h 0m',
        offline_duration_formatted: '0m',
        polling_history_8h: buildPollingHistory(8, 0.99),
        polling_summary: {
          total_polls: 5760,
          successful_polls: 5710,
          failed_polls: 50,
          success_rate: 99.1,
          avg_response_time_ms: 48,
          current_streak: 88,
        },
      },
      {
        machine_id: 3,
        machine_name: 'Mill-03',
        asset_kind: 'cnc',
        is_online: true,
        uptime_8h_percent: 65,
        current_status: 'error',
        connection_health: 'degraded',
        online_duration_formatted: '7h 10m',
        offline_duration_formatted: '50m',
        polling_history_8h: buildPollingHistory(8, 0.92),
        polling_summary: {
          total_polls: 5760,
          successful_polls: 5300,
          failed_polls: 460,
          success_rate: 92.0,
          avg_response_time_ms: 120,
          current_streak: 12,
        },
      },
      {
        machine_id: 1,
        machine_name: 'Kaeser ASD',
        asset_kind: 'compressor',
        is_online: true,
        uptime_8h_percent: 98,
        current_status: 'load',
        connection_health: 'healthy',
        online_duration_formatted: '8h 0m',
        offline_duration_formatted: '0m',
        polling_history_8h: buildPollingHistory(8, 0.995),
        polling_summary: {
          total_polls: 960,
          successful_polls: 950,
          failed_polls: 10,
          success_rate: 99.0,
          avg_response_time_ms: 85,
          current_streak: 40,
        },
      },
    ],
  };
}

type Prd3Seed = {
  start: string;
  end: string | null;
  status: string;
  program: string | null;
  label: string;
  error?: string;
};

function programPoolForMachine(machineId: number): string[] {
  if (machineId === 1) return ['1234', '2000', '3100', '4100', '1234'];
  if (machineId === 2) return ['2000', '3100', '3200', '2000'];
  return ['5500', '5510', '5500'];
}

function statusPatternForMachine(machineId: number): string[] {
  if (machineId === 3) {
    return ['standby', 'operating', 'operating', 'stopped', 'operating', 'stopped', 'error'];
  }
  if (machineId === 2) {
    return ['off', 'standby', 'operating', 'stopped', 'operating', 'standby'];
  }
  return ['off', 'standby', 'operating', 'stopped', 'operating', 'standby', 'operating'];
}

function generatePrd3Seeds(machineId: number, intervalCount = 42): Prd3Seed[] {
  const programPool = programPoolForMachine(machineId);
  const pattern = statusPatternForMachine(machineId);
  const rows: Prd3Seed[] = [];
  let hoursBack = 7 * 24;

  for (let i = 0; i < intervalCount; i++) {
    const isLast = i === intervalCount - 1;
    const durHours = 0.12 + (i % 9) * 0.38 + (machineId === 1 ? 0.15 : 0);
    const endHoursBack = hoursBack;
    hoursBack -= durHours;
    const startHoursBack = hoursBack;

    let status = pattern[i % pattern.length];
    if (isLast) {
      status = machineId === 3 ? 'error' : machineId === 1 ? 'operating' : 'standby';
    }

    const programNo = programPool[Math.floor(i / 2) % programPool.length];
    const program =
      status === 'off' || status === 'standby' ? null : `O${programNo}`;

    const label =
      status === 'operating'
        ? `Running ${program ?? 'program'}`
        : status === 'stopped'
          ? i % 3 === 0
            ? 'Tool change pause'
            : 'Feed hold'
          : status === 'error'
            ? 'Alarm SL3001'
            : status === 'standby'
              ? 'Idle — cycle start pending'
              : 'Powered off';

    rows.push({
      start: hoursAgo(startHoursBack),
      end: isLast ? null : hoursAgo(endHoursBack),
      status,
      program,
      label,
      error: status === 'error' ? 'SL3001' : undefined,
    });
  }

  return rows;
}

function mapPrd3Row(r: Prd3Seed) {
  return {
    status: r.status,
    status_code:
      r.status === 'operating' ? 1 : r.status === 'error' ? 3 : r.status === 'stopped' ? 2 : 0,
    program_no: r.program,
    error_no: r.error ?? null,
    start_time: r.start,
    end_time: r.end,
    label: r.label,
    detail: r.error ? 'Shop air below minimum threshold' : null,
    duration_seconds: durationSeconds(r.start, r.end),
  };
}

const prd3Cache = new Map<number, ReturnType<typeof mapPrd3Row>[]>();

function allPrd3Intervals(machineId: number) {
  let cached = prd3Cache.get(machineId);
  if (!cached) {
    cached = generatePrd3Seeds(machineId)
      .map(mapPrd3Row)
      .sort(
        (a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime(),
      );
    prd3Cache.set(machineId, cached);
  }
  return cached;
}

export function prd3StatusHistory(machineId: number, limit = 500, offset = 0) {
  const all = allPrd3Intervals(machineId);
  return all.slice(offset, offset + limit);
}

export function statusHistoryEvents(machineId: number) {
  const seeds = generatePrd3Seeds(machineId);
  const events: Array<{
    time: string;
    machine_id: number;
    status: string;
    previous_status?: string;
    program_name?: string;
    o_number?: string;
    error?: string;
  }> = [];

  let prev: string | null = null;
  for (const s of seeds) {
    if (s.status !== prev) {
      events.push({
        time: s.start,
        machine_id: machineId,
        status: s.status,
        previous_status: prev ?? undefined,
        program_name: s.program ? `${s.program}.NC` : undefined,
        o_number: s.program?.replace(/^O(\d+)$/i, '$1'),
        error: s.error ? `${s.error} Air pressure low` : undefined,
      });
      prev = s.status;
    }
  }

  // Heartbeat-style repeats for long operating blocks
  if (machineId === 1) {
    events.push({
      time: hoursAgo(4.5),
      machine_id: machineId,
      status: 'operating',
      previous_status: 'operating',
      program_name: 'O1234.NC',
      o_number: '1234',
    });
  }

  return events
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
    .map((e, idx) => ({ ...e, id: idx + 1 }));
}

export function productionRunsTimeline(machineId: number) {
  if (machineId === 1) {
    return [
      {
        program_no: '1234',
        run_start: hoursAgo(5.5),
        run_end: null as string | null,
        cycles: 142,
        part_count: 142,
        segments: [
          {
            status: 'operating',
            status_code: 1,
            start_time: hoursAgo(5.5),
            end_time: hoursAgo(4),
            error_no: null,
          },
          {
            status: 'stopped',
            status_code: 2,
            start_time: hoursAgo(4),
            end_time: hoursAgo(3.8),
            error_no: null,
          },
          {
            status: 'operating',
            status_code: 1,
            start_time: hoursAgo(3.8),
            end_time: null,
            error_no: null,
          },
        ],
      },
      {
        program_no: '2000',
        run_start: hoursAgo(20),
        run_end: hoursAgo(12),
        cycles: 24,
        part_count: 24,
        segments: [
          { status: 'operating', start_time: hoursAgo(20), end_time: hoursAgo(18), error_no: null },
          { status: 'stopped', start_time: hoursAgo(18), end_time: hoursAgo(17.5), error_no: null },
          { status: 'operating', start_time: hoursAgo(17.5), end_time: hoursAgo(12), error_no: null },
        ],
      },
      {
        program_no: '3100',
        run_start: hoursAgo(48),
        run_end: hoursAgo(44),
        cycles: 8,
        part_count: 8,
        segments: [
          { status: 'operating', start_time: hoursAgo(48), end_time: hoursAgo(44), error_no: null },
        ],
      },
      {
        program_no: '4100',
        run_start: daysAgo(2),
        run_end: daysAgo(2),
        cycles: 12,
        part_count: 12,
        segments: [
          { status: 'operating', start_time: daysAgo(2), end_time: daysAgo(2), error_no: null },
        ],
      },
      {
        program_no: '1234',
        run_start: daysAgo(4),
        run_end: daysAgo(3.8),
        cycles: 64,
        part_count: 64,
        segments: [
          { status: 'operating', start_time: daysAgo(4), end_time: daysAgo(3.8), error_no: null },
        ],
      },
    ];
  }
  if (machineId === 2) {
    return [
      {
        program_no: '3100',
        run_start: hoursAgo(20),
        run_end: hoursAgo(8),
        cycles: 16,
        part_count: 16,
        segments: [
          { status: 'operating', start_time: hoursAgo(20), end_time: hoursAgo(8), error_no: null },
        ],
      },
      {
        program_no: '3200',
        run_start: hoursAgo(52),
        run_end: hoursAgo(48),
        cycles: 6,
        part_count: 6,
        segments: [
          { status: 'operating', start_time: hoursAgo(52), end_time: hoursAgo(48), error_no: null },
        ],
      },
      {
        program_no: '2000',
        run_start: daysAgo(3),
        run_end: daysAgo(2.5),
        cycles: 22,
        part_count: 22,
        segments: [
          { status: 'operating', start_time: daysAgo(3), end_time: daysAgo(2.5), error_no: null },
        ],
      },
    ];
  }
  return [
    {
      program_no: '5500',
      run_start: hoursAgo(16),
      run_end: hoursAgo(2),
      cycles: 31,
      part_count: 31,
      segments: [
        { status: 'operating', start_time: hoursAgo(16), end_time: hoursAgo(6), error_no: null },
        { status: 'stopped', start_time: hoursAgo(6), end_time: hoursAgo(2), error_no: null },
        { status: 'error', start_time: hoursAgo(2), end_time: hoursAgo(2), error_no: 'SL3001' },
      ],
    },
    {
      program_no: '5510',
      run_start: daysAgo(5),
      run_end: daysAgo(4.5),
      cycles: 18,
      part_count: 18,
      segments: [
        { status: 'operating', start_time: daysAgo(5), end_time: daysAgo(4.5), error_no: null },
      ],
    },
  ];
}

export function machineAlarms(machineId: number) {
  if (machineId === 3) {
    return [
      {
        time: hoursAgo(2),
        machine_id: 3,
        alarm_code: 'SL3001',
        alarm_message: 'Air pressure low',
        alarm_type: 'machine',
        severity: 'error',
        cleared_at: null,
        duration_seconds: durationSeconds(hoursAgo(2), null),
      },
      {
        time: hoursAgo(2.05),
        machine_id: 3,
        alarm_code: 'SL2104',
        alarm_message: 'Spindle lubrication pressure',
        alarm_type: 'machine',
        severity: 'warning',
        cleared_at: null,
        duration_seconds: durationSeconds(hoursAgo(2.05), null),
      },
      {
        time: daysAgo(1),
        machine_id: 3,
        alarm_code: 'SL1205',
        alarm_message: 'Tool life warning T4',
        alarm_type: 'machine',
        severity: 'warning',
        cleared_at: daysAgo(1),
        duration_seconds: 900,
      },
      {
        time: daysAgo(3),
        machine_id: 3,
        alarm_code: 'SL0801',
        alarm_message: 'ATC door open timeout',
        alarm_type: 'machine',
        severity: 'error',
        cleared_at: daysAgo(3),
        duration_seconds: 45,
      },
      {
        time: daysAgo(5),
        machine_id: 3,
        alarm_code: 'SL0902',
        alarm_message: 'Coolant level low',
        alarm_type: 'machine',
        severity: 'warning',
        cleared_at: daysAgo(5),
        duration_seconds: 3600,
      },
    ];
  }
  if (machineId === 1) {
    return [
      {
        time: daysAgo(1),
        machine_id: 1,
        alarm_code: 'SL0902',
        alarm_message: 'Coolant level low',
        alarm_type: 'machine',
        severity: 'warning',
        cleared_at: daysAgo(1),
        duration_seconds: 1200,
      },
      {
        time: daysAgo(2),
        machine_id: 1,
        alarm_code: 'SL1205',
        alarm_message: 'Tool life warning T3',
        alarm_type: 'machine',
        severity: 'warning',
        cleared_at: daysAgo(2),
        duration_seconds: 600,
      },
      {
        time: daysAgo(4),
        machine_id: 1,
        alarm_code: 'SL0401',
        alarm_message: 'Workpiece counter mismatch',
        alarm_type: 'machine',
        severity: 'error',
        cleared_at: daysAgo(4),
        duration_seconds: 180,
      },
    ];
  }
  if (machineId === 2) {
    return [
      {
        time: daysAgo(6),
        machine_id: 2,
        alarm_code: 'SL1205',
        alarm_message: 'Tool life warning T1',
        alarm_type: 'machine',
        severity: 'warning',
        cleared_at: daysAgo(6),
        duration_seconds: 300,
      },
    ];
  }
  return [];
}

export function cycleHistory(machineId: number) {
  if (machineId !== 1) return [];
  const cycles = [];
  for (let i = 0; i < 48; i++) {
    const startHours = 5.5 - i * 0.045;
    const endHours = startHours - 0.04;
    cycles.push({
      start_time: hoursAgo(startHours),
      end_time: hoursAgo(endHours),
      part_count: 1,
    });
  }
  return cycles;
}

export function compressorStatusHistory() {
  return [
    { time: hoursAgo(24), compressor_id: 1, status: 'off', previous_status: null },
    { time: hoursAgo(22), compressor_id: 1, status: 'loaded', previous_status: 'off' },
    { time: hoursAgo(20), compressor_id: 1, status: 'running', previous_status: 'loaded' },
    { time: hoursAgo(14), compressor_id: 1, status: 'running', previous_status: 'running' },
    { time: hoursAgo(8), compressor_id: 1, status: 'loaded', previous_status: 'running' },
    { time: hoursAgo(6), compressor_id: 1, status: 'running', previous_status: 'loaded' },
    { time: hoursAgo(2), compressor_id: 1, status: 'running', previous_status: 'running' },
  ];
}
