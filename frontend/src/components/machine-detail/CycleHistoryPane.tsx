import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';
import './CycleHistoryPane.css';

interface ProductionRun {
  id: number;
  program_name: string;
  started_at: string;
  ended_at?: string;
  duration_seconds?: number;
  parts_produced?: number;
}

interface CycleHistoryPaneProps {
  machineId: number;
  onExpand?: () => void;
}

export const CycleHistoryPane: React.FC<CycleHistoryPaneProps> = ({ machineId, onExpand }) => {
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [stats, setStats] = useState({
    totalRuns: 0,
    avgCycle: 0,
    totalParts: 0,
    lastRun: null as string | null,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProductionRuns = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/production-runs?limit=20`);
        if (response.ok) {
          const data = await response.json();
          setRuns(data);

          // Calculate stats
          const totalRuns = data.length;
          const completedRuns = data.filter((r: ProductionRun) => r.ended_at);
          const totalParts = completedRuns.reduce((sum: number, r: ProductionRun) => sum + (r.parts_produced || 0), 0);
          const totalDuration = completedRuns.reduce((sum: number, r: ProductionRun) => sum + (r.duration_seconds || 0), 0);
          const avgCycle = completedRuns.length > 0 ? totalDuration / completedRuns.length : 0;
          const lastRun = data.length > 0 ? data[0].started_at : null;

          setStats({
            totalRuns,
            avgCycle,
            totalParts,
            lastRun,
          });
        }
      } catch (error) {
        console.error('Error fetching production runs:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProductionRuns();
    // Refresh every 60 seconds
    const interval = setInterval(fetchProductionRuns, 60000);
    return () => clearInterval(interval);
  }, [machineId]);

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Only show "more" indicator if there are significantly more items (2+ more)
  const hasMoreRuns = runs.length > 6; // Changed from 5 to 6
  const visibleCount = 5;

  return (
    <div 
      className="cycle-history-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ CYCLE HISTORY {'─'.repeat(27)}</span>
            {hasMoreRuns && onExpand && (
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
        {loading ? (
          <div className="cycle-loading">LOADING...</div>
        ) : (
          <>
            <div className="cycle-stats">
              <div className="terminal-box-inner">
                <div className="terminal-box-inner-top">
                  ┌─ STATISTICS {'─'.repeat(28)}┐
                </div>
                <div className="terminal-box-inner-content">
                  <div className="stat-row">
                    <span className="stat-label">TOTAL RUNS:</span>
                    <span className="stat-value">{stats.totalRuns}</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">AVG CYCLE:</span>
                    <span className="stat-value">{formatTime(stats.avgCycle)}</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">TOTAL PARTS:</span>
                    <span className="stat-value">{stats.totalParts.toLocaleString()}</span>
                  </div>
                  {stats.lastRun && (
                    <div className="stat-row">
                      <span className="stat-label">LAST RUN:</span>
                      <span className="stat-value">{formatDateTime(stats.lastRun)}</span>
                    </div>
                  )}
                </div>
                <div className="terminal-box-inner-footer">
                  └{'─'.repeat(42)}┘
                </div>
              </div>
            </div>

            {runs.length > 0 && (
              <div className="validation-section">
                <div className="section-header">PRODUCTION RUNS</div>
                <table className="validation-table">
                  <thead>
                    <tr className="validation-table-header">
                      <th>#</th>
                      <th>PROGRAM</th>
                      <th>START</th>
                      <th>DURATION</th>
                      <th>PARTS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.slice(0, visibleCount).map((run, idx) => {
                      const startTime = new Date(run.started_at).toLocaleTimeString();
                      const duration = run.duration_seconds ? formatTime(run.duration_seconds) : '─';
                      const parts = run.parts_produced || 0;
                      return (
                        <tr key={run.id} className="validation-table-row">
                          <td>{String(idx + 1).padStart(2, '0')}</td>
                          <td>{run.program_name || '─'}</td>
                          <td>{startTime}</td>
                          <td>{duration}</td>
                          <td>{parts}</td>
                        </tr>
                      );
                    })}
                    {hasMoreRuns && onExpand && (
                      <tr 
                        className="validation-table-row runs-more"
                        onClick={(e) => {
                          e.stopPropagation();
                          onExpand();
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <td colSpan={5} style={{ textAlign: 'center', color: 'var(--color-text-dim)', fontStyle: 'italic' }}>
                          +{runs.length - visibleCount} MORE
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

