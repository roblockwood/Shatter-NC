import React from 'react';
import './StatusIndicator.css';

type Status = 'online' | 'offline' | 'warning' | 'error' | 'idle' | 'running';

interface StatusIndicatorProps {
  status: Status;
  label?: string;
  blink?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  blink = false,
  className = '',
}) => {
  const statusConfig = {
    online: { icon: '●', color: 'var(--color-success)', text: 'ONLINE' },
    running: { icon: '►', color: 'var(--color-success)', text: 'RUNNING' },
    offline: { icon: '○', color: 'var(--color-offline)', text: 'OFFLINE' },
    idle: { icon: '◌', color: 'var(--color-info)', text: 'IDLE' },
    warning: { icon: '◐', color: 'var(--color-warning)', text: 'WARNING' },
    error: { icon: '✕', color: 'var(--color-error)', text: 'ERROR' },
  };

  const config = statusConfig[status];

  return (
    <span
      className={`status-indicator ${blink ? 'status-blink' : ''} ${className}`}
      style={{ color: config.color }}
    >
      <span className="status-icon">{config.icon}</span>
      {label !== undefined && <span className="status-label"> {label}</span>}
      {label === undefined && <span className="status-label"> [{config.text}]</span>}
    </span>
  );
};
