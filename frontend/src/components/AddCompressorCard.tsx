import React, { useState, useEffect } from 'react';
import './AddMachineCard.css';
import { MachineCardAsciiDivider } from './MachineCardAsciiDivider';
import { API_BASE, getApiErrorMessage } from '../config/api';
import type { CompressorStatus } from '../hooks/useWebSocket';

interface CompressorForm {
  name: string;
  ip_address: string;
  poll_interval_seconds: number;
  enabled: boolean;
  kaeser_connect_base_url: string;
  kaeser_username: string;
  kaeser_password: string;
}

interface AddCompressorCardProps {
  onCancel?: () => void;
  onAdd?: (compressor: CompressorStatus) => void;
  fullWidth?: boolean;
  onActiveChange?: (active: boolean) => void;
  startActive?: boolean;
}

function emptyForm(): CompressorForm {
  return {
    name: '',
    ip_address: '',
    poll_interval_seconds: 1,
    enabled: true,
    kaeser_connect_base_url: '',
    kaeser_username: '',
    kaeser_password: '',
  };
}

export const AddCompressorCard: React.FC<AddCompressorCardProps> = ({
  onAdd,
  onCancel: onCancelProp,
  fullWidth = false,
  onActiveChange,
  startActive = false,
}) => {
  const [isActive, setIsActive] = useState(startActive);

  React.useEffect(() => {
    return () => {
      if (isActive && onActiveChange) {
        onActiveChange(false);
      }
    };
  }, [isActive, onActiveChange]);

  useEffect(() => {
    onActiveChange?.(isActive);
  }, [isActive, onActiveChange]);

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<CompressorForm>(emptyForm);

  const kUrl = formData.kaeser_connect_base_url.trim();
  const kUser = formData.kaeser_username.trim();
  const kPass = formData.kaeser_password;
  const kaeserPartial =
    (kUrl || kUser || kPass) && !(kUrl && kUser && kPass);

  const isFormValid = Boolean(
    formData.name?.trim() &&
      formData.ip_address?.trim() &&
      !kaeserPartial
  );

  const handleSave = async () => {
    if (!isFormValid) {
      setError(
        kaeserPartial
          ? 'Kaeser Connect URL, username, and password must all be filled (or all left blank).'
          : 'Name and SC2 host are required'
      );
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { ...formData };
      if (!kUrl && !kUser && !kPass) {
        delete body.kaeser_connect_base_url;
        delete body.kaeser_username;
        delete body.kaeser_password;
      } else {
        body.kaeser_connect_base_url = kUrl;
        body.kaeser_username = kUser;
        body.kaeser_password = kPass;
      }
      const response = await fetch(`${API_BASE}/compressors/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (response.ok) {
        const row = await response.json();
        setIsActive(false);
        setFormData(emptyForm());
        const now = new Date().toISOString();
        onAdd?.({
          asset_kind: 'compressor',
          compressor_id: row.id,
          compressor_name: row.name,
          ip_address: row.ip_address,
          enabled: row.enabled,
          poll_interval_seconds: row.poll_interval_seconds,
          kaeser_connect_base_url: row.kaeser_connect_base_url ?? undefined,
          kaeser_username: row.kaeser_username ?? undefined,
          kaeser_credentials_configured: row.kaeser_credentials_configured,
          is_online: false,
          status: 'offline',
          poll_timestamp: now,
          last_successful_poll_at: null,
          alarms: [],
          layout_config: row.layout_config ?? null,
        });
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(getApiErrorMessage(errorData.detail) || 'Failed to create compressor');
      }
    } catch (err) {
      setError(`Save failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setIsActive(false);
    setFormData(emptyForm());
    setError(null);
    onCancelProp?.();
  };

  if (!isActive) {
    return (
      <div className={`add-machine-card ${fullWidth ? 'full-width' : ''}`}>
        <div className="add-machine-content clickable-content" onClick={() => setIsActive(true)}>
          <div className="add-icon clickable-icon">+</div>
          <div className="add-text">[ ADD COMPRESSOR ]</div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`machine-card add-machine-editing add-compressor-editing ${fullWidth ? 'full-width' : ''}`}
    >
      <div className="machine-card-header">
        <div className="machine-header-edit-row">
          <input
            className="machine-name-input"
            placeholder="NEW COMPRESSOR"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            disabled={isSaving}
          />
          <div className="form-checkbox machine-header-checkbox">
            <input
              type="checkbox"
              id="enabled-new-compressor"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              disabled={isSaving}
            />
            <label htmlFor="enabled-new-compressor">ENABLED</label>
          </div>
        </div>
        <div className="machine-header-actions">
          <button
            className="card-action-btn"
            onClick={handleSave}
            disabled={!isFormValid || isSaving}
            title="Save compressor"
          >
            [✓]
          </button>
          <button className="card-action-btn delete" onClick={handleCancel} disabled={isSaving} title="Cancel">
            [X]
          </button>
        </div>
      </div>

      <MachineCardAsciiDivider />

      <div className="form-sections-horizontal">
        <div className="network-config-section">
          <div className="network-config-header">KAESER SC2</div>
          <p className="form-hint" style={{ marginBottom: '0.75rem', lineHeight: 1.4 }}>
            Kaeser Connect URL + user + password are saved in Shatter and used directly by the backend to poll SC2.
          </p>
          {error && <div className="form-error text-error">{error}</div>}
          <div className="form-row">
            <label>SC2 host (display):</label>
            <input
              type="text"
              value={formData.ip_address}
              onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
              placeholder="192.168.1.50"
              disabled={isSaving}
            />
          </div>
          <div className="form-row">
            <label>Kaeser Connect URL:</label>
            <input
              type="text"
              value={formData.kaeser_connect_base_url}
              onChange={(e) => setFormData({ ...formData, kaeser_connect_base_url: e.target.value })}
              placeholder="https://192.168.1.102"
              disabled={isSaving}
            />
          </div>
          <div className="form-row">
            <label>Kaeser username:</label>
            <input
              type="text"
              value={formData.kaeser_username}
              onChange={(e) => setFormData({ ...formData, kaeser_username: e.target.value })}
              autoComplete="off"
              disabled={isSaving}
            />
          </div>
          <div className="form-row">
            <label>Kaeser password:</label>
            <input
              type="password"
              value={formData.kaeser_password}
              onChange={(e) => setFormData({ ...formData, kaeser_password: e.target.value })}
              autoComplete="new-password"
              disabled={isSaving}
            />
          </div>
          <div className="form-row">
            <label>POLL INTERVAL (s):</label>
            <input
              type="number"
              min={1}
              max={300}
              value={formData.poll_interval_seconds}
              onChange={(e) =>
                setFormData({ ...formData, poll_interval_seconds: parseInt(e.target.value, 10) || 5 })
              }
              disabled={isSaving}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
