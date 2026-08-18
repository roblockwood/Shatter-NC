import React, { useState, useMemo, useEffect, useLayoutEffect, useRef, useId } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useBetaMode } from '../../hooks/useBetaMode';
import { formatDimension } from '../../utils/formatDimension';
import type { UnitType } from '../../utils/formatDimension';
import { API_BASE_URL } from '../../config/api';
import { ColorSelect } from './ColorSelect';
import { Select } from '../ui/Select';
import './ToolsPane.css';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { ToolsOptimizerTab } from './ToolsOptimizerTab';
import {
  buildUnifiedToolViewFromLegacy,
  type EmptyPocket,
  type UnifiedToolRow,
  type UnifiedToolView,
} from '../../utils/unifiedToolView';

// Define type locally to avoid Vite import issues
type ToolModificationOperationType = 
  | 'color' 
  | 'tool_number' 
  | 'pot_number'
  | 'tool_type' 
  | 'delete' 
  | 'cap'
  | 'life' 
  | 'offset' 
  | 'spindle'
  | 'name';

interface Tool {
  pot_number?: string | number;
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
  group?: string | number;
  life?: number;
  tool_type?: number;
  color?: number;
  in_atc?: boolean;
  /** Empty-pocket row: ATCTL cap marker (panel shows tool 0). */
  is_cap?: boolean;
}

interface ToolsPaneProps {
  tools: Tool[];  // Legacy ATC data (fallback builder input)
  toolTable?: Tool[];  // Legacy TOLN data (fallback builder input)
  toolsUnified?: UnifiedToolView;  // Preferred when connected to a machine
  currentTool?: number;
  machineId?: number;
  source?: 'atc' | 'table';  // Deprecated — unified view ignores this when machineId is set
  units?: UnitType;
  machineStatus?: string;  // Status from WebSocket polling (e.g., "operating", "standby", "error")
  memMode?: number;  // MEM mode from WebSocket polling: 0=Manual, 1=MDI, 2=Memory, 3=Edit, 4=MDI manual, 5=Memory edit
  memOperationStatus?: number;  // MEM operation_status from WebSocket polling: 0=Reset, 1=Operation, 2=Temporary stop, 3=Block stop
  toolsTimestamp?: string | null;
  toolTableTimestamp?: string | null;
  toolPollIntervalSeconds?: number;
  /** Compact layout for machine-card hover preview (scroll + slimmer chrome). */
  variant?: 'default' | 'hover';
  /** O-number of the currently active program on the machine (e.g. "O2045"). Used by the Optimizer tab. */
  programName?: string;
  /** ATC carousel pocket count — defaults to 21. */
  numPockets?: number;
  /** Live macro variables from polling (#500-999). */
  macros?: Record<string, number>;
}

type SortColumn = 'pot_number' | 'tool_number' | 'tool_name' | 'diameter' | 'length' | 'group' | 'life' | 'tool_type' | 'color';
type SortDirection = 'asc' | 'desc';
type ToolsViewFilter = 'all' | 'atc' | 'empty';

const TOOL_TYPE_OPTIONS = [
  { value: '1', label: 'STD' },
  { value: '2', label: 'LARGE' },
  { value: '3', label: 'MED' },
];

interface PendingChange {
  tool: Tool;
  field: string;
  oldValue: string | number;
  newValue: string | number;
  operationType: ToolModificationOperationType;
  cacheSlice: 'tool' | 'pocket' | 'spindle';
}

interface ToolChangeBatchItem {
  operation_type: string;
  client_id?: string;
  pot_number?: number;
  tool_number?: number;
  color?: number;
  tool_type?: number;
  offset_type?: 'H' | 'D' | 'W';
  value?: number;
  life_value?: number;
  life_type?: 'TIME' | 'COUNT';
  name_value?: string;
}

interface ToolChangeBatchResult {
  operation_type: string;
  client_id?: string;
  success: boolean;
  message?: string;
  pot_number?: number;
  tool_number?: number;
  color?: number;
  tool_type?: number;
  offset_type?: string;
  value?: number;
  life_value?: number;
  name_value?: string;
}

function parsePotNumber(pot: string | number | undefined): number | null {
  if (pot === undefined || pot === null) return null;
  if (typeof pot === 'string' && pot.toUpperCase() === 'SPINDLE') return 0;
  const n = typeof pot === 'number' ? pot : parseInt(String(pot), 10);
  return Number.isFinite(n) ? n : null;
}

function isSpindlePot(pot: string | number | undefined): boolean {
  return typeof pot === 'string' && pot.toUpperCase() === 'SPINDLE';
}

function formatPotDisplay(pot: string | number | undefined): string {
  if (pot === undefined || pot === null || pot === '') return '──';
  return String(pot);
}

interface NumericEditInputProps {
  className?: string;
  value: string | number | undefined;
  onValueChange: (raw: string) => void;
  onClick?: (e: React.MouseEvent<HTMLInputElement>) => void;
  placeholder?: string;
  decimal?: boolean;
}

function NumericEditInput({
  className,
  value,
  onValueChange,
  onClick,
  placeholder,
  decimal = false,
}: NumericEditInputProps) {
  const externalDisplay =
    value === undefined || value === null || value === ''
      ? ''
      : String(value);
  const [draft, setDraft] = useState(externalDisplay);
  const focusedRef = useRef(false);

  useEffect(() => {
    if (!focusedRef.current) {
      setDraft(externalDisplay);
    }
  }, [externalDisplay]);

  return (
    <input
      type="text"
      inputMode={decimal ? 'decimal' : 'numeric'}
      autoComplete="off"
      className={className}
      value={draft}
      placeholder={placeholder}
      onClick={onClick}
      onMouseDown={(e) => e.stopPropagation()}
      onFocus={(e) => {
        focusedRef.current = true;
        e.stopPropagation();
      }}
      onBlur={(e) => {
        focusedRef.current = false;
        const finalValue = e.target.value;
        if (!valuesEqual(finalValue, externalDisplay)) {
          onValueChange(finalValue);
        }
      }}
      onChange={(e) => {
        setDraft(e.target.value);
      }}
    />
  );
}

interface TextEditInputProps {
  className?: string;
  value: string | undefined;
  onValueChange: (raw: string) => void;
  onClick?: (e: React.MouseEvent<HTMLInputElement>) => void;
  placeholder?: string;
  maxLength?: number;
}

/** Text entry with local draft while focused (tool name, etc.). */
function TextEditInput({
  className,
  value,
  onValueChange,
  onClick,
  placeholder,
  maxLength,
}: TextEditInputProps) {
  const externalDisplay = value ?? '';
  const [draft, setDraft] = useState(externalDisplay);
  const focusedRef = useRef(false);

  useEffect(() => {
    if (!focusedRef.current) {
      setDraft(externalDisplay);
    }
  }, [externalDisplay]);

  return (
    <input
      type="text"
      autoComplete="off"
      className={className}
      value={draft}
      placeholder={placeholder}
      maxLength={maxLength}
      onClick={onClick}
      onMouseDown={(e) => e.stopPropagation()}
      onFocus={(e) => {
        focusedRef.current = true;
        e.stopPropagation();
      }}
      onBlur={(e) => {
        focusedRef.current = false;
        const finalValue = e.target.value;
        if (finalValue !== externalDisplay) {
          onValueChange(finalValue);
        }
      }}
      onChange={(e) => {
        setDraft(e.target.value);
      }}
    />
  );
}

function makePendingKey(
  tool: Tool,
  field: string,
  operationType: ToolModificationOperationType,
): string {
  const pot = tool.pot_number ?? '';
  const tn = tool.tool_number;
  switch (operationType) {
    case 'color':
      return `${pot}-${tn}-color`;
    case 'tool_number':
      return `${pot}-assignment`;
    case 'pot_number':
      return `${tn}-pot-assignment`;
    case 'tool_type':
      return `${pot}-type`;
    case 'delete':
      return `${pot}-delete`;
    case 'cap':
      return `${pot}-cap`;
    case 'spindle':
      return 'spindle-tool';
    case 'offset':
      return `${tn}-offset-${field}`;
    case 'life':
      return `${tn}-life`;
    case 'name':
      return `${tn}-name`;
    default:
      return `${pot}-${tn}-${field}`;
  }
}

function applyFieldToTool(tool: Tool, field: string, value: string | number): Tool {
  switch (field) {
    case 'color':
      return { ...tool, color: Number(value) };
    case 'tool_number':
      return { ...tool, tool_number: Number(value) };
    case 'pot_number':
      if (value === '' || value === undefined || value === null) {
        return { ...tool, pot_number: undefined };
      }
      return { ...tool, pot_number: Number(value) };
    case 'tool_type':
      return { ...tool, tool_type: Number(value) };
    case 'length':
      return { ...tool, length: Number(value) };
    case 'diameter':
      return { ...tool, diameter: Number(value) };
    case 'H':
      return { ...tool, length: Number(value) };
    case 'D':
      return { ...tool, diameter: Number(value) };
    case 'life':
      return { ...tool, life: Number(value) };
    case 'tool_name':
      return { ...tool, tool_name: String(value) };
    default:
      return tool;
  }
}

function valuesEqual(a: string | number, b: string | number): boolean {
  if (typeof a === 'number' && typeof b === 'number') {
    return Math.abs(a - b) < 0.000001;
  }
  return a === b;
}

function potsEqual(
  a: string | number | undefined,
  b: string | number | undefined,
): boolean {
  if (a === b) return true;
  if (isSpindlePot(a) && isSpindlePot(b)) return true;
  const pa = parsePotNumber(a);
  const pb = parsePotNumber(b);
  return pa !== null && pb !== null && pa === pb;
}

function unifiedRowAsTool(row: UnifiedToolRow): Tool {
  return { ...row };
}

function emptyPocketAsTool(pocket: EmptyPocket): Tool {
  return {
    pot_number: pocket.pot_number,
    tool_number: 0,
    tool_type: pocket.tool_type,
    color: pocket.color,
    is_cap: pocket.is_cap,
  };
}

const CAP_ATC_TOOL_NUMBERS = new Set([255, 999]);

function isRealAtcToolNumber(toolNumber: number): boolean {
  return toolNumber > 0 && !CAP_ATC_TOOL_NUMBERS.has(toolNumber);
}

function buildPotOccupancyMap(
  cache: UnifiedToolView,
  pending: Map<string, PendingChange>,
): Map<number, number> {
  const occupancy = new Map<number, number>();

  for (const row of cache.tools) {
    const merged = mergeServerToolWithPending(unifiedRowAsTool(row), pending, 'tool');
    const pot = parsePotNumber(merged.pot_number);
    if (pot !== null && pot > 0 && merged.in_atc && isRealAtcToolNumber(merged.tool_number)) {
      occupancy.set(pot, merged.tool_number);
    }
  }

  for (const pocket of cache.empty_pockets) {
    const asTool = emptyPocketAsTool(pocket);
    const merged = mergeServerToolWithPending(asTool, pending, 'pocket');
    const pot = parsePotNumber(merged.pot_number);
    if (pot !== null && pot > 0 && isRealAtcToolNumber(merged.tool_number)) {
      occupancy.set(pot, merged.tool_number);
    }
  }

  return occupancy;
}

function findToolPotAssignment(
  cache: UnifiedToolView,
  pending: Map<string, PendingChange>,
  toolNumber: number,
): number | null {
  for (const [pot, tool] of buildPotOccupancyMap(cache, pending)) {
    if (tool === toolNumber) return pot;
  }
  return null;
}

function findToolTableEntry(
  cache: UnifiedToolView,
  pending: Map<string, PendingChange>,
  toolNumber: number,
): Tool | undefined {
  const row = cache.tools.find((t) => t.tool_number === toolNumber);
  if (!row) return undefined;
  return mergeServerToolWithPending(unifiedRowAsTool(row), pending, 'tool');
}

function getPotOccupantTool(
  cache: UnifiedToolView,
  pending: Map<string, PendingChange>,
  potNumber: number,
  excludeToolNumber?: number,
): number | null {
  const occupant = buildPotOccupancyMap(cache, pending).get(potNumber);
  if (occupant === undefined) return null;
  if (excludeToolNumber !== undefined && occupant === excludeToolNumber) return null;
  return occupant;
}

function clearAtcAssignment(tool: Tool): Tool {
  return {
    ...tool,
    in_atc: false,
    pot_number: undefined,
    group: undefined,
    tool_type: undefined,
    color: undefined,
  };
}

function restoreAtcAssignment(tool: Tool, snapshot: Tool): Tool {
  return {
    ...tool,
    tool_number: snapshot.tool_number,
    in_atc: true,
    pot_number: snapshot.pot_number,
    group: snapshot.group,
    tool_type: snapshot.tool_type,
    color: snapshot.color,
  };
}

function applyAssignmentEdge(tool: Tool, field: string, value: string | number): Tool {
  if (field === 'tool_number' && Number(value) === 0) {
    return clearAtcAssignment(tool);
  }
  const next = applyFieldToTool(tool, field, value);
  if (field === 'pot_number') {
    if (value === '' || value === undefined || value === null) {
      return clearAtcAssignment(next);
    }
    return { ...next, in_atc: true };
  }
  return next;
}

function toolsMatchForSlice(
  a: Tool,
  b: Tool,
  slice: PendingChange['cacheSlice'],
): boolean {
  if (slice === 'tool') return a.tool_number === b.tool_number && a.tool_number > 0;
  if (slice === 'pocket') return potsEqual(a.pot_number, b.pot_number);
  if (slice === 'spindle') return isSpindlePot(a.pot_number) && isSpindlePot(b.pot_number);
  return false;
}

function mergeServerToolWithPending(
  serverTool: Tool,
  pendingChanges: Map<string, PendingChange>,
  cacheSlice: PendingChange['cacheSlice'],
): Tool {
  let merged = { ...serverTool };
  pendingChanges.forEach((change) => {
    if (change.cacheSlice !== cacheSlice) return;
    if (!toolsMatchForSlice(change.tool, serverTool, cacheSlice)) return;
    if (change.operationType === 'delete') {
      merged = clearAtcAssignment(merged);
      return;
    }
    if (change.operationType === 'cap') {
      merged = { ...merged, tool_number: 0, is_cap: true };
      return;
    }
    merged =
      cacheSlice === 'tool' && (change.field === 'pot_number' || change.field === 'tool_number')
        ? applyAssignmentEdge(merged, change.field, change.newValue)
        : applyFieldToTool(merged, change.field, change.newValue);
  });
  return merged;
}

async function loadUnifiedToolsCache(machineId: number): Promise<UnifiedToolView | null> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/tools?source=atc`);
  if (!response.ok) return null;
  const data = await response.json();
  if (data?.tools_unified) {
    return { ...data.tools_unified, spindle: data.tools_unified.spindle ?? null };
  }
  if (data?.tools) {
    return buildUnifiedToolViewFromLegacy(data.tool_table || [], data.tools);
  }
  return null;
}

function applyConfirmedToolChange(
  tool: Tool,
  change: PendingChange,
  result: ToolChangeBatchResult,
): Tool {
  const confirmed = getConfirmedValueFromResult(result);
  if (change.operationType === 'delete') {
    return clearAtcAssignment(tool);
  }
  if (change.operationType === 'pot_number') {
    const potVal = result.pot_number ?? Number(change.newValue);
    return applyAssignmentEdge(tool, 'pot_number', potVal);
  }
  if (change.operationType === 'cap') {
    return { ...tool, is_cap: true };
  }
  if (confirmed) {
    if (change.cacheSlice === 'tool' && (confirmed.field === 'pot_number' || confirmed.field === 'tool_number')) {
      return applyAssignmentEdge(tool, confirmed.field, confirmed.value);
    }
    return applyFieldToTool(tool, confirmed.field, confirmed.value);
  }
  return tool;
}

function reconcileUnifiedCacheAfterBatch(
  cache: UnifiedToolView,
  results: ToolChangeBatchResult[],
  pendingByClientId: Map<string, PendingChange>,
): UnifiedToolView {
  let tools = cache.tools.map((row) => unifiedRowAsTool(row));
  let empty_pockets = cache.empty_pockets.map((pocket) => ({ ...pocket }));
  let spindle = cache.spindle;

  for (const result of results) {
    if (!result.success || !result.client_id) continue;
    const change = pendingByClientId.get(result.client_id);
    if (!change) continue;

    if (change.operationType === 'delete') {
      const clearedPot = parsePotNumber(change.tool.pot_number);
      tools = tools.map((row) =>
        toolsMatchForSlice(change.tool, row, 'tool') ? clearAtcAssignment(row) : row,
      );
      if (clearedPot !== null && !empty_pockets.some((p) => p.pot_number === clearedPot)) {
        empty_pockets.push({
          pot_number: clearedPot,
          tool_type: change.tool.tool_type ?? 1,
          color: change.tool.color ?? 0,
        });
      }
      continue;
    }

    if (
      change.operationType === 'pot_number'
      || (change.operationType === 'tool_number' && change.cacheSlice === 'pocket')
    ) {
      const targetPot =
        change.operationType === 'pot_number'
          ? Number(change.newValue)
          : parsePotNumber(change.tool.pot_number);
      const assignedTool =
        change.operationType === 'pot_number'
          ? change.tool.tool_number
          : Number(change.newValue);

      if (targetPot === null || !Number.isFinite(targetPot) || targetPot < 1 || !Number.isFinite(assignedTool)) {
        continue;
      }

      tools = tools.map((row) => {
        if (row.tool_number === assignedTool) {
          return {
            ...row,
            in_atc: true,
            pot_number: targetPot,
          };
        }
        if (row.in_atc && parsePotNumber(row.pot_number) === targetPot) {
          return clearAtcAssignment(row);
        }
        return row;
      });
      empty_pockets = empty_pockets.filter((p) => p.pot_number !== targetPot);
      continue;
    }

    if (change.operationType === 'cap' && change.cacheSlice === 'pocket') {
      const pot = parsePotNumber(change.tool.pot_number);
      if (pot === null) continue;
      empty_pockets = empty_pockets.map((p) =>
        p.pot_number === pot ? { ...p, is_cap: true } : p,
      );
      continue;
    }

    if (change.cacheSlice === 'tool') {
      tools = tools.map((row) =>
        toolsMatchForSlice(change.tool, row, 'tool')
          ? applyConfirmedToolChange(row, change, result)
          : row,
      );
    } else if (change.cacheSlice === 'pocket') {
      empty_pockets = empty_pockets.map((pocket) => {
        const asTool = emptyPocketAsTool(pocket);
        if (!toolsMatchForSlice(change.tool, asTool, 'pocket')) return pocket;
        const updated = applyConfirmedToolChange(asTool, change, result);
        return {
          pot_number: pocket.pot_number,
          tool_type: updated.tool_type,
          color: updated.color,
          is_cap: updated.is_cap,
        };
      });
    } else if (change.cacheSlice === 'spindle' && spindle) {
      spindle = {
        ...spindle,
        tool_number: Number(result.tool_number ?? change.newValue),
      };
    }
  }

  empty_pockets.sort((a, b) => a.pot_number - b.pot_number);

  return {
    ...cache,
    tools: tools as UnifiedToolRow[],
    empty_pockets,
    spindle,
  };
}

function FieldValidationPopover({
  message,
  anchorRef,
}: {
  message?: string;
  anchorRef: React.RefObject<HTMLElement | null>;
}) {
  const popoverId = useId();
  const [pos, setPos] = useState<{
    top: number;
    left: number;
    transform: string;
  } | null>(null);

  useLayoutEffect(() => {
    if (!message) {
      setPos(null);
      return;
    }

    const update = () => {
      const el = anchorRef.current;
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const margin = 8;
      const popoverWidth = 240;
      const popoverHeight = 48;
      const spaceRight = window.innerWidth - rect.right;
      const spaceLeft = rect.left;
      const placeRight = spaceRight >= popoverWidth + margin || spaceRight >= spaceLeft;

      let left = placeRight ? rect.right + margin : rect.left - margin;
      let top = rect.top + rect.height / 2;
      let transform = 'translateY(-50%)';

      if (!placeRight) {
        transform = 'translate(-100%, -50%)';
      }

      if (top - popoverHeight / 2 < margin) {
        top = margin + popoverHeight / 2;
      } else if (top + popoverHeight / 2 > window.innerHeight - margin) {
        top = window.innerHeight - margin - popoverHeight / 2;
      }

      if (placeRight && left + popoverWidth > window.innerWidth - margin) {
        left = window.innerWidth - margin - popoverWidth;
      }
      if (!placeRight && left - popoverWidth < margin) {
        left = margin + popoverWidth;
        transform = 'translate(-100%, -50%)';
      }

      setPos({ top, left, transform });
    };

    update();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [message, anchorRef]);

  if (!message || !pos) return null;

  return createPortal(
    <div
      id={popoverId}
      role="alert"
      className="tools-field-popover"
      style={{
        position: 'fixed',
        top: pos.top,
        left: pos.left,
        transform: pos.transform,
        zIndex: 10000,
      }}
    >
      <span className="tools-field-popover__icon" aria-hidden>
        ⚠
      </span>
      <span className="tools-field-popover__text">{message}</span>
    </div>,
    document.body,
  );
}

function ValidatedFieldAnchor({
  warningKey,
  fieldWarnings,
  className,
  children,
}: {
  warningKey: string;
  fieldWarnings: Map<string, string>;
  className?: string;
  children: React.ReactNode;
}) {
  const anchorRef = useRef<HTMLDivElement>(null);
  const message = fieldWarnings.get(warningKey);
  const invalid = Boolean(message);

  return (
    <>
      <div
        ref={anchorRef}
        className={`${className ?? ''}${invalid ? ' tools-validated-field--invalid' : ''}`.trim()}
      >
        {children}
      </div>
      <FieldValidationPopover message={message} anchorRef={anchorRef} />
    </>
  );
}

function PotPickerPopover({
  open,
  anchorRef,
  numPockets,
  occupancy,
  toolNumber,
  currentPot,
  onSelect,
  onClose,
}: {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement | null>;
  numPockets: number;
  occupancy: Map<number, number>;
  toolNumber: number;
  currentPot: number | undefined;
  onSelect: (pot: number) => void;
  onClose: () => void;
}) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!open) {
      setPos(null);
      return;
    }

    const update = () => {
      const el = anchorRef.current;
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const margin = 8;
      const popoverWidth = 224;
      const popoverHeight = popoverRef.current?.offsetHeight ?? 160;

      let left = rect.left + rect.width / 2 - popoverWidth / 2;
      let top = rect.bottom + margin;

      if (left + popoverWidth > window.innerWidth - margin) {
        left = window.innerWidth - margin - popoverWidth;
      }
      if (left < margin) {
        left = margin;
      }

      if (top + popoverHeight > window.innerHeight - margin) {
        top = rect.top - margin - popoverHeight;
      }
      if (top < margin) {
        top = margin;
      }

      setPos({ top, left });
    };

    update();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [open, anchorRef, numPockets]);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (popoverRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, anchorRef, onClose]);

  if (!open || !pos) return null;

  const columns = numPockets <= 12 ? 4 : numPockets <= 20 ? 5 : 7;

  return createPortal(
    <div
      ref={popoverRef}
      id={popoverId}
      role="listbox"
      aria-label="Select ATC pot"
      data-testid="pot-picker-popover"
      className="tools-pot-picker-popover"
      style={{
        position: 'fixed',
        top: pos.top,
        left: pos.left,
        zIndex: 10001,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="tools-pot-picker-popover__header">SELECT POT</div>
      <div
        className="tools-pot-picker-popover__grid"
        style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
      >
        {Array.from({ length: numPockets }, (_, idx) => {
          const pot = idx + 1;
          const occupant = occupancy.get(pot);
          const isOccupied = occupant !== undefined && occupant !== toolNumber;
          const isCurrent = currentPot === pot;

          return (
            <button
              key={pot}
              type="button"
              role="option"
              data-testid={`pot-option-${pot}`}
              aria-selected={isCurrent}
              disabled={isOccupied}
              className={[
                'tools-pot-picker-option',
                isOccupied ? 'tools-pot-picker-option--occupied' : 'tools-pot-picker-option--available',
                isCurrent ? 'tools-pot-picker-option--current' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              title={
                isOccupied
                  ? `Pot ${pot} — T${String(occupant).padStart(2, '0')}`
                  : isCurrent
                    ? `Pot ${pot} (current)`
                    : `Assign to pot ${pot}`
              }
              onClick={() => {
                onSelect(pot);
                onClose();
              }}
            >
              <span className="tools-pot-picker-option__num">{pot}</span>
              {isOccupied ? (
                <span className="tools-pot-picker-option__tag">
                  T{String(occupant).padStart(2, '0')}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>,
    document.body,
  );
}

function PotAssignCell({
  tool,
  isAtcAssigned,
  potPending,
  numPockets,
  unifiedCache,
  pendingChanges,
  fieldWarnings,
  onPotNumberChange,
  onClear,
}: {
  tool: Tool;
  isAtcAssigned: boolean;
  potPending: boolean;
  numPockets: number;
  unifiedCache: UnifiedToolView;
  pendingChanges: Map<string, PendingChange>;
  fieldWarnings: Map<string, string>;
  onPotNumberChange: (tool: Tool, raw: string) => void;
  onClear: (tool: Tool) => void;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerAnchorRef = useRef<HTMLButtonElement>(null);
  const occupancy = useMemo(
    () => buildPotOccupancyMap(unifiedCache, pendingChanges),
    [unifiedCache, pendingChanges],
  );
  const currentPot = parsePotNumber(tool.pot_number);
  const currentPotNum = currentPot !== null && currentPot > 0 ? currentPot : undefined;

  return (
    <ValidatedFieldAnchor
      warningKey={potAssignWarningKey(tool.tool_number)}
      fieldWarnings={fieldWarnings}
      className="tools-pot-assign-anchor"
    >
      <div className="tools-pot-cell">
        <NumericEditInput
          className={pendingInputClass(
            potPending,
            'tools-edit-input tools-edit-input--pot-number',
          )}
          value={isAtcAssigned ? tool.pot_number : ''}
          placeholder="—"
          onValueChange={(raw) => onPotNumberChange(tool, raw)}
        />
        <button
          ref={pickerAnchorRef}
          type="button"
          className={`tools-pot-picker-btn${pickerOpen ? ' tools-pot-picker-btn--open' : ''}`}
          data-testid="pot-picker-btn"
          aria-label="Choose pot from list"
          aria-haspopup="listbox"
          aria-expanded={pickerOpen}
          title="Choose pot"
          onClick={(e) => {
            e.stopPropagation();
            setPickerOpen((prev) => !prev);
          }}
        >
          ▾
        </button>
        {isAtcAssigned ? (
          <button
            type="button"
            className="tools-clear-pot-btn"
            title="Unassign from pocket"
            aria-label="Unassign from pocket"
            onClick={(e) => {
              e.stopPropagation();
              onClear(tool);
            }}
          >
            ×
          </button>
        ) : (
          <span className="tools-clear-pot-btn tools-clear-pot-btn--spacer" aria-hidden="true" />
        )}
        <PotPickerPopover
          open={pickerOpen}
          anchorRef={pickerAnchorRef}
          numPockets={numPockets}
          occupancy={occupancy}
          toolNumber={tool.tool_number}
          currentPot={currentPotNum}
          onSelect={(pot) => onPotNumberChange(tool, String(pot))}
          onClose={() => setPickerOpen(false)}
        />
      </div>
    </ValidatedFieldAnchor>
  );
}

function pendingInputClass(pending: boolean, base = 'tools-edit-input'): string {
  return pending ? `${base} tools-edit-input--pending` : base;
}

function potAssignWarningKey(toolNumber: number): string {
  return `pot-tool-${toolNumber}`;
}

function pocketAssignWarningKey(potNumber: number): string {
  return `pocket-${potNumber}`;
}

function pendingToBatchItem(key: string, change: PendingChange): ToolChangeBatchItem | null {
  const pot = parsePotNumber(change.tool.pot_number);
  switch (change.operationType) {
    case 'color':
      if (pot === null || pot < 1) return null;
      return {
        operation_type: 'color',
        client_id: key,
        pot_number: pot,
        tool_number: change.tool.tool_number,
        color: Number(change.newValue),
      };
    case 'tool_number':
      if (pot === null || pot < 1) return null;
      return {
        operation_type: 'assignment',
        client_id: key,
        pot_number: pot,
        tool_number: Number(change.newValue),
      };
    case 'pot_number': {
      const assignPot = Number(change.newValue);
      if (!Number.isFinite(assignPot) || assignPot < 1) return null;
      return {
        operation_type: 'assignment',
        client_id: key,
        pot_number: assignPot,
        tool_number: change.tool.tool_number,
      };
    }
    case 'tool_type':
      if (pot === null || pot < 1) return null;
      return {
        operation_type: 'type',
        client_id: key,
        pot_number: pot,
        tool_type: Number(change.newValue),
      };
    case 'cap':
      if (pot === null || pot < 1) return null;
      return {
        operation_type: 'cap',
        client_id: key,
        pot_number: pot,
      };
    case 'delete':
      if (pot === null || pot < 1) return null;
      return {
        operation_type: 'delete',
        client_id: key,
        pot_number: pot,
        tool_number: change.tool.tool_number,
      };
    case 'spindle':
      return {
        operation_type: 'spindle',
        client_id: key,
        tool_number: Number(change.newValue),
      };
    case 'offset':
      return {
        operation_type: 'offset',
        client_id: key,
        tool_number: change.tool.tool_number,
        offset_type: change.field as 'H' | 'D' | 'W',
        value: Number(change.newValue),
      };
    case 'life':
      return {
        operation_type: 'life',
        client_id: key,
        tool_number: change.tool.tool_number,
        life_value: Number(change.newValue),
      };
    case 'name':
      return {
        operation_type: 'name',
        client_id: key,
        tool_number: change.tool.tool_number,
        name_value: String(change.newValue).trim().slice(0, 14),
      };
    default:
      return null;
  }
}

function getToolFieldValue(tool: Tool, field: string): string | number | undefined {
  switch (field) {
    case 'color':
      return tool.color;
    case 'tool_number':
      return tool.tool_number;
    case 'pot_number':
      return tool.pot_number;
    case 'tool_type':
      return tool.tool_type;
    case 'length':
      return tool.length;
    case 'diameter':
      return tool.diameter;
    case 'life':
      return tool.life;
    case 'tool_name':
      return tool.tool_name;
    case 'H':
      return tool.length;
    case 'D':
      return tool.diameter;
    default:
      return undefined;
  }
}

function serverConfirmsPendingChange(
  change: PendingChange,
  serverTool: Tool,
  allTools: UnifiedToolRow[],
): boolean {
  switch (change.operationType) {
    case 'delete':
      return !serverTool.in_atc;
    case 'pot_number': {
      const targetPot = Number(change.newValue);
      return Boolean(
        serverTool.in_atc && parsePotNumber(serverTool.pot_number) === targetPot,
      );
    }
    case 'tool_number':
      if (change.cacheSlice === 'pocket') {
        const targetPot = parsePotNumber(change.tool.pot_number);
        const assignedTool = Number(change.newValue);
        if (targetPot === null || !Number.isFinite(assignedTool)) return false;
        const row = allTools.find((t) => t.tool_number === assignedTool);
        return Boolean(row?.in_atc && parsePotNumber(row.pot_number) === targetPot);
      }
      return false;
    case 'cap':
      return false;
    default:
      break;
  }
  const fieldVal = getToolFieldValue(serverTool, change.field);
  return valuesEqual(fieldVal ?? '', change.newValue);
}

function mergePendingOntoUnifiedCache(
  cache: UnifiedToolView,
  pending: Map<string, PendingChange>,
): UnifiedToolView {
  return {
    ...cache,
    tools: cache.tools.map((row) =>
      mergeServerToolWithPending(unifiedRowAsTool(row), pending, 'tool') as UnifiedToolRow,
    ),
    empty_pockets: cache.empty_pockets.map((pocket) =>
      mergeServerToolWithPending(emptyPocketAsTool(pocket), pending, 'pocket') as EmptyPocket,
    ),
  };
}

function isSpindleToolRow(
  tool: Tool,
  spindleToolNumber: number | null | undefined,
): boolean {
  return spindleToolNumber != null && tool.tool_number === spindleToolNumber;
}

function getToolRowState(
  tool: Tool,
  spindleToolNumber: number | null | undefined,
  programToolNumbers: Set<number>,
): 'spindle' | 'program-atc' | 'program' | 'atc' | null {
  const inProgram = programToolNumbers.has(tool.tool_number);
  const inAtc = Boolean(tool.in_atc);

  if (isSpindleToolRow(tool, spindleToolNumber)) return 'spindle';
  if (inProgram && inAtc) return 'program-atc';
  if (inProgram) return 'program';
  if (inAtc) return 'atc';
  return null;
}

const TOOL_ROW_STATE_TITLES: Record<NonNullable<ReturnType<typeof getToolRowState>>, string> = {
  spindle: 'Tool is in the spindle',
  'program-atc': 'Used in current program and assigned to ATC',
  program: 'Used in current program (not in ATC)',
  atc: 'Assigned to ATC (not used in current program)',
};

function extractProgramToolNumbers(deploymentData: {
  deployment?: { validation_results?: { tools?: Record<string, unknown> } };
  program?: { program_metadata?: { tools?: Array<{ tool_number?: number }> } };
}): Set<number> {
  const nums = new Set<number>();

  const validationTools = deploymentData.deployment?.validation_results?.tools;
  if (validationTools) {
    Object.keys(validationTools).forEach((key) => {
      const n = parseInt(key, 10);
      if (Number.isFinite(n) && n > 0) nums.add(n);
    });
  }

  const metaTools = deploymentData.program?.program_metadata?.tools;
  if (Array.isArray(metaTools)) {
    metaTools.forEach((tool) => {
      if (tool.tool_number && tool.tool_number > 0) {
        nums.add(tool.tool_number);
      }
    });
  }

  return nums;
}

function getConfirmedValueFromResult(result: ToolChangeBatchResult): {
  field: string;
  value: string | number;
} | null {
  switch (result.operation_type) {
    case 'color':
      return result.color !== undefined ? { field: 'color', value: result.color } : null;
    case 'assignment':
      return result.tool_number !== undefined
        ? { field: 'tool_number', value: result.tool_number }
        : null;
    case 'type':
      return result.tool_type !== undefined
        ? { field: 'tool_type', value: result.tool_type }
        : null;
    case 'spindle':
      return result.tool_number !== undefined
        ? { field: 'tool_number', value: result.tool_number }
        : null;
    case 'offset':
      return result.value !== undefined && result.offset_type
        ? { field: result.offset_type, value: result.value }
        : null;
    case 'life':
      return result.life_value !== undefined
        ? { field: 'life', value: result.life_value }
        : null;
    case 'name':
      return result.name_value !== undefined
        ? { field: 'tool_name', value: result.name_value }
        : null;
    default:
      return null;
  }
}

export const ToolsPane: React.FC<ToolsPaneProps> = ({ 
  tools: initialTools, 
  toolTable: initialToolTable,
  toolsUnified: initialToolsUnified,
  currentTool, 
  machineId,
  units = 'in',
  machineStatus,
  memMode,
  memOperationStatus,
  toolsTimestamp,
  toolTableTimestamp,
  toolPollIntervalSeconds = 30,
  variant = 'default',
  programName,
  numPockets: numPocketsProp = 21,
  macros,
}) => {
  const useUnifiedView = Boolean(machineId);

  const resolvedUnifiedView = useMemo((): UnifiedToolView => {
    if (initialToolsUnified) return initialToolsUnified;
    return buildUnifiedToolViewFromLegacy(
      initialToolTable || [],
      initialTools || [],
      numPocketsProp,
    );
  }, [initialToolsUnified, initialToolTable, initialTools, numPocketsProp]);

  const [sortColumn, setSortColumn] = useState<SortColumn>('tool_number');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [searchQuery, setSearchQuery] = useState('');

  const [unifiedCache, setUnifiedCache] = useState<UnifiedToolView>(() => resolvedUnifiedView);
  const [legacyTools] = useState<Tool[]>(() => initialTools || []);

  const [cacheTimestamp, setCacheTimestamp] = useState<number | null>(null);
  const [isLoadingTools, setIsLoadingTools] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [toolsSummary, setToolsSummary] = useState<Array<{ tool_number: number; description: string }>>([]);
  const [programToolNumbers, setProgramToolNumbers] = useState<Set<number>>(() => new Set());

  // Track pending changes (changes not yet pushed to server)
  const [pendingChanges, setPendingChanges] = useState<Map<string, PendingChange>>(new Map());
  const pendingChangesRef = useRef<Map<string, PendingChange>>(pendingChanges);
  const updatePendingChanges = (
    updater: (prev: Map<string, PendingChange>) => Map<string, PendingChange>,
  ) => {
    setPendingChanges((prev) => {
      const next = updater(prev);
      pendingChangesRef.current = next;
      return next;
    });
  };
  const [isPushingChanges, setIsPushingChanges] = useState(false);
  const [pushComplete, setPushComplete] = useState(false);
  const [pushError, setPushError] = useState<string | null>(null);
  const [fieldWarnings, setFieldWarnings] = useState<Map<string, string>>(() => new Map());

  const setFieldWarning = (key: string, message: string) => {
    setFieldWarnings((prev) => {
      const next = new Map(prev);
      next.set(key, message);
      return next;
    });
  };

  const clearFieldWarning = (key: string) => {
    setFieldWarnings((prev) => {
      if (!prev.has(key)) return prev;
      const next = new Map(prev);
      next.delete(key);
      return next;
    });
  };

  // ──────────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<'tools' | 'optimizer'>('tools');
  const [toolsViewFilter, setToolsViewFilter] = useState<ToolsViewFilter>('all');

  const [measurementTool, setMeasurementTool] = useState<number | null>(null);
  const [measurementSaving, setMeasurementSaving] = useState(false);
  const [measurementError, setMeasurementError] = useState<string | null>(null);

  useEffect(() => {
    const raw = macros?.['920'];
    if (raw === undefined || raw === null || !Number.isFinite(Number(raw))) {
      return;
    }
    const parsed = Math.round(Number(raw));
    if (parsed > 0) {
      setMeasurementTool(parsed);
    }
  }, [macros]);

  // Track recently pushed items to prevent stale WebSocket data from overwriting confirmed values
  const recentlyPushedRef = useRef<Map<string, { field: string; value: string | number; timestamp: number }>>(new Map());

  const machineStateWarning = useMemo(() => {
    if (!machineStatus && memMode === undefined) return undefined;
    const status = machineStatus?.toLowerCase();
    const programActive =
      memOperationStatus !== undefined && memOperationStatus !== 0;
    if (status === 'operating' && programActive) {
      return 'Machine reports operating — push may be rejected by the control.';
    }
    if (memMode === 2 && programActive) {
      return 'Program operation in progress — push may be rejected by the control.';
    }
    if (memMode === 3 || memMode === 4 || memMode === 5) {
      return 'Machine is in edit mode — exit edit mode before pushing ATC changes.';
    }
    return undefined;
  }, [machineStatus, memMode, memOperationStatus]);

  const toolsDataLastUpdatedAt = useMemo(() => {
    const wsAt = toolsTimestamp || toolTableTimestamp;
    if (wsAt) return wsAt;
    return cacheTimestamp != null ? cacheTimestamp : null;
  }, [toolsTimestamp, toolTableTimestamp, cacheTimestamp]);

  const toolExpectedIntervalMs = Math.max((toolPollIntervalSeconds ?? 30) * 1000, 5000);

  const toolsAgeMs = useMemo(() => {
    if (!toolsDataLastUpdatedAt) return null;
    const parsed = typeof toolsDataLastUpdatedAt === 'number'
      ? toolsDataLastUpdatedAt
      : Date.parse(String(toolsDataLastUpdatedAt));
    if (!Number.isFinite(parsed)) return null;
    return Math.max(0, Date.now() - parsed);
  }, [toolsDataLastUpdatedAt]);

  const visibleToolsCount = useUnifiedView
    ? unifiedCache.tools.length
    : legacyTools.length;

  const isToolsSnapshotStale = useMemo(() => {
    if (visibleToolsCount === 0) return false;
    if (toolsAgeMs === null) return true;
    return toolsAgeMs > toolExpectedIntervalMs * 2;
  }, [visibleToolsCount, toolsAgeMs, toolExpectedIntervalMs]);

  const formatToolsAge = useMemo(() => {
    if (toolsAgeMs === null) return 'unknown age';
    const secs = Math.floor(toolsAgeMs / 1000);
    if (secs < 60) return `${secs}s old`;
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return `${mins}m ${rem}s old`;
  }, [toolsAgeMs]);
  
  const tools = useUnifiedView
    ? unifiedCache.tools.map(unifiedRowAsTool)
    : legacyTools;
  const currentError = toolsError;
  
  // Update unified cache when WebSocket data arrives
  useEffect(() => {
    if (!useUnifiedView) return;

    const hasData =
      (initialToolsUnified && initialToolsUnified.tools.length > 0) ||
      (initialToolTable && initialToolTable.length > 0) ||
      (initialTools && initialTools.length > 0);

    if (!hasData) return;

    const incoming = resolvedUnifiedView;

    setUnifiedCache(() => {
      if (isPushingChanges) {
        return {
          ...incoming,
          tools: incoming.tools.map((serverTool) =>
            mergeServerToolWithPending(
              unifiedRowAsTool(serverTool),
              pendingChanges,
              'tool',
            ) as UnifiedToolRow,
          ),
          empty_pockets: incoming.empty_pockets.map((pocket) =>
            mergeServerToolWithPending(
              emptyPocketAsTool(pocket),
              pendingChanges,
              'pocket',
            ) as EmptyPocket,
          ),
        };
      }

      const mergedTools = incoming.tools.map((serverTool) => {
        const asTool = unifiedRowAsTool(serverTool);
        const pendingMerged = mergeServerToolWithPending(asTool, pendingChanges, 'tool');
        const trackKey = `${serverTool.tool_number}-tool`;
        const recentlyPushed = recentlyPushedRef.current.get(trackKey);
        if (recentlyPushed) {
          const serverVal = getToolFieldValue(asTool, recentlyPushed.field);
          const matches =
            recentlyPushed.field === 'pot_number'
              ? potsEqual(serverVal, recentlyPushed.value)
              : serverVal === recentlyPushed.value;
          if (matches) {
            recentlyPushedRef.current.delete(trackKey);
            return pendingMerged as UnifiedToolRow;
          }
          return applyFieldToTool(pendingMerged, recentlyPushed.field, recentlyPushed.value) as UnifiedToolRow;
        }
        return pendingMerged as UnifiedToolRow;
      });

      const mergedPockets = incoming.empty_pockets.map((pocket) => {
        const asTool = emptyPocketAsTool(pocket);
        return mergeServerToolWithPending(asTool, pendingChanges, 'pocket') as EmptyPocket;
      });

      return {
        ...incoming,
        tools: mergedTools,
        empty_pockets: mergedPockets,
        spindle: incoming.spindle,
      };
    });

    setCacheTimestamp(Date.now());
    setToolsError(null);

    if (!isPushingChanges) {
      updatePendingChanges((prev) => {
        const next = new Map(prev);
        incoming.tools.forEach((serverTool) => {
          const asTool = unifiedRowAsTool(serverTool);
          next.forEach((change, key) => {
            if (change.cacheSlice !== 'tool') return;
            if (change.tool.tool_number !== asTool.tool_number) return;
            if (serverConfirmsPendingChange(change, asTool, incoming.tools)) {
              next.delete(key);
            }
          });
        });
        incoming.empty_pockets.forEach((pocket) => {
          const asTool = emptyPocketAsTool(pocket);
          next.forEach((change, key) => {
            if (change.cacheSlice !== 'pocket') return;
            if (!potsEqual(change.tool.pot_number, asTool.pot_number)) return;
            if (serverConfirmsPendingChange(change, asTool, incoming.tools)) {
              next.delete(key);
            }
          });
        });
        return next;
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedUnifiedView, useUnifiedView, machineId, isPushingChanges]);
  const navigate = useNavigate();
  const { isBetaMode } = useBetaMode();
  const [toolsColorMode, setToolsColorMode] = useState<boolean>(() => {
    return localStorage.getItem('toolsPaneColorMode') === 'true';
  });

  useEffect(() => {
    localStorage.setItem('toolsPaneColorMode', String(toolsColorMode));
  }, [toolsColorMode]);

  // Fetch tools summary for matching (only if beta mode is enabled)
  useEffect(() => {
    if (isBetaMode) {
      fetch(`${API_BASE_URL}/api/tools/summary`)
        .then(res => res.json())
        .then(data => {
          if (data.tools) {
            setToolsSummary(data.tools);
          }
        })
        .catch(err => {
          console.error('Error fetching tools summary:', err);
        });
    } else {
      setToolsSummary([]);
    }
  }, [isBetaMode]);

  useEffect(() => {
    if (!machineId || !programName) {
      setProgramToolNumbers(new Set());
      return;
    }

    fetch(
      `${API_BASE_URL}/api/programs/machines/${machineId}/deployments/by-onumber/${encodeURIComponent(programName)}?include_program=true`,
    )
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setProgramToolNumbers(extractProgramToolNumbers(data));
        } else {
          setProgramToolNumbers(new Set());
        }
      })
      .catch(() => setProgramToolNumbers(new Set()));
  }, [machineId, programName]);

  useEffect(() => {
    if (!machineId || !useUnifiedView) return;

    const now = Date.now();
    const STALE_THRESHOLD = 60000;
    const needsFetch = cacheTimestamp && (now - cacheTimestamp) > STALE_THRESHOLD;

    if (needsFetch) {
      setIsLoadingTools(true);
      fetch(`${API_BASE_URL}/api/machines/${machineId}/tools?source=atc`)
        .then((res) => {
          if (!res.ok) {
            return res.json().then((errData) => {
              const errorMsg = errData.detail || `HTTP ${res.status}: ${res.statusText}`;
              if (res.status === 503) {
                throw new Error(
                  `Machine temporarily unavailable: ${errorMsg}. The machine may be busy or Telnet port 10000 may be blocked. Please try again in a moment.`,
                );
              }
              throw new Error(errorMsg);
            });
          }
          return res.json();
        })
        .then((data) => {
          if (data?.tools_unified) {
            setUnifiedCache(data.tools_unified);
          } else if (data?.tools) {
            setUnifiedCache(buildUnifiedToolViewFromLegacy(data.tool_table || [], data.tools));
          }
          setCacheTimestamp(Date.now());
          setToolsError(null);
          setIsLoadingTools(false);
        })
        .catch((err) => {
          console.error('Error fetching tools data:', err);
          setToolsError(err instanceof Error ? err.message : 'Failed to fetch tools data');
          setIsLoadingTools(false);
        });
    } else {
      setIsLoadingTools(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machineId, useUnifiedView, cacheTimestamp]);


  const formatLife = (value: number | string | undefined) => {
    if (value === undefined || value === null) return '──';
    // Handle both string and number (in case backend hasn't updated yet)
    let numValue: number;
    if (typeof value === 'string') {
      // Extract first number from string (handles "9952mi9952" -> 9952)
      const match = value.match(/(\d+)/);
      if (!match) return '──';
      numValue = parseInt(match[1], 10);
      if (isNaN(numValue)) return '──';
    } else {
      numValue = value;
    }
    return `${numValue}`;
  };

  const formatToolType = (value: number | undefined) => {
    if (value === undefined || value === null) return '──';
    switch (value) {
      case 1:
        return 'STD';
      case 2:
        return 'LARGE';
      case 3:
        return 'MED';
      default:
        return String(value);
    }
  };

  const stagePendingChange = (
    tool: Tool,
    field: string,
    oldValue: string | number,
    newValue: string | number,
    operationType: ToolModificationOperationType,
    cacheSlice: PendingChange['cacheSlice'],
  ) => {
    const changeKey = makePendingKey(tool, field, operationType);

    updatePendingChanges((prev) => {
      const existing = prev.get(changeKey);
      const baseline = existing?.oldValue ?? oldValue;

      const applyToTool = (t: Tool): Tool => {
        if (operationType === 'delete') {
          return applyAssignmentEdge(t, 'tool_number', 0);
        }
        if (operationType === 'cap') {
          return { ...t, tool_number: 0, is_cap: true };
        }
        if (operationType === 'tool_number' && cacheSlice === 'pocket') {
          return { ...applyFieldToTool(t, field, newValue), is_cap: false };
        }
        if (cacheSlice === 'tool' && (field === 'pot_number' || field === 'tool_number')) {
          return applyAssignmentEdge(t, field, newValue);
        }
        return applyFieldToTool(t, field, newValue);
      };

      const revertTool = (t: Tool): Tool => {
        if (operationType === 'delete') {
          return restoreAtcAssignment(t, tool);
        }
        if (operationType === 'cap') {
          return { ...t, is_cap: Boolean(baseline) };
        }
        if (cacheSlice === 'tool' && (field === 'pot_number' || field === 'tool_number')) {
          return applyAssignmentEdge(t, field, baseline);
        }
        return applyFieldToTool(t, field, baseline);
      };

      if (valuesEqual(newValue, baseline)) {
        const next = new Map(prev);
        next.delete(changeKey);
        if (useUnifiedView) {
          setUnifiedCache((cachePrev) => {
            if (cacheSlice === 'tool') {
              return {
                ...cachePrev,
                tools: cachePrev.tools.map((row) => {
                  const asTool = unifiedRowAsTool(row);
                  if (!toolsMatchForSlice(asTool, tool, 'tool')) return row;
                  return revertTool(asTool) as UnifiedToolRow;
                }),
              };
            }
            if (cacheSlice === 'pocket') {
              return {
                ...cachePrev,
                empty_pockets: cachePrev.empty_pockets.map((pocket) => {
                  const asTool = emptyPocketAsTool(pocket);
                  if (!toolsMatchForSlice(asTool, tool, 'pocket')) return pocket;
                  const reverted = revertTool(asTool);
                  return {
                    pot_number: pocket.pot_number,
                    tool_type: reverted.tool_type,
                    color: reverted.color,
                    is_cap: reverted.is_cap,
                  };
                }),
              };
            }
            return cachePrev;
          });
        }
        return next;
      }

      const next = new Map(prev);
      next.set(changeKey, {
        tool,
        field,
        oldValue: baseline,
        newValue,
        operationType,
        cacheSlice,
      });

      if (useUnifiedView) {
        setUnifiedCache((cachePrev) => {
          if (cacheSlice === 'tool') {
            return {
              ...cachePrev,
              tools: cachePrev.tools.map((row) => {
                const asTool = unifiedRowAsTool(row);
                if (!toolsMatchForSlice(asTool, tool, 'tool')) return row;
                return applyToTool(asTool) as UnifiedToolRow;
              }),
            };
          }
          if (cacheSlice === 'pocket') {
            return {
              ...cachePrev,
              empty_pockets: cachePrev.empty_pockets.map((pocket) => {
                const asTool = emptyPocketAsTool(pocket);
                if (!toolsMatchForSlice(asTool, tool, 'pocket')) return pocket;
                const updated = applyToTool(asTool);
                return {
                  pot_number: pocket.pot_number,
                  tool_type: updated.tool_type,
                  color: updated.color,
                  is_cap: updated.is_cap,
                };
              }),
            };
          }
          if (cacheSlice === 'spindle' && cachePrev.spindle) {
            return {
              ...cachePrev,
              spindle: {
                ...cachePrev.spindle,
                tool_number: Number(newValue),
              },
            };
          }
          return cachePrev;
        });
      }

      return next;
    });
  };

  const handleColorChange = (tool: Tool, newColor: number) => {
    if (!machineId || !tool.pot_number || !tool.in_atc) return;
    stagePendingChange(tool, 'color', tool.color ?? 0, newColor, 'color', 'tool');
  };

  const handleToolNumberChange = (tool: Tool, raw: string, cacheSlice: 'spindle' | 'pocket') => {
    if (!machineId) return;
    const parsed = parseInt(raw, 10);
    if (!Number.isFinite(parsed)) return;

    if (cacheSlice === 'spindle' || isSpindlePot(tool.pot_number)) {
      stagePendingChange(tool, 'tool_number', tool.tool_number, parsed, 'spindle', 'spindle');
      return;
    }

    if (cacheSlice === 'pocket') {
      const pot = parsePotNumber(tool.pot_number);
      if (pot === null || pot < 1) return;

      const pending = pendingChangesRef.current;

      if (parsed === 0) {
        const occupant = getPotOccupantTool(unifiedCache, pending, pot);
        if (occupant != null) {
          setFieldWarning(
            pocketAssignWarningKey(pot),
            `Pot ${pot} in use (T${String(occupant).padStart(2, '0')}) — clear first`,
          );
          return;
        }
        clearFieldWarning(pocketAssignWarningKey(pot));
        stagePendingChange(tool, 'is_cap', tool.is_cap ? 1 : 0, 1, 'cap', 'pocket');
        return;
      }

      if (parsed < 1 || parsed > 999) return;

      const potOccupant = getPotOccupantTool(unifiedCache, pending, pot);
      if (potOccupant != null) {
        setFieldWarning(
          pocketAssignWarningKey(pot),
          `Pot ${pot} in use (T${String(potOccupant).padStart(2, '0')}) — clear first`,
        );
        return;
      }

      const existingPot = findToolPotAssignment(unifiedCache, pending, parsed);
      if (existingPot != null && existingPot !== pot) {
        setFieldWarning(
          pocketAssignWarningKey(pot),
          `T${String(parsed).padStart(2, '0')} already in pot ${existingPot} — clear first`,
        );
        return;
      }

      clearFieldWarning(pocketAssignWarningKey(pot));
      stagePendingChange(tool, 'tool_number', tool.tool_number, parsed, 'tool_number', 'pocket');
    }
  };

  const handlePotNumberChange = (tool: Tool, raw: string) => {
    if (!machineId || !tool.tool_number) return;
    const trimmed = raw.trim();
    const warningKey = potAssignWarningKey(tool.tool_number);
    if (trimmed === '') {
      clearFieldWarning(warningKey);
      return;
    }
    const parsed = parseInt(trimmed, 10);
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > numPocketsProp) return;

    const occupant = getPotOccupantTool(
      unifiedCache,
      pendingChangesRef.current,
      parsed,
      tool.tool_number,
    );
    if (occupant != null) {
      setFieldWarning(
        warningKey,
        `Pot ${parsed} in use (T${String(occupant).padStart(2, '0')}) — clear first`,
      );
      return;
    }

    clearFieldWarning(warningKey);
    stagePendingChange(
      tool,
      'pot_number',
      tool.pot_number ?? '',
      parsed,
      'pot_number',
      'tool',
    );
  };

  const handleToolTypeChange = (tool: Tool, raw: string) => {
    if (!machineId || !tool.pot_number || !tool.in_atc || isSpindlePot(tool.pot_number)) return;
    const parsed = parseInt(raw, 10);
    if (![1, 2, 3].includes(parsed)) return;
    stagePendingChange(tool, 'tool_type', tool.tool_type ?? 1, parsed, 'tool_type', 'tool');
  };

  const handleDeleteFromPot = (tool: Tool) => {
    if (!machineId || !tool.pot_number || isSpindlePot(tool.pot_number) || !tool.in_atc) return;
    if (!tool.tool_number) return;
    stagePendingChange(tool, 'tool_number', tool.tool_number, 0, 'delete', 'tool');
  };

  const handleOffsetChange = (tool: Tool, offsetType: 'H' | 'D', raw: string) => {
    if (!machineId) return;
    const parsed = parseFloat(raw);
    if (!Number.isFinite(parsed)) return;
    const oldValue = offsetType === 'H' ? (tool.length ?? 0) : (tool.diameter ?? 0);
    stagePendingChange(tool, offsetType, oldValue, parsed, 'offset', 'tool');
  };

  const handleLifeChange = (tool: Tool, raw: string) => {
    if (!machineId) return;
    const parsed = parseInt(raw, 10);
    if (!Number.isFinite(parsed) || parsed < 0) return;
    stagePendingChange(tool, 'life', tool.life ?? 0, parsed, 'life', 'tool');
  };

  const handleNameChange = (tool: Tool, raw: string) => {
    if (!machineId) return;
    const trimmed = raw.trim().slice(0, 14);
    const oldName = (tool.tool_name ?? '').trimEnd();
    stagePendingChange(tool, 'tool_name', oldName, trimmed, 'name', 'tool');
  };

  const toolHasPending = (tool: Tool, slice?: PendingChange['cacheSlice']): boolean =>
    Array.from(pendingChanges.values()).some(
      (c) =>
        (slice ? c.cacheSlice === slice : true) &&
        toolsMatchForSlice(c.tool, tool, c.cacheSlice),
    );

  const isToolFieldPending = (
    tool: Tool,
    cacheSlice: PendingChange['cacheSlice'],
    match: (change: PendingChange) => boolean,
  ): boolean =>
    Array.from(pendingChanges.values()).some(
      (c) =>
        c.cacheSlice === cacheSlice &&
        toolsMatchForSlice(c.tool, tool, cacheSlice) &&
        match(c),
    );

  const getColorInfo = (value: number | undefined): { name: string; hex: string } => {
    if (value === undefined || value === null) {
      return { name: '──', hex: '#666666' };
    }
    switch (value) {
      case 0:
        return { name: 'NONE', hex: '#666666' };
      case 1:
        return { name: 'BLUE', hex: '#0066ff' };
      case 2:
        return { name: 'RED', hex: '#ff0000' };
      case 3:
        return { name: 'PURPLE', hex: '#9900ff' };
      case 4:
        return { name: 'GREEN', hex: '#00ff00' };
      case 5:
        return { name: 'LT BLUE', hex: '#00ccff' };
      case 6:
        return { name: 'YELLOW', hex: '#ffff00' };
      case 7:
        return { name: 'WHITE', hex: '#ffffff' };
      default:
        return { name: String(value), hex: '#666666' };
    }
  };

  const getToolDisplayName = (tool: Tool) => {
    return (tool.tool_name ?? '').trimEnd();
  };

  /** Beta row tint: 0–7 matching ColorSelect / getColorInfo. */
  const getToolColorClassIndex = (tool: Tool): number => {
    const c = tool.color;
    if (c === undefined || c === null || !Number.isFinite(Number(c))) return 0;
    const n = Math.floor(Number(c));
    if (n < 0 || n > 7) return 0;
    return n;
  };

  const handleMeasurementToolSelect = async (tool: Tool) => {
    if (!machineId || !tool.tool_number) return;
    if (measurementTool === tool.tool_number || measurementSaving) {
      return;
    }

    setMeasurementSaving(true);
    setMeasurementError(null);
    const previous = measurementTool;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/machines/${machineId}/tools/measurement-tool?tool_number=${tool.tool_number}`,
        { method: 'PUT' }
      );

      if (!response.ok) {
        const error = await response.json();
        const detail = error.detail;
        const message =
          typeof detail === 'string'
            ? detail
            : detail?.message || 'Failed to set measurement tool';
        throw new Error(message);
      }

      const data = await response.json();
      const verified = data.verified_value ?? data.tool_number;
      setMeasurementTool(Math.round(Number(verified)));
    } catch (err) {
      setMeasurementTool(previous ?? null);
      setMeasurementError(err instanceof Error ? err.message : 'Failed to set measurement tool');
    } finally {
      setMeasurementSaving(false);
    }
  };

  const handlePushChanges = async () => {
    if (pendingChangesRef.current.size === 0 || !machineId || isPushingChanges) {
      return;
    }

    if (document.activeElement instanceof HTMLInputElement) {
      document.activeElement.blur();
    }

    setIsPushingChanges(true);
    setPushComplete(false);
    setPushError(null);

    try {
      const entries = Array.from(pendingChangesRef.current.entries());
      const changes: ToolChangeBatchItem[] = [];
      for (const [key, change] of entries) {
        const item = pendingToBatchItem(key, change);
        if (item) changes.push(item);
      }

      if (changes.length === 0) {
        throw new Error('No valid changes to push');
      }

      const batchResponse = await fetch(
        `${API_BASE_URL}/api/machines/${machineId}/tools/changes/batch`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ changes }),
        },
      );

      if (!batchResponse.ok) {
        const error = await batchResponse.json();
        const detail = error.detail;
        const message =
          typeof detail === 'string'
            ? detail
            : detail?.message || 'Batch operation failed';
        setPushError(message);
        return;
      }

      const batchData = await batchResponse.json();
      const results: ToolChangeBatchResult[] = batchData.results || [];
      const successes = results.filter((r) => r.success);
      const failures = results.filter((r) => !r.success);
      const pendingSnapshot = new Map(pendingChangesRef.current);

      if (successes.length > 0) {
        setUnifiedCache((prev) =>
          reconcileUnifiedCacheAfterBatch(prev, successes, pendingSnapshot),
        );

        updatePendingChanges((prev) => {
          const next = new Map(prev);
          successes.forEach((result) => {
            if (result.client_id) next.delete(result.client_id);
          });
          return next;
        });

        recentlyPushedRef.current.clear();

        const freshCache = await loadUnifiedToolsCache(machineId);
        if (freshCache) {
          setUnifiedCache(mergePendingOntoUnifiedCache(freshCache, pendingChangesRef.current));
          setCacheTimestamp(Date.now());
        }
      }

      if (failures.length > 0) {
        setPushError(
          failures.map((f) => f.message || `${f.operation_type} failed`).join('; '),
        );
      } else if (successes.length > 0) {
        setPushComplete(true);
        setTimeout(() => setPushComplete(false), 1500);
      } else {
        setPushError('No changes were applied.');
      }
    } catch (error) {
      console.error('Error pushing changes:', error);
      setPushError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsPushingChanges(false);
    }
  };

  const handleDiscardChanges = () => {
    if (pendingChanges.size === 0) return;
    setFieldWarnings(new Map());
    setPushError(null);

    setUnifiedCache((prev) => {
      let tools = [...prev.tools];
      let empty_pockets = [...prev.empty_pockets];
      let spindle = prev.spindle;

      pendingChanges.forEach((change) => {
        const revert = (t: Tool): Tool => {
          if (change.operationType === 'delete') {
            return restoreAtcAssignment(t, change.tool);
          }
          if (change.cacheSlice === 'tool' && (change.field === 'pot_number' || change.field === 'tool_number')) {
            return applyAssignmentEdge(t, change.field, change.oldValue);
          }
          return applyFieldToTool(t, change.field, change.oldValue);
        };

        if (change.cacheSlice === 'tool') {
          tools = tools.map((row) => {
            const asTool = unifiedRowAsTool(row);
            return toolsMatchForSlice(change.tool, asTool, 'tool')
              ? (revert(asTool) as UnifiedToolRow)
              : row;
          });
        } else if (change.cacheSlice === 'pocket') {
          empty_pockets = empty_pockets.map((pocket) => {
            const asTool = emptyPocketAsTool(pocket);
            if (!toolsMatchForSlice(change.tool, asTool, 'pocket')) return pocket;
            const reverted = revert(asTool);
            return {
              pot_number: pocket.pot_number,
              tool_type: reverted.tool_type,
              color: reverted.color,
            };
          });
        } else if (change.cacheSlice === 'spindle' && spindle) {
          spindle = {
            ...spindle,
            tool_number: Number(change.oldValue),
          };
        }
      });

      return { ...prev, tools, empty_pockets, spindle };
    });

    updatePendingChanges(() => new Map());
  };

  const actualPotMap = useMemo(() => {
    const map = new Map<number, number>();
    unifiedCache.tools.forEach((tool) => {
      if (tool.in_atc && tool.pot_number != null) {
        const pot = Number(tool.pot_number);
        if (tool.tool_number && !Number.isNaN(pot)) {
          map.set(tool.tool_number, pot);
        }
      }
    });
    return map;
  }, [unifiedCache.tools]);

  const handleTabClick = (tab: 'tools' | 'optimizer', e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveTab(tab);
  };

  const handleViewFilterClick = (filter: ToolsViewFilter, e: React.MouseEvent) => {
    e.stopPropagation();
    setToolsViewFilter(filter);
    if (filter === 'empty' || filter === 'atc') {
      setSortColumn('pot_number');
      setSortDirection('asc');
    } else {
      setSortColumn('tool_number');
      setSortDirection('asc');
    }
  };

  const atcAssignedCount = useMemo(
    () => tools.filter((t) => t.in_atc).length,
    [tools],
  );

  const emptyPocketCount = unifiedCache.empty_pockets.length;

  const spindleToolNumber = unifiedCache.spindle?.tool_number ?? null;

  const getToolRowStateClass = (tool: Tool): string => {
    const state = getToolRowState(tool, spindleToolNumber, programToolNumbers);
    return state ? `tools-state-${state}` : '';
  };

  const getToolRowStateTitle = (tool: Tool): string | undefined => {
    const state = getToolRowState(tool, spindleToolNumber, programToolNumbers);
    return state ? TOOL_ROW_STATE_TITLES[state] : undefined;
  };

  const isCurrentTool = (toolNum: number) => {
    return currentTool !== undefined && currentTool === toolNum;
  };

  // Check if tool exists in tools table (by name match or tool number)
  const getMatchedTool = (tool: Tool) => {
    // Try to match by tool name (case-insensitive) if available
    if (tool.tool_name) {
      const matched = toolsSummary.find(t => 
        t.description && 
        t.description.toLowerCase().trim() === tool.tool_name!.toLowerCase().trim()
      );
      
      if (matched) return matched;
    }
    
    // Fallback: match by tool number
    return toolsSummary.find(t => t.tool_number === tool.tool_number) || null;
  };

  const handleToolClick = (tool: Tool, e: React.MouseEvent) => {
    e.stopPropagation();
    const matched = getMatchedTool(tool);
    if (matched) {
      navigate(`/tools?tool=${matched.tool_number}`);
    }
  };

  const handleRowClick = (tool: Tool, e: React.MouseEvent) => {
    e.stopPropagation();
    const matched = getMatchedTool(tool);
    if (matched && isBetaMode) {
      handleToolClick(tool, e);
    }
  };

  // Filter and sort tools
  const filteredAndSortedTools = useMemo(() => {
    let filtered = tools.map((tool) =>
      mergeServerToolWithPending(tool, pendingChanges, 'tool'),
    );

    if (toolsViewFilter === 'atc') {
      filtered = filtered.filter((tool) => tool.in_atc);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter((tool) => (
        String(tool.tool_number).includes(query) ||
        (tool.tool_name && tool.tool_name.toLowerCase().includes(query)) ||
        (tool.pot_number && String(tool.pot_number).toLowerCase().includes(query)) ||
        (tool.group && String(tool.group).toLowerCase().includes(query)) ||
        (tool.tool_type !== undefined && formatToolType(tool.tool_type).toLowerCase().includes(query)) ||
        (tool.color !== undefined && getColorInfo(tool.color).name.toLowerCase().includes(query)) ||
        (tool.life !== undefined && String(tool.life).includes(query))
      ));
    }

    const sorted = [...filtered].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      switch (sortColumn) {
        case 'pot_number':
          // Numeric sorting for pot numbers (handle string "SPINDLE" and numeric values)
          if (a.pot_number === undefined || a.pot_number === null) {
            aVal = Infinity; // Put undefined/null at end
          } else if (typeof a.pot_number === 'string' && a.pot_number.toUpperCase() === 'SPINDLE') {
            aVal = -1; // Put SPINDLE at beginning
          } else {
            aVal = typeof a.pot_number === 'number' ? a.pot_number : parseFloat(String(a.pot_number)) || Infinity;
          }
          if (b.pot_number === undefined || b.pot_number === null) {
            bVal = Infinity;
          } else if (typeof b.pot_number === 'string' && b.pot_number.toUpperCase() === 'SPINDLE') {
            bVal = -1;
          } else {
            bVal = typeof b.pot_number === 'number' ? b.pot_number : parseFloat(String(b.pot_number)) || Infinity;
          }
          break;
        case 'tool_number':
          aVal = a.tool_number;
          bVal = b.tool_number;
          break;
        case 'tool_name':
          aVal = getToolDisplayName(a).toLowerCase();
          bVal = getToolDisplayName(b).toLowerCase();
          break;
        case 'diameter':
          aVal = a.diameter || 0;
          bVal = b.diameter || 0;
          break;
        case 'length':
          aVal = a.length || 0;
          bVal = b.length || 0;
          break;
        case 'group':
          aVal = a.group ? String(a.group) : '';
          bVal = b.group ? String(b.group) : '';
          break;
        case 'life':
          aVal = a.life !== undefined && a.life !== null ? a.life : -1;
          bVal = b.life !== undefined && b.life !== null ? b.life : -1;
          break;
        case 'tool_type':
          aVal = a.tool_type !== undefined && a.tool_type !== null ? a.tool_type : -1;
          bVal = b.tool_type !== undefined && b.tool_type !== null ? b.tool_type : -1;
          break;
        case 'color':
          aVal = a.color !== undefined && a.color !== null ? a.color : -1;
          bVal = b.color !== undefined && b.color !== null ? b.color : -1;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [tools, toolsViewFilter, searchQuery, sortColumn, sortDirection, pendingChanges]);

  const filteredAndSortedEmptyPockets = useMemo(() => {
    if (!useUnifiedView || !unifiedCache.atc_available) return [];

    let items = unifiedCache.empty_pockets.map((pocket) => {
      const asTool = emptyPocketAsTool(pocket);
      const merged = mergeServerToolWithPending(asTool, pendingChanges, 'pocket');
      const assignedToolNumber = merged.is_cap ? 0 : merged.tool_number;
      const assignedTool = isRealAtcToolNumber(assignedToolNumber)
        ? findToolTableEntry(unifiedCache, pendingChanges, assignedToolNumber)
        : undefined;
      return { pocket, merged, assignedTool };
    });

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      items = items.filter(({ pocket }) => String(pocket.pot_number).includes(query));
    }

    return [...items].sort((a, b) => {
      const cmp = a.pocket.pot_number - b.pocket.pot_number;
      return sortDirection === 'asc' ? cmp : -cmp;
    });
  }, [
    useUnifiedView,
    unifiedCache.empty_pockets,
    unifiedCache.atc_available,
    searchQuery,
    sortDirection,
    pendingChanges,
  ]);

  const showingEmptyPots = toolsViewFilter === 'empty' && activeTab === 'tools';
  const visibleRows = showingEmptyPots ? filteredAndSortedEmptyPockets : filteredAndSortedTools;
  const visibleCount = visibleRows.length;

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const toolsListTitleMid =
    activeTab === 'optimizer'
      ? `OPTIMIZER${programName ? ` ─ ${programName}` : ''}`
      : toolsViewFilter === 'atc'
        ? `ATC (${atcAssignedCount})`
        : toolsViewFilter === 'empty'
          ? `EMPTY POTS (${emptyPocketCount})`
          : `TOOLS (${tools.length})`;
  /** Long run clipped by flex so header rule length matches pane width for any label. */
  const terminalRuleFill = '─'.repeat(320);

  const isHoverPreview = variant === 'hover';

  return (
    <div 
      className={`tools-pane terminal-box${isHoverPreview ? ' tools-pane--hover-preview' : ''}`}
      onClick={(e) => e.stopPropagation()}
    >
      <div 
        className="terminal-box-header"
      >
        <div className="terminal-box-top">
          <div className="terminal-box-title-row tools-pane-title-row">
            <span className="tools-pane-title-label">┌─ {toolsListTitleMid}</span>
            <span className="tools-pane-title-dash-fill" aria-hidden>
              {terminalRuleFill}
            </span>
            <div className="pane-header-right-actions tools-pane-header-actions">
              {!isHoverPreview && (
                <PollingStatusLight
                  lastUpdatedAt={toolsDataLastUpdatedAt}
                  expectedIntervalMs={toolExpectedIntervalMs}
                  ariaLabel="Tools data freshness"
                />
              )}
              {!isHoverPreview && isToolsSnapshotStale && activeTab !== 'optimizer' && (
                <span
                  className="tools-stale-chip"
                  title={`Visible tools are stale (${formatToolsAge}). Validation uses backend live data.`}
                >
                  STALE SNAPSHOT
                </span>
              )}
              {!isHoverPreview && isBetaMode && (
                <button
                  type="button"
                  className={`tools-color-toggle ${toolsColorMode ? 'active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setToolsColorMode((prev) => !prev);
                  }}
                  title="Tint rows by tool color (matches COLOR column)"
                >
                  [COLOR]
                </button>
              )}
              {machineId && (
                <div className="tools-source-toggle" onClick={(e) => e.stopPropagation()}>
                  {!isHoverPreview && activeTab === 'tools' && (
                    <>
                      <button
                        className={`source-toggle-btn ${toolsViewFilter === 'all' ? 'active' : ''}`}
                        onClick={(e) => handleViewFilterClick('all', e)}
                        title="All tool table entries"
                      >
                        ALL
                      </button>
                      <button
                        className={`source-toggle-btn ${toolsViewFilter === 'atc' ? 'active' : ''}`}
                        onClick={(e) => handleViewFilterClick('atc', e)}
                        title="Tools assigned to ATC pockets"
                      >
                        IN ATC
                      </button>
                      <button
                        className={`source-toggle-btn ${toolsViewFilter === 'empty' ? 'active' : ''}`}
                        onClick={(e) => handleViewFilterClick('empty', e)}
                        title="Empty ATC pockets"
                      >
                        EMPTY
                      </button>
                    </>
                  )}
                  {!isHoverPreview && activeTab === 'optimizer' && (
                    <button
                      className="source-toggle-btn"
                      onClick={(e) => handleTabClick('tools', e)}
                      title="Tool table"
                    >
                      TOOLS
                    </button>
                  )}
                  {!isHoverPreview && (
                    <button
                      className={`source-toggle-btn ${activeTab === 'optimizer' ? 'active' : ''}`}
                      onClick={(e) => handleTabClick('optimizer', e)}
                      title="ATC Pot Optimizer"
                    >
                      OPTIMIZER
                    </button>
                  )}
                </div>
              )}
              {pendingChanges.size > 0 && (
                <div className="tools-pending-actions" onClick={(e) => e.stopPropagation()}>
                  <span className="tools-pending-hint" title="Table edits are local until you push">
                    LOCAL ({pendingChanges.size})
                  </span>
                  <button
                    className="tools-action-btn tools-discard-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDiscardChanges();
                    }}
                    disabled={isPushingChanges}
                    title="Discard all pending changes"
                  >
                    DISCARD ({pendingChanges.size})
                  </button>
                  <button
                    className={`tools-action-btn tools-push-btn ${isPushingChanges ? 'pushing' : ''} ${pushComplete ? 'complete' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePushChanges();
                    }}
                    disabled={isPushingChanges}
                    title={
                      machineStateWarning
                        ? machineStateWarning
                        : 'Push all pending changes to machine'
                    }
                  >
                    {pushComplete
                      ? '✓ PUSHED'
                      : isPushingChanges
                      ? 'PUSHING...'
                      : `PUSH (${pendingChanges.size})`}
                  </button>
                </div>
              )}
              <span>┐</span>
            </div>
          </div>
        </div>
      </div>
      <div className="terminal-box-content">
        {activeTab === 'optimizer' ? (
          <div className="tools-pane-content-inner">
            <ToolsOptimizerTab
              machineId={machineId}
              programName={programName}
              numPockets={numPocketsProp}
              actualPotMap={actualPotMap}
            />
          </div>
        ) : tools.length === 0 && !showingEmptyPots && !isLoadingTools && !currentError ? (
          <div className="tools-empty">NO TOOLS LOADED</div>
        ) : showingEmptyPots && !unifiedCache.atc_available && !isLoadingTools ? (
          <div className="tools-empty">ATC UNAVAILABLE</div>
        ) : (
          <div className="tools-pane-content-inner">
            {/* Show error message if present */}
            {currentError && (
              <div className="tools-error-message" onClick={(e) => e.stopPropagation()}>
                <span className="tools-error-text">⚠ {currentError}</span>
              </div>
            )}
            {measurementError && (
              <div className="tools-error-message" onClick={(e) => e.stopPropagation()}>
                <span className="tools-error-text">⚠ {measurementError}</span>
              </div>
            )}
            {pushError && (
              <div className="tools-push-error-message" onClick={(e) => e.stopPropagation()}>
                <span className="tools-push-error-text">⚠ Push failed: {pushError}</span>
              </div>
            )}
            {pendingChanges.size > 0 && !pushError && (
              <div className="tools-pending-banner" onClick={(e) => e.stopPropagation()}>
                <span className="tools-pending-banner-text">
                  {pendingChanges.size} local edit{pendingChanges.size === 1 ? '' : 's'} — not on machine until PUSH (MEAS writes immediately)
                </span>
              </div>
            )}
            {!isHoverPreview && isToolsSnapshotStale && !currentError && (
              <div className="tools-stale-banner" onClick={(e) => e.stopPropagation()}>
                <span className="tools-stale-text">
                  STALE TOOL DATA ({formatToolsAge}) - DISPLAY MAY SHOW LAST KNOWN TOOLS
                </span>
              </div>
            )}
            {/* Show subtle loading indicator while fetching, but keep previous data visible */}
            {isLoadingTools && !currentError && (
              <div className="tools-loading-indicator" onClick={(e) => e.stopPropagation()}>
                <span className="tools-loading-text">UPDATING...</span>
              </div>
            )}
            {!isHoverPreview && (
              <div className="tools-search-container" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  className="tools-search-input"
                  placeholder={showingEmptyPots ? 'SEARCH POTS...' : 'SEARCH TOOLS...'}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
                {searchQuery && (
                  <span className="tools-search-results">
                    {visibleCount} / {showingEmptyPots ? emptyPocketCount : toolsViewFilter === 'atc' ? atcAssignedCount : tools.length}
                  </span>
                )}
              </div>
            )}
            {!isHoverPreview && programName && toolsViewFilter === 'all' && (
              <div className="tools-state-legend" onClick={(e) => e.stopPropagation()}>
                <span className="tools-state-legend-item">
                  <span className="tools-state-legend-swatch tools-state-legend-swatch--spindle" aria-hidden />
                  Spindle
                </span>
                <span className="tools-state-legend-item">
                  <span className="tools-state-legend-swatch tools-state-legend-swatch--program-atc" aria-hidden />
                  Program + ATC
                </span>
                <span className="tools-state-legend-item">
                  <span className="tools-state-legend-swatch tools-state-legend-swatch--program" aria-hidden />
                  Program
                </span>
                <span className="tools-state-legend-item">
                  <span className="tools-state-legend-swatch tools-state-legend-swatch--atc" aria-hidden />
                  ATC only
                </span>
              </div>
            )}
            <div className="tools-table-wrapper">
              <table className="tools-table">
              <thead onClick={(e) => e.stopPropagation()}>
                {useUnifiedView && (
                  <tr className="tools-col-group-row">
                    <th colSpan={5} className="tools-col-group-label tools-col-group-label--tool">
                      TOOL
                    </th>
                    <th colSpan={machineId ? 5 : 4} className="tools-col-group-label tools-col-group-label--atc">
                      ATC {unifiedCache.atc_available ? '' : '(unavailable)'}
                    </th>
                  </tr>
                )}
                <tr>
                  <th
                    className="tools-col-number tools-sortable"
                    onClick={() => handleSort('tool_number')}
                  >
                    T# {sortColumn === 'tool_number' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-name tools-sortable"
                    onClick={() => handleSort('tool_name')}
                  >
                    NAME {sortColumn === 'tool_name' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-diameter tools-sortable"
                    onClick={() => handleSort('diameter')}
                  >
                    D {sortColumn === 'diameter' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-length tools-sortable"
                    onClick={() => handleSort('length')}
                  >
                    H {sortColumn === 'length' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-life tools-sortable"
                    onClick={() => handleSort('life')}
                  >
                    LIFE {sortColumn === 'life' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-pot tools-sortable tools-col-atc"
                    onClick={() => handleSort('pot_number')}
                  >
                    POT {sortColumn === 'pot_number' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-group tools-sortable tools-col-atc"
                    onClick={() => handleSort('group')}
                  >
                    GRP {sortColumn === 'group' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th
                    className="tools-col-type tools-sortable tools-col-atc"
                    onClick={() => handleSort('tool_type')}
                  >
                    TYPE {sortColumn === 'tool_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  {machineId ? (
                    <th className="tools-col-measure tools-col-atc" title="Writes to machine immediately (macro #920). All other edits require PUSH.">
                      MEAS
                    </th>
                  ) : null}
                  <th
                    className="tools-col-color tools-sortable tools-col-atc"
                    onClick={() => handleSort('color')}
                  >
                    COLOR {sortColumn === 'color' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleCount === 0 ? (
                  <tr>
                    <td colSpan={machineId ? 10 : 9} className="tools-empty-row">
                      {showingEmptyPots
                        ? (searchQuery.trim() ? 'NO POTS MATCH SEARCH' : 'NO EMPTY POTS')
                        : 'NO TOOLS MATCH SEARCH'}
                    </td>
                  </tr>
                ) : showingEmptyPots ? (
                  filteredAndSortedEmptyPockets.map(({ pocket, merged, assignedTool }, idx) => {
                    const asTool = emptyPocketAsTool(pocket);
                    const hasPending = toolHasPending(asTool, 'pocket');
                    const pocketAssignPending = isToolFieldPending(asTool, 'pocket', (c) =>
                      c.operationType === 'tool_number' || c.operationType === 'cap',
                    );
                    const isEditable = !!machineId && useUnifiedView;
                    const previewType = assignedTool?.tool_type ?? pocket.tool_type;
                    const previewColor = assignedTool?.color ?? pocket.color;
                    return (
                      <tr
                        key={`empty-pot-${pocket.pot_number}-${idx}`}
                        className={`tools-row-empty-pot ${hasPending ? 'tools-row-pending' : ''}`}
                      >
                        <td className="tools-col-number" onClick={(e) => e.stopPropagation()}>
                          {isEditable ? (
                            <ValidatedFieldAnchor
                              warningKey={pocketAssignWarningKey(pocket.pot_number)}
                              fieldWarnings={fieldWarnings}
                              className="tools-pocket-assign-anchor"
                            >
                              <NumericEditInput
                                className={pendingInputClass(
                                  pocketAssignPending,
                                  'tools-edit-input tools-edit-input--tool-number',
                                )}
                                value={merged.is_cap ? 0 : (merged.tool_number || '')}
                                placeholder="T# or 0"
                                onValueChange={(raw) => handleToolNumberChange(asTool, raw, 'pocket')}
                              />
                            </ValidatedFieldAnchor>
                          ) : merged.is_cap ? (
                            'CAP'
                          ) : merged.tool_number ? (
                            `T${String(merged.tool_number).padStart(2, '0')}`
                          ) : (
                            '──'
                          )}
                        </td>
                        <td className="tools-col-name">
                          {assignedTool ? getToolDisplayName(assignedTool) || '──' : '──'}
                        </td>
                        <td className="tools-col-diameter">
                          {assignedTool ? formatDimension(assignedTool.diameter, units) : '──'}
                        </td>
                        <td className="tools-col-length">
                          {assignedTool ? formatDimension(assignedTool.length, units) : '──'}
                        </td>
                        <td className="tools-col-life">
                          {assignedTool ? formatLife(assignedTool.life) : '──'}
                        </td>
                        <td className="tools-col-pot tools-col-atc">
                          {formatPotDisplay(pocket.pot_number)}
                        </td>
                        <td className="tools-col-group tools-col-atc">
                          {assignedTool?.group != null && assignedTool.group !== ''
                            ? String(assignedTool.group)
                            : '──'}
                        </td>
                        <td className="tools-col-type tools-col-atc">
                          {formatToolType(previewType)}
                        </td>
                        {machineId ? (
                          <td className="tools-col-measure tools-col-atc">──</td>
                        ) : null}
                        <td className="tools-col-color tools-col-atc">
                          {previewColor != null ? getColorInfo(previewColor).name : '──'}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  filteredAndSortedTools.slice(0, visibleCount).map((tool, idx) => {
                const isCurrent = isCurrentTool(tool.tool_number);
                const matched = getMatchedTool(tool);
                const hasMatch = matched !== null && isBetaMode;
                const colorIdx = getToolColorClassIndex(tool);
                const rowStateClass = getToolRowStateClass(tool);
                const rowStateTitle = getToolRowStateTitle(tool);
                const rowMagazineColored =
                  isBetaMode && toolsColorMode && tool.in_atc && !isSpindleToolRow(tool, spindleToolNumber);
                const isMeasurementTool = measurementTool === tool.tool_number;
                const hasPending = toolHasPending(tool);
                const isEditable = !!machineId && useUnifiedView;
                const isAtcAssigned = Boolean(tool.in_atc && tool.pot_number);
                const namePending = isToolFieldPending(tool, 'tool', (c) => c.operationType === 'name');
                const diameterPending = isToolFieldPending(tool, 'tool', (c) => c.operationType === 'offset' && c.field === 'D');
                const lengthPending = isToolFieldPending(tool, 'tool', (c) => c.operationType === 'offset' && c.field === 'H');
                const lifePending = isToolFieldPending(tool, 'tool', (c) => c.operationType === 'life');
                const potPending = isToolFieldPending(
                  tool,
                  'tool',
                  (c) => c.operationType === 'pot_number' || c.operationType === 'delete',
                );
                const typePending = isToolFieldPending(tool, 'tool', (c) => c.operationType === 'tool_type');
                const colorPending = isToolFieldPending(tool, 'tool', (c) => c.operationType === 'color');
                const rowTitle = [rowStateTitle, hasMatch ? `Click to view tool ${matched!.tool_number} in Tool Management` : undefined]
                  .filter(Boolean)
                  .join(' — ') || undefined;
                return (
                  <tr
                    key={`tool-${tool.tool_number}-${idx}`}
                    className={`${isCurrent ? 'current-tool' : ''} ${hasMatch ? 'tool-matched' : ''} ${
                      isMeasurementTool ? 'measurement-tool' : ''
                    } ${hasPending ? 'tools-row-pending' : ''} ${rowStateClass} ${
                      rowMagazineColored ? `tools-row-colored tool-color-${colorIdx}` : ''
                    }`}
                    onClick={(e) => handleRowClick(tool, e)}
                    style={{ cursor: hasMatch ? 'pointer' : 'default' }}
                    title={rowTitle}
                  >
                    <td className="tools-col-number" onClick={(e) => e.stopPropagation()}>
                      {isCurrent && <span className="current-indicator">►</span>}
                      {hasMatch && <span className="matched-indicator" title="Tool exists in Tool Management">●</span>}
                      T{String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td className="tools-col-name" onClick={(e) => e.stopPropagation()}>
                      {isEditable ? (
                        <TextEditInput
                          className={pendingInputClass(namePending, 'tools-edit-input tools-edit-input-name')}
                          value={getToolDisplayName(tool)}
                          maxLength={14}
                          placeholder="──"
                          onClick={(e) => e.stopPropagation()}
                          onValueChange={(raw) => handleNameChange(tool, raw)}
                        />
                      ) : (
                        getToolDisplayName(tool) || '──'
                      )}
                    </td>
                    <td className="tools-col-diameter">
                      {isEditable ? (
                        <NumericEditInput
                          className={pendingInputClass(diameterPending)}
                          value={tool.diameter ?? ''}
                          decimal
                          onClick={(e) => e.stopPropagation()}
                          onValueChange={(raw) => handleOffsetChange(tool, 'D', raw)}
                        />
                      ) : (
                        formatDimension(tool.diameter, units)
                      )}
                    </td>
                    <td className="tools-col-length">
                      {isEditable ? (
                        <NumericEditInput
                          className={pendingInputClass(lengthPending)}
                          value={tool.length ?? ''}
                          decimal
                          onClick={(e) => e.stopPropagation()}
                          onValueChange={(raw) => handleOffsetChange(tool, 'H', raw)}
                        />
                      ) : (
                        formatDimension(tool.length, units)
                      )}
                    </td>
                    <td className="tools-col-life">
                      {isEditable ? (
                        <NumericEditInput
                          className={pendingInputClass(lifePending, 'tools-edit-input tools-edit-input--life')}
                          value={tool.life ?? ''}
                          onClick={(e) => e.stopPropagation()}
                          onValueChange={(raw) => handleLifeChange(tool, raw)}
                        />
                      ) : (
                        formatLife(tool.life)
                      )}
                    </td>
                    <td className="tools-col-pot tools-col-atc" onClick={(e) => e.stopPropagation()}>
                      {isEditable && unifiedCache.atc_available ? (
                        <PotAssignCell
                          tool={tool}
                          isAtcAssigned={isAtcAssigned}
                          potPending={potPending}
                          numPockets={numPocketsProp}
                          unifiedCache={unifiedCache}
                          pendingChanges={pendingChanges}
                          fieldWarnings={fieldWarnings}
                          onPotNumberChange={handlePotNumberChange}
                          onClear={handleDeleteFromPot}
                        />
                      ) : (
                        formatPotDisplay(isAtcAssigned ? tool.pot_number : undefined)
                      )}
                    </td>
                    <td className="tools-col-group tools-col-atc">{isAtcAssigned ? (tool.group ?? '──') : '──'}</td>
                    <td className="tools-col-type tools-col-atc" onClick={(e) => e.stopPropagation()}>
                      {isEditable && isAtcAssigned ? (
                        <Select
                          compact
                          className={`tools-type-select${typePending ? ' tools-type-select--pending' : ''}`}
                          value={String(tool.tool_type ?? 1)}
                          onChange={(raw) => handleToolTypeChange(tool, raw)}
                          options={TOOL_TYPE_OPTIONS}
                        />
                      ) : (
                        isAtcAssigned ? formatToolType(tool.tool_type) : '──'
                      )}
                    </td>
                    {machineId ? (
                      <td className="tools-col-measure tools-col-atc" onClick={(e) => e.stopPropagation()}>
                        {isAtcAssigned ? (
                          <button
                            type="button"
                            className={`tools-measure-btn ${isMeasurementTool ? 'active' : ''}`}
                            disabled={measurementSaving}
                            title={
                              isMeasurementTool
                                ? `T${String(tool.tool_number).padStart(2, '0')} is the measurement tool`
                                : `Set T${String(tool.tool_number).padStart(2, '0')} as measurement tool`
                            }
                            onClick={() => handleMeasurementToolSelect(tool)}
                            aria-pressed={isMeasurementTool}
                          >
                            {isMeasurementTool ? '●' : '○'}
                          </button>
                        ) : (
                          '──'
                        )}
                      </td>
                    ) : null}
                    <td className="tools-col-color tools-col-atc" onClick={(e) => e.stopPropagation()}>
                      {isEditable && isAtcAssigned ? (
                        <ColorSelect
                          className={colorPending ? 'tools-color-select--pending' : ''}
                          value={tool.color ?? 0}
                          onChange={(newColor) => handleColorChange(tool, newColor)}
                        />
                      ) : (
                        '──'
                      )}
                    </td>
                  </tr>
                );
                  })
                )}
              </tbody>
              </table>
            </div>
            {useUnifiedView && unifiedCache.spindle && !showingEmptyPots && (
              <div className="tools-spindle-row tools-state-spindle">
                <span className="tools-spindle-label">SPINDLE</span>
                {machineId ? (
                  <NumericEditInput
                    className={pendingInputClass(
                      isToolFieldPending(
                        { pot_number: 'SPINDLE', tool_number: unifiedCache.spindle.tool_number },
                        'spindle',
                        (c) => c.operationType === 'spindle',
                      ),
                      'tools-edit-input tools-edit-input--tool-number',
                    )}
                    value={unifiedCache.spindle.tool_number}
                    onValueChange={(raw) =>
                      handleToolNumberChange(
                        { pot_number: 'SPINDLE', tool_number: unifiedCache.spindle!.tool_number },
                        raw,
                        'spindle',
                      )
                    }
                  />
                ) : (
                  <span>T{String(unifiedCache.spindle.tool_number).padStart(2, '0')}</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="terminal-box-footer tools-pane-footer">
        <span className="tools-pane-footer-corner">└</span>
        <span className="tools-pane-footer-dash-fill" aria-hidden>
          {terminalRuleFill}
        </span>
        <span className="tools-pane-footer-corner">┘</span>
      </div>
      
    </div>
  );
};

