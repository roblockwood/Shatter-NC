import React from 'react';
import type { OnlineSummaryMachine } from '../../../api/summary';
import './SummaryRow.css';

interface OnlineSummaryRowProps {
  machine: OnlineSummaryMachine;
}

export const OnlineSummaryRow: React.FC<OnlineSummaryRowProps> = ({ machine }) => {
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

  const getServiceIcon = (status: string) => {
    return status === 'connected' ? '●' : '○';
  };

  const getServiceClass = (status: string) => {
    return status === 'connected' ? 'text-success' : 'text-error';
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
      <div className="summary-cell services">
        <span className={getServiceClass(machine.services.http.status)}>
          HTTP {getServiceIcon(machine.services.http.status)}
        </span>
        {' '}
        <span className={getServiceClass(machine.services.ftp.status)}>
          FTP {getServiceIcon(machine.services.ftp.status)}
        </span>
      </div>
      <div className="summary-cell last-seen">
        {formatLastSeen()}
      </div>
    </div>
  );
};
