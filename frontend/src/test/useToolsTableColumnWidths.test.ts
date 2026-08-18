import { describe, it, expect } from 'vitest';
import {
  TOOLS_TABLE_COLUMN_MIN_PX,
  TOOLS_TABLE_NAME_COLUMN_INDEX,
  distributeColumnWidths,
} from '../hooks/useToolsTableColumnWidths';

describe('distributeColumnWidths', () => {
  const mins = TOOLS_TABLE_COLUMN_MIN_PX;
  const sumMin = mins.reduce((a, b) => a + b, 0);

  it('keeps compact columns at minimum and gives NAME the remainder', () => {
    const available = sumMin + 100;
    const widths = distributeColumnWidths(available, mins);

    expect(widths[TOOLS_TABLE_NAME_COLUMN_INDEX]).toBe(mins[TOOLS_TABLE_NAME_COLUMN_INDEX]! + 100);
    widths.forEach((width, index) => {
      if (index !== TOOLS_TABLE_NAME_COLUMN_INDEX) {
        expect(width).toBe(mins[index]);
      }
    });
    expect(widths.reduce((a, b) => a + b, 0)).toBe(available);
  });

  it('uses minimums when pane is too narrow', () => {
    const widths = distributeColumnWidths(sumMin - 10, mins);
    expect(widths).toEqual([...mins]);
  });
});
