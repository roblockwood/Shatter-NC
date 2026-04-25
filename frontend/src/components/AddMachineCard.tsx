import React, { useState, useEffect } from 'react';
import './AddMachineCard.css';
import { API_BASE } from '../config/api';
import { Select } from './ui/Select';

interface MachineData {
  name: string;
  ip_address: string;
  ftp_username: string;
  ftp_password: string;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  tool_poll_interval_seconds?: number;
  enabled?: boolean;
  model?: string;
  diameter_tolerance?: number;
  length_tolerance_plus?: number;
  length_tolerance_minus?: number;
  tolerance_x?: number;
  tolerance_y?: number;
  tolerance_z?: number;
  use_machine_tool_tolerances?: boolean;
  use_machine_wcs_tolerances?: boolean;
  validate_tool_diameter?: boolean;
  validate_tool_length?: boolean;
  units?: string;
  control_version?: 'AUTO' | 'C00' | 'D00';
}

interface AddMachineCardProps {
  onCancel?: () => void;
  onAdd?: (machine: Record<string, unknown>) => void;
  fullWidth?: boolean;
  onActiveChange?: (active: boolean) => void;
}

export const AddMachineCard: React.FC<AddMachineCardProps> = ({ onAdd, onCancel: onCancelProp, fullWidth = false, onActiveChange }) => {
  const [isActive, setIsActive] = useState(false);

  // Reset state when component unmounts (user navigates away)
  React.useEffect(() => {
    return () => {
      if (isActive && onActiveChange) {
        onActiveChange(false);
      }
    };
  }, [isActive, onActiveChange]);

  // Notify parent when active state changes
  useEffect(() => {
    onActiveChange?.(isActive);
  }, [isActive, onActiveChange]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<MachineData>({
    name: '',
    ip_address: '',
    ftp_username: 'anonymous',
    ftp_password: 'anonymous',
    ftp_port: 21,
    http_port: 80,
    path: '/',
    poll_interval_seconds: 5,
    tool_poll_interval_seconds: 30,
    enabled: true,
    model: 'Brother CNC',
    diameter_tolerance: 0.010,
    length_tolerance_plus: 0.02,
    length_tolerance_minus: 0.0,
    tolerance_x: 0.0394,
    tolerance_y: 0.0394,
    tolerance_z: 0.0394,
    use_machine_tool_tolerances: false,
    use_machine_wcs_tolerances: false,
    validate_tool_diameter: true,
    validate_tool_length: true,
    units: 'in',
    control_version: 'AUTO',
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
      const payload = {
        ...formData,
        control_version: formData.control_version === 'AUTO' ? null : formData.control_version,
      };
      const response = await fetch(`${API_BASE}/machines/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
          path: '/',
          poll_interval_seconds: 5,
          tool_poll_interval_seconds: 30,
          enabled: true,
          model: 'Brother CNC',
          diameter_tolerance: 0.010,
          length_tolerance_plus: 0.02,
          length_tolerance_minus: 0.0,
          tolerance_x: 0.0394,
          tolerance_y: 0.0394,
          tolerance_z: 0.0394,
          use_machine_tool_tolerances: false,
          use_machine_wcs_tolerances: false,
          validate_tool_diameter: true,
          validate_tool_length: true,
          units: 'in',
          control_version: 'AUTO',
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
      path: '/',
      poll_interval_seconds: 5,
      tool_poll_interval_seconds: 30,
      enabled: true,
      model: 'Brother CNC',
      diameter_tolerance: 0.010,
      length_tolerance_plus: 0.02,
      length_tolerance_minus: 0.0,
      tolerance_x: 0.0394,
      tolerance_y: 0.0394,
      tolerance_z: 0.0394,
      use_machine_tool_tolerances: false,
      use_machine_wcs_tolerances: false,
      validate_tool_diameter: true,
      validate_tool_length: true,
      units: 'in',
      control_version: 'AUTO',
    });
    setError(null);
    if (onCancelProp) {
      onCancelProp();
    }
  };

  if (!isActive) {
    return (
      <div className={`add-machine-card ${fullWidth ? 'full-width' : ''}`}>
        <div 
          className="add-machine-content clickable-content"
          onClick={() => setIsActive(true)}
        >
          <div className="add-icon clickable-icon">
            +
          </div>
          <div className="add-text">[ ADD MACHINE ]</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`machine-card add-machine-editing ${fullWidth ? 'full-width' : ''}`}>
      <div className="machine-card-header">
        <div className="machine-header-edit-row">
          <input
            className="machine-name-input"
            placeholder="NEW MACHINE"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            disabled={isSaving}
          />
          <div className="form-checkbox machine-header-checkbox">
            <input
              type="checkbox"
              id="enabled-new-header"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              disabled={isSaving}
            />
            <label htmlFor="enabled-new-header">ENABLED</label>
          </div>
        </div>
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

      {/* Horizontal Form Sections */}
      <div className="form-sections-horizontal">
        {/* Network Configuration Section */}
        <div className="network-config-section">
          <div className="network-config-header">NETWORK CONFIGURATION</div>

          {error && (
            <div className="form-error text-error">
              {error}
            </div>
          )}

          {/* Basic Settings */}
          <div className="form-row-inline">
            <div style={{ flex: '0 0 auto', minWidth: '200px' }}>
              <label>UNITS:</label>
              <Select
                value={formData.units || 'in'}
                onChange={(value) => setFormData({ ...formData, units: value })}
                disabled={isSaving}
                options={[
                  { value: 'in', label: 'INCHES (in)' },
                  { value: 'mm', label: 'MILLIMETERS (mm)' },
                ]}
              />
            </div>
            <div style={{ flex: '0 0 auto', minWidth: '220px' }}>
              <label>CONTROL TYPE:</label>
              <Select
                value={formData.control_version || 'AUTO'}
                onChange={(value) =>
                  setFormData({
                    ...formData,
                    control_version: value as 'AUTO' | 'C00' | 'D00',
                  })
                }
                disabled={isSaving}
                options={[
                  { value: 'AUTO', label: 'AUTO DETECT' },
                  { value: 'C00', label: 'C00' },
                  { value: 'D00', label: 'D00' },
                ]}
              />
            </div>
          </div>

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

          <div className="form-row">
            <label>FTP PATH:</label>
            <input
              type="text"
              value={formData.path}
              onChange={(e) => setFormData({ ...formData, path: e.target.value })}
              placeholder="/"
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
              <label>COM PORT:</label>
              <input
                type="number"
                min="1"
                max="65535"
                value={10000}
                disabled={true}
                title="Telnet communication port (fixed at 10000)"
              />
            </div>
          </div>

          <div className="form-row-inline">
            <div>
              <label>POLL INTERVAL (s):</label>
              <input
                type="number"
                min="1"
                max="300"
                value={formData.poll_interval_seconds}
                onChange={(e) => setFormData({ ...formData, poll_interval_seconds: parseInt(e.target.value) })}
                disabled={isSaving}
              />
            </div>
            <div>
              <label>TOOL POLL INTERVAL (s):</label>
              <input
                type="number"
                min="1"
                max="600"
                value={formData.tool_poll_interval_seconds}
                onChange={(e) => setFormData({ ...formData, tool_poll_interval_seconds: parseInt(e.target.value) })}
                disabled={isSaving}
              />
            </div>
          </div>

        </div>

        {/* Tolerances Section */}
        <div className="tolerances-section">
          <div className="tolerances-header">VALIDATION TOLERANCES ({formData.units === 'mm' ? 'mm' : 'inches'})</div>

          {/* Tool Tolerances Group */}
          <div className="tolerance-group">
            <div className="tolerance-group-header">
              <div className="tolerance-group-label">TOOL TOLERANCES</div>
              <div className="tolerance-override-toggle" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div>
                  <input
                    type="checkbox"
                    id="validate-tool-diameter-new"
                    checked={formData.validate_tool_diameter ?? true}
                    onChange={(e) => setFormData({ ...formData, validate_tool_diameter: e.target.checked })}
                    disabled={isSaving}
                  />
                  <label htmlFor="validate-tool-diameter-new">
                    Validate diameter
                  </label>
                </div>
                <div>
                  <input
                    type="checkbox"
                    id="validate-tool-length-new"
                    checked={formData.validate_tool_length ?? true}
                    onChange={(e) => setFormData({ ...formData, validate_tool_length: e.target.checked })}
                    disabled={isSaving}
                  />
                  <label htmlFor="validate-tool-length-new">
                    Validate length
                  </label>
                </div>
              </div>
              <div className="tolerance-override-toggle">
                <input
                  type="checkbox"
                  id="use-machine-tool-tolerances-new"
                  checked={formData.use_machine_tool_tolerances || false}
                  onChange={(e) => setFormData({ ...formData, use_machine_tool_tolerances: e.target.checked })}
                  disabled={isSaving}
                />
                <label htmlFor="use-machine-tool-tolerances-new">
                  Use machine settings
                </label>
              </div>
            </div>
            
            <div className={`tolerance-group-content ${!formData.use_machine_tool_tolerances ? 'disabled' : ''}`}>
              {/* Tool Diameter Group */}
              <div className="tolerance-subgroup">
                <div className="tolerance-group-label">TOOL DIAMETER</div>
                <div className="tolerance-field tolerance-field-inline">
                  <label>(±):</label>
                  <input
                    type="number"
                    step="0.00001"
                    value={formData.diameter_tolerance || 0.010}
                    onChange={(e) => setFormData({ ...formData, diameter_tolerance: parseFloat(e.target.value) })}
                    disabled={isSaving || !formData.use_machine_tool_tolerances}
                  />
                </div>
              </div>

              {/* Tool Length Group */}
              <div className="tolerance-subgroup">
                <div className="tolerance-group-label">TOOL LENGTH</div>
                <div className="tolerance-group-row">
                  <div className="tolerance-field tolerance-field-inline">
                    <label>(+):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={formData.length_tolerance_plus || 0.02}
                      onChange={(e) => setFormData({ ...formData, length_tolerance_plus: parseFloat(e.target.value) })}
                      disabled={isSaving || !formData.use_machine_tool_tolerances}
                    />
                  </div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>(-):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={formData.length_tolerance_minus || 0.0}
                      onChange={(e) => setFormData({ ...formData, length_tolerance_minus: parseFloat(e.target.value) })}
                      disabled={isSaving || !formData.use_machine_tool_tolerances}
                    />
                  </div>
                </div>
              </div>
            </div>
            {!formData.use_machine_tool_tolerances && (
              <div className="tolerance-hint">
                Using G-code defaults: diameter must match exactly, length must be ≥ required
              </div>
            )}
          </div>

          {/* WCS Offset Group */}
          <div className="tolerance-group">
            <div className="tolerance-group-header">
              <div className="tolerance-group-label">WCS OFFSET</div>
              <div className="tolerance-override-toggle">
                <input
                  type="checkbox"
                  id="use-machine-wcs-tolerances-new"
                  checked={formData.use_machine_wcs_tolerances || false}
                  onChange={(e) => setFormData({ ...formData, use_machine_wcs_tolerances: e.target.checked })}
                  disabled={isSaving}
                />
                <label htmlFor="use-machine-wcs-tolerances-new">
                  Use machine settings
                </label>
              </div>
            </div>
            
            <div className={`tolerance-group-content ${!formData.use_machine_wcs_tolerances ? 'disabled' : ''}`}>
              <div className="tolerance-group-row">
                <div className="tolerance-field tolerance-field-inline">
                  <label>X (±):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formData.tolerance_x || 0.0394}
                    onChange={(e) => setFormData({ ...formData, tolerance_x: parseFloat(e.target.value) })}
                    disabled={isSaving || !formData.use_machine_wcs_tolerances}
                  />
                </div>
                <div className="tolerance-field tolerance-field-inline">
                  <label>Y (±):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formData.tolerance_y || 0.0394}
                    onChange={(e) => setFormData({ ...formData, tolerance_y: parseFloat(e.target.value) })}
                    disabled={isSaving || !formData.use_machine_wcs_tolerances}
                  />
                </div>
                <div className="tolerance-field tolerance-field-inline">
                  <label>Z (±):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formData.tolerance_z || 0.0394}
                    onChange={(e) => setFormData({ ...formData, tolerance_z: parseFloat(e.target.value) })}
                    disabled={isSaving || !formData.use_machine_wcs_tolerances}
                  />
                </div>
              </div>
            </div>
            {!formData.use_machine_wcs_tolerances && (
              <div className="tolerance-hint">
                Using G-code E parameter if present in WCS validation macro
              </div>
            )}
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
