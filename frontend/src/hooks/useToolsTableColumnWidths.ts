import { useLayoutEffect, type RefObject } from 'react';

export const TOOL_NAME_MAX_LENGTH = 14;
export const TOOLS_TABLE_NAME_COLUMN_INDEX = 1;
export const TOOLS_TABLE_MEASURE_COLUMN_INDEX = 8;
export const TOOLS_TABLE_COLOR_COLUMN_INDEX = 9;

/** Surplus width split: most extra goes to NAME; COLOR gets a slice so labels are not truncated. */
export const TOOLS_TABLE_NAME_SURPLUS_RATIO = 0.85;

/** Column order matches `<colgroup>` in ToolsPane. */
export const TOOLS_TABLE_COLUMN_MIN_PX: readonly number[] = [
  26, // T# (T99)
  154, // NAME fallback (14 chars — remeasured in hook)
  42, // D
  46, // H (slightly wider than D for values like 96.065)
  24, // LIFE (1–3 digits)
  68, // POT (input + picker + clear)
  20, // GRP
  32, // TYPE (STD)
  20, // MEAS
  90, // COLOR (full labels e.g. PURPLE)
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

function colorColumnIndex(columnCount: number): number {
  return columnCount === TOOLS_TABLE_COLUMN_MIN_PX.length
    ? TOOLS_TABLE_COLOR_COLUMN_INDEX
    : TOOLS_TABLE_COLOR_COLUMN_INDEX - 1;
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
  return includeMeasure ? mins : mins.filter((_, index) => index !== TOOLS_TABLE_MEASURE_COLUMN_INDEX);
}

/**
 * Compact columns stay at minimum. Surplus width goes mostly to NAME (~85%) and partly
 * to COLOR (~15%) so tool names and color labels both have room.
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

  const extra = availableWidth - sumMin;
  const nameBonus = Math.floor(extra * TOOLS_TABLE_NAME_SURPLUS_RATIO);
  const colorBonus = extra - nameBonus;
  const colorIndex = colorColumnIndex(mins.length);

  return mins.map((min, index) => {
    if (index === flexIndex) return min + nameBonus;
    if (index === colorIndex) return min + colorBonus;
    return min;
  });
}

/**
 * Fixed-layout table: tight ATC/numeric columns; NAME + COLOR share surplus width.
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
