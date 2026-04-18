/** URL segments under `/tablet/compressor/:id/:paneSlug` — one pane per fullscreen swipe/nav slot.
 * Order mirrors CNC tablet nav: status + alarms first, detail panes mid, history then panel last. */
export const TABLET_COMPRESSOR_PANE_SLUGS = [
  'status',
  'alarms',
  'overview',
  'psi',
  'temp',
  'history',
  'panel',
] as const;

export type TabletCompressorPaneSlug = (typeof TABLET_COMPRESSOR_PANE_SLUGS)[number];

const SLUG_SET = new Set<string>(TABLET_COMPRESSOR_PANE_SLUGS);

export function isTabletCompressorPaneSlug(s: string): s is TabletCompressorPaneSlug {
  return SLUG_SET.has(s);
}

export const TABLET_COMPRESSOR_NAV_ITEMS: { slug: TabletCompressorPaneSlug; label: string }[] = [
  { slug: 'status', label: 'STATUS' },
  { slug: 'alarms', label: 'ALARMS' },
  { slug: 'overview', label: 'OVERVIEW' },
  { slug: 'psi', label: 'PSI' },
  { slug: 'temp', label: 'TEMP' },
  { slug: 'history', label: 'HISTORY' },
  { slug: 'panel', label: 'PANEL' },
];

/** Opening `/tablet/compressor/:id` lands here (aligned with CNC default `status`). */
export const TABLET_DEFAULT_COMPRESSOR_PANE: TabletCompressorPaneSlug = 'status';
