/** ATC pot multi-select grid for multi-tool length measure. */
import React, { useMemo } from 'react';
import type { UnifiedToolView } from '../../../utils/unifiedToolView';
import './AtcPotSelectGrid.css';

const CAP_TOOL_NUMBERS = new Set([255, 999]);

export interface AtcPotCell {
  pot: number;
  toolNumber: number | null;
  toolName?: string;
  color?: number;
  toolType?: number;
  diameter?: number;
  length?: number;
  empty: boolean;
  isCap: boolean;
}

function toolColorHex(color: number | undefined): string {
  switch (color) {
    case 1:
      return '#0066ff';
    case 2:
      return '#ff0000';
    case 3:
      return '#9900ff';
    case 4:
      return '#00ff00';
    case 5:
      return '#00ccff';
    case 6:
      return '#ffff00';
    case 7:
      return '#ffffff';
    default:
      return '#666666';
  }
}

function parsePot(pot: string | number | undefined): number | null {
  if (pot == null) return null;
  if (typeof pot === 'string' && pot.toUpperCase() === 'SPINDLE') return null;
  const n = typeof pot === 'number' ? pot : Number.parseInt(String(pot), 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function buildAtcPotCells(
  unified: UnifiedToolView | null | undefined,
  numPockets: number
): AtcPotCell[] {
  const n = Math.max(1, Math.min(99, Math.floor(numPockets) || 21));
  const byPot = new Map<number, AtcPotCell>();

  for (let pot = 1; pot <= n; pot++) {
    byPot.set(pot, {
      pot,
      toolNumber: null,
      empty: true,
      isCap: false,
    });
  }

  if (unified) {
    for (const t of unified.tools) {
      const pot = parsePot(t.pot_number);
      if (pot == null || pot < 1 || pot > n) continue;
      const tn = t.tool_number ?? 0;
      if (tn <= 0 || CAP_TOOL_NUMBERS.has(tn)) {
        byPot.set(pot, {
          pot,
          toolNumber: null,
          empty: true,
          isCap: CAP_TOOL_NUMBERS.has(tn),
          color: t.color,
          toolType: t.tool_type,
        });
        continue;
      }
      byPot.set(pot, {
        pot,
        toolNumber: tn,
        toolName: t.tool_name,
        color: t.color,
        toolType: t.tool_type,
        diameter: t.diameter,
        length: t.length,
        empty: false,
        isCap: false,
      });
    }
    for (const p of unified.empty_pockets) {
      const pot = p.pot_number;
      if (pot < 1 || pot > n) continue;
      const existing = byPot.get(pot);
      if (existing && !existing.empty) continue;
      byPot.set(pot, {
        pot,
        toolNumber: null,
        empty: true,
        isCap: Boolean(p.is_cap),
        color: p.color,
        toolType: p.tool_type,
      });
    }
  }

  return Array.from({ length: n }, (_, i) => byPot.get(i + 1)!);
}

export interface AtcPotSelectGridProps {
  unified?: UnifiedToolView | null;
  numPockets: number;
  selectedPots: number[];
  disabled?: boolean;
  onChange: (selectedPots: number[]) => void;
}

export const AtcPotSelectGrid: React.FC<AtcPotSelectGridProps> = ({
  unified,
  numPockets,
  selectedPots,
  disabled,
  onChange,
}) => {
  const cells = useMemo(
    () => buildAtcPotCells(unified, numPockets),
    [unified, numPockets]
  );
  const selected = useMemo(() => new Set(selectedPots), [selectedPots]);
  const fullCount = cells.filter((c) => !c.empty && c.toolNumber != null).length;

  function toggle(cell: AtcPotCell) {
    if (disabled || cell.empty || cell.toolNumber == null) return;
    const next = new Set(selected);
    if (next.has(cell.pot)) next.delete(cell.pot);
    else next.add(cell.pot);
    onChange(Array.from(next).sort((a, b) => a - b));
  }

  function selectAllFull() {
    if (disabled) return;
    onChange(
      cells
        .filter((c) => !c.empty && c.toolNumber != null)
        .map((c) => c.pot)
    );
  }

  function clearAll() {
    if (disabled) return;
    onChange([]);
  }

  return (
    <div className="atc-pot-select">
      <div className="atc-pot-select-header">
        <span className="atc-pot-select-title">
          ATC POTS · {selectedPots.length} selected / {fullCount} full
        </span>
        <span className="atc-pot-select-actions">
          <button
            type="button"
            className="atc-pot-select-link"
            disabled={disabled || fullCount === 0}
            onClick={selectAllFull}
          >
            [ ALL FULL ]
          </button>
          <button
            type="button"
            className="atc-pot-select-link"
            disabled={disabled || selectedPots.length === 0}
            onClick={clearAll}
          >
            [ CLEAR ]
          </button>
        </span>
      </div>
      <div
        className="atc-pot-select-grid"
        role="group"
        aria-label="ATC pot multi-select for tool length measure"
      >
        {cells.map((cell) => {
          const isSelected = selected.has(cell.pot);
          const canSelect = !cell.empty && cell.toolNumber != null;
          const color = toolColorHex(cell.color);
          return (
            <button
              key={cell.pot}
              type="button"
              className={[
                'atc-pot-cell',
                canSelect ? 'atc-pot-cell--full' : 'atc-pot-cell--empty',
                isSelected ? 'atc-pot-cell--selected' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              disabled={disabled || !canSelect}
              aria-pressed={isSelected}
              title={
                canSelect
                  ? `Pot ${cell.pot} · T${String(cell.toolNumber).padStart(2, '0')}${
                      cell.toolName ? ` · ${cell.toolName}` : ''
                    }`
                  : cell.isCap
                    ? `Pot ${cell.pot} · CAP`
                    : `Pot ${cell.pot} · empty`
              }
              onClick={() => toggle(cell)}
            >
              <span
                className="atc-pot-cell-swatch"
                style={{ background: canSelect ? color : 'transparent' }}
              />
              <span className="atc-pot-cell-pot">P{cell.pot}</span>
              <span className="atc-pot-cell-tool">
                {canSelect
                  ? `T${String(cell.toolNumber).padStart(2, '0')}`
                  : cell.isCap
                    ? 'CAP'
                    : '──'}
              </span>
              {canSelect && (cell.diameter != null || cell.length != null) && (
                <span className="atc-pot-cell-meta">
                  {cell.diameter != null ? `Ø${cell.diameter}` : ''}
                  {cell.diameter != null && cell.length != null ? ' ' : ''}
                  {cell.length != null ? `L${cell.length}` : ''}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
