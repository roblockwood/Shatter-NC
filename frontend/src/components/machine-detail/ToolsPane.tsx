import React from 'react';
import './ToolsPane.css';

interface Tool {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}

interface ToolsPaneProps {
  tools: Tool[];
  currentTool?: number;
  onExpand?: () => void;
}

export const ToolsPane: React.FC<ToolsPaneProps> = ({ tools, currentTool, onExpand }) => {
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

  // Only show "more" indicator if there are significantly more items (2+ more)
  const hasMoreTools = tools.length > 6; // Changed from 5 to 6
  const visibleCount = 5;

  return (
    <div 
      className="tools-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ TOOLS ({tools.length}) {'─'.repeat(Math.max(0, 40 - 8 - String(tools.length).length))}</span>
            {hasMoreTools && onExpand && (
              <button 
                className="expand-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  onExpand();
                }}
                title="Expand"
              >
                [EXPAND]
              </button>
            )}
            <span>┐</span>
          </div>
        </div>
      </div>
      <div className="terminal-box-content">
        {tools.length === 0 ? (
          <div className="tools-empty">NO TOOLS LOADED</div>
        ) : (
          <div className="tools-table-wrapper">
            <div className="tools-table-header">
              ┌────┬──────────────┬──────────┬─────────┐
            </div>
            <div className="tools-table-header-row">
              │ T# │ TOOL NAME    │ DIAMETER │ LENGTH  │
            </div>
            <div className="tools-table-divider">
              ├────┼──────────────┼──────────┼─────────┤
            </div>
            <div className="tools-table-body">
              {tools.slice(0, visibleCount).map((tool, idx) => {
                const toolNum = String(tool.tool_number).padStart(2, '0');
                const toolName = getToolDisplayName(tool).padEnd(12).substring(0, 12);
                const diameter = formatDimension(tool.diameter).padStart(8);
                const length = formatDimension(tool.length).padStart(7);
                const indicator = isCurrentTool(tool.tool_number) ? '►' : ' ';
                return (
                  <div key={idx} className={`tools-table-row ${isCurrentTool(tool.tool_number) ? 'current-tool' : ''}`}>
                    <div className="tools-row-content">
                      │ {indicator}{toolNum}│ {toolName} │ {diameter}" │ {length}" │
                    </div>
                  </div>
                );
              })}
            </div>
            {hasMoreTools && onExpand && (
              <div 
                className="tools-more" 
                onClick={(e) => {
                  e.stopPropagation();
                  onExpand();
                }}
                style={{ cursor: 'pointer' }}
              >
                +{tools.length - visibleCount} MORE
              </div>
            )}
            <div className="tools-table-footer">
              └────┴──────────────┴──────────┴─────────┘
            </div>
          </div>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

