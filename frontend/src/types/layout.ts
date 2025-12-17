/**
 * Layout configuration types for machine detail panes
 */

export type PaneId = 'statusTimeline' | 'alarms' | 'currentProgram' | 'tools' | 'cycleHistory';

export interface PaneLayout {
  i: string;        // Pane ID: 'statusTimeline', 'alarms', 'currentProgram', 'tools', 'cycleHistory'
  x: number;        // Grid column position
  y: number;        // Grid row position
  w: number;        // Width in grid units
  h: number;        // Height in grid units
  minW?: number;    // Minimum width
  minH?: number;    // Minimum height
  static?: boolean; // Whether pane is static (not draggable/resizable)
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
  CYCLE_HISTORY: 'cycleHistory' as const,
} as const;

// Default layout configuration matching current hardcoded structure
export const DEFAULT_LAYOUT: PaneLayout[] = [
  {
    i: PANE_IDS.STATUS_TIMELINE,
    x: 0,
    y: 0,
    w: 12,
    h: 5,
    minW: 6,
    minH: 3,
  },
  {
    i: PANE_IDS.ALARMS,
    x: 0,
    y: 5,
    w: 6,
    h: 7,
    minW: 4,
    minH: 4,
  },
  {
    i: PANE_IDS.CURRENT_PROGRAM,
    x: 6,
    y: 5,
    w: 6,
    h: 7,
    minW: 4,
    minH: 4,
  },
  {
    i: PANE_IDS.TOOLS,
    x: 0,
    y: 12,
    w: 6,
    h: 7,
    minW: 4,
    minH: 4,
  },
  {
    i: PANE_IDS.CYCLE_HISTORY,
    x: 6,
    y: 12,
    w: 6,
    h: 7,
    minW: 4,
    minH: 4,
  },
];
