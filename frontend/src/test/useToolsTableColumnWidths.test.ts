import { describe, it, expect } from 'vitest';
import {
  TOOLS_TABLE_COLUMN_MIN_PX,
  TOOLS_TABLE_NAME_COLUMN_INDEX,
  TOOLS_TABLE_COLOR_COLUMN_INDEX,
  TOOLS_TABLE_NAME_SURPLUS_RATIO,
  distributeColumnWidths,
} from '../hooks/useToolsTableColumnWidths';

describe('distributeColumnWidths', () => {
  const mins = TOOLS_TABLE_COLUMN_MIN_PX;
  const sumMin = mins.reduce((a, b) => a + b, 0);

  it('keeps compact columns at min and splits surplus between NAME and COLOR', () => {
    const available = sumMin + 100;
    const widths = distributeColumnWidths(available, mins);
    const nameBonus = Math.floor(100 * TOOLS_TABLE_NAME_SURPLUS_RATIO);
    const colorBonus = 100 - nameBonus;

    expect(widths[TOOLS_TABLE_NAME_COLUMN_INDEX]).toBe(mins[TOOLS_TABLE_NAME_COLUMN_INDEX]! + nameBonus);
    expect(widths[TOOLS_TABLE_COLOR_COLUMN_INDEX]).toBe(mins[TOOLS_TABLE_COLOR_COLUMN_INDEX]! + colorBonus);
    widths.forEach((width, index) => {
      if (index !== TOOLS_TABLE_NAME_COLUMN_INDEX && index !== TOOLS_TABLE_COLOR_COLUMN_INDEX) {
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
