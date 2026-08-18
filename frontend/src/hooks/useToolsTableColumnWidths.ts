import { useLayoutEffect, type RefObject } from 'react';

export const TOOL_NAME_MAX_LENGTH = 14;
export const TOOLS_TABLE_NAME_COLUMN_INDEX = 1;
export const TOOLS_TABLE_MEASURE_COLUMN_INDEX = 8;

/**
 * Column order matches `<colgroup>` in ToolsPane.
 * Each entry is content/control minimum; headers are measured separately and take the max.
 */
export const TOOLS_TABLE_CONTENT_MIN_PX: readonly number[] = [
  34, // T# — T99 (+ optional ►)
  170, // NAME fallback (14ch content-box + chrome — remeasured from DOM)
  44, // D — 999.999
  48, // H — 999.999
  28, // LIFE — up to 3 digits
  68, // POT — input + picker + clear
  28, // GRP — 2 digits
  40, // TYPE — STD + chevron
  22, // MEAS — toggle
  78, // COLOR — swatch + PURPLE (padding tightened in CSS)
];

/** Header labels used for min-width = max(content, header). Sort arrows omitted. */
export const TOOLS_TABLE_HEADER_LABELS: readonly string[] = [
  'T#',
  'NAME',
  'D',
  'H',
  'LIFE',
  'POT',
  'GRP',
  'TYPE',
  'M',
  'COLOR',
];

function horizontalChrome(style: CSSStyleDeclaration): number {
  return (
    (parseFloat(style.paddingLeft) || 0) +
    (parseFloat(style.paddingRight) || 0) +
    (parseFloat(style.borderLeftWidth) || 0) +
    (parseFloat(style.borderRightWidth) || 0)
  );
}

function measureTextWidthPx(font: string, text: string): number {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return text.length * 8;
  ctx.font = font;
  return ctx.measureText(text).width;
}

function headerFontFromTable(table: HTMLTableElement): string {
  const th =
    table.querySelector('th.tools-col-name') ??
    table.querySelector('thead th') ??
    table;
  const style = getComputedStyle(th);
  return `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
}

function cellHorizontalChrome(table: HTMLTableElement, selector: string): number {
  const cell =
    table.querySelector(`td.${selector}`) ??
    table.querySelector(`th.${selector}`) ??
    table.querySelector('td') ??
    table;
  return horizontalChrome(getComputedStyle(cell));
}

/** Measure NAME column from a real 14ch content-box input in the table font. */
export function measureNameColumnMinPx(table: HTMLTableElement): number {
  const probe = document.createElement('input');
  probe.type = 'text';
  probe.className = 'tools-edit-input tools-edit-input-name';
  probe.value = 'W'.repeat(TOOL_NAME_MAX_LENGTH);
  probe.setAttribute('size', String(TOOL_NAME_MAX_LENGTH));
  probe.setAttribute('maxlength', String(TOOL_NAME_MAX_LENGTH));
  // Measure with content-box 14ch so padding/border are additive (not subtracted).
  probe.style.position = 'absolute';
  probe.style.left = '-9999px';
  probe.style.top = '0';
  probe.style.visibility = 'hidden';
  probe.style.pointerEvents = 'none';
  probe.style.boxSizing = 'content-box';
  probe.style.width = '14ch';
  probe.style.minWidth = '14ch';
  probe.style.maxWidth = '14ch';
  table.appendChild(probe);

  const textNeed = Math.ceil(probe.scrollWidth);
  const boxNeed = Math.ceil(probe.offsetWidth);
  table.removeChild(probe);

  const inputWidth = Math.max(textNeed, boxNeed) + 2; // caret / anti-alias cushion
  return inputWidth + cellHorizontalChrome(table, 'tools-col-name');
}

/**
 * Resolve per-column minimums: max(content min, measured header label width).
 * NAME is always the measured 14-character width (hard cap — not a flex sink).
 */
export function resolveToolsTableColumnMinimums(
  table: HTMLTableElement,
  includeMeasure: boolean,
): number[] {
  const headerFont = headerFontFromTable(table);
  const headerPad = cellHorizontalChrome(table, 'tools-col-number');
  // Small cushion for sort caret when active (▲/▼)
  const sortCaret = Math.ceil(measureTextWidthPx(headerFont, '▲')) + 2;

  const mins = TOOLS_TABLE_CONTENT_MIN_PX.map((contentMin, index) => {
    const label = TOOLS_TABLE_HEADER_LABELS[index]!;
    const headerMin = Math.ceil(measureTextWidthPx(headerFont, label) + headerPad + sortCaret);
    return Math.max(contentMin, headerMin);
  });

  mins[TOOLS_TABLE_NAME_COLUMN_INDEX] = measureNameColumnMinPx(table);

  return includeMeasure
    ? mins
    : mins.filter((_, index) => index !== TOOLS_TABLE_MEASURE_COLUMN_INDEX);
}

/** Subtract from wrapper width so table L/R borders + rounding don't force horizontal scroll. */
export const TOOLS_TABLE_WIDTH_GUTTER_PX = 4;

/**
 * Columns keep content/header minimums. Leftover pane width is split evenly
 * across every column (integer pixels) so the table fills the panel.
 */
export function distributeColumnWidths(
  availableWidth: number,
  mins: readonly number[],
): { widths: number[]; tableWidth: number } {
  const sumMin = mins.reduce((sum, min) => sum + min, 0);

  if (availableWidth <= sumMin) {
    return { widths: [...mins], tableWidth: sumMin };
  }

  const extra = availableWidth - sumMin;
  const baseExtra = Math.floor(extra / mins.length);
  let remainder = extra - baseExtra * mins.length;

  const widths = mins.map((min) => {
    const bump = remainder > 0 ? 1 : 0;
    if (remainder > 0) remainder -= 1;
    return min + baseExtra + bump;
  });

  return { widths, tableWidth: availableWidth };
}

/**
 * Fixed-layout table: columns sized to content/header mins, then grow evenly
 * to fill the pane width. NAME floor remains 14 characters.
 */
export function useToolsTableColumnWidths(
  wrapperRef: RefObject<HTMLDivElement | null>,
  includeMeasure: boolean,
  enabled: boolean,
): void {
  useLayoutEffect(() => {
    if (!enabled) return;

    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    const table = wrapper.querySelector<HTMLTableElement>('table.tools-table');
    const cols = wrapper.querySelectorAll<HTMLTableColElement>('table.tools-table colgroup col');
    if (!table || !cols.length) return;

    const apply = () => {
      const mins = resolveToolsTableColumnMinimums(table, includeMeasure);
      if (cols.length !== mins.length) return;

      // Wrapper clientWidth is the content box; table border sits inside/outside
      // that and was causing ~2–4px horizontal overflow.
      const available = Math.max(
        0,
        Math.floor(wrapper.clientWidth) - TOOLS_TABLE_WIDTH_GUTTER_PX,
      );
      const { widths, tableWidth } = distributeColumnWidths(available, mins);

      cols.forEach((col, index) => {
        col.style.width = `${widths[index]!}px`;
      });
      table.style.width = `${tableWidth}px`;
      table.style.minWidth = `${tableWidth}px`;
    };

    apply();
    // Remeasure after webfonts load — first paint may use a narrower fallback.
    const fontsReady =
      typeof document !== 'undefined' && document.fonts?.ready
        ? document.fonts.ready.then(apply).catch(() => undefined)
        : Promise.resolve();

    const observer = new ResizeObserver(apply);
    observer.observe(wrapper);
    return () => {
      observer.disconnect();
      table.style.width = '';
      table.style.minWidth = '';
      void fontsReady;
    };
  }, [wrapperRef, includeMeasure, enabled]);
}
