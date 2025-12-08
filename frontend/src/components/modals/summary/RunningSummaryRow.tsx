import React from 'react';
import type { RunningSummaryMachine } from '../../../api/summary';
import './SummaryRow.css';

interface RunningSummaryRowProps {
  machine: RunningSummaryMachine;
  compact?: boolean;
}

export const RunningSummaryRow: React.FC<RunningSummaryRowProps> = ({ machine, compact = false }) => {
  const getStatusClass = () => {
    if (!machine.current_status) return 'text-dim';
    if (machine.current_status.toLowerCase().includes('running')) return 'text-success';
    if (machine.current_status.toLowerCase().includes('error')) return 'text-error';
    return 'text-info';
  };

  const getLastActive = () => {
    if (!machine.last_run_start) return 'Never';

    const lastRun = new Date(machine.last_run_start);
    const now = new Date();
    const diffMs = now.getTime() - lastRun.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    // If currently running
    if (machine.current_status?.toLowerCase().includes('running')) {
      return 'Running now';
    }

    // Format relative time
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (compact) {
    // Compact layout for popup (4 columns: machine, run time, percentage, last active)
    return (
      <div className="summary-row">
        <div className="summary-cell machine-name">
          <span className={getStatusClass()}>{machine.machine_name}</span>
        </div>
        <div className="summary-cell run-time">
          {machine.total_run_time_formatted}
        </div>
        <div className="summary-cell percentage">
          {machine.run_percentage.toFixed(1)}%
        </div>
        <div className="summary-cell last-active">
          {getLastActive()}
        </div>
      </div>
    );
  }

  // Full layout for modal (5 columns)
  return (
    <div className="summary-row">
      <div className="summary-cell machine-name">
        <span className={getStatusClass()}>{machine.machine_name}</span>
      </div>
      <div className="summary-cell run-time">
        {machine.total_run_time_formatted}
      </div>
      <div className="summary-cell percentage">
        <div className="percentage-bar-container">
          <div
            className="percentage-bar"
            style={{ width: `${Math.min(machine.run_percentage, 100)}%` }}
          />
          <span className="percentage-text">{machine.run_percentage}%</span>
        </div>
      </div>
      <div className="summary-cell last-active">
        {getLastActive()}
      </div>
      <div className="summary-cell program">
        {machine.current_program || '-'}
      </div>
    </div>
  );
};
