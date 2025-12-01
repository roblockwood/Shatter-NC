import React, { useState, useRef } from 'react';
import { TerminalBox, ProgressBar, StatusIndicator } from './ui';
import { ToolListModal } from './ToolListModal';
import { ValidationResultModal } from './ValidationResultModal';
import './MachineCard.css';

interface Tool {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}

interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  tools?: Tool[];
  current_tool?: number;
  alarms?: Array<{ code: string; message: string }>;
  error?: string;
  poll_timestamp: string;
}

interface MachineCardProps {
  machine: MachineStatus;
}

export const MachineCard: React.FC<MachineCardProps> = ({ machine }) => {
  const [showToolModal, setShowToolModal] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [selectedFilename, setSelectedFilename] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getStatusType = () => {
    if (!machine.is_online) return 'offline';
    if (machine.status?.includes('Error')) return 'error';
    if (machine.status?.includes('Running')) return 'running';
    return 'idle';
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFilename(file.name);
    setIsValidating(true);

    try {
      const content = await file.text();
      const response = await fetch(`http://localhost:8000/api/machines/${machine.machine_id}/programs/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gcode_content: content }),
      });

      if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
      }

      const result = await response.json();
      setValidationResult(result);
      setShowValidationModal(true);
    } catch (error) {
      console.error('Validation error:', error);
      alert(`Validation failed: ${error}`);
    } finally {
      setIsValidating(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const formatTime = (time: string | undefined) => {
    if (!time || time === '0000:00:00.0') return '00:00:00';
    return time.substring(0, 8); // Remove decimal if present
  };

  return (
    <div className="machine-card">
      <div className="machine-card-header">
        <span className="machine-name text-glow">{machine.machine_name}</span>
        <StatusIndicator
          status={getStatusType()}
          label=""
          blink={!machine.is_online}
        />
      </div>

      <div className="machine-card-divider">
        ├{'─'.repeat(30)}┤
      </div>

      {machine.is_online ? (
        <div className="machine-card-content">
          <div className="machine-row">
            <span className="label">STATUS:</span>
            <span className={`value ${getStatusType() === 'error' ? 'text-error' : 'text-success'}`}>
              {machine.status || 'UNKNOWN'}
            </span>
          </div>

          <div className="machine-row">
            <span className="label">CYCLE:</span>
            <span className="value">{formatTime(machine.cycle_time)}</span>
          </div>

          <div className="machine-row">
            <span className="label">POWER:</span>
            <span className="value">{machine.power_on_hours || '00:00:00'}</span>
          </div>

          {machine.counters && machine.counters.length > 0 && (
            <div className="machine-row">
              <span className="label">PARTS:</span>
              <span className="value">{machine.counters[0].count}</span>
            </div>
          )}

          {machine.current_tool && (
            <div className="machine-row">
              <span className="label">TOOL:</span>
              <span className="value text-info">T{String(machine.current_tool).padStart(2, '0')}</span>
            </div>
          )}

          {machine.alarms && machine.alarms.length > 0 && (
            <>
              <div className="machine-card-divider-thin">
                {'─'.repeat(32)}
              </div>
              <div className="machine-alarms">
                <div className="alarm-header text-error blink">
                  ⚠ {machine.alarms.length} ALARM{machine.alarms.length > 1 ? 'S' : ''}
                </div>
                {machine.alarms.slice(0, 2).map((alarm, idx) => (
                  <div key={idx} className="alarm-item text-warning">
                    {alarm.code}: {alarm.message.substring(0, 20)}
                  </div>
                ))}
              </div>
            </>
          )}

          {machine.tools && machine.tools.length > 0 && (
            <>
              <div className="machine-card-divider-thin">
                {'─'.repeat(32)}
              </div>
              <div
                className="tool-summary"
                onClick={() => setShowToolModal(true)}
                style={{ cursor: 'pointer' }}
              >
                <div className="tool-count text-muted">
                  {machine.tools.length} TOOLS IN ATC [VIEW]
                </div>
              </div>
            </>
          )}

          <div className="machine-card-divider-thin">
            {'─'.repeat(32)}
          </div>

          <div className="machine-actions">
            <button
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isValidating}
            >
              {isValidating ? '[ VALIDATING... ]' : '[ UPLOAD & VALIDATE ]'}
            </button>
          </div>

          <div className="machine-card-divider-thin">
            {'─'.repeat(32)}
          </div>

          <div className="machine-timestamp">
            LAST UPDATE: {new Date(machine.poll_timestamp).toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <div className="machine-card-content machine-offline">
          <div className="machine-row">
            <span className="label text-error">OFFLINE</span>
          </div>
          {machine.error && (
            <div className="machine-row">
              <span className="value text-muted">{machine.error}</span>
            </div>
          )}
          <div className="machine-card-divider-thin">
            {'─'.repeat(32)}
          </div>
          <div className="machine-timestamp">
            LAST SEEN: {new Date(machine.poll_timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}

      <ToolListModal
        isOpen={showToolModal}
        onClose={() => setShowToolModal(false)}
        tools={machine.tools || []}
        machineName={machine.machine_name}
      />

      <ValidationResultModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        result={validationResult}
        filename={selectedFilename}
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".nc,.NC,.txt"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </div>
  );
};
