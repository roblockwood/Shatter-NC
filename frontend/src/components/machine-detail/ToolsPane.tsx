import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBetaMode } from '../../hooks/useBetaMode';
import { formatDimension } from '../../utils/formatDimension';
import type { UnitType } from '../../utils/formatDimension';
import './ToolsPane.css';
import { API_BASE_URL } from '../../config/api';

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
}

type SortColumn = 'pot_number' | 'tool_number' | 'tool_name' | 'diameter' | 'length' | 'group' | 'life' | 'tool_type' | 'color';
type SortDirection = 'asc' | 'desc';

export const ToolsPane: React.FC<ToolsPaneProps> = ({ 
  tools: initialTools, 
  toolTable: initialToolTable,
  currentTool, 
  machineId,
  source: initialSource = 'atc',
  units = 'in'
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
  
  // Get current tools from cache based on active source
  const tools = toolsCache[toolSource];
  // Get current error for active source
  const currentError = toolsError[toolSource];
  
  // Update cache when WebSocket data arrives (fresh Telnet data from polling)
  useEffect(() => {
    if (machineId) {
      // Update ATC cache from WebSocket
      if (initialTools && initialTools.length > 0) {
        setToolsCache(prev => ({
          ...prev,
          atc: initialTools
        }));
        setCacheTimestamps(prev => ({
          ...prev,
          atc: Date.now()
        }));
        // Clear error when fresh data arrives
        setToolsError(prev => ({
          ...prev,
          atc: null
        }));
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
  }, [initialTools, initialToolTable, machineId]);
  const navigate = useNavigate();
  const { isBetaMode } = useBetaMode();

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
  // Only fetch as fallback if WebSocket data doesn't arrive within timeout
  useEffect(() => {
    if (machineId && toolSource) {
      const cachedTools = toolsCache[toolSource];
      const cacheTimestamp = cacheTimestamps[toolSource];
      const now = Date.now();
      const INITIAL_LOAD_TIMEOUT = 10000; // 10 seconds - wait for WebSocket to provide data
      const STALE_THRESHOLD = 60000; // 60 seconds - only fetch if WebSocket is clearly broken
      
      // Check if we need to fetch (fallback only):
      // 1. No cached data AND we've waited long enough for WebSocket (10s)
      // 2. Cache is very stale (>60s - indicating WebSocket is broken)
      const needsFetch = (
        (!cachedTools || cachedTools.length === 0) && 
        cacheTimestamp && (now - cacheTimestamp) > INITIAL_LOAD_TIMEOUT
      ) || (
        cacheTimestamp && (now - cacheTimestamp) > STALE_THRESHOLD
      );
      
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
      } else if (!cachedTools || cachedTools.length === 0) {
        // No data yet, but haven't waited long enough - show loading while waiting for WebSocket
        setIsLoadingTools(true);
      } else {
        // Have cached data - no fetch needed, WebSocket will keep it fresh
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
      let aVal: any;
      let bVal: any;

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

  return (
    <div 
      className="tools-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div 
        className="terminal-box-header"
      >
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ TOOLS ({tools.length}) {'─'.repeat(Math.max(0, 15 - 8 - String(tools.length).length))}</span>
            {machineId && (
              <div className="tools-source-toggle" onClick={(e) => e.stopPropagation()}>
                <button
                  className={`source-toggle-btn ${toolSource === 'atc' ? 'active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setToolSource('atc');
                  }}
                  title="ATC Table"
                >
                  ATC
                </button>
                <button
                  className={`source-toggle-btn ${toolSource === 'table' ? 'active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setToolSource('table');
                  }}
                  title="Tool Table"
                >
                  TABLE
                </button>
              </div>
            )}
            <span>┐</span>
          </div>
        </div>
      </div>
      <div className="terminal-box-content">
        {tools.length === 0 && !isLoadingTools && !currentError ? (
          <div className="tools-empty">NO TOOLS LOADED</div>
        ) : (
          <>
            {/* Show error message if present */}
            {currentError && (
              <div className="tools-error-message" onClick={(e) => e.stopPropagation()}>
                <span className="tools-error-text">⚠ {currentError}</span>
              </div>
            )}
            {/* Show subtle loading indicator while fetching, but keep previous data visible */}
            {isLoadingTools && !currentError && (
              <div className="tools-loading-indicator" onClick={(e) => e.stopPropagation()}>
                <span className="tools-loading-text">UPDATING...</span>
              </div>
            )}
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
                return (
                  <tr 
                    key={idx} 
                    className={`${isCurrent ? 'current-tool' : ''} ${hasMatch ? 'tool-matched' : ''}`}
                    onClick={(e) => handleRowClick(tool, e)}
                    style={{ cursor: hasMatch ? 'pointer' : 'default' }}
                    title={hasMatch ? `Click to view tool ${matched.tool_number} in Tool Management` : undefined}
                  >
                    <td className="tools-col-pot">{tool.pot_number ?? '──'}</td>
                    <td className="tools-col-number">
                      {isCurrent && <span className="current-indicator">►</span>}
                      {hasMatch && <span className="matched-indicator" title="Tool exists in Tool Management">●</span>}
                      {String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td className="tools-col-name">{getToolDisplayName(tool) || '──'}</td>
                    <td className="tools-col-diameter">{formatDimension(tool.diameter, units)}</td>
                    <td className="tools-col-length">{formatDimension(tool.length, units)}</td>
                    <td className="tools-col-group">{tool.group ?? '──'}</td>
                    <td className="tools-col-life">{formatLife(tool.life)}</td>
                    <td className="tools-col-type">{formatToolType(tool.tool_type)}</td>
                    <td className="tools-col-color">
                      {tool.color !== undefined && tool.color !== null ? (
                        <span className="color-display">
                          <span 
                            className="color-indicator" 
                            style={{ backgroundColor: getColorInfo(tool.color).hex }}
                            title={getColorInfo(tool.color).name}
                          />
                          <span className="color-name">{getColorInfo(tool.color).name}</span>
                        </span>
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
          </>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

