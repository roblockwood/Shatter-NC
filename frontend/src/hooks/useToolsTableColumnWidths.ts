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

    const cols = wrapper.querySelectorAll<HTMLTableColElement>('table.tools-table colgroup col');
    if (!cols.length) return;

    const mins = includeMeasure
      ? TOOLS_TABLE_COLUMN_MIN_PX
      : TOOLS_TABLE_COLUMN_MIN_PX_NO_MEASURE;

    if (cols.length !== mins.length) return;

    const apply = () => {
      const totalWidth = wrapper.clientWidth;
      const sumMin = mins.reduce((sum, min) => sum + min, 0);
      const extraPerCol = Math.max(0, totalWidth - sumMin) / mins.length;

      cols.forEach((col, index) => {
        col.style.width = `${mins[index]! + extraPerCol}px`;
      });
    };

    apply();

    const observer = new ResizeObserver(apply);
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, [wrapperRef, includeMeasure, enabled]);
}
