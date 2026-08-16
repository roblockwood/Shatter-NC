import React, { useState, useMemo, useEffect, useRef } from 'react';
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

// Define type locally to avoid Vite import issues
type ToolModificationOperationType = 
  | 'color' 
  | 'tool_number' 
  | 'pot_number'
  | 'tool_type' 
  | 'delete' 
  | 'life' 
  | 'offset' 
  | 'spindle';

interface Tool {
  pot_number?: string | number;
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
  group?: string | number;
  life?: number; // Tool life remaining in minutes (integer)
  tool_type?: number; // 1=STD Tool, 2=Large Tool
  color?: number; // 0=no color, 1=blue, 2=red, 3=purple, 4=green, 5=light blue, 6=yellow, 7=white
}

interface ToolsPaneProps {
  tools: Tool[];  // ATC data from WebSocket
  toolTable?: Tool[];  // TABLE data from WebSocket (new)
  currentTool?: number;
  machineId?: number;
  source?: 'atc' | 'table';
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
  cacheSlice: 'atc' | 'table';
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

/** Free-form numeric entry without browser spinner arrows. Keeps local draft while focused. */
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
        onValueChange(e.target.value);
      }}
    />
  );
}

function expandAtcToolsWithEmptyPots(tools: Tool[]): Tool[] {
  const spindleRows = tools.filter((tool) => isSpindlePot(tool.pot_number));
  const byPot = new Map<number, Tool>();
  let maxPot = 0;

  for (const tool of tools) {
    if (isSpindlePot(tool.pot_number)) continue;
    const pot = parsePotNumber(tool.pot_number);
    if (pot === null || pot < 1) continue;
    byPot.set(pot, tool);
    maxPot = Math.max(maxPot, pot);
  }

  if (maxPot === 0) {
    return tools;
  }

  const expanded: Tool[] = [...spindleRows];
  for (let pot = 1; pot <= maxPot; pot += 1) {
    expanded.push(byPot.get(pot) ?? { pot_number: pot, tool_number: 0 });
  }
  return expanded;
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
    case 'spindle':
      return 'spindle-tool';
    case 'offset':
      return `${tn}-offset-${field}`;
    case 'life':
      return `${tn}-life`;
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

function toolsMatchForSlice(a: Tool, b: Tool, slice: 'atc' | 'table'): boolean {
  if (slice === 'table') return a.tool_number === b.tool_number;
  return potsEqual(a.pot_number, b.pot_number);
}

function mergeServerToolWithPending(
  serverTool: Tool,
  pendingChanges: Map<string, PendingChange>,
  cacheSlice: 'atc' | 'table',
): Tool {
  let merged = { ...serverTool };
  pendingChanges.forEach((change) => {
    if (change.cacheSlice !== cacheSlice) return;
    if (!toolsMatchForSlice(change.tool, serverTool, cacheSlice)) return;
    if (change.operationType === 'delete') {
      merged = { ...merged, tool_number: 0 };
      return;
    }
    merged = applyFieldToTool(merged, change.field, change.newValue);
  });
  return merged;
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
    case 'H':
      return tool.length;
    case 'D':
      return tool.diameter;
    default:
      return undefined;
  }
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
    default:
      return null;
  }
}

export const ToolsPane: React.FC<ToolsPaneProps> = ({ 
  tools: initialTools, 
  toolTable: initialToolTable,
  currentTool, 
  machineId,
  source: initialSource = 'atc',
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
  // Cache sort settings separately for each view (ATC and TABLE)
  const [sortSettings, setSortSettings] = useState<{
    atc: { column: SortColumn; direction: SortDirection };
    table: { column: SortColumn; direction: SortDirection };
  }>({
    atc: { column: 'pot_number', direction: 'asc' },  // ATC defaults to POT# ascending
    table: { column: 'tool_number', direction: 'asc' }  // TABLE defaults to T# ascending
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [toolSource, setToolSource] = useState<'atc' | 'table'>(initialSource);
  
  // Get current sort settings based on active source
  const sortColumn = sortSettings[toolSource].column;
  const sortDirection = sortSettings[toolSource].direction;
  // Cache tools separately for each source (ATC and TABLE)
  const [toolsCache, setToolsCache] = useState<{ atc: Tool[]; table: Tool[] }>({
    atc: initialSource === 'atc' ? initialTools : [],
    table: initialSource === 'table' ? (initialToolTable || []) : []
  });
  // Track timestamps for cache entries to determine if data is stale
  const [cacheTimestamps, setCacheTimestamps] = useState<{
    atc: number | null;
    table: number | null;
  }>({
    atc: null,
    table: null
  });
  const [isLoadingTools, setIsLoadingTools] = useState(false);
  const [toolsError, setToolsError] = useState<{ atc: string | null; table: string | null }>({
    atc: null,
    table: null
  });
  const [toolsSummary, setToolsSummary] = useState<Array<{ tool_number: number; description: string }>>([]);

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

  // ──────────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<'atc' | 'table' | 'optimizer'>('atc');

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
    if (status === 'operating') {
      return 'Machine reports operating — push may be rejected by the control.';
    }
    if (memMode === 2 && memOperationStatus !== undefined && memOperationStatus !== 0) {
      return 'Program operation in progress — push may be rejected by the control.';
    }
    return undefined;
  }, [machineStatus, memMode, memOperationStatus]);

  const toolsDataLastUpdatedAt = useMemo(() => {
    const wsAt = toolSource === 'atc' ? toolsTimestamp : toolTableTimestamp;
    if (wsAt) return wsAt;
    const ct = cacheTimestamps[toolSource];
    return ct != null ? ct : null;
  }, [toolSource, toolsTimestamp, toolTableTimestamp, cacheTimestamps]);

  const toolExpectedIntervalMs = Math.max((toolPollIntervalSeconds ?? 30) * 1000, 5000);

  const toolsAgeMs = useMemo(() => {
    if (!toolsDataLastUpdatedAt) return null;
    const parsed = typeof toolsDataLastUpdatedAt === 'number'
      ? toolsDataLastUpdatedAt
      : Date.parse(String(toolsDataLastUpdatedAt));
    if (!Number.isFinite(parsed)) return null;
    return Math.max(0, Date.now() - parsed);
  }, [toolsDataLastUpdatedAt]);

  const visibleToolsCount = toolsCache[toolSource]?.length ?? 0;

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
  
  // Get current tools from cache based on active source
  const tools = toolsCache[toolSource];
  // Get current error for active source
  const currentError = toolsError[toolSource];
  
  // Update cache when WebSocket data arrives (fresh Telnet data from polling)
  useEffect(() => {
    if (machineId) {
      if (initialTools && initialTools.length > 0) {
        setToolsCache(prev => {
          if (isPushingChanges) {
            const pushingKeys = new Set(Array.from(pendingChanges.keys()));
            return {
              ...prev,
              atc: initialTools.map(serverTool =>
                pushingKeys.size > 0
                  ? mergeServerToolWithPending(serverTool, pendingChanges, 'atc')
                  : serverTool,
              ),
            };
          }

          const merged = initialTools.map(serverTool => {
            const pendingMerged = mergeServerToolWithPending(
              serverTool,
              pendingChanges,
              'atc',
            );
            const potKey = `${serverTool.pot_number}-${serverTool.tool_number}`;
            const recentlyPushed = recentlyPushedRef.current.get(potKey);
            if (recentlyPushed) {
              const serverVal = getToolFieldValue(serverTool, recentlyPushed.field);
              if (serverVal === recentlyPushed.value) {
                recentlyPushedRef.current.delete(potKey);
                return pendingMerged;
              }
              return applyFieldToTool(pendingMerged, recentlyPushed.field, recentlyPushed.value);
            }
            return pendingMerged;
          });

          return { ...prev, atc: merged };
        });
        setCacheTimestamps(prev => ({ ...prev, atc: Date.now() }));
        setToolsError(prev => ({ ...prev, atc: null }));

        if (!isPushingChanges) {
          updatePendingChanges((prev) => {
            const next = new Map(prev);
            initialTools.forEach(serverTool => {
              next.forEach((change, key) => {
                if (change.cacheSlice !== 'atc') return;
                if (!toolsMatchForSlice(change.tool, serverTool, 'atc')) return;
                if (change.operationType === 'delete' && !serverTool.tool_number) {
                  next.delete(key);
                } else {
                  const fieldVal = getToolFieldValue(serverTool, change.field);
                  if (valuesEqual(fieldVal ?? '', change.newValue)) {
                    next.delete(key);
                  }
                }
              });
            });
            return next;
          });
        }
      }

      if (initialToolTable && initialToolTable.length > 0) {
        setToolsCache(prev => ({
          ...prev,
          table: initialToolTable.map(serverTool =>
            mergeServerToolWithPending(serverTool, pendingChanges, 'table'),
          ),
        }));
        setCacheTimestamps(prev => ({ ...prev, table: Date.now() }));
        setToolsError(prev => ({ ...prev, table: null }));

        if (!isPushingChanges) {
          updatePendingChanges((prev) => {
            const next = new Map(prev);
            initialToolTable.forEach(serverTool => {
              next.forEach((change, key) => {
                if (change.cacheSlice !== 'table') return;
                if (change.tool.tool_number !== serverTool.tool_number) return;
                const fieldVal = getToolFieldValue(serverTool, change.field);
                if (valuesEqual(fieldVal ?? '', change.newValue)) {
                  next.delete(key);
                }
              });
            });
            return next;
          });
        }
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTools, initialToolTable, machineId, isPushingChanges]);
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


  // Rely on WebSocket data - no automatic fetching to avoid Telnet conflicts
  // WebSocket provides fresh data every 5 seconds via polling service
  // Only fetch as fallback if WebSocket connection appears broken (cache >60s stale)
  useEffect(() => {
    if (machineId && toolSource) {
      const cacheTimestamp = cacheTimestamps[toolSource];
      const now = Date.now();
      const STALE_THRESHOLD = 60000; // 60 seconds - only fetch if WebSocket is clearly broken
      
      // Check if we need to fetch (fallback only):
      // Cache is very stale (>60s - indicating WebSocket connection is broken)
      const needsFetch = cacheTimestamp && (now - cacheTimestamp) > STALE_THRESHOLD;
      
      if (needsFetch) {
        // Only fetch as fallback - WebSocket should provide data
      setIsLoadingTools(true);
        
        const sourceParam = toolSource === 'atc' ? 'atc' : 'table';
        fetch(`${API_BASE_URL}/api/machines/${machineId}/tools?source=${sourceParam}`)
          .then(res => {
            if (!res.ok) {
              return res.json().then(errData => {
                const errorMsg = errData.detail || `HTTP ${res.status}: ${res.statusText}`;
                // For 503 errors, provide more helpful message
                if (res.status === 503) {
                  throw new Error(`Machine temporarily unavailable: ${errorMsg}. The machine may be busy or Telnet port 10000 may be blocked. Please try again in a moment.`);
                }
                throw new Error(errorMsg);
              });
            }
            return res.json();
          })
        .then(data => {
            if (data && data.tools) {
              // Update cache for this source
              setToolsCache(prev => ({
                ...prev,
                [toolSource]: data.tools
              }));
              setCacheTimestamps(prev => ({
                ...prev,
                [toolSource]: Date.now()
              }));
              // Clear error on successful fetch
              setToolsError(prev => ({
                ...prev,
                [toolSource]: null
              }));
            } else {
              console.warn(`Tool ${sourceParam} response missing tools array:`, data);
              // Only clear cache if we had no previous data
              setToolsCache(prev => {
                if (prev[toolSource].length === 0) {
                  return {
                    ...prev,
                    [toolSource]: []
                  };
                }
                return prev; // Keep existing cache
              });
          }
          setIsLoadingTools(false);
        })
        .catch(err => {
            console.error(`Error fetching ${sourceParam} data:`, err);
            // Store error message for display
            const errorMessage = err instanceof Error ? err.message : `Failed to fetch ${sourceParam} data`;
            setToolsError(prev => ({
              ...prev,
              [toolSource]: errorMessage
            }));
            // Don't clear cache on error - keep previous data visible
          setIsLoadingTools(false);
        });
      } else {
        // Have cached data or waiting for WebSocket - no fetch needed
        setIsLoadingTools(false);
      }
    }
    // Only check when source changes, not on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machineId, toolSource]);


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
    cacheSlice: 'atc' | 'table',
  ) => {
    const changeKey = makePendingKey(tool, field, operationType);

    updatePendingChanges((prev) => {
      const existing = prev.get(changeKey);
      const baseline = existing?.oldValue ?? oldValue;

      if (valuesEqual(newValue, baseline)) {
        const next = new Map(prev);
        next.delete(changeKey);
        setToolsCache((cachePrev) => ({
          ...cachePrev,
          [cacheSlice]: cachePrev[cacheSlice].map((t) => {
            if (!toolsMatchForSlice(t, tool, cacheSlice)) return t;
            if (operationType === 'delete') {
              return { ...t, tool_number: baseline as number };
            }
            return applyFieldToTool(t, field, baseline);
          }),
        }));
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

      setToolsCache((cachePrev) => ({
        ...cachePrev,
        [cacheSlice]: cachePrev[cacheSlice].map((t) => {
          if (!toolsMatchForSlice(t, tool, cacheSlice)) return t;
          if (operationType === 'delete') {
            return { ...t, tool_number: 0 };
          }
          return applyFieldToTool(t, field, newValue);
        }),
      }));

      return next;
    });
  };

  const handleColorChange = (tool: Tool, newColor: number) => {
    if (toolSource !== 'atc' || !machineId || !tool.pot_number) {
      return;
    }
    stagePendingChange(
      tool,
      'color',
      tool.color ?? 0,
      newColor,
      'color',
      'atc',
    );
  };

  const handleToolNumberChange = (tool: Tool, raw: string) => {
    if (toolSource !== 'atc' || !machineId || !tool.pot_number) return;
    const parsed = parseInt(raw, 10);
    if (!Number.isFinite(parsed)) return;

    if (isSpindlePot(tool.pot_number)) {
      stagePendingChange(tool, 'tool_number', tool.tool_number, parsed, 'spindle', 'atc');
      return;
    }

    if (parsed < 1 || parsed > 999) return;
    stagePendingChange(
      tool,
      'tool_number',
      tool.tool_number,
      parsed,
      'tool_number',
      'atc',
    );
  };

  const handlePotNumberChange = (tool: Tool, raw: string) => {
    if (toolSource !== 'table' || !machineId || !tool.tool_number) return;
    const trimmed = raw.trim();
    if (trimmed === '') return;
    const parsed = parseInt(trimmed, 10);
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > numPocketsProp) return;

    const oldPot = tool.pot_number ?? '';
    stagePendingChange(
      tool,
      'pot_number',
      oldPot,
      parsed,
      'pot_number',
      'table',
    );
  };

  const handleToolTypeChange = (tool: Tool, raw: string) => {
    if (toolSource !== 'atc' || !machineId || !tool.pot_number || isSpindlePot(tool.pot_number)) {
      return;
    }
    const parsed = parseInt(raw, 10);
    if (![1, 2, 3].includes(parsed)) return;
    stagePendingChange(
      tool,
      'tool_type',
      tool.tool_type ?? 1,
      parsed,
      'tool_type',
      'atc',
    );
  };

  const handleDeleteFromPot = (tool: Tool) => {
    if (toolSource !== 'atc' || !machineId || !tool.pot_number || isSpindlePot(tool.pot_number)) {
      return;
    }
    if (!tool.tool_number) return;
    stagePendingChange(tool, 'tool_number', tool.tool_number, 0, 'delete', 'atc');
  };

  const handleOffsetChange = (tool: Tool, offsetType: 'H' | 'D', raw: string) => {
    if (toolSource !== 'table' || !machineId) return;
    const parsed = parseFloat(raw);
    if (!Number.isFinite(parsed)) return;
    const oldValue = offsetType === 'H' ? (tool.length ?? 0) : (tool.diameter ?? 0);
    stagePendingChange(tool, offsetType, oldValue, parsed, 'offset', 'table');
  };

  const handleLifeChange = (tool: Tool, raw: string) => {
    if (toolSource !== 'table' || !machineId) return;
    const parsed = parseInt(raw, 10);
    if (!Number.isFinite(parsed) || parsed < 0) return;
    stagePendingChange(tool, 'life', tool.life ?? 0, parsed, 'life', 'table');
  };

  const toolHasPending = (tool: Tool): boolean =>
    Array.from(pendingChanges.values()).some(
      c => c.cacheSlice === toolSource && toolsMatchForSlice(c.tool, tool, toolSource),
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
    // Return empty string if no tool_name, so it displays as blank
    return tool.tool_name || '';
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
    if (toolSource !== 'atc' || !machineId || !tool.tool_number) {
      return;
    }
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
        throw new Error(
          typeof error.detail === 'string'
            ? error.detail
            : error.detail?.message || 'Batch operation failed',
        );
      }

      const batchData = await batchResponse.json();
      const results: ToolChangeBatchResult[] = batchData.results || [];
      const failures = results.filter(r => !r.success);

      setToolsCache(prev => {
        let atc = [...prev.atc];
        let table = [...prev.table];

        results.forEach(result => {
          if (!result.success || !result.client_id) return;
          const change = pendingChangesRef.current.get(result.client_id);
          if (!change) return;

          const confirmed = getConfirmedValueFromResult(result);
          const applyConfirmed = (t: Tool): Tool => {
            if (change.operationType === 'pot_number') {
              const potVal = result.pot_number ?? Number(change.newValue);
              return applyFieldToTool(t, 'pot_number', potVal);
            }
            if (confirmed) {
              return applyFieldToTool(t, confirmed.field, confirmed.value);
            }
            return t;
          };

          if (change.cacheSlice === 'atc') {
            atc = atc.map(t => {
              if (!toolsMatchForSlice(change.tool, t, 'atc')) return t;
              return applyConfirmed(t);
            });
            const trackKey = `${change.tool.pot_number}-${change.tool.tool_number}`;
            if (confirmed) {
              recentlyPushedRef.current.set(trackKey, {
                field: confirmed.field,
                value: confirmed.value,
                timestamp: Date.now(),
              });
            }
          } else {
            table = table.map(t => {
              if (t.tool_number !== change.tool.tool_number) return t;
              return applyConfirmed(t);
            });
          }
        });

        return { atc, table };
      });

      updatePendingChanges((prev) => {
        const next = new Map(prev);
        results.forEach(result => {
          if (result.success && result.client_id) {
            next.delete(result.client_id);
          }
        });
        return next;
      });

      if (failures.length > 0) {
        const errorMessages = failures
          .map(f => f.message || `${f.operation_type} failed`)
          .join('; ');
        alert(`Some changes failed: ${errorMessages}`);
      } else {
        setPushComplete(true);
        setTimeout(() => setPushComplete(false), 1500);
      }
    } catch (error) {
      console.error('Error pushing changes:', error);
      alert(`Failed to push changes: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsPushingChanges(false);
    }
  };

  const handleDiscardChanges = () => {
    if (pendingChanges.size === 0) return;

    setToolsCache(prev => {
      let atc = [...prev.atc];
      let table = [...prev.table];

      pendingChanges.forEach(change => {
        const revert = (t: Tool) => {
          if (change.operationType === 'delete') {
            return { ...t, tool_number: change.oldValue as number };
          }
          return applyFieldToTool(t, change.field, change.oldValue);
        };

        if (change.cacheSlice === 'atc') {
          atc = atc.map(t =>
            toolsMatchForSlice(change.tool, t, 'atc') ? revert(t) : t,
          );
        } else {
          table = table.map(t =>
            t.tool_number === change.tool.tool_number ? revert(t) : t,
          );
        }
      });

      return { atc, table };
    });

    updatePendingChanges(() => new Map());
  };

  // Build tool_number → actual_pot map from live ATC data (passed to optimizer tab)
  const actualPotMap = useMemo(() => {
    const map = new Map<number, number>();
    (toolsCache.atc || []).forEach(tool => {
      const tn = tool.tool_number;
      const pot = Number(tool.pot_number);
      if (tn && !isNaN(pot)) map.set(tn, pot);
    });
    return map;
  }, [toolsCache.atc]);

  const handleTabClick = (tab: 'atc' | 'table' | 'optimizer', e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveTab(tab);
    if (tab === 'atc' || tab === 'table') {
      setToolSource(tab);
    }
    // Optimizer auto-runs in ToolsOptimizerTab when it mounts with a programName
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
    let filtered = tools;
    if (toolSource === 'atc' && machineId) {
      filtered = expandAtcToolsWithEmptyPots(tools).map((tool) =>
        mergeServerToolWithPending(tool, pendingChanges, 'atc'),
      );
    } else if (toolSource === 'table' && machineId) {
      filtered = tools.map((tool) =>
        mergeServerToolWithPending(tool, pendingChanges, 'table'),
      );
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(tool => {
        return (
          String(tool.tool_number).includes(query) ||
          (tool.tool_name && tool.tool_name.toLowerCase().includes(query)) ||
          (tool.pot_number && String(tool.pot_number).toLowerCase().includes(query)) ||
          (tool.group && String(tool.group).toLowerCase().includes(query)) ||
          (tool.tool_type !== undefined && formatToolType(tool.tool_type).toLowerCase().includes(query)) ||
          (tool.color !== undefined && getColorInfo(tool.color).name.toLowerCase().includes(query)) ||
          (tool.life !== undefined && String(tool.life).includes(query))
        );
      });
    }

    // Apply sorting
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
  }, [tools, searchQuery, sortColumn, sortDirection, toolSource, machineId, pendingChanges]);

  const handleSort = (column: SortColumn) => {
    setSortSettings(prev => {
      const current = prev[toolSource];
      if (current.column === column) {
        // Toggle direction for same column
        return {
          ...prev,
          [toolSource]: {
            column,
            direction: current.direction === 'asc' ? 'desc' : 'asc'
          }
        };
    } else {
        // New column - default to ascending
        return {
          ...prev,
          [toolSource]: {
            column,
            direction: 'asc'
          }
        };
    }
    });
  };

  // Show all tools since list is scrollable
  const visibleCount = filteredAndSortedTools.length;

  const toolsListTitleMid =
    activeTab === 'optimizer'
      ? `OPTIMIZER${programName ? ` ─ ${programName}` : ''}`
      : activeTab === 'atc' ? `ATC (${tools.length})` : `TABLE (${tools.length})`;
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
                  ariaLabel={`Tools (${toolSource.toUpperCase()}) data freshness`}
                />
              )}
              {!isHoverPreview && isToolsSnapshotStale && activeTab !== 'optimizer' && (
                <span
                  className="tools-stale-chip"
                  title={`Visible ${toolSource.toUpperCase()} tools are stale (${formatToolsAge}). Validation uses backend live data.`}
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
                  <button
                    className={`source-toggle-btn ${activeTab === 'atc' ? 'active' : ''}`}
                    onClick={(e) => handleTabClick('atc', e)}
                    title="ATC Magazine"
                  >
                    ATC
                  </button>
                  <button
                    className={`source-toggle-btn ${activeTab === 'table' ? 'active' : ''}`}
                    onClick={(e) => handleTabClick('table', e)}
                    title="Tool Table"
                  >
                    TABLE
                  </button>
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
        ) : tools.length === 0 && !isLoadingTools && !currentError ? (
          <div className="tools-empty">NO TOOLS LOADED</div>
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
            {!isHoverPreview && isToolsSnapshotStale && !currentError && (
              <div className="tools-stale-banner" onClick={(e) => e.stopPropagation()}>
                <span className="tools-stale-text">
                  STALE {toolSource.toUpperCase()} DATA ({formatToolsAge}) - DISPLAY MAY SHOW LAST KNOWN TOOLS
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
                  placeholder="SEARCH TOOLS..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
                {searchQuery && (
                  <span className="tools-search-results">
                    {filteredAndSortedTools.length} / {tools.length}
                  </span>
                )}
              </div>
            )}
            <div className="tools-table-wrapper">
              <table className="tools-table">
              <thead onClick={(e) => e.stopPropagation()}>
                <tr>
                  <th 
                    className="tools-col-pot tools-sortable"
                    onClick={() => handleSort('pot_number')}
                  >
                    POT {sortColumn === 'pot_number' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
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
                    TOOL NAME {sortColumn === 'tool_name' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th 
                    className="tools-col-diameter tools-sortable"
                    onClick={() => handleSort('diameter')}
                  >
                    DIAMETER {sortColumn === 'diameter' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th 
                    className="tools-col-length tools-sortable"
                    onClick={() => handleSort('length')}
                  >
                    LENGTH {sortColumn === 'length' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th 
                    className="tools-col-group tools-sortable"
                    onClick={() => handleSort('group')}
                  >
                    GROUP {sortColumn === 'group' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th 
                    className="tools-col-life tools-sortable"
                    onClick={() => handleSort('life')}
                  >
                    LIFE {sortColumn === 'life' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th 
                    className="tools-col-type tools-sortable"
                    onClick={() => handleSort('tool_type')}
                  >
                    TYPE {sortColumn === 'tool_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  {toolSource === 'atc' && machineId ? (
                    <th className="tools-col-measure" title="Tool selected for measurement (macro #920)">
                      MEAS
                    </th>
                  ) : null}
                  <th 
                    className="tools-col-color tools-sortable"
                    onClick={() => handleSort('color')}
                  >
                    COLOR {sortColumn === 'color' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedTools.length === 0 ? (
                  <tr>
                    <td colSpan={toolSource === 'atc' && machineId ? 10 : 9} className="tools-empty-row">
                      NO TOOLS MATCH SEARCH
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedTools.slice(0, visibleCount).map((tool, idx) => {
                const isCurrent = isCurrentTool(tool.tool_number);
                const matched = getMatchedTool(tool);
                const hasMatch = matched !== null && isBetaMode;
                const colorIdx = getToolColorClassIndex(tool);
                const rowColored = isBetaMode && toolsColorMode;
                const isMeasurementTool = measurementTool === tool.tool_number;
                const hasPending = toolHasPending(tool);
                const isAtcRowEditable =
                  toolSource === 'atc' &&
                  !!machineId &&
                  (isSpindlePot(tool.pot_number) || parsePotNumber(tool.pot_number) !== null);
                const isTableEditable = toolSource === 'table' && !!machineId;
                const isEmptyPot = !isSpindlePot(tool.pot_number) && !tool.tool_number;
                return (
                  <tr 
                    key={idx} 
                    className={`${isCurrent ? 'current-tool' : ''} ${hasMatch ? 'tool-matched' : ''} ${
                      isMeasurementTool ? 'measurement-tool' : ''
                    } ${hasPending ? 'tools-row-pending' : ''} ${
                      isEmptyPot ? 'tools-row-empty-pot' : ''
                    } ${
                      rowColored ? `tools-row-colored tool-color-${colorIdx}` : ''
                    }`}
                    onClick={(e) => handleRowClick(tool, e)}
                    style={{ cursor: hasMatch ? 'pointer' : 'default' }}
                    title={hasMatch ? `Click to view tool ${matched.tool_number} in Tool Management` : undefined}
                  >
                    <td className="tools-col-pot" onClick={(e) => e.stopPropagation()}>
                      {isTableEditable ? (
                        <NumericEditInput
                          className="tools-edit-input tools-edit-input--pot-number"
                          value={tool.pot_number}
                          placeholder="—"
                          onValueChange={(raw) => handlePotNumberChange(tool, raw)}
                        />
                      ) : (
                        formatPotDisplay(tool.pot_number)
                      )}
                      {isAtcRowEditable && !isSpindlePot(tool.pot_number) && tool.tool_number ? (
                        <button
                          type="button"
                          className="tools-clear-pot-btn"
                          title="Clear pocket (remove tool)"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteFromPot(tool);
                          }}
                        >
                          CLR
                        </button>
                      ) : null}
                    </td>
                    <td className="tools-col-number" onClick={(e) => e.stopPropagation()}>
                      {isCurrent && <span className="current-indicator">►</span>}
                      {hasMatch && <span className="matched-indicator" title="Tool exists in Tool Management">●</span>}
                      {isAtcRowEditable ? (
                        <NumericEditInput
                          className="tools-edit-input tools-edit-input--tool-number"
                          value={tool.tool_number || ''}
                          placeholder="—"
                          onValueChange={(raw) => handleToolNumberChange(tool, raw)}
                        />
                      ) : (
                        <>T{String(tool.tool_number).padStart(2, '0')}</>
                      )}
                    </td>
                    <td className="tools-col-name">{getToolDisplayName(tool) || '──'}</td>
                    <td className="tools-col-diameter">
                      {isTableEditable ? (
                        <NumericEditInput
                          className="tools-edit-input"
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
                      {isTableEditable ? (
                        <NumericEditInput
                          className="tools-edit-input"
                          value={tool.length ?? ''}
                          decimal
                          onClick={(e) => e.stopPropagation()}
                          onValueChange={(raw) => handleOffsetChange(tool, 'H', raw)}
                        />
                      ) : (
                        formatDimension(tool.length, units)
                      )}
                    </td>
                    <td className="tools-col-group">{tool.group ?? '──'}</td>
                    <td className="tools-col-life">
                      {isTableEditable ? (
                        <NumericEditInput
                          className="tools-edit-input tools-edit-input--life"
                          value={tool.life ?? ''}
                          onClick={(e) => e.stopPropagation()}
                          onValueChange={(raw) => handleLifeChange(tool, raw)}
                        />
                      ) : (
                        formatLife(tool.life)
                      )}
                    </td>
                    <td
                      className="tools-col-type"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {isAtcRowEditable && !isSpindlePot(tool.pot_number) && tool.tool_number ? (
                        <Select
                          compact
                          className="tools-type-select"
                          value={String(tool.tool_type ?? 1)}
                          onChange={(raw) => handleToolTypeChange(tool, raw)}
                          options={TOOL_TYPE_OPTIONS}
                        />
                      ) : (
                        formatToolType(tool.tool_type)
                      )}
                    </td>
                    {toolSource === 'atc' && machineId ? (
                      <td
                        className="tools-col-measure"
                        onClick={(e) => e.stopPropagation()}
                      >
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
                      </td>
                    ) : null}
                    <td
                      className="tools-col-color"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {toolSource === 'atc' && tool.pot_number && machineId && tool.tool_number ? (
                        <ColorSelect
                          value={tool.color ?? 0}
                          onChange={(newColor) => handleColorChange(tool, newColor)}
                        />
                      ) : tool.color !== undefined && tool.color !== null && tool.tool_number ? (
                        <ColorSelect
                          value={tool.color}
                          onChange={() => {}}
                          readOnly
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

