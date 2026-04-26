import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';

export interface ATCOptimizerResult {
  tool_sequence: number[];
  unique_tools: number[];
  tool_change_count: number;
  transition_matrix: { [key: string]: number };
  baseline_assignment: { [key: string]: number };
  optimized_assignment: { [key: string]: number };
  baseline_cost: number;
  optimized_cost: number;
  improvement_pct: number;
}

export interface ToolsOptimizerTabProps {
  machineId: number | undefined;
  programName: string | undefined;
  numPockets: number;
  /** Live pot→tool mapping from the ATC cache, used to show current assignments. */
  actualPotMap: Map<number, number>;
}

export const ToolsOptimizerTab: React.FC<ToolsOptimizerTabProps> = ({
  machineId,
  programName,
  numPockets: numPocketsProp,
  actualPotMap,
}) => {
  const [optimizerResult, setOptimizerResult] = useState<ATCOptimizerResult | null>(null);
  const [optimizerLoading, setOptimizerLoading] = useState(false);
  const [optimizerError, setOptimizerError] = useState<string | null>(null);
  const [optimizerNumPockets, setOptimizerNumPockets] = useState(numPocketsProp);
  const [optimizerAnalyzedProgram, setOptimizerAnalyzedProgram] = useState<string | null>(null);
  const [pinnedTools, setPinnedTools] = useState<Set<number>>(new Set());
  const [optimizerAnalyzedPins, setOptimizerAnalyzedPins] = useState<string>('');

  // Reset pins when program changes
  useEffect(() => {
    setPinnedTools(new Set());
    setOptimizerAnalyzedPins('');
  }, [programName]);

  // Auto-run when tab becomes active with a new program
  useEffect(() => {
    if (machineId && programName && optimizerAnalyzedProgram !== programName && !optimizerLoading) {
      runOptimizer();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machineId, programName]);

  const runOptimizer = async (force = false) => {
    if (!machineId || optimizerLoading) return;
    const effectiveProgramName = programName || (force ? optimizerAnalyzedProgram : null);
    if (!effectiveProgramName) {
      setOptimizerError('No active program on machine. Load a program first.');
      return;
    }
    if (!force && optimizerAnalyzedProgram === effectiveProgramName && optimizerResult) return;

    setOptimizerLoading(true);
    setOptimizerError(null);
    try {
      // Resolve the actual FTP path via the deployment record
      let filePath: string | null = null;
      const deplRes = await fetch(
        `${API_BASE_URL}/api/programs/machines/${machineId}/deployments/by-onumber/${encodeURIComponent(effectiveProgramName)}?include_program=false`
      );
      if (deplRes.ok) {
        const deplData = await deplRes.json();
        filePath = deplData.deployment?.deployed_path ?? null;
      }
      // Fallback: construct path from O-number alone (root directory)
      if (!filePath) {
        const oNum = effectiveProgramName.replace(/^O/i, '').replace(/\.NC$/i, '');
        const oNumPadded = oNum.padStart(4, '0');
        filePath = `/O${oNumPadded}.NC`;
      }

      const viewRes = await fetch(
        `${API_BASE_URL}/api/machines/${machineId}/view?file_path=${encodeURIComponent(filePath)}`
      );
      if (!viewRes.ok) {
        const errData = await viewRes.json().catch(() => ({}));
        throw new Error(errData.detail || `Cannot read ${filePath} (HTTP ${viewRes.status})`);
      }
      const viewData = await viewRes.json();
      const gcodeContent: string = viewData.content;
      if (!gcodeContent) throw new Error('Empty response for program file');

      // Build current_assignment from live ATC data for accurate CURR POT + pinning
      const currentAssignment: { [key: string]: number } = {};
      actualPotMap.forEach((pot, toolNum) => { currentAssignment[String(toolNum)] = pot; });

      const optRes = await fetch(`${API_BASE_URL}/api/programs/analyze-atc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gcode_content: gcodeContent,
          num_pockets: optimizerNumPockets,
          current_assignment: currentAssignment,
          pinned_tools: Array.from(pinnedTools),
        }),
      });
      if (!optRes.ok) {
        const err = await optRes.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : `Optimizer error (HTTP ${optRes.status})`);
      }
      const result = await optRes.json();
      setOptimizerResult(result);
      setOptimizerAnalyzedProgram(effectiveProgramName);
      setOptimizerAnalyzedPins(JSON.stringify(Array.from(pinnedTools).sort()));
    } catch (e) {
      setOptimizerError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setOptimizerLoading(false);
    }
  };

  if (optimizerLoading) {
    return (
      <div className="optimizer-loading" onClick={(e) => e.stopPropagation()}>
        ANALYZING TOOL SEQUENCE...
      </div>
    );
  }
  if (optimizerError) {
    return (
      <div className="optimizer-error" onClick={(e) => e.stopPropagation()}>
        <div className="optimizer-error-msg">⚠ {optimizerError}</div>
        <button className="optimizer-action-btn" onClick={(e) => { e.stopPropagation(); runOptimizer(true); }}>
          [ RETRY ]
        </button>
      </div>
    );
  }
  if (!optimizerResult) {
    return (
      <div className="optimizer-empty" onClick={(e) => e.stopPropagation()}>
        {programName ? (
          <>
            <div className="optimizer-empty-label">PROGRAM: {programName}</div>
            <button className="optimizer-action-btn" onClick={(e) => { e.stopPropagation(); runOptimizer(); }}>
              [ ANALYZE ]
            </button>
          </>
        ) : (
          <div className="optimizer-empty-label">NO ACTIVE PROGRAM ON MACHINE</div>
        )}
      </div>
    );
  }

  const {
    unique_tools, tool_change_count,
    baseline_assignment, optimized_assignment,
    baseline_cost, optimized_cost, improvement_pct,
    transition_matrix,
  } = optimizerResult;

  const currentPinsJson = JSON.stringify(Array.from(pinnedTools).sort());
  const pinsChanged = optimizerResult !== null && currentPinsJson !== optimizerAnalyzedPins;

  const maxTrans = Math.max(...Object.values(transition_matrix), 1);
  const BAR = 8;
  const bar = (n: number) => '█'.repeat(Math.round((n / maxTrans) * BAR)) + '░'.repeat(BAR - Math.round((n / maxTrans) * BAR));

  const potToTool: { [pot: number]: number } = {};
  unique_tools.forEach(t => {
    const pot = optimized_assignment[String(t)];
    if (pot != null) potToTool[pot] = t;
  });

  const savings = Math.max(0, improvement_pct);
  const savingsFilled = Math.round(savings / 5);

  return (
    <div className="optimizer-view" onClick={(e) => e.stopPropagation()}>

      {/* Pins-changed banner */}
      {pinsChanged && (
        <div className="optimizer-pins-changed">
          PINS CHANGED —
          <button className="optimizer-action-btn optimizer-recalc-btn" onClick={(e) => { e.stopPropagation(); runOptimizer(true); }}>
            [ RE-ANALYZE ]
          </button>
        </div>
      )}

      {/* Summary row */}
      <div className="optimizer-summary">
        <span>CAROUSEL: {optimizerNumPockets} POCKETS</span>
        <span className="optimizer-sep">│</span>
        <span>TOOLS: {unique_tools.length}</span>
        <span className="optimizer-sep">│</span>
        <span>CHANGES: {tool_change_count}</span>
        <span className="optimizer-sep">│</span>
        <span className={savings > 0 ? 'optimizer-savings-highlight' : ''}>
          SAVINGS: {improvement_pct}%
        </span>
      </div>

      {/* Progress bar */}
      {savings > 0 && (
        <div className="optimizer-progress-row">
          <span className="optimizer-progress-bar">
            {'█'.repeat(savingsFilled)}{'░'.repeat(20 - savingsFilled)}
          </span>
          <span className="optimizer-progress-label">
            &nbsp;{baseline_cost} steps → {optimized_cost} steps
          </span>
        </div>
      )}

      {/* Assignment table */}
      <div className="optimizer-section-label">─ POT ASSIGNMENT ─</div>
      <table className="optimizer-table">
        <thead>
          <tr>
            <th>TOOL</th>
            <th>CURR POT</th>
            <th>OPT POT</th>
            <th>MOVE</th>
            <th>LOCK</th>
          </tr>
        </thead>
        <tbody>
          {unique_tools.map(t => {
            const currPot = actualPotMap.get(t) ?? baseline_assignment[String(t)];
            const opt = optimized_assignment[String(t)];
            const isPinned = pinnedTools.has(t);
            const moved = !isPinned && currPot !== opt;
            return (
              <tr key={t} className={isPinned ? 'optimizer-pinned-row' : ''}>
                <td>T{String(t).padStart(2, '0')}</td>
                <td>{currPot ?? '─'}</td>
                <td className={moved ? 'optimizer-moved' : ''}>{opt ?? '─'}</td>
                <td className={moved ? 'optimizer-moved' : 'optimizer-nomove'}>
                  {isPinned ? '🔒' : moved ? '←' : '─'}
                </td>
                <td>
                  <button
                    className={`optimizer-pin-btn${isPinned ? ' optimizer-pin-btn--active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setPinnedTools(prev => {
                        const next = new Set(prev);
                        if (next.has(t)) next.delete(t); else next.add(t);
                        return next;
                      });
                    }}
                  >{isPinned ? 'LOCKED' : 'LOCK'}</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Transition matrix */}
      {Object.keys(transition_matrix).length > 0 && (
        <>
          <div className="optimizer-section-label">─ TRANSITIONS ─</div>
          <div className="optimizer-transitions">
            {Object.entries(transition_matrix).map(([pair, count]) => (
              <div key={pair} className="optimizer-transition-row">
                <span className="optimizer-transition-pair">{pair}</span>
                <span className="optimizer-transition-bar">{bar(count as number)}</span>
                <span className="optimizer-transition-count">&nbsp;{count}×</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Carousel strip */}
      <div className="optimizer-section-label">─ OPTIMIZED CAROUSEL ─</div>
      <div className="optimizer-carousel">
        {Array.from({ length: optimizerNumPockets }, (_, i) => {
          const pot = i + 1;
          const toolNum = potToTool[pot];
          return (
            <span
              key={pot}
              className={`optimizer-pocket ${toolNum ? 'optimizer-pocket-filled' : 'optimizer-pocket-empty'}`}
            >
              [{String(pot).padStart(2, '0')}:{toolNum ? `T${String(toolNum).padStart(2, '0')}` : '───'}]
            </span>
          );
        })}
      </div>

      {/* Controls */}
      <div className="optimizer-actions">
        <select
          className="optimizer-pockets-select"
          value={optimizerNumPockets}
          onChange={(e) => setOptimizerNumPockets(Number(e.target.value))}
          onClick={(e) => e.stopPropagation()}
        >
          {[8, 14, 21, 30, 40, 60].map(n => (
            <option key={n} value={n}>{n} POCKETS</option>
          ))}
        </select>
        <button
          className="optimizer-action-btn"
          onClick={(e) => { e.stopPropagation(); runOptimizer(true); }}
        >
          [ RE-ANALYZE ]
        </button>
      </div>

    </div>
  );
};
