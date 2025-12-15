import React from 'react';
import type { RunningSummaryMachine } from '../../../api/summary';
import { StatusOscilloscope } from '../../ui/StatusOscilloscope';
import './SummaryRow.css';

interface RunningSummaryRowProps {
  machine: RunningSummaryMachine;
  compact?: boolean;
  timeRange?: '1h' | '8h' | '24h' | '7d';
  onMachineClick?: (machineId: number) => void;
}

export const RunningSummaryRow: React.FC<RunningSummaryRowProps> = ({ machine, compact = false, timeRange = '24h', onMachineClick }) => {
  // Normalize status to match machine status values: operating, standby, stopped, error, off
  const normalizeStatus = (status: string | undefined): string => {
    if (!status) return 'standby';
    const lower = status.toLowerCase().trim();
    
    // Map to actual machine statuses
    if (lower === 'operating' || lower.includes('operating')) return 'operating';
    if (lower === 'standby' || lower.includes('standby') || lower.includes('idle')) return 'standby';
    if (lower === 'stopped' || lower.includes('stopped')) return 'stopped';
    if (lower === 'error' || lower.includes('error') || lower.includes('occurred')) return 'error';
    if (lower === 'off' || lower.includes('off')) return 'off';
    
    // Legacy mappings
    if (lower.includes('running')) return 'operating';
    return 'standby';
  };

  const getStatusClass = () => {
    const normalized = normalizeStatus(machine.current_status);
    if (normalized === 'operating') return 'text-success';
    if (normalized === 'error') return 'text-error';
    if (normalized === 'stopped') return 'text-warning';
    if (normalized === 'off') return 'text-dim';
    return 'text-info'; // standby
  };

  const getStatusDisplay = () => {
    const normalized = normalizeStatus(machine.current_status);
    return normalized.toUpperCase();
  };

  if (compact) {
    // Compact layout for popup (4 columns: machine, run time, percentage, status oscilloscope)
    return (
      <div 
        className="summary-row"
        onClick={(e) => {
          if (onMachineClick) {
            e.stopPropagation();
            onMachineClick(machine.machine_id);
          }
        }}
        style={{ cursor: onMachineClick ? 'pointer' : 'default' }}
      >
        <div className="summary-cell machine-name">
          <span className={getStatusClass()}>
            {machine.machine_name} {machine.current_status && `(${getStatusDisplay()})`}
          </span>
        </div>
        <div className="summary-cell run-time" style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>
          {machine.total_run_time_formatted}
        </div>
        <div className="summary-cell percentage" style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>
          {machine.run_percentage.toFixed(1)}%
        </div>
        <div className="summary-cell graph">
          {machine.status_history && machine.status_history.length > 0 ? (
            <StatusOscilloscope
              statusHistory={machine.status_history}
              currentStatus={machine.current_status}
              timeRange={timeRange}
              compact={true}
            />
          ) : (
            <span className="text-dim">-</span>
          )}
        </div>
      </div>
    );
  }

  // Full layout for modal (4 columns with enhanced oscilloscope)
  return (
    <div className="summary-row summary-row-modal">
      <div className="summary-cell machine-name">
        <span className={getStatusClass()}>{machine.machine_name}</span>
      </div>
      <div className="summary-cell run-time">
        {machine.total_run_time_formatted}
      </div>
      <div className="summary-cell percentage">
        {Math.round(machine.run_percentage)}%
      </div>
      <div className="summary-cell graph summary-cell-oscilloscope-full">
        {machine.status_history && machine.status_history.length > 0 ? (
          <StatusOscilloscope
            statusHistory={machine.status_history}
            currentStatus={machine.current_status}
            timeRange={timeRange}
            compact={false}
          />
        ) : (
          <span className="text-dim">-</span>
        )}
      </div>
    </div>
  );
};
