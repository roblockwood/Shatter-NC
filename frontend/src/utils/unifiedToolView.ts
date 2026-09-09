/** Tool-centric view: TOLN rows are primary; ATC fields are assignment edges. */

export interface UnifiedToolRow {
  row_kind?: 'tool';
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
  life?: number;
  in_atc?: boolean;
  pot_number?: string | number;
  group?: string | number;
  tool_type?: number;
  color?: number;
}

export interface EmptyPocket {
  pot_number: number;
  tool_type?: number;
  color?: number;
  /** True when ATCTL marks this pocket as cap (C00: 255, D00: 999). Panel shows tool 0. */
  is_cap?: boolean;
}

export interface SpindleAssignment {
  pot_number: 'SPINDLE';
  tool_number: number;
  tool_type?: number;
  color?: number;
  group?: string | number;
}

export interface UnifiedToolView {
  tools: UnifiedToolRow[];
  empty_pockets: EmptyPocket[];
  spindle: SpindleAssignment | null;
  atc_available: boolean;
}

type LegacyAtcTool = {
  pot_number?: string | number;
  tool_number: number;
  tool_type?: number;
  color?: number;
  group?: string | number;
};

type LegacyTableTool = {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
  life?: number;
};

function isSpindlePot(pot: string | number | undefined): boolean {
  return typeof pot === 'string' && pot.toUpperCase() === 'SPINDLE';
}

/** Build unified view client-side when WebSocket has not yet sent tools_unified. */
export function buildUnifiedToolViewFromLegacy(
  tableTools: LegacyTableTool[],
  atcTools: LegacyAtcTool[],
  numPockets?: number,
): UnifiedToolView {
  const byTool = new Map<number, LegacyAtcTool>();
  const emptyByPot = new Map<number, EmptyPocket>();
  const occupiedPots = new Set<number>();
  let spindle: SpindleAssignment | null = null;

  for (const atc of atcTools) {
    const pot = atc.pot_number;
    const tn = atc.tool_number ?? 0;

    if (isSpindlePot(pot)) {
      if (tn > 0 && tn !== 255 && tn !== 999) {
        spindle = {
          pot_number: 'SPINDLE',
          tool_number: tn,
          tool_type: atc.tool_type,
          color: atc.color,
          group: atc.group,
        };
      }
      continue;
    }

    if (pot === undefined || pot === null) continue;
    const potNum = typeof pot === 'number' ? pot : parseInt(String(pot), 10);
    if (!Number.isFinite(potNum)) continue;

    if (tn === 0 || tn === 255 || tn === 999) {
      emptyByPot.set(potNum, {
        pot_number: potNum,
        tool_type: atc.tool_type,
        color: atc.color,
        is_cap: tn === 255 || tn === 999,
      });
    } else if (tn > 0) {
      byTool.set(tn, atc);
      occupiedPots.add(potNum);
    }
  }

  let empty_pockets: EmptyPocket[];
  if (numPockets && numPockets > 0) {
    empty_pockets = [];
    for (let pot = 1; pot <= numPockets; pot += 1) {
      if (occupiedPots.has(pot)) continue;
      empty_pockets.push(
        emptyByPot.get(pot) ?? { pot_number: pot, tool_type: 1, color: 0 },
      );
    }
  } else {
    empty_pockets = [...emptyByPot.values()].sort((a, b) => a.pot_number - b.pot_number);
  }

  const tools: UnifiedToolRow[] = tableTools
    .filter((t) => t.tool_number)
    .map((tol) => {
      const atc = byTool.get(tol.tool_number);
      const row: UnifiedToolRow = {
        row_kind: 'tool',
        tool_number: tol.tool_number,
        tool_name: tol.tool_name,
        diameter: tol.diameter,
        length: tol.length,
        life: tol.life,
        in_atc: !!atc,
      };
      if (atc) {
        row.pot_number = atc.pot_number;
        row.group = atc.group;
        row.tool_type = atc.tool_type;
        row.color = atc.color;
      }
      return row;
    });

  return {
    tools,
    empty_pockets,
    spindle,
    atc_available: atcTools.length > 0,
  };
}
