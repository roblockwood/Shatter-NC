import type { Program } from '../../pages/FileBrowserTypes';
import { daysAgo, hoursAgo } from './demoTime';

const GCODE: Record<string, string> = {
  O1234: `(O1234 — BRACKET POCKET)
(Fusion post — demo)
G90 G54 G17 G21
(T1 — 3/8 EM)
T1 M6
S12000 M3
G0 X-1.5 Y-1.0
G43 H1 Z0.1
G1 Z-0.375 F12
G1 X1.5 F45
G1 Y1.0
G1 X-1.5
G1 Y-1.0
G0 Z1.0
(T3 — 1/4 DRILL)
T3 M6
S4500 M3
G0 X0 Y0
G1 Z-0.5 F8
G0 Z1.0
M5
M30
`,
  O2000: `(O2000 — FACE OP)
G90 G54 G17
T1 M6
S6000 M3
G0 X0 Y0 Z0.1
G1 Z-0.02 F20
G1 X4.0 F80
G1 Y3.0
G1 X0
G1 Y0
M5
M30
`,
  O3100: `(O3100 — SECOND OP)
G90 G55 G17
T2 M6
S10000 M3
G0 X0 Y0
G43 H2 Z0.05
G1 Z-0.25 F15
G2 X1.0 Y1.0 R0.5 F30
G0 Z1.0
M5
M30
`,
  O5500: `(O5500 — LONG RUN JOB)
G90 G54 G17
T1 M6
S8000 M3
G0 X0 Y0
G1 Z-0.125 F10
G1 X2.0 F60
M99 P1234
M30
`,
  O1234S1: `(O1234S1 — SUB POCKET)
G90 G54
T4 M6
S9000 M3
G0 X0.5 Y0.5
G1 Z-0.2 F12
G1 X1.0 F40
M5
M99
`,
  O8891: `(O8891 — LEGACY)
G90
M30
`,
};

export const DEMO_PROGRAMS_ROOT: Program[] = [
  { name: 'O1234.NC', size: 412, modified: hoursAgo(6), is_directory: false, path: '/O1234.NC' },
  { name: 'O2000.NC', size: 288, modified: daysAgo(2), is_directory: false, path: '/O2000.NC' },
  { name: 'O3100.NC', size: 356, modified: daysAgo(1), is_directory: false, path: '/O3100.NC' },
  { name: 'O5500.NC', size: 198, modified: daysAgo(5), is_directory: false, path: '/O5500.NC' },
  { name: 'SETUP.NC', size: 64, modified: daysAgo(14), is_directory: false, path: '/SETUP.NC' },
  { name: 'SUBPROGS', size: 0, modified: daysAgo(12), is_directory: true, path: '/SUBPROGS' },
  { name: 'ARCHIVE', size: 0, modified: daysAgo(30), is_directory: true, path: '/ARCHIVE' },
];

export const DEMO_PROGRAMS_SUBPROGS: Program[] = [
  { name: 'O1234S1.NC', size: 156, modified: daysAgo(12), is_directory: false, path: '/SUBPROGS/O1234S1.NC' },
  { name: 'O1234S2.NC', size: 140, modified: daysAgo(12), is_directory: false, path: '/SUBPROGS/O1234S2.NC' },
];

export const DEMO_PROGRAMS_ARCHIVE: Program[] = [
  { name: 'O8891.NC', size: 48, modified: daysAgo(45), is_directory: false, path: '/ARCHIVE/O8891.NC' },
  { name: 'O7720.NC', size: 920, modified: daysAgo(60), is_directory: false, path: '/ARCHIVE/O7720.NC' },
];

const ONUMBER_FROM_PATH = (filePath: string): string | null => {
  const m = filePath.toUpperCase().match(/O(\d+)/);
  return m ? m[1] : null;
};

export function programsForPath(path: string | null): Program[] {
  const normalized = path && path !== '/' ? path.replace(/\/$/, '') : '';
  if (!normalized || normalized === '') return DEMO_PROGRAMS_ROOT;
  if (normalized === '/SUBPROGS' || normalized === 'SUBPROGS') return DEMO_PROGRAMS_SUBPROGS;
  if (normalized === '/ARCHIVE' || normalized === 'ARCHIVE') return DEMO_PROGRAMS_ARCHIVE;
  return [];
}

export function viewContentForFile(filePath: string): { content: string; size: number; lines: number } {
  const upper = filePath.toUpperCase();
  let content = '(DEMO FILE)\nG90\nM30\n';
  for (const [key, src] of Object.entries(GCODE)) {
    if (upper.includes(key)) {
      content = src;
      break;
    }
  }
  const lines = content.split('\n').length;
  return { content, size: content.length, lines };
}

export function metadataForFile(filePath: string) {
  const on = ONUMBER_FROM_PATH(filePath);
  const toolMap: Record<string, number[]> = {
    '1234': [1, 3],
    '2000': [1],
    '3100': [2, 4],
    '5500': [1],
  };
  return {
    file_path: filePath,
    tools: on ? toolMap[on] ?? [1] : [],
    runtime_seconds: on === '1234' ? 420 : on === '2000' ? 180 : 540,
    has_errors: false,
    onumber: on ?? undefined,
  };
}

const TOOL_VALIDATION = {
  1: {
    tool_number: 1,
    required_diameter: 0.375,
    required_length: 2.5,
    available: true,
    diameter_match: true,
    length_sufficient: true,
    machine_tool_data: { tool_name: '3/8 EM', diameter: 0.375, length: 2.5 },
    warnings: [] as string[],
    validate_diameter: true,
    validate_length: true,
    requirements_complete: true,
    tolerance_source: 'machine_settings' as const,
    diameter_tolerance: 0.001,
    length_tolerance_plus: 0.02,
    length_tolerance_minus: 0.01,
  },
  3: {
    tool_number: 3,
    required_diameter: 0.25,
    required_length: 1.75,
    available: true,
    diameter_match: true,
    length_sufficient: true,
    machine_tool_data: { tool_name: '1/4 DRILL', diameter: 0.25, length: 1.75 },
    warnings: [] as string[],
    validate_diameter: true,
    validate_length: true,
    requirements_complete: true,
    tolerance_source: 'machine_settings' as const,
    diameter_tolerance: 0.001,
    length_tolerance_plus: 0.02,
    length_tolerance_minus: 0.01,
  },
};

const WCS_VALIDATION = {
  valid: true,
  work_offset: 54,
  expected: { x: -12.5, y: 3.0, z: -6.0 },
  actual: { x: -12.5, y: 3.0, z: -6.0 },
  difference: { x: 0, y: 0, z: 0 },
  tolerance: 0.001,
  within_tolerance: true,
  warnings: [] as string[],
};

function buildDeploymentDetail(onumber: string, filename: string, deployedAt: string, isCurrent: boolean) {
  const id = onumber === '1234' ? 1 : onumber === '2000' ? 2 : 3;
  return {
    deployment: {
      id,
      deployed_filename: filename,
      deployed_path: `/${filename}`,
      deployed_at: deployedAt,
      validation_passed: true,
      validation_results: {
        valid: true,
        tools: onumber === '1234' ? { 1: TOOL_VALIDATION[1], 3: TOOL_VALIDATION[3] } : { 1: TOOL_VALIDATION[1] },
        wcs_offset: WCS_VALIDATION,
        warnings: [],
        errors: [],
      },
    },
    program: {
      id: 10 + id,
      original_filename: filename,
      version_number: isCurrent ? 3 : 2,
      posted_date: hoursAgo(24 + id * 6),
      estimated_runtime_seconds: onumber === '1234' ? 420 : 180,
      program_metadata: {
        tools: [
          { tool_number: 1, diameter: 0.375, corner_radius: 0, description: '3/8 EM', length_total: 2.5 },
          ...(onumber === '1234'
            ? [{ tool_number: 3, diameter: 0.25, corner_radius: 0, description: '1/4 DRILL', length_total: 1.75 }]
            : []),
        ],
        wcs_offset: WCS_VALIDATION,
      },
      file_size_bytes: 412,
      line_count: 22,
    },
    history: [
      {
        id,
        deployed_at: deployedAt,
        validation_passed: true,
        replaced_at: isCurrent ? null : hoursAgo(2),
        is_current: isCurrent,
        program_version: isCurrent ? 3 : 2,
        original_filename: filename,
      },
      {
        id: id + 10,
        deployed_at: daysAgo(7),
        validation_passed: true,
        replaced_at: deployedAt,
        is_current: false,
        program_version: 1,
        original_filename: filename,
      },
    ],
  };
}

export function deploymentDetailForOnumber(onumberRaw: string) {
  const clean = decodeURIComponent(onumberRaw).toUpperCase().replace(/\.NC$/, '');
  const num = clean.replace(/^O/, '');
  const filename = `O${num.padStart(4, '0')}.NC`;
  if (num === '1234') return buildDeploymentDetail('1234', filename, hoursAgo(8), true);
  if (num === '2000') return buildDeploymentDetail('2000', filename, daysAgo(2), true);
  if (num === '3100') return buildDeploymentDetail('3100', filename, daysAgo(1), true);
  return buildDeploymentDetail('1234', 'O1234.NC', hoursAgo(8), true);
}

export function deploymentsForMachine(_machineId: number) {
  return [
    {
      id: 1,
      program_id: 11,
      machine_id: 1,
      deployed_filename: 'O1234.NC',
      deployed_path: '/O1234.NC',
      deployed_at: hoursAgo(8),
      deployed_by: 'demo',
      is_current: true,
      onumber: '1234',
    },
    {
      id: 2,
      program_id: 12,
      machine_id: 1,
      deployed_filename: 'O2000.NC',
      deployed_path: '/O2000.NC',
      deployed_at: daysAgo(2),
      deployed_by: 'demo',
      is_current: false,
      onumber: '2000',
    },
    {
      id: 3,
      program_id: 13,
      machine_id: 1,
      deployed_filename: 'O3100.NC',
      deployed_path: '/O3100.NC',
      deployed_at: daysAgo(1),
      deployed_by: 'demo',
      is_current: false,
      onumber: '3100',
    },
  ];
}

export function deploymentDetailById(deploymentId: number) {
  if (deploymentId === 2) return buildDeploymentDetail('2000', 'O2000.NC', daysAgo(2), false);
  if (deploymentId === 3) return buildDeploymentDetail('3100', 'O3100.NC', daysAgo(1), false);
  return buildDeploymentDetail('1234', 'O1234.NC', hoursAgo(8), true);
}

export function programRecordById(programId: number) {
  const map: Record<number, { id: number; filename: string; onumber: string; content_hash: string }> = {
    11: { id: 11, filename: 'O1234.NC', onumber: '1234', content_hash: 'demo-1234' },
    12: { id: 12, filename: 'O2000.NC', onumber: '2000', content_hash: 'demo-2000' },
    13: { id: 13, filename: 'O3100.NC', onumber: '3100', content_hash: 'demo-3100' },
  };
  return map[programId] ?? map[11];
}

export const DEMO_DEPLOYMENT_DETAIL = buildDeploymentDetail('1234', 'O1234.NC', hoursAgo(8), true);
export const DEMO_DEPLOYMENTS = deploymentsForMachine(1);
export const DEMO_PROGRAM_RECORD = programRecordById(11);

/** @deprecated use viewContentForFile */
export const SAMPLE_GCODE = GCODE.O1234;
