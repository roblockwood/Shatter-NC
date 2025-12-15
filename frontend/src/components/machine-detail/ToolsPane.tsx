import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBetaMode } from '../../hooks/useBetaMode';
import './ToolsPane.css';
import { API_BASE_URL } from '../../config/api';

interface Tool {
  pot_number?: string | number;
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
  group?: string | number;
  life?: string | number;
  tool_type?: string;
  color?: string;
}

interface ToolsPaneProps {
  tools: Tool[];
  currentTool?: number;
  onExpand?: () => void;
  isExpanded?: boolean;
  isFullExpanded?: boolean;
  machineId?: number;
  source?: 'atc' | 'table';
}

type SortColumn = 'pot_number' | 'tool_number' | 'tool_name' | 'diameter' | 'length' | 'group' | 'life' | 'tool_type' | 'color';
type SortDirection = 'asc' | 'desc';

export const ToolsPane: React.FC<ToolsPaneProps> = ({ 
  tools: initialTools, 
  currentTool, 
  onExpand, 
  isExpanded = false,
  isFullExpanded = false,
  machineId,
  source: initialSource = 'atc'
}) => {
  const [sortColumn, setSortColumn] = useState<SortColumn>('tool_number');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [searchQuery, setSearchQuery] = useState('');
  const [toolSource, setToolSource] = useState<'atc' | 'table'>(initialSource);
  const [tools, setTools] = useState<Tool[]>(initialTools);
  const [isLoadingTools, setIsLoadingTools] = useState(false);
  const [toolsSummary, setToolsSummary] = useState<Array<{ tool_number: number; description: string }>>([]);
  const navigate = useNavigate();
  const { isBetaMode } = useBetaMode();

  // Update tools from initialTools when on ATC source (updates from polling)
  useEffect(() => {
    if (toolSource === 'atc') {
      setTools(initialTools);
    }
  }, [initialTools, toolSource]);

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

  // Fetch tool table only when user switches to 'table' source (once per switch)
  useEffect(() => {
    if (machineId && toolSource === 'table') {
      setIsLoadingTools(true);
      fetch(`${API_BASE_URL}/api/machines/${machineId}/tools?source=table`)
        .then(res => res.json())
        .then(data => {
          if (data.tools) {
            setTools(data.tools);
          }
          setIsLoadingTools(false);
        })
        .catch(err => {
          console.error('Error fetching tool table:', err);
          setIsLoadingTools(false);
        });
    } else if (toolSource === 'atc') {
      setTools(initialTools);
    }
    // Only fetch when source changes to 'table', not on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machineId, toolSource]);

  const formatDimension = (value: number | undefined) => {
    if (!value || value <= 0) return '────';
    return value.toFixed(4);
  };

  const getToolDisplayName = (tool: Tool) => {
    if (tool.tool_name) return tool.tool_name;
    return `TOOL ${tool.tool_number}`;
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
    } else if (onExpand) {
      handleExpand(e);
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
          (tool.tool_type && tool.tool_type.toLowerCase().includes(query)) ||
          (tool.color && tool.color.toLowerCase().includes(query))
        );
      });
    }

    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortColumn) {
        case 'pot_number':
          aVal = a.pot_number ? String(a.pot_number) : '';
          bVal = b.pot_number ? String(b.pot_number) : '';
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
          aVal = a.life ? String(a.life) : '';
          bVal = b.life ? String(b.life) : '';
          break;
        case 'tool_type':
          aVal = a.tool_type ? a.tool_type.toLowerCase() : '';
          bVal = b.tool_type ? b.tool_type.toLowerCase() : '';
          break;
        case 'color':
          aVal = a.color ? a.color.toLowerCase() : '';
          bVal = b.color ? b.color.toLowerCase() : '';
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
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Show all tools since list is scrollable
  const visibleCount = filteredAndSortedTools.length;

  const handleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onExpand) {
      onExpand();
    }
  };

  return (
    <div 
      className={`tools-pane terminal-box ${isFullExpanded ? 'tools-pane-full-expanded' : ''}`}
      onClick={(e) => e.stopPropagation()}
    >
      <div 
        className="terminal-box-header"
        onClick={handleExpand}
        style={{ cursor: onExpand ? 'pointer' : 'default' }}
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
        {isLoadingTools ? (
          <div className="tools-empty">LOADING TOOL TABLE...</div>
        ) : tools.length === 0 ? (
          <div className="tools-empty">NO TOOLS LOADED</div>
        ) : (
          <>
            {(isExpanded || isFullExpanded) && (
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
              <tbody 
                onClick={handleExpand}
                style={{ cursor: onExpand ? 'pointer' : 'default' }}
              >
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
                    style={{ cursor: hasMatch ? 'pointer' : (onExpand ? 'pointer' : 'default') }}
                    title={hasMatch ? `Click to view tool ${matched.tool_number} in Tool Management` : undefined}
                  >
                    <td className="tools-col-pot">{tool.pot_number ?? '──'}</td>
                    <td className="tools-col-number">
                      {isCurrent && <span className="current-indicator">►</span>}
                      {hasMatch && <span className="matched-indicator" title="Tool exists in Tool Management">●</span>}
                      {String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td className="tools-col-name">{getToolDisplayName(tool)}</td>
                    <td className="tools-col-diameter">{formatDimension(tool.diameter)}"</td>
                    <td className="tools-col-length">{formatDimension(tool.length)}"</td>
                    <td className="tools-col-group">{tool.group ?? '──'}</td>
                    <td className="tools-col-life">{tool.life ?? '──'}</td>
                    <td className="tools-col-type">{tool.tool_type ?? '──'}</td>
                    <td className="tools-col-color">{tool.color ?? '──'}</td>
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
      {!isFullExpanded && (
        <div className="terminal-box-footer">
          └{'─'.repeat(42)}┘
        </div>
      )}
      {isFullExpanded && onExpand && (
        <div className="terminal-box-footer">
          <button
            className="tools-collapse-btn"
            onClick={(e) => {
              e.stopPropagation();
              onExpand();
            }}
          >
            [COLLAPSE]
          </button>
          └{'─'.repeat(42)}┘
        </div>
      )}
    </div>
  );
};

