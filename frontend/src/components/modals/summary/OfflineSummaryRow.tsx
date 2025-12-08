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

  const getServiceError = (serviceType: 'http' | 'ftp') => {
    const service = machine.services[serviceType];
    if (service.last_error) {
      return service.last_error;
    }
    return service.status === 'not_responding' ? 'Not responding' : 'Unknown';
  };

  const getServiceStatus = (serviceType: 'http' | 'ftp') => {
    const service = machine.services[serviceType];
    return service.status === 'not_responding' ? '○' : '?';
  };

  if (compact) {
    // Compact layout for popup (4 columns: machine, offline duration, since, services)
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
        <div className="summary-cell services">
          <span className="text-error">
            H{getServiceStatus('http')}
          </span>
          {' '}
          <span className="text-error">
            F{getServiceStatus('ftp')}
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
      <div className="summary-cell service-errors">
        <div className="service-error">
          <span className="service-label">HTTP:</span> {getServiceError('http')}
        </div>
        <div className="service-error">
          <span className="service-label">FTP:</span> {getServiceError('ftp')}
        </div>
      </div>
      <div className="summary-cell last-status">
        {machine.last_known_status || 'Unknown'}
      </div>
    </div>
  );
};
