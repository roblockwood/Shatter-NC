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
  154, // NAME fallback (14 chars — remeasured from font)
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

/** Measure NAME column width for exactly 14 mono characters + input/cell chrome. */
export function measureNameColumnMinPx(table: HTMLTableElement): number {
  const existingInput = table.querySelector<HTMLElement>('.tools-edit-input-name');

  let inputStyle: CSSStyleDeclaration;
  if (existingInput) {
    inputStyle = getComputedStyle(existingInput);
  } else {
    const probe = document.createElement('input');
    probe.type = 'text';
    probe.className = 'tools-edit-input tools-edit-input-name';
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.pointerEvents = 'none';
    table.appendChild(probe);
    inputStyle = getComputedStyle(probe);
    table.removeChild(probe);
  }

  const font = `${inputStyle.fontWeight} ${inputStyle.fontSize} ${inputStyle.fontFamily}`;
  const textWidth = measureTextWidthPx(font, '0'.repeat(TOOL_NAME_MAX_LENGTH));

  return Math.ceil(
    textWidth + horizontalChrome(inputStyle) + cellHorizontalChrome(table, 'tools-col-name'),
  );
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

/**
 * Columns stay at their content/header minimums. Surplus is not redistributed —
 * NAME is fixed at 14 chars, so leftover pane width stays empty beside the table.
 */
export function distributeColumnWidths(
  _availableWidth: number,
  mins: readonly number[],
): { widths: number[]; tableWidth: number } {
  const sumMin = mins.reduce((sum, min) => sum + min, 0);
  // Always use mins; table width equals sum (never stretch columns to fill the pane).
  return { widths: [...mins], tableWidth: sumMin };
}

/**
 * Fixed-layout table: NAME sized for 14 chars; other cols sized to fit content AND headers.
 * Table width equals the sum of column mins (empty space on the right if the pane is wider).
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

      const { widths, tableWidth } = distributeColumnWidths(table.clientWidth, mins);

      cols.forEach((col, index) => {
        col.style.width = `${widths[index]!}px`;
      });
      // Pin table to column sum so table-layout:fixed does not redistribute leftover width.
      table.style.width = `${tableWidth}px`;
      table.style.minWidth = `${tableWidth}px`;
    };

    apply();

    const observer = new ResizeObserver(apply);
    observer.observe(wrapper);
    return () => {
      observer.disconnect();
      table.style.width = '';
      table.style.minWidth = '';
    };
  }, [wrapperRef, includeMeasure, enabled]);
}
