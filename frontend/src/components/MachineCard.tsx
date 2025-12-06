import React, { useState, useRef, useEffect } from 'react';
import { ToolListModal } from './ToolListModal';
import { ValidationResultModal } from './ValidationResultModal';
import './MachineCard.css';

interface Tool {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}

interface Alarm {
  code: string;
  message: string;
  severity?: string;
  level_class?: string;
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
  alarms?: Alarm[];
  error?: string;
  poll_timestamp: string;
  ip_address?: string;
  ftp_username?: string;
  ftp_password?: string;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  enabled?: boolean;
}

interface MachineCardProps {
  machine: MachineStatus;
  editMode?: boolean;
  onDelete?: (machine: MachineStatus) => void;
}

export const MachineCard: React.FC<MachineCardProps> = ({ machine, editMode = false, onDelete }) => {
  // Debug: Log machine status for debugging name color
  console.log(`Machine: ${machine.machine_name}, is_online: ${machine.is_online}, status: "${machine.status}"`);

  const [showToolModal, setShowToolModal] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [selectedFilename, setSelectedFilename] = useState('');
  const [fileContent, setFileContent] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState(false);
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [isEditTesting, setIsEditTesting] = useState(false);
  const [editTestResult, setEditTestResult] = useState<any>(null);
  const [editFormData, setEditFormData] = useState({
    ip_address: machine.ip_address || '',
    ftp_username: machine.ftp_username || '',
    ftp_password: machine.ftp_password || '',
    ftp_port: machine.ftp_port || 21,
    http_port: machine.http_port || 80,
    path: machine.path !== undefined && machine.path !== null ? machine.path : '/program',
    poll_interval_seconds: machine.poll_interval_seconds || 5,
    enabled: machine.enabled !== false,
  });
  const [editMachineName, setEditMachineName] = useState(machine.machine_name || '');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch full machine configuration data on mount
  useEffect(() => {
    const fetchMachineConfig = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/machines/${machine.machine_id}`);
        if (response.ok) {
          const fullMachineData = await response.json();
          // Update form data with fetched configuration
          setEditMachineName(fullMachineData.name || '');
          setEditFormData({
            ip_address: fullMachineData.ip_address || '',
            ftp_username: fullMachineData.ftp_username || '',
            ftp_password: fullMachineData.ftp_password || '',
            ftp_port: fullMachineData.ftp_port || 21,
            http_port: fullMachineData.http_port || 80,
            path: fullMachineData.path !== undefined && fullMachineData.path !== null ? fullMachineData.path : '/program',
            poll_interval_seconds: fullMachineData.poll_interval_seconds || 5,
            enabled: fullMachineData.enabled !== false,
          });
        }
      } catch (error) {
        console.error('Error fetching machine configuration:', error);
      }
    };

    fetchMachineConfig();
  }, [machine.machine_id]);

  const editFormValid = editMachineName && editFormData.ip_address && editFormData.ftp_username && editFormData.ftp_password;

  const handleEditSave = async () => {
    if (!editFormValid) {
      setEditError('Please fill in all required fields');
      return;
    }

    setIsEditSaving(true);
    setEditError(null);
    setEditSuccess(false);

    try {
      const response = await fetch(`http://localhost:8000/api/machines/${machine.machine_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editFormData),
      });

      if (!response.ok) {
        throw new Error(`Update failed: ${response.statusText}`);
      }

      setEditSuccess(true);
      setTimeout(() => {
        setIsEditing(false);
        setEditSuccess(false);
      }, 1500);
    } catch (error) {
      console.error('Edit error:', error);
      setEditError(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsEditSaving(false);
    }
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    setEditError(null);
    setEditSuccess(false);
    setEditTestResult(null);
    setEditMachineName(machine.machine_name || '');
    setEditFormData({
      ip_address: machine.ip_address || '',
      ftp_username: machine.ftp_username || '',
      ftp_password: machine.ftp_password || '',
      ftp_port: machine.ftp_port || 21,
      http_port: machine.http_port || 80,
      path: machine.path !== undefined && machine.path !== null ? machine.path : '/program',
      poll_interval_seconds: machine.poll_interval_seconds || 5,
      enabled: machine.enabled !== false,
    });
  };

  const handleEditTestConnection = async () => {
    if (!editFormData.ip_address) {
      setEditError('IP address required for connection test');
      return;
    }

    setIsEditTesting(true);
    setEditError(null);
    setEditTestResult(null);
    try {
      const response = await fetch(`http://localhost:8000/api/machines/${machine.machine_id}/test`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();

        // Check if connection actually succeeded
        if (result.overall_status === 'online') {
          setEditTestResult(result);
        } else {
          // Build error message from failed services
          const errors = [];
          if (!result.http?.success) {
            errors.push(`HTTP: ${result.http?.error || 'Connection failed'}`);
          }
          if (!result.ftp?.success) {
            errors.push(`FTP: ${result.ftp?.error || 'Connection failed'}`);
          }
          setEditError(`Connection test failed: ${errors.join(', ')}`);
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setEditError(errorData.detail || 'Connection test failed');
      }
    } catch (err) {
      setEditError(`Test failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsEditTesting(false);
    }
  };

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
      setFileContent(content); // Store for upload

      const response = await fetch(`http://localhost:8000/api/programs/machines/${machine.machine_id}/programs/validate`, {
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
      setFileContent('');
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
        {isEditing ? (
          <input
            type="text"
            value={editMachineName}
            onChange={(e) => setEditMachineName(e.target.value)}
            className="machine-name-edit"
            disabled={isEditSaving}
          />
        ) : (
          <span className={`machine-name ${!machine.is_online ? 'text-error' : (machine.status?.includes('Running') ? 'text-glow' : 'text-muted')}`}>{machine.machine_name}</span>
        )}
        <div className="machine-header-actions">
          {!isEditing && machine.alarms && machine.alarms.length > 0 && (
            <div className={`alarm-indicator has-alarms ${!machine.is_online ? 'blink' : ''}`}>
              <div className="alarm-label">
                {machine.alarms.length} ALARMS
              </div>
              <div className="alarm-tooltip">
                <div className="alarm-tooltip-title">
                  {machine.alarms.length} ALARM{machine.alarms.length > 1 ? 'S' : ''}
                </div>
                <div className="alarm-tooltip-list">
                  {machine.alarms.map((alarm, idx) => (
                    <div key={idx} className="alarm-tooltip-item">
                      <span className="alarm-tooltip-code">{alarm.code}</span>
                      <span className="alarm-tooltip-message">{alarm.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {editMode && !isEditing && (
            <>
              <button
                className="card-action-btn"
                onClick={() => setIsEditing(true)}
                title="Edit machine"
              >
                [=]
              </button>
              <button
                className="card-action-btn delete"
                onClick={() => onDelete?.(machine)}
                title="Delete machine"
              >
                [X]
              </button>
            </>
          )}
        </div>
      </div>

      <div className="machine-card-divider">
        ├{'─'.repeat(30)}┤
      </div>

      {isEditing ? (
        <div className="machine-edit-form">
          {editError && (
            <div className="form-error text-error">
              {editError}
            </div>
          )}

          {editSuccess && (
            <div className="form-success text-success">
              Machine updated successfully!
            </div>
          )}

          <div className="form-row">
            <label>IP:</label>
            <input
              type="text"
              value={editFormData.ip_address}
              onChange={(e) => setEditFormData({ ...editFormData, ip_address: e.target.value })}
              placeholder="192.168.1.100"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row">
            <label>FTP USER:</label>
            <input
              type="text"
              value={editFormData.ftp_username}
              onChange={(e) => setEditFormData({ ...editFormData, ftp_username: e.target.value })}
              placeholder="anonymous"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row">
            <label>FTP PASS:</label>
            <input
              type="password"
              value={editFormData.ftp_password}
              onChange={(e) => setEditFormData({ ...editFormData, ftp_password: e.target.value })}
              placeholder="anonymous"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row">
            <label>FTP PATH:</label>
            <input
              type="text"
              value={editFormData.path}
              onChange={(e) => setEditFormData({ ...editFormData, path: e.target.value })}
              placeholder="/program"
              disabled={isEditSaving}
            />
          </div>

          <div className="form-row-inline">
            <div>
              <label>FTP PORT:</label>
              <input
                type="number"
                min="1"
                max="65535"
                value={editFormData.ftp_port}
                onChange={(e) => setEditFormData({ ...editFormData, ftp_port: parseInt(e.target.value) })}
                disabled={isEditSaving}
              />
            </div>
            <div>
              <label>HTTP PORT:</label>
              <input
                type="number"
                min="1"
                max="65535"
                value={editFormData.http_port}
                onChange={(e) => setEditFormData({ ...editFormData, http_port: parseInt(e.target.value) })}
                disabled={isEditSaving}
              />
            </div>
          </div>

          <div className="form-row-inline">
            <div>
              <label>POLL INTERVAL:</label>
              <input
                type="number"
                min="1"
                max="300"
                value={editFormData.poll_interval_seconds}
                onChange={(e) => setEditFormData({ ...editFormData, poll_interval_seconds: parseInt(e.target.value) })}
                disabled={isEditSaving}
              />
              <span className="form-hint">seconds</span>
            </div>
            <div className="form-checkbox">
              <input
                type="checkbox"
                id={`enabled-${machine.machine_id}`}
                checked={editFormData.enabled}
                onChange={(e) => setEditFormData({ ...editFormData, enabled: e.target.checked })}
                disabled={isEditSaving}
              />
              <label htmlFor={`enabled-${machine.machine_id}`}>ENABLED</label>
            </div>
          </div>

          {editTestResult && (
            <div className="form-success text-success">
              Connection successful!
            </div>
          )}

          <div className="form-actions">
            <button
              className="form-button test"
              onClick={handleEditTestConnection}
              disabled={!editFormData.ip_address || isEditSaving || isEditTesting}
            >
              {isEditTesting ? '[ TESTING... ]' : '[ TEST CONNECTION ]'}
            </button>
            <button
              className="form-button cancel"
              onClick={handleEditCancel}
              disabled={isEditSaving}
            >
              [ CANCEL ]
            </button>
            <button
              className="form-button save"
              onClick={handleEditSave}
              disabled={!editFormValid || isEditSaving}
            >
              {isEditSaving ? '[ SAVING... ]' : '[ SAVE ]'}
            </button>
          </div>
        </div>
      ) : machine.is_online ? (
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
        tools={(machine.tools || []) as any}
        machineName={machine.machine_name}
      />

      <ValidationResultModal
        isOpen={showValidationModal}
        onClose={() => {
          setShowValidationModal(false);
          setFileContent('');
          setValidationResult(null);
          setSelectedFilename('');
        }}
        result={validationResult}
        filename={selectedFilename}
        machineId={machine.machine_id}
        machineName={machine.machine_name}
        machinePath={machine.path || '/PROGRAM'}
        fileContent={fileContent}
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
