import React from 'react';
import type { OnlineSummaryMachine } from '../../../api/summary';
import './SummaryRow.css';

interface OnlineSummaryRowProps {
  machine: OnlineSummaryMachine;
  compact?: boolean;
}

export const OnlineSummaryRow: React.FC<OnlineSummaryRowProps> = ({ machine, compact = false }) => {
  const getHealthIcon = () => {
    switch (machine.connection_health) {
      case 'healthy':
        return '●';
      case 'degraded':
        return '◐';
      case 'stale':
        return '○';
      default:
        return '?';
    }
  };

  const getHealthClass = () => {
    switch (machine.connection_health) {
      case 'healthy':
        return 'text-success';
      case 'degraded':
        return 'text-warning';
      case 'stale':
        return 'text-error';
      default:
        return 'text-dim';
    }
  };

  const getPollingSuccessRate = () => {
    if (!machine.polling_history_8h || machine.polling_history_8h.length === 0) {
      return 'N/A';
    }
    const successCount = machine.polling_history_8h.filter(p => p.success).length;
    const rate = Math.round((successCount / machine.polling_history_8h.length) * 100);
    return `${rate}%`;
  };

  const getAverageResponseTime = () => {
    if (!machine.polling_history_8h || machine.polling_history_8h.length === 0) {
      return 'N/A';
    }
    const times = machine.polling_history_8h.filter(p => p.response_time_ms);
    if (times.length === 0) return 'N/A';
    const avg = Math.round(times.reduce((sum, p) => sum + (p.response_time_ms || 0), 0) / times.length);
    return `${avg}ms`;
  };

  const getPollingTrendIndicator = () => {
    if (!machine.polling_history_8h || machine.polling_history_8h.length < 2) {
      return '';
    }
    // Simple trend: check if recent polls are successful
    const recentPolls = machine.polling_history_8h.slice(-3);
    const recentSuccess = recentPolls.filter(p => p.success).length;
    if (recentSuccess === recentPolls.length) return '↗'; // All recent successful
    if (recentSuccess === 0) return '↘'; // All recent failed
    return '→'; // Mixed
  };

  const formatLastSeen = () => {
    if (!machine.last_seen_at) return 'Never';

    const lastSeen = new Date(machine.last_seen_at);
    const now = new Date();
    const diffMs = now.getTime() - lastSeen.getTime();
    const diffSecs = Math.floor(diffMs / 1000);

    if (diffSecs < 30) return 'Just now';
    if (diffSecs < 60) return `${diffSecs}s ago`;

    const diffMins = Math.floor(diffSecs / 60);
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    return `${diffHours}h ago`;
  };

  if (compact) {
    // Compact layout for popup (4 columns: machine, online duration, health, polling)
    return (
      <div className="summary-row">
        <div className="summary-cell machine-name">
          <span className="text-success">{machine.machine_name}</span>
        </div>
        <div className="summary-cell online-duration">
          {machine.online_duration_formatted}
        </div>
        <div className="summary-cell health">
          <span className={getHealthClass()}>
            {getHealthIcon()}
          </span>
        </div>
        <div className="summary-cell polling">
          <span className="text-info">
            {getPollingSuccessRate()} {getPollingTrendIndicator()}
          </span>
        </div>
      </div>
    );
  }

  // Full layout for modal (5 columns)
  return (
    <div className="summary-row">
      <div className="summary-cell machine-name">
        <span className="text-success">{machine.machine_name}</span>
      </div>
      <div className="summary-cell online-duration">
        {machine.online_duration_formatted}
      </div>
      <div className="summary-cell health">
        <span className={getHealthClass()}>
          {getHealthIcon()} {machine.connection_health}
        </span>
      </div>
      <div className="summary-cell polling">
        <span className="text-info">
          {getAverageResponseTime()}
        </span>
        <span className="text-dim"> | </span>
        <span className="text-info">
          {getPollingSuccessRate()} {getPollingTrendIndicator()}
        </span>
      </div>
      <div className="summary-cell last-seen">
        {formatLastSeen()}
      </div>
    </div>
  );
};
