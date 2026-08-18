import { useLayoutEffect, type RefObject } from 'react';

/** Column order matches `<colgroup>` in ToolsPane. Mins = max input/content width + cell padding. */
export const TOOLS_TABLE_COLUMN_MIN_PX: readonly number[] = [
  30, // T# (T99 + indicators)
  98, // NAME (14 chars)
  52, // D (e.g. 999.999)
  52, // H
  36, // LIFE
  72, // POT (input + picker + clear)
  28, // GRP
  40, // TYPE (STD)
  22, // MEAS (toggle)
  76, // COLOR (swatch + label)
];

const TOOLS_TABLE_COLUMN_MIN_PX_NO_MEASURE = TOOLS_TABLE_COLUMN_MIN_PX.filter(
  (_, index) => index !== 8,
);

/** Split extra width across columns using whole pixels so the sum matches exactly. */
export function distributeColumnWidths(
  availableWidth: number,
  mins: readonly number[],
): number[] {
  const sumMin = mins.reduce((sum, min) => sum + min, 0);
  if (availableWidth <= sumMin) {
    return [...mins];
  }

  const extra = availableWidth - sumMin;
  const baseExtra = Math.floor(extra / mins.length);
  let remainder = extra - baseExtra * mins.length;

  return mins.map((min) => {
    const bump = remainder > 0 ? 1 : 0;
    if (remainder > 0) remainder -= 1;
    return min + baseExtra + bump;
  });
}

/**
 * Fixed-layout table columns: each gets its content minimum, then leftover width
 * is divided evenly across every column (not just NAME).
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

    const mins = includeMeasure
      ? TOOLS_TABLE_COLUMN_MIN_PX
      : TOOLS_TABLE_COLUMN_MIN_PX_NO_MEASURE;

    if (cols.length !== mins.length) return;

    const apply = () => {
      // Use the table's inner width (between borders), not the scroll wrapper —
      // assigning col widths to wrapper.clientWidth ignores the table's own border box.
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
