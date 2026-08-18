import { useLayoutEffect, type RefObject } from 'react';

export const TOOL_NAME_MAX_LENGTH = 14;
export const TOOLS_TABLE_NAME_COLUMN_INDEX = 1;

/** Column order matches `<colgroup>` in ToolsPane. Mins = max input/content width + cell padding. */
export const TOOLS_TABLE_COLUMN_MIN_PX: readonly number[] = [
  30, // T# (T99 + indicators)
  154, // NAME fallback (14 chars @ mono xs — remeasured from font in hook)
  48, // D (e.g. 999.999)
  48, // H
  34, // LIFE
  72, // POT (input + picker + clear)
  26, // GRP
  38, // TYPE (STD)
  22, // MEAS (toggle)
  76, // COLOR (swatch + label)
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

/** Measure NAME column min from the actual input font + cell padding (14-char tool names). */
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

  const cellStyle = getComputedStyle(
    table.querySelector('td.tools-col-name') ??
      table.querySelector('th.tools-col-name') ??
      table,
  );

  const font = `${inputStyle.fontWeight} ${inputStyle.fontSize} ${inputStyle.fontFamily}`;
  const textWidth = measureTextWidthPx(font, '0'.repeat(TOOL_NAME_MAX_LENGTH));

  return Math.ceil(textWidth + horizontalChrome(inputStyle) + horizontalChrome(cellStyle));
}

export function resolveToolsTableColumnMinimums(
  table: HTMLTableElement,
  includeMeasure: boolean,
): number[] {
  const mins = [...TOOLS_TABLE_COLUMN_MIN_PX];
  mins[TOOLS_TABLE_NAME_COLUMN_INDEX] = measureNameColumnMinPx(table);
  return includeMeasure ? mins : mins.filter((_, index) => index !== 8);
}

/**
 * Compact columns stay at their minimum; NAME absorbs all leftover table width.
 * When the pane is narrower than the sum of minimums, use minimums (horizontal scroll).
 */
export function distributeColumnWidths(
  availableWidth: number,
  mins: readonly number[],
  flexIndex: number = TOOLS_TABLE_NAME_COLUMN_INDEX,
): number[] {
  const sumMin = mins.reduce((sum, min) => sum + min, 0);
  if (availableWidth <= sumMin) {
    return [...mins];
  }

  const fixedTotal = sumMin - mins[flexIndex]!;
  const flexWidth = availableWidth - fixedTotal;

  return mins.map((min, index) => (index === flexIndex ? flexWidth : min));
}

/**
 * Fixed-layout table: compact columns at content minimum, NAME takes remaining width.
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

      const available = table.clientWidth;
      const widths = distributeColumnWidths(available, mins);

      cols.forEach((col, index) => {
        col.style.width = `${widths[index]!}px`;
      });
    };

    apply();

    const observer = new ResizeObserver(apply);
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, [wrapperRef, includeMeasure, enabled]);
}
