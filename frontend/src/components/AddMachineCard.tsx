import React, { useState } from 'react';
import './AddMachineCard.css';
import { API_BASE } from '../config/api';

interface MachineData {
  name: string;
  ip_address: string;
  ftp_username: string;
  ftp_password: string;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  enabled?: boolean;
  model?: string;
}

interface AddMachineCardProps {
  onCancel?: () => void;
  onAdd?: (machine: any) => void;
  fullWidth?: boolean;
}

export const AddMachineCard: React.FC<AddMachineCardProps> = ({ onAdd, onCancel: onCancelProp, fullWidth = false }) => {
  const [isActive, setIsActive] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<MachineData>({
    name: '',
    ip_address: '',
    ftp_username: 'anonymous',
    ftp_password: 'anonymous',
    ftp_port: 21,
    http_port: 80,
    path: '/PROGRAM',
    poll_interval_seconds: 5,
    enabled: true,
    model: 'Brother CNC'
  });

  const isFormValid = formData.name && formData.ip_address && formData.ftp_username && formData.ftp_password;

  const handleSave = async () => {
    if (!isFormValid) {
      setError('Please fill in all required fields');
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/machines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const newMachine = await response.json();
        setIsActive(false);
        setFormData({
          name: '',
          ip_address: '',
          ftp_username: 'anonymous',
          ftp_password: 'anonymous',
          ftp_port: 21,
          http_port: 80,
          path: '/PROGRAM',
          poll_interval_seconds: 5,
          enabled: true,
          model: 'Brother CNC'
        });
        // Notify parent that machine was added
        if (onAdd) {
          onAdd({
            machine_id: newMachine.id,
            machine_name: newMachine.name,
            ip_address: newMachine.ip_address,
            ftp_username: newMachine.ftp_username,
            ftp_password: newMachine.ftp_password,
            ftp_port: newMachine.ftp_port,
            http_port: newMachine.http_port,
            poll_interval_seconds: newMachine.poll_interval_seconds,
            enabled: newMachine.enabled,
            is_online: false,
            status: 'offline',
            poll_timestamp: new Date().toISOString(),
          });
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Failed to create machine');
      }
    } catch (err) {
      setError(`Save failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setIsActive(false);
    setFormData({
      name: '',
      ip_address: '',
      ftp_username: 'anonymous',
      ftp_password: 'anonymous',
      ftp_port: 21,
      http_port: 80,
      path: '/PROGRAM',
      poll_interval_seconds: 5,
      enabled: true,
      model: 'Brother CNC'
    });
    setError(null);
    if (onCancelProp) {
      onCancelProp();
    }
  };

  if (!isActive) {
    return (
      <div
        className={`add-machine-card ${fullWidth ? 'full-width' : ''}`}
        onClick={() => setIsActive(true)}
      >
        <div className="add-machine-content">
          <div className="add-icon">+</div>
          <div className="add-text">[ ADD MACHINE ]</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`machine-card add-machine-editing ${fullWidth ? 'full-width' : ''}`}>
      <div className="machine-card-header">
        <input
          className="machine-name-input"
          placeholder="NEW MACHINE"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          disabled={isSaving}
        />
        <div className="machine-header-actions">
          <button
            className="card-action-btn"
            onClick={handleSave}
            disabled={!isFormValid || isSaving}
            title="Save machine"
          >
            [✓]
          </button>
          <button
            className="card-action-btn delete"
            onClick={handleCancel}
            disabled={isSaving}
            title="Cancel"
          >
            [X]
          </button>
        </div>
      </div>

      <div className="machine-card-divider">
        ├{'─'.repeat(30)}┤
      </div>

      <div className="machine-edit-form">
        {error && (
          <div className="form-error text-error">
            {error}
          </div>
        )}

        <div className="form-row">
          <label>IP:</label>
          <input
            type="text"
            value={formData.ip_address}
            onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
            placeholder="192.168.1.100"
            disabled={isSaving}
          />
        </div>

        <div className="form-row">
          <label>FTP USER:</label>
          <input
            type="text"
            value={formData.ftp_username}
            onChange={(e) => setFormData({ ...formData, ftp_username: e.target.value })}
            placeholder="anonymous"
            disabled={isSaving}
          />
        </div>

        <div className="form-row">
          <label>FTP PASS:</label>
          <input
            type="password"
            value={formData.ftp_password}
            onChange={(e) => setFormData({ ...formData, ftp_password: e.target.value })}
            placeholder="anonymous"
            disabled={isSaving}
          />
        </div>

        <div className="form-row-inline">
          <div>
            <label>FTP PORT:</label>
            <input
              type="number"
              min="1"
              max="65535"
              value={formData.ftp_port}
              onChange={(e) => setFormData({ ...formData, ftp_port: parseInt(e.target.value) })}
              disabled={isSaving}
            />
          </div>
          <div>
            <label>HTTP PORT:</label>
            <input
              type="number"
              min="1"
              max="65535"
              value={formData.http_port}
              onChange={(e) => setFormData({ ...formData, http_port: parseInt(e.target.value) })}
              disabled={isSaving}
            />
          </div>
        </div>

        <div className="form-row">
          <label>FTP PATH:</label>
          <input
            type="text"
            value={formData.path}
            onChange={(e) => setFormData({ ...formData, path: e.target.value })}
            placeholder="/PROGRAM"
            disabled={isSaving}
          />
        </div>

        <div className="form-row-inline">
          <div>
            <label>POLL INTERVAL:</label>
            <input
              type="number"
              min="1"
              max="300"
              value={formData.poll_interval_seconds}
              onChange={(e) => setFormData({ ...formData, poll_interval_seconds: parseInt(e.target.value) })}
              disabled={isSaving}
            />
            <span className="form-hint">seconds</span>
          </div>
          <div className="form-checkbox">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              disabled={isSaving}
            />
            <label htmlFor="enabled">ENABLED</label>
          </div>
        </div>

        <div className="form-actions">
          <button
            className="form-button cancel"
            onClick={handleCancel}
            disabled={isSaving}
          >
            [ CANCEL ]
          </button>
          <button
            className="form-button save"
            onClick={handleSave}
            disabled={!isFormValid || isSaving}
          >
            {isSaving ? '[ SAVING... ]' : '[ SAVE ]'}
          </button>
        </div>
      </div>
    </div>
  );
};
