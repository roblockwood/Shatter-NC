import React from 'react';
import type { OfflineSummaryMachine } from '../../../api/summary';
import './SummaryRow.css';

interface OfflineSummaryRowProps {
  machine: OfflineSummaryMachine;
}

export const OfflineSummaryRow: React.FC<OfflineSummaryRowProps> = ({ machine }) => {
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
