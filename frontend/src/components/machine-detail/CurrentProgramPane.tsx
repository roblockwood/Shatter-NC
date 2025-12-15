import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';
import './CurrentProgramPane.css';

interface Deployment {
  id: number;
  deployed_filename: string;
  deployed_at: string;
  validation_passed?: boolean;
  program_id?: number;
}

interface CurrentProgramPaneProps {
  machineId: number;
  machineStatus?: string;
  onExpand?: () => void;
}

export const CurrentProgramPane: React.FC<CurrentProgramPaneProps> = ({ machineId, machineStatus, onExpand }) => {
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCurrentDeployment = async () => {
      try {
        setLoading(true);
        // Try to get current deployment - we'll need to check what the actual endpoint is
        // For now, let's try the deployments endpoint
        const response = await fetch(`${API_BASE_URL}/api/programs/machines/${machineId}/deployments?current_only=true`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            setDeployment(data[0]);
          } else {
            setDeployment(null);
          }
        }
      } catch (error) {
        console.error('Error fetching current deployment:', error);
        setDeployment(null);
      } finally {
        setLoading(false);
      }
    };

    fetchCurrentDeployment();
    // Refresh every 30 seconds
    const interval = setInterval(fetchCurrentDeployment, 30000);
    return () => clearInterval(interval);
  }, [machineId]);

  const isRunning = machineStatus?.includes('Running');

  return (
    <div 
      className="current-program-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ CURRENT PROGRAM {'─'.repeat(25)}</span>
            {onExpand && (
              <button 
                className="expand-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  onExpand();
                }}
                title="Expand"
              >
                [EXPAND]
              </button>
            )}
            <span>┐</span>
          </div>
        </div>
      </div>
      <div className="terminal-box-content">
        {loading ? (
          <div className="program-loading">LOADING...</div>
        ) : !deployment || !isRunning ? (
          <div className="program-empty">
            {isRunning ? 'NO PROGRAM RUNNING' : '───────'}
          </div>
        ) : (
          <div className="program-info">
            <div className="program-row">
              <span className="program-label">PROGRAM:</span>
              <span className="program-value">{deployment.deployed_filename}</span>
            </div>
            <div className="program-row">
              <span className="program-label">DEPLOYED:</span>
              <span className="program-value">
                {new Date(deployment.deployed_at).toLocaleString()}
              </span>
            </div>
            <div className="program-row">
              <span className="program-label">STATUS:</span>
              <span className={`program-value ${deployment.validation_passed !== false ? 'text-success' : 'text-error'}`}>
                {deployment.validation_passed !== false ? '[VALIDATED] ✓' : '[INVALID] ✕'}
              </span>
            </div>
          </div>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

