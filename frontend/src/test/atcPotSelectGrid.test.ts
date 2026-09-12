import { describe, expect, it } from 'vitest';
import { buildAtcPotCells } from '../components/machine-detail/probe/AtcPotSelectGrid';
import type { UnifiedToolView } from '../utils/unifiedToolView';

describe('buildAtcPotCells', () => {
  it('builds N empty pots when no unified data', () => {
    const cells = buildAtcPotCells(null, 5);
    expect(cells).toHaveLength(5);
    expect(cells.every((c) => c.empty && c.toolNumber == null)).toBe(true);
    expect(cells.map((c) => c.pot)).toEqual([1, 2, 3, 4, 5]);
  });

  it('maps occupied tools and marks caps empty', () => {
    const unified = {
      tools: [
        {
          tool_number: 12,
          pot_number: 3,
          tool_name: 'EM',
          color: 2,
          diameter: 6,
          length: 45,
        },
        {
          tool_number: 255,
          pot_number: 4,
          color: 1,
        },
      ],
      empty_pockets: [{ pot_number: 1, is_cap: false }],
      spindle: null,
    } as unknown as UnifiedToolView;

    const cells = buildAtcPotCells(unified, 4);
    expect(cells[0]).toMatchObject({ pot: 1, empty: true });
    expect(cells[1]).toMatchObject({ pot: 2, empty: true });
    expect(cells[2]).toMatchObject({
      pot: 3,
      empty: false,
      toolNumber: 12,
      diameter: 6,
      length: 45,
    });
    expect(cells[3]).toMatchObject({ pot: 4, empty: true, isCap: true });
  });
});
