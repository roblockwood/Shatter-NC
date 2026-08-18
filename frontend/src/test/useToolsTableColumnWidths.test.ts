import { describe, it, expect } from 'vitest';
import {
  TOOLS_TABLE_CONTENT_MIN_PX,
  TOOLS_TABLE_NAME_COLUMN_INDEX,
  distributeColumnWidths,
} from '../hooks/useToolsTableColumnWidths';

describe('distributeColumnWidths', () => {
  const mins = [...TOOLS_TABLE_CONTENT_MIN_PX];
  const sumMin = mins.reduce((a, b) => a + b, 0);

  it('keeps every column at its minimum and does not grow NAME with surplus', () => {
    const { widths, tableWidth } = distributeColumnWidths(sumMin + 200, mins);

    expect(widths).toEqual(mins);
    expect(widths[TOOLS_TABLE_NAME_COLUMN_INDEX]).toBe(mins[TOOLS_TABLE_NAME_COLUMN_INDEX]);
    expect(tableWidth).toBe(sumMin);
  });

  it('still uses minimums when the pane is narrower than the sum', () => {
    const { widths, tableWidth } = distributeColumnWidths(sumMin - 50, mins);
    expect(widths).toEqual(mins);
    expect(tableWidth).toBe(sumMin);
  });
});
