import React from 'react';
import type { MachineStatusSummary } from '../../../api/summary';
import { generatePollingGraph, getUptimeClass, formatUptimePercent } from '../../../utils/pollingGraphGenerator';
import './SummaryRow.css';

interface MachineStatusRowProps {
  machine: MachineStatusSummary;
  compact?: boolean;
}

export const MachineStatusRow: React.FC<MachineStatusRowProps> = ({ machine, compact = false }) => {
  const getStatusIcon = () => {
    if (machine.is_online) {
      return '●'; // Filled circle for online
    } else {
      return '○'; // Empty circle for offline
    }
  };

  const getStatusColor = () => {
    return machine.is_online ? 'text-success' : 'text-error';
  };

  const getDurationText = () => {
    if (machine.is_online) {
      return machine.online_duration_formatted;
    } else {
      return machine.offline_duration_formatted;
    }
  };

  const getConnectionHealthIcon = () => {
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

  const pollingGraph = generatePollingGraph(machine.polling_history_8h, 30);
  const uptimePercent = machine.uptime_8h_percent;

  if (compact) {
    // Compact layout for popup (4 columns: machine, status, duration, graph)
    return (
      <div className="summary-row">
        <div className="summary-cell machine-name">
          <span className={getStatusColor()}>
            {getStatusIcon()} {machine.machine_name}
          </span>
        </div>
        <div className="summary-cell duration">
          {getDurationText()}
        </div>
        <div className="summary-cell graph">
          <code className={getUptimeClass(uptimePercent)}>
            {pollingGraph}
          </code>
        </div>
        <div className="summary-cell uptime">
          <span className={getUptimeClass(uptimePercent)}>
            {formatUptimePercent(uptimePercent)}
          </span>
        </div>
      </div>
    );
  }

  // Full layout for modal (6 columns: machine, status, duration, graph, uptime, health)
  return (
    <div className="summary-row">
      <div className="summary-cell machine-name">
        <span className={getStatusColor()}>
          {getStatusIcon()} {machine.machine_name}
        </span>
      </div>
      <div className="summary-cell duration">
        {getDurationText()}
      </div>
      <div className="summary-cell graph">
        <code className={getUptimeClass(uptimePercent)}>
          {pollingGraph}
        </code>
      </div>
      <div className="summary-cell uptime">
        <span className={getUptimeClass(uptimePercent)}>
          {formatUptimePercent(uptimePercent)} uptime
        </span>
      </div>
      <div className="summary-cell health">
        <span className={getHealthClass()}>
          {getConnectionHealthIcon()} {machine.connection_health}
        </span>
      </div>
      <div className="summary-cell polls-summary">
        <div className="text-dim text-xs">
          {machine.polling_summary.successful_polls}/{machine.polling_summary.total_polls} polls
        </div>
        {machine.polling_summary.avg_response_time_ms && (
          <div className="text-dim text-xs">
            avg {machine.polling_summary.avg_response_time_ms}ms
          </div>
        )}
      </div>
    </div>
  );
};
