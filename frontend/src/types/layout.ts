/**
 * Layout configuration types for machine detail panes
 */

export type PaneId =
  | 'statusTimeline'
  | 'alarms'
  | 'currentProgram'
  | 'tools'
  | 'productionRuns'
  | 'statusHistory'
  | 'panel'
  | 'fileManager'
  | 'compressorOverview'
  | 'compressorAlarms'
  | 'compressorStatusTimeline'
  | 'compressorPsiTimeline'
  | 'compressorTempTimeline'
  | 'compressorStatusHistory'
  | 'compressorPanel';

export interface PaneLayout {
  i: string;        // Pane ID: 'statusTimeline', 'alarms', 'currentProgram', 'tools', 'productionRuns', 'statusHistory', etc.
  x: number;        // Grid column position
  y: number;        // Grid row position
  w: number;        // Width in grid units
  h: number;        // Height in grid units
  minW?: number;    // Minimum width
  minH?: number;    // Minimum height
  static?: boolean; // Whether pane is static (not draggable/resizable)
  visible?: boolean; // Whether pane is visible (defaults to true for backward compatibility)
}

export interface LayoutConfig {
  panes: PaneLayout[];
  gridCols?: number;
}

// Pane ID constants
export const PANE_IDS = {
  STATUS_TIMELINE: 'statusTimeline' as const,
  ALARMS: 'alarms' as const,
  CURRENT_PROGRAM: 'currentProgram' as const,
  TOOLS: 'tools' as const,
  PRODUCTION_RUNS: 'productionRuns' as const,
  STATUS_HISTORY: 'statusHistory' as const,
  PANEL: 'panel' as const,
  FILE_MANAGER: 'fileManager' as const,
  COMPRESSOR_OVERVIEW: 'compressorOverview' as const,
  COMPRESSOR_ALARMS: 'compressorAlarms' as const,
  COMPRESSOR_STATUS_TIMELINE: 'compressorStatusTimeline' as const,
  COMPRESSOR_PSI_TIMELINE: 'compressorPsiTimeline' as const,
  COMPRESSOR_TEMP_TIMELINE: 'compressorTempTimeline' as const,
  COMPRESSOR_STATUS_HISTORY: 'compressorStatusHistory' as const,
  COMPRESSOR_PANEL: 'compressorPanel' as const,
} as const;

/** Default grid for Kaeser / compressor detail (no CNC panes). */
export const DEFAULT_COMPRESSOR_LAYOUT: PaneLayout[] = [
  {
    i: PANE_IDS.COMPRESSOR_PANEL,
    x: 0,
    y: 0,
    w: 24,
    h: 8,
    minW: 8,
    minH: 5,
    visible: true,
  },
  {
    i: PANE_IDS.COMPRESSOR_OVERVIEW,
    x: 0,
    y: 8,
    w: 24,
    h: 5,
    minW: 6,
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.COMPRESSOR_ALARMS,
    x: 0,
    y: 13,
    w: 12,
    h: 7,
    minW: 3,
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.COMPRESSOR_STATUS_TIMELINE,
    x: 12,
    y: 13,
    w: 12,
    h: 7,
    minW: 6,
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.COMPRESSOR_PSI_TIMELINE,
    x: 0,
    y: 20,
    w: 12,
    h: 7,
    minW: 6,
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.COMPRESSOR_TEMP_TIMELINE,
    x: 12,
    y: 20,
    w: 12,
    h: 7,
    minW: 6,
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.COMPRESSOR_STATUS_HISTORY,
    x: 0,
    y: 27,
    w: 24,
    h: 6,
    minW: 6,
    minH: 3,
    visible: true,
  },
];

// Default layout configuration matching current hardcoded structure
// Grid uses 24 columns for finer positioning (doubled from 12 for 0.5-unit precision)
export const DEFAULT_LAYOUT: PaneLayout[] = [
  {
    i: PANE_IDS.STATUS_TIMELINE,
    x: 0,
    y: 0,
    w: 24,
    h: 5,
    minW: 6,  // 25% minimum width (6/24 = 25%)
    minH: 3,
    visible: true,
  },
  {
    i: PANE_IDS.ALARMS,
    x: 0,
    y: 5,
    w: 12,
    h: 7,
    minW: 3,  // 12.5% minimum width (3/24 = 12.5%) - allows single internal frame width
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.CURRENT_PROGRAM,
    x: 12,
    y: 5,
    w: 12,
    h: 7,
    minW: 6,  // 25% minimum width (6/24 = 25%)
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.TOOLS,
    x: 0,
    y: 12,
    w: 12,
    h: 7,
    minW: 6,  // 25% minimum width (6/24 = 25%)
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.PRODUCTION_RUNS,
    x: 12,
    y: 12,
    w: 12,
    h: 7,
    minW: 6,  // 25% minimum width (6/24 = 25%)
    minH: 4,
    visible: true,
  },
  {
    i: PANE_IDS.STATUS_HISTORY,
    x: 0,
    y: 19,
    w: 24,
    h: 6,
    minW: 6,
    minH: 3,
    visible: true,
  },
  {
    i: PANE_IDS.PANEL,
    x: 0,
    y: 25,
    w: 24,
    h: 8,
    minW: 3,  // 12.5% minimum width (3/24 = 12.5%) - allows single internal frame width
    minH: 6,  // Minimum vertical size to prevent clipping
    visible: true,
  },
  {
    i: PANE_IDS.FILE_MANAGER,
    x: 0,
    y: 27,
    w: 24,
    h: 8,
    minW: 6,  // 25% minimum width (6/24 = 25%)
    minH: 4,
    visible: true,
  },
];
