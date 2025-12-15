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
              <div className="cycle-runs">
                <div className="runs-table-header">
                  ┌────┬──────────────┬──────────┬─────────┬────────┐
                </div>
                <div className="runs-table-header-row">
                  │ #  │ PROGRAM      │ START    │ DURATION│ PARTS  │
                </div>
                <div className="runs-table-divider">
                  ├────┼──────────────┼──────────┼─────────┼────────┤
                </div>
                <div className="runs-table-body">
                  {runs.slice(0, visibleCount).map((run, idx) => (
                    <div key={run.id} className="runs-table-row">
                      <div className="runs-row-content">
                        │ {String(idx + 1).padStart(2, '0')} │ {run.program_name.padEnd(12).substring(0, 12)} │ {new Date(run.started_at).toLocaleTimeString().padStart(8)} │ {run.duration_seconds ? formatTime(run.duration_seconds).padStart(8) : '───────'.padStart(8)} │ {(run.parts_produced || 0).toString().padStart(6)} │
                      </div>
                    </div>
                  ))}
                  {hasMoreRuns && onExpand && (
                    <div 
                      className="runs-more" 
                      onClick={(e) => {
                        e.stopPropagation();
                        onExpand();
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      +{runs.length - visibleCount} MORE
                    </div>
                  )}
                </div>
                <div className="runs-table-footer">
                  └────┴──────────────┴──────────┴─────────┴────────┘
                </div>
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

