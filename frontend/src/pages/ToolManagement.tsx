import { useState, useEffect } from 'react';
import './ToolManagement.css';
import { API_BASE } from '../config/api';
import { AsciiLoadingScreen } from '../components/AsciiLoadingScreen';
import { ToolDetailModal } from '../components/ToolDetailModal';

interface ToolSummary {
  tool_number: number;
  diameter: number;
  description: string;
  programs_using: number;
  estimated_runtime_seconds: number;
  total_runs: number;
  machines_used: number[];
  operation_types: string[];
}

interface ToolSummaryResponse {
  total_unique_tools: number;
  total_programs: number;
  total_production_runs: number;
  tools: ToolSummary[];
}

export const ToolManagement = () => {
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [selectedTool, setSelectedTool] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryStats, setSummaryStats] = useState({
    total_unique_tools: 0,
    total_programs: 0,
    total_production_runs: 0
  });

  useEffect(() => {
    fetchToolSummary();
  }, []);

  const fetchToolSummary = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tools/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: ToolSummaryResponse = await response.json();
      setTools(data.tools);
      setSummaryStats({
        total_unique_tools: data.total_unique_tools,
        total_programs: data.total_programs,
        total_production_runs: data.total_production_runs
      });
    } catch (error) {
      console.error('Failed to fetch tools:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatRuntime = (seconds: number): string => {
    if (seconds === 0) return '0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatToolNumber = (num: number): string => {
    return `T${num.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return <AsciiLoadingScreen />;
  }

  return (
    <div className="tool-management">
      {/* Summary Header */}
      <div className="tool-summary">
        <span className="text-info">TOTAL: {summaryStats.total_unique_tools}</span>
        <span className="separator">│</span>
        <span>PROGRAMS: {summaryStats.total_programs}</span>
        <span className="separator">│</span>
        <span>RUNS: {summaryStats.total_production_runs}</span>
        <span className="separator">│</span>
        <button
          className="terminal-button"
          onClick={() => alert('Export modal coming soon!')}
        >
          [ EXPORT DATA ]
        </button>
      </div>

      {/* Tool List Table */}
      <div className="tool-list-container">
        <div className="tool-list-header">
          ┌─ TOOL INVENTORY {'─'.repeat(100)}┐
        </div>
        <table className="tool-list-table">
          <thead>
            <tr>
              <th>T#</th>
              <th>DIA</th>
              <th>DESCRIPTION</th>
              <th>PROGRAMS</th>
              <th>RUNS</th>
              <th>RUNTIME</th>
              <th>OPERATIONS</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tools.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-state">
                  NO TOOLS FOUND - UPLOAD PROGRAMS TO POPULATE TOOL DATA
                </td>
              </tr>
            ) : (
              tools.map((tool) => (
                <tr
                  key={tool.tool_number}
                  className="tool-row clickable"
                  onClick={() => setSelectedTool(tool.tool_number)}
                >
                  <td className="text-info">{formatToolNumber(tool.tool_number)}</td>
                  <td>{tool.diameter.toFixed(3)}"</td>
                  <td className="description">{tool.description}</td>
                  <td className="text-center">{tool.programs_using}</td>
                  <td className="text-center">{tool.total_runs}</td>
                  <td className="text-right">{formatRuntime(tool.estimated_runtime_seconds)}</td>
                  <td className="operations-cell">
                    {tool.operation_types.slice(0, 2).join(', ')}
                    {tool.operation_types.length > 2 && (
                      <span className="text-dim"> +{tool.operation_types.length - 2}</span>
                    )}
                  </td>
                  <td className="text-info detail-link">[&gt;]</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <div className="tool-list-footer">
          └{'─'.repeat(119)}┘
        </div>
      </div>

      {/* Footer/Command Line */}
      <div className="tool-footer">
        <div className="tool-divider">
          ╠{'═'.repeat(100)}╣
        </div>
        <div className="command-line">
          <span className="prompt">&gt;</span>
          <span className="cursor">STATUS: STATIC ANALYSIS</span>
          <span className="separator">│</span>
          <span className="text-dim">LAST REFRESH: {new Date().toLocaleTimeString()}</span>
          <span className="separator">│</span>
          <button className="terminal-button-small" onClick={fetchToolSummary}>
            [ REFRESH ]
          </button>
        </div>
      </div>

      {/* Tool Detail Modal */}
      {selectedTool !== null && (
        <ToolDetailModal
          toolNumber={selectedTool}
          onClose={() => setSelectedTool(null)}
        />
      )}
    </div>
  );
};
