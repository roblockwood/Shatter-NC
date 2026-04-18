import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import './CycleHistoryPane.css';

interface CycleHistoryEntry {
  program_no: string | null;
  folder_name?: string | null;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  part_count: number;
  parts_by_counter: Record<number, number>;
  alarms: {
    time: string;
    alarm_code: string;
    alarm_message: string;
    severity?: string | null;
  }[];
}

interface CycleHistoryPaneProps {
  machineId: number;
}

export const CycleHistoryPane: React.FC<CycleHistoryPaneProps> = ({ machineId }) => {
  const [cycles, setCycles] = useState<CycleHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const PAGE_SIZE = 100;
  const [page, setPage] = useState(0);

  useEffect(() => {
    const fetchCycleHistory = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/cycle-history?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`
        );
        if (response.ok) {
          const data: CycleHistoryEntry[] = await response.json();
          setCycles(data);
        }
      } catch (error) {
        console.error('Error fetching cycle history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCycleHistory();
    const interval = setInterval(fetchCycleHistory, 60000);
    return () => clearInterval(interval);
  }, [machineId, page]);

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const hasPrevPage = page > 0;
  const hasNextPage = cycles.length === PAGE_SIZE;

  return (
    <div 
      className="cycle-history-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <PaneTerminalHeader label="CYCLE HISTORY" />
      <div className="terminal-box-content">
        {loading ? (
          <div className="cycle-loading">LOADING...</div>
        ) : (
          <>
            {cycles.length > 0 && (
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
                    {cycles.map((cycle, idx) => {
                      const startTime = new Date(cycle.start_time).toLocaleTimeString();
                      const duration = cycle.duration_seconds ? formatTime(cycle.duration_seconds) : '─';
                      const parts = cycle.part_count || 0;
                      return (
                        <tr key={`${cycle.program_no || 'UNKNOWN'}-${cycle.start_time}`} className="validation-table-row">
                          <td>{String(idx + 1).padStart(2, '0')}</td>
                          <td>{cycle.program_no || '─'}</td>
                          <td>{startTime}</td>
                          <td>{duration}</td>
                          <td>{parts}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                <div className="cycle-pagination">
                  <button
                    className="cycle-page-btn"
                    disabled={!hasPrevPage || loading}
                    onClick={(e) => {
                      e.stopPropagation();
                      setPage((p) => Math.max(0, p - 1));
                    }}
                  >
                    [PREV 100]
                  </button>
                  <span className="cycle-page-info">
                    PAGE {page + 1}
                  </span>
                  <button
                    className="cycle-page-btn"
                    disabled={!hasNextPage || loading}
                    onClick={(e) => {
                      e.stopPropagation();
                      setPage((p) => p + 1);
                    }}
                  >
                    [NEXT 100]
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
      <PaneTerminalFooter />
    </div>
  );
};

