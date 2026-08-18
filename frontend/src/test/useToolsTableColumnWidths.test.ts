import { describe, it, expect } from 'vitest';
import {
  TOOLS_TABLE_CONTENT_MIN_PX,
  TOOLS_TABLE_NAME_COLUMN_INDEX,
  distributeColumnWidths,
} from '../hooks/useToolsTableColumnWidths';

describe('distributeColumnWidths', () => {
  const mins = [...TOOLS_TABLE_CONTENT_MIN_PX];
  const sumMin = mins.reduce((a, b) => a + b, 0);

  it('splits surplus evenly across all columns to fill the pane', () => {
    const available = sumMin + 100;
    const { widths, tableWidth } = distributeColumnWidths(available, mins);
    const baseExtra = Math.floor(100 / mins.length);
    const remainder = 100 - baseExtra * mins.length;

    expect(tableWidth).toBe(available);
    expect(widths.reduce((a, b) => a + b, 0)).toBe(available);
    widths.forEach((width, index) => {
      const expectedBump = index < remainder ? baseExtra + 1 : baseExtra;
      expect(width).toBe(mins[index]! + expectedBump);
    });
    expect(widths[TOOLS_TABLE_NAME_COLUMN_INDEX]).toBeGreaterThan(mins[TOOLS_TABLE_NAME_COLUMN_INDEX]!);
  });

  it('uses minimums when the pane is narrower than the sum', () => {
    const { widths, tableWidth } = distributeColumnWidths(sumMin - 50, mins);
    expect(widths).toEqual(mins);
    expect(tableWidth).toBe(sumMin);
  });
});
