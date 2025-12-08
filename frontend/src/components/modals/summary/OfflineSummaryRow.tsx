import React from 'react';
import type { OfflineSummaryMachine } from '../../../api/summary';
import './SummaryRow.css';

interface OfflineSummaryRowProps {
  machine: OfflineSummaryMachine;
  compact?: boolean;
}

export const OfflineSummaryRow: React.FC<OfflineSummaryRowProps> = ({ machine, compact = false }) => {
  const formatOfflineSince = () => {
    if (!machine.offline_since) return 'Unknown';

    const offlineSince = new Date(machine.offline_since);
    return offlineSince.toLocaleString();
  };

  const getLastFailureReason = () => {
    if (!machine.polling_history_8h || machine.polling_history_8h.length === 0) {
      return 'Unknown';
    }
    // Find the last failed poll
    const lastFailure = [...machine.polling_history_8h].reverse().find(p => !p.success);
    if (lastFailure) {
      const failureTime = new Date(lastFailure.time);
      const now = new Date();
      const diffMins = Math.floor((now.getTime() - failureTime.getTime()) / 1000 / 60);
      return `Failed ${diffMins}m ago`;
    }
    return 'Unknown';
  };

  const getFailureCount = () => {
    if (!machine.polling_history_8h) return 0;
    return machine.polling_history_8h.filter(p => !p.success).length;
  };

  if (compact) {
    // Compact layout for popup (4 columns: machine, offline duration, since, failures)
    return (
      <div className="summary-row">
        <div className="summary-cell machine-name">
          <span className="text-error">{machine.machine_name}</span>
        </div>
        <div className="summary-cell offline-duration">
          {machine.offline_duration_formatted}
        </div>
        <div className="summary-cell offline-since">
          {formatOfflineSince().split(',')[0]}
        </div>
        <div className="summary-cell failures">
          <span className="text-error">
            {getFailureCount()} failures
          </span>
        </div>
      </div>
    );
  }

  // Full layout for modal (5 columns)
  return (
    <div className="summary-row">
      <div className="summary-cell machine-name">
        <span className="text-error">{machine.machine_name}</span>
      </div>
      <div className="summary-cell offline-duration">
        {machine.offline_duration_formatted}
      </div>
      <div className="summary-cell offline-since">
        {formatOfflineSince()}
      </div>
      <div className="summary-cell failure-info">
        <div className="text-error">
          {getLastFailureReason()}
        </div>
        <div className="text-dim text-xs">
          {getFailureCount()} total failures in last 8h
        </div>
      </div>
      <div className="summary-cell last-status">
        {machine.last_known_status || 'Unknown'}
      </div>
    </div>
  );
};
