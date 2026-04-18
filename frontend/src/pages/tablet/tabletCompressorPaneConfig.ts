/** URL segments under `/tablet/compressor/:id/:paneSlug` — one pane per fullscreen swipe/nav slot.
 * Bottom nav order: overview left (first), then panel through history (matches CNC tablet). */
export const TABLET_COMPRESSOR_PANE_SLUGS = [
  'overview',
  'panel',
  'status',
  'alarms',
  'psi',
  'temp',
  'history',
] as const;

export type TabletCompressorPaneSlug = (typeof TABLET_COMPRESSOR_PANE_SLUGS)[number];

const SLUG_SET = new Set<string>(TABLET_COMPRESSOR_PANE_SLUGS);

export function isTabletCompressorPaneSlug(s: string): s is TabletCompressorPaneSlug {
  return SLUG_SET.has(s);
}

export const TABLET_COMPRESSOR_NAV_ITEMS: { slug: TabletCompressorPaneSlug; label: string }[] = [
  { slug: 'overview', label: 'OVERVIEW' },
  { slug: 'panel', label: 'PANEL' },
  { slug: 'status', label: 'STATUS' },
  { slug: 'alarms', label: 'ALARMS' },
  { slug: 'psi', label: 'PSI' },
  { slug: 'temp', label: 'TEMP' },
  { slug: 'history', label: 'HISTORY' },
];

/** Opening `/tablet/compressor/:id` lands here (aligned with CNC tablet default). */
export const TABLET_DEFAULT_COMPRESSOR_PANE: TabletCompressorPaneSlug = 'overview';
