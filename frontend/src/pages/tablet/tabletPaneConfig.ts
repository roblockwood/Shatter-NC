export const TABLET_PANE_SLUGS = [
  'status',
  'alarms',
  'program',
  'tools',
  'runs',
  'history',
  'panel',
  'files',
] as const;

export type TabletPaneSlug = (typeof TABLET_PANE_SLUGS)[number];

const SLUG_SET = new Set<string>(TABLET_PANE_SLUGS);

export function isTabletPaneSlug(s: string): s is TabletPaneSlug {
  return SLUG_SET.has(s);
}

/** Bottom nav: slug + short label */
export const TABLET_NAV_ITEMS: { slug: TabletPaneSlug; label: string }[] = [
  { slug: 'status', label: 'STATUS' },
  { slug: 'alarms', label: 'ALARMS' },
  { slug: 'program', label: 'PROGRAM' },
  { slug: 'tools', label: 'TOOLS' },
  { slug: 'runs', label: 'RUNS' },
  { slug: 'history', label: 'HISTORY' },
  { slug: 'panel', label: 'PANEL' },
  { slug: 'files', label: 'FILES' },
];

/** Default pane when opening /tablet/:id */
export const TABLET_DEFAULT_PANE: TabletPaneSlug = 'status';
