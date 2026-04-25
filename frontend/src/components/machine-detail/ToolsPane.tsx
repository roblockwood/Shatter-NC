import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBetaMode } from '../../hooks/useBetaMode';
import { formatDimension } from '../../utils/formatDimension';
import type { UnitType } from '../../utils/formatDimension';
import './ToolsPane.css';
import { API_BASE_URL } from '../../config/api';
import { ColorSelect } from './ColorSelect';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { ToolsOptimizerTab } from './ToolsOptimizerTab';

// Define type locally to avoid Vite import issues
type ToolModificationOperationType = 
  | 'color' 
  | 'tool_number' 
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
}

type SortColumn = 'pot_number' | 'tool_number' | 'tool_name' | 'diameter' | 'length' | 'group' | 'life' | 'tool_type' | 'color';
type SortDirection = 'asc' | 'desc';

export const ToolsPane: React.FC<ToolsPaneProps> = ({ 
  tools: initialTools, 
  toolTable: initialToolTable,
  currentTool, 
  machineId,
  source: initialSource = 'atc',
  units = 'in',
  machineStatus,
  memMode,
  memOperationStatus: _memOperationStatus,
  toolsTimestamp,
  toolTableTimestamp,
  toolPollIntervalSeconds = 30,
  variant = 'default',
  programName,
  numPockets: numPocketsProp = 21,
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
  const [toolSource, setToolSource] = useState<'atc' | 'table'>(() => {
    if (initialSource === 'atc' && (!initialTools || initialTools.length === 0) && initialToolTable && initialToolTable.length > 0) {
      return 'table';
    }
    return initialSource;
  });
  
  // Get current sort settings based on active source
  const sortColumn = sortSettings[toolSource].column;
  const sortDirection = sortSettings[toolSource].direction;
  // Cache tools separately for each source (ATC and TABLE)
  const [toolsCache, setToolsCache] = useState<{ atc: Tool[]; table: Tool[] }>({
    atc: initialSource === 'atc' ? initialTools : [],
    table: initialSource === 'table' ? (initialToolTable || []) : (initialToolTable || [])
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
  const [pendingChanges, setPendingChanges] = useState<Map<string, { tool: Tool; field: string; oldValue: string | number; newValue: string | number; operationType: ToolModificationOperationType }>>(new Map());
  const [isPushingChanges, setIsPushingChanges] = useState(false);
  const [pushComplete, setPushComplete] = useState(false);

  // ──────────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<'atc' | 'table' | 'optimizer'>(() => {
    // If no ATC data but table data exists on mount, default to TABLE tab
    if (initialSource === 'atc' && (!initialTools || initialTools.length === 0) && initialToolTable && initialToolTable.length > 0) {
      return 'table';
    }
    return initialSource === 'table' ? 'table' : 'atc';
  });

  // Track recently pushed items to prevent stale WebSocket data from overwriting confirmed values
  const recentlyPushedRef = useRef<Map<string, { potNumber: number; toolNumber: number; color: number; timestamp: number }>>(new Map());
  
  // Determine if machine is safe for push operations based on cached status
  const isMachineSafeForPush = useMemo(() => {
    if (!machineStatus && memMode === undefined) return true; // Default to safe if status unknown
    const status = machineStatus?.toLowerCase();
    // Block PRD3 status "operating" (machine is actively running)
    if (status === 'operating') {
      return false;
    }
    // Block MEM mode 2 (Memory operation - actively running program)
    if (memMode === 2) {
      return false;
    }
    return true;
  }, [machineStatus, memMode]);

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

  const machineStateReason = useMemo(() => {
    if (!machineStatus && memMode === undefined) return undefined;
    const status = machineStatus?.toLowerCase();
    if (status === 'operating') {
      return 'Machine is currently running a program. Stop the program before making changes.';
    }
    if (memMode === 2) {
      return 'Machine is running a program (Memory operation mode). Stop the program before making changes.';
    }
    return undefined;
  }, [machineStatus, memMode]);
  
  // Get current tools from cache based on active source
  const tools = toolsCache[toolSource];
  // Get current error for active source
  const currentError = toolsError[toolSource];
  
  // Update cache when WebSocket data arrives (fresh Telnet data from polling)
  useEffect(() => {
    if (machineId) {
      // Update ATC cache from WebSocket
      if (initialTools && initialTools.length > 0) {
        setToolsCache(prev => {
          // If we're pushing changes, merge WebSocket data but preserve optimistic values for tools being pushed
          if (isPushingChanges) {
            // Merge: use WebSocket data for tools NOT being pushed, keep optimistic values for tools being pushed
            const toolsBeingPushed = new Set(
              Array.from(pendingChanges.keys()).map(key => {
                const parts = key.split('-');
                return `${parts[0]}-${parts[1]}`; // pot_number-tool_number
              })
            );
            
            return {
              ...prev,
              atc: initialTools.map(serverTool => {
                const toolKey = `${serverTool.pot_number}-${serverTool.tool_number}`;
                if (toolsBeingPushed.has(toolKey)) {
                  // This tool is being pushed - find it in current cache to preserve optimistic value
                  const cachedTool = prev.atc.find(t => 
                    t.pot_number === serverTool.pot_number && 
                    t.tool_number === serverTool.tool_number
                  );
                  return cachedTool || serverTool; // Use cached (optimistic) value if available
                }
                return serverTool; // Use fresh WebSocket data for other tools
              })
            };
          } else {
            // Not pushing - merge WebSocket data but preserve pending changes and recently pushed items
            // Start with server tools, then apply pending changes and protect recently pushed items
            const merged = initialTools.map(serverTool => {
              const toolKey = `${serverTool.pot_number}-${serverTool.tool_number}`;
              
              // Check if this tool was recently pushed - protect from stale WebSocket data
              const recentlyPushed = recentlyPushedRef.current.get(toolKey);
              if (recentlyPushed) {
                // Check if WebSocket data matches our pushed value (confirmation)
                if (serverTool.color === recentlyPushed.color) {
                  // WebSocket confirms our value - remove from recentlyPushed tracking
                  recentlyPushedRef.current.delete(toolKey);
                  return serverTool;
                } else {
                  // WebSocket has stale data - keep our confirmed value from cache
                  const cachedTool = prev.atc.find(t => 
                    t.pot_number === serverTool.pot_number && 
                    t.tool_number === serverTool.tool_number
                  );
                  if (cachedTool && cachedTool.color === recentlyPushed.color) {
                    return cachedTool; // Use cached (confirmed) value
                  }
                  // Fallback to recently pushed value
                  return { ...serverTool, color: recentlyPushed.color as number };
                }
              }
              
              // Check if this tool has a pending change
              const changeKey = `${serverTool.pot_number}-${serverTool.tool_number}-color`;
              const change = pendingChanges.get(changeKey);
              if (change) {
                // Has pending change - apply the optimistic newValue to the server tool
                return { ...serverTool, color: change.newValue as number };
              }
              return serverTool; // No pending change - use fresh WebSocket data
            });
            
            return {
              ...prev,
              atc: merged
            };
          }
        });
        setCacheTimestamps(prev => ({
          ...prev,
          atc: Date.now()
        }));
        // Clear error when fresh data arrives
        setToolsError(prev => ({
          ...prev,
          atc: null
        }));
        // Clear pending changes that match the fresh data (server has confirmed the change)
        // Only do this if we're NOT pushing (to avoid clearing during push)
        if (!isPushingChanges) {
          setPendingChanges(prev => {
            const next = new Map(prev);
            initialTools.forEach(serverTool => {
              const changeKey = `${serverTool.pot_number}-${serverTool.tool_number}-color`;
              const change = next.get(changeKey);
              if (change && serverTool.color === change.newValue) {
                // Server has our change, remove from pending
                next.delete(changeKey);
              }
            });
            return next;
          });
        }
      }
      
      // Update TABLE cache from WebSocket
      if (initialToolTable && initialToolTable.length > 0) {
        setToolsCache(prev => ({
          ...prev,
          table: initialToolTable
        }));
        setCacheTimestamps(prev => ({
          ...prev,
          table: Date.now()
        }));
        // Clear error when fresh data arrives
        setToolsError(prev => ({
          ...prev,
          table: null
        }));
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
      default:
        return String(value);
    }
  };

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

  const handleColorChange = (tool: Tool, newColor: number) => {
    // Only allow color changes in ATC view
    if (toolSource !== 'atc' || !machineId || !tool.pot_number) {
      return;
    }

    const oldValue = tool.color ?? 0;
    if (newColor === oldValue) {
      // Remove from pending changes if reverting to original
      const changeKey = `${tool.pot_number}-${tool.tool_number}-color`;
      setPendingChanges(prev => {
        const next = new Map(prev);
        next.delete(changeKey);
        return next;
      });
      
      // Update local cache to show original value
      setToolsCache(prev => ({
        ...prev,
        atc: prev.atc.map(t =>
          t.pot_number === tool.pot_number && t.tool_number === tool.tool_number
            ? { ...t, color: oldValue }
            : t
        ),
      }));
      return;
    }

    // Add to pending changes
    const changeKey = `${tool.pot_number}-${tool.tool_number}-color`;
    setPendingChanges(prev => {
      const next = new Map(prev);
      next.set(changeKey, {
        tool,
        field: 'color',
        oldValue,
        newValue: newColor,
        operationType: 'color' as ToolModificationOperationType,
      });
      return next;
    });

    // Update local cache optimistically
    setToolsCache(prev => ({
      ...prev,
      atc: prev.atc.map(t =>
        t.pot_number === tool.pot_number && t.tool_number === tool.tool_number
          ? { ...t, color: newColor }
          : t
      ),
    }));
  };

  const handlePushChanges = async () => {
    if (pendingChanges.size === 0 || !machineId || isPushingChanges) {
      return;
    }

    setIsPushingChanges(true);
    setPushComplete(false);

    try {
      // Backend validator handles machine state validation - no need to check here
      // Process all pending changes
      const changeArray = Array.from(pendingChanges.values());
      
      // Separate color changes from other operation types
      const colorChanges = changeArray.filter(c => c.operationType === 'color');
      const otherChanges = changeArray.filter(c => c.operationType !== 'color');
      
      interface ColorChangeResult {
        pot_number: number;
        tool_number: number;
        color: number;
        success: boolean;
        message?: string;
      }
      // Process color changes in batch (more efficient)
      let colorResults: ColorChangeResult[] = [];
      if (colorChanges.length > 0) {
        const batchRequest = {
          changes: colorChanges.map(change => {
            const potNumber = change.tool.pot_number
              ? (typeof change.tool.pot_number === 'string'
                  ? parseInt(change.tool.pot_number, 10)
                  : change.tool.pot_number)
              : undefined;
            if (!potNumber) throw new Error('Pot number required');
            return {
              pot_number: potNumber,
              tool_number: change.tool.tool_number,
              color: change.newValue
            };
          })
        };
        
        const batchResponse = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/tools/atc/colors/batch`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(batchRequest)
          }
        );
        
        if (!batchResponse.ok) {
          const error = await batchResponse.json();
          throw new Error(typeof error.detail === 'string' ? error.detail : (error.detail?.message || 'Batch operation failed'));
        }
        
        const batchData = await batchResponse.json();
        colorResults = batchData.results || [];
        
        // Check for failures in batch
        const batchFailures = colorResults.filter((r) => !r.success);
        if (batchFailures.length > 0) {
          const errorMessages = batchFailures.map((f) => 
            `Pot ${f.pot_number}: ${f.message || 'Unknown error'}`
          ).join('; ');
          throw new Error(`Some color changes failed: ${errorMessages}`);
        }
        
        // Update cache with confirmed results immediately (don't wait for next poll)
        setToolsCache(prev => {
          const updated = {
            ...prev,
            atc: prev.atc.map(tool => {
              const result = colorResults.find((r) => 
                r.pot_number === tool.pot_number && 
                r.tool_number === tool.tool_number &&
                r.success
              );
              if (result) {
                // Track this as recently pushed to protect from stale WebSocket data
                const toolKey = `${result.pot_number}-${result.tool_number}`;
                recentlyPushedRef.current.set(toolKey, {
                  potNumber: result.pot_number,
                  toolNumber: result.tool_number,
                  color: result.color,
                  timestamp: Date.now()
                });
                return { ...tool, color: result.color };
              }
              return tool;
            })
          };
          return updated;
        });
        
        // Show success state briefly before clearing pending changes
        setIsPushingChanges(false);
        setPushComplete(true);
        setTimeout(() => {
          // Clear pending changes after success animation
          setPendingChanges(prev => {
            const next = new Map(prev);
            colorResults.forEach((result) => {
              if (result.success) {
                const changeKey = `${result.pot_number}-${result.tool_number}-color`;
                next.delete(changeKey);
              }
            });
            return next;
          });
          setPushComplete(false);
        }, 1500); // Show success for 1500ms, then clear
      }
      
      // Process other operation types individually (if any)
      // Currently only color changes are supported, but this structure allows for future operation types
      if (otherChanges.length > 0) {
        throw new Error(`Unsupported operation types: ${otherChanges.map(c => c.operationType).join(', ')}`);
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

    // Revert all pending changes
    setToolsCache(prev => {
      const atc = prev.atc.map(tool => {
        const changeKey = `${tool.pot_number}-${tool.tool_number}-color`;
        const change = pendingChanges.get(changeKey);
        if (change) {
          return { ...tool, color: change.oldValue as number };
        }
        return tool;
      });
      return { ...prev, atc };
    });

    // Clear pending changes
    setPendingChanges(new Map());
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

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = tools.filter(tool => {
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
  }, [tools, searchQuery, sortColumn, sortDirection]);

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
                    className={`tools-action-btn tools-push-btn ${!isMachineSafeForPush ? 'disabled' : ''} ${isPushingChanges ? 'pushing' : ''} ${pushComplete ? 'complete' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePushChanges();
                    }}
                    disabled={isPushingChanges || !isMachineSafeForPush}
                    title={
                      !isMachineSafeForPush
                        ? `Cannot push changes: ${machineStateReason || 'Machine is not in a safe state'}`
                        : 'Push all pending changes to machine'
                    }
                  >
                    {pushComplete
                      ? '✓ PUSHED'
                      : isPushingChanges 
                      ? 'PUSHING...' 
                      : !isMachineSafeForPush
                      ? `BLOCKED (${pendingChanges.size})`
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
          <div className="tools-empty">
            {activeTab === 'atc' && toolsCache.table.length > 0
              ? <><div>ATC MAGAZINE DATA UNAVAILABLE</div><div className="tools-empty-sub">This machine does not expose an ATC pot file (ATCTL/ATDTL). Switch to the TABLE tab to view tool data.</div></>
              : 'NO TOOLS LOADED'}
          </div>
        ) : (
          <div className="tools-pane-content-inner">
            {/* Show error message if present */}
            {currentError && (
              <div className="tools-error-message" onClick={(e) => e.stopPropagation()}>
                <span className="tools-error-text">⚠ {currentError}</span>
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
                    <td colSpan={9} className="tools-empty-row">
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
                return (
                  <tr 
                    key={idx} 
                    className={`${isCurrent ? 'current-tool' : ''} ${hasMatch ? 'tool-matched' : ''} ${
                      rowColored ? `tools-row-colored tool-color-${colorIdx}` : ''
                    }`}
                    onClick={(e) => handleRowClick(tool, e)}
                    style={{ cursor: hasMatch ? 'pointer' : 'default' }}
                    title={hasMatch ? `Click to view tool ${matched.tool_number} in Tool Management` : undefined}
                  >
                    <td className="tools-col-pot">{tool.pot_number ?? '──'}</td>
                    <td className="tools-col-number">
                      {isCurrent && <span className="current-indicator">►</span>}
                      {hasMatch && <span className="matched-indicator" title="Tool exists in Tool Management">●</span>}
                      T{String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td className="tools-col-name">{getToolDisplayName(tool) || '──'}</td>
                    <td className="tools-col-diameter">{formatDimension(tool.diameter, units)}</td>
                    <td className="tools-col-length">{formatDimension(tool.length, units)}</td>
                    <td className="tools-col-group">{tool.group ?? '──'}</td>
                    <td className="tools-col-life">{formatLife(tool.life)}</td>
                    <td className="tools-col-type">{formatToolType(tool.tool_type)}</td>
                    <td
                      className="tools-col-color"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {toolSource === 'atc' && tool.pot_number && machineId ? (
                        <ColorSelect
                          value={tool.color ?? 0}
                          onChange={(newColor) => handleColorChange(tool, newColor)}
                        />
                      ) : tool.color !== undefined && tool.color !== null ? (
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

