import type { MachineCapability, ControllerType } from '../../types/machine';
import { hasCapability } from '../../types/machine';

export const TABLET_PANE_SLUGS = [
  'overview',
  'panel',
  'status',
  'alarms',
  'program',
  'tools',
  'runs',
  'history',
  'files',
] as const;

export type TabletPaneSlug = (typeof TABLET_PANE_SLUGS)[number];

const SLUG_SET = new Set<string>(TABLET_PANE_SLUGS);

export function isTabletPaneSlug(s: string): s is TabletPaneSlug {
  return SLUG_SET.has(s);
}

/** Bottom nav: slug + short label */
export const TABLET_NAV_ITEMS: { slug: TabletPaneSlug; label: string }[] = [
  { slug: 'overview', label: 'OVERVIEW' },
  { slug: 'panel', label: 'PANEL' },
  { slug: 'status', label: 'STATUS' },
  { slug: 'alarms', label: 'ALARMS' },
  { slug: 'program', label: 'PROGRAM' },
  { slug: 'tools', label: 'TOOLS' },
  { slug: 'runs', label: 'RUNS' },
  { slug: 'history', label: 'HISTORY' },
  { slug: 'files', label: 'FILES' },
];

const TABLET_PANE_CAPABILITY: Partial<Record<TabletPaneSlug, MachineCapability>> = {
  panel: 'panel',
  status: 'statusTimeline',
  alarms: 'alarms',
  program: 'program',
  tools: 'tools',
  runs: 'productionRuns',
  history: 'statusTimeline',
  files: 'fileManager',
};

/** Filter bottom nav items by machine controller capabilities. Overview is always shown. */
export function getTabletNavItemsForMachine(machine: {
  capabilities?: MachineCapability[];
  controller_type?: ControllerType;
}): { slug: TabletPaneSlug; label: string }[] {
  return TABLET_NAV_ITEMS.filter(({ slug }) => {
    const cap = TABLET_PANE_CAPABILITY[slug];
    if (!cap) {
      return true;
    }
    return hasCapability(machine, cap);
  });
}

/** Default pane when opening /tablet/:id */
export const TABLET_DEFAULT_PANE: TabletPaneSlug = 'overview';
