import React, { useState, useEffect } from 'react';
import { SaveConfirmModal } from '../SaveConfirmModal';
import { Select } from '../ui/Select';
import { API_BASE_URL } from '../../config/api';
import type { MachineStatus, ConnectionTestResult } from '../MachineCardTypes';
import type { ControllerType } from '../../types/machine';
import { defaultModelForController } from '../../types/machine';
import { useBetaMode } from '../../hooks/useBetaMode';

interface MachineEditPanelProps {
  machine: MachineStatus;
  pendingEditSwitch: boolean;
  pendingCollapse: boolean;
  onEditEnd: () => void;
  onCancelEditSwitch?: () => void;
  onCancelCollapse?: () => void;
  onDelete?: (machine: MachineStatus) => void;
}

type EditFormData = {
  controller_type: ControllerType;
  ip_address: string;
  ftp_username: string;
  ftp_password: string;
  ftp_port: number;
  path: string;
  poll_interval_seconds: number;
  tool_poll_interval_seconds: number;
  enabled: boolean;
  part_display_mode: string;
  diameter_tolerance: number;
  length_tolerance_plus: number;
  length_tolerance_minus: number;
  tolerance_x: number;
  tolerance_y: number;
  tolerance_z: number;
  use_machine_tool_tolerances: boolean;
  use_machine_wcs_tolerances: boolean;
  validate_tool_diameter: boolean;
  validate_tool_length: boolean;
  units: string;
  control_version: 'AUTO' | 'C00' | 'D00';
  opcua_port: number;
  opcua_username: string;
  opcua_password: string;
  opcua_channel: string;
};

function makeFormDataFromMachine(m: MachineStatus): EditFormData {
  const cfg = m.controller_config;
  return {
    controller_type: (m.controller_type ?? 'brother') as ControllerType,
    ip_address: m.ip_address || '',
    ftp_username: m.ftp_username || '',
    ftp_password: m.ftp_password || '',
    ftp_port: m.ftp_port || 21,
    path: m.path !== undefined && m.path !== null ? m.path : '/',
    poll_interval_seconds: m.poll_interval_seconds || 5,
    tool_poll_interval_seconds: m.tool_poll_interval_seconds || 30,
    enabled: m.enabled !== false,
    part_display_mode: m.part_display_mode || 'parts',
    diameter_tolerance: m.diameter_tolerance || 0.010,
    length_tolerance_plus: m.length_tolerance_plus || 0.02,
    length_tolerance_minus: m.length_tolerance_minus || 0.0,
    tolerance_x: m.tolerance_x || 0.0394,
    tolerance_y: m.tolerance_y || 0.0394,
    tolerance_z: m.tolerance_z || 0.0394,
    use_machine_tool_tolerances: m.use_machine_tool_tolerances || false,
    use_machine_wcs_tolerances: m.use_machine_wcs_tolerances || false,
    validate_tool_diameter: m.validate_tool_diameter !== false,
    validate_tool_length: m.validate_tool_length !== false,
    units: m.units || 'in',
    control_version: (m.control_version ?? 'AUTO') as 'AUTO' | 'C00' | 'D00',
    opcua_port: cfg?.opcua_port ?? 4840,
    opcua_username: cfg?.opcua_username ?? '',
    opcua_password: '',
    opcua_channel: cfg?.channel ?? '0',
  };
}

function makeFormDataFromApi(d: Record<string, unknown>): EditFormData {
  const cfg = (d.controller_config ?? {}) as Record<string, unknown>;
  return {
    controller_type: (d.controller_type ?? 'brother') as ControllerType,
    ip_address: (d.ip_address as string) || '',
    ftp_username: (d.ftp_username as string) || '',
    ftp_password: (d.ftp_password as string) || '',
    ftp_port: (d.ftp_port as number) || 21,
    path: d.path !== undefined && d.path !== null ? (d.path as string) : '/',
    poll_interval_seconds: (d.poll_interval_seconds as number) || 5,
    tool_poll_interval_seconds: (d.tool_poll_interval_seconds as number) || 30,
    enabled: d.enabled !== false,
    part_display_mode: (d.part_display_mode as string) || 'parts',
    diameter_tolerance: (d.diameter_tolerance as number) || 0.010,
    length_tolerance_plus: (d.length_tolerance_plus as number) || 0.02,
    length_tolerance_minus: (d.length_tolerance_minus as number) || 0.0,
    tolerance_x: (d.tolerance_x as number) || 0.0394,
    tolerance_y: (d.tolerance_y as number) || 0.0394,
    tolerance_z: (d.tolerance_z as number) || 0.0394,
    use_machine_tool_tolerances: (d.use_machine_tool_tolerances as boolean) || false,
    use_machine_wcs_tolerances: (d.use_machine_wcs_tolerances as boolean) || false,
    validate_tool_diameter: d.validate_tool_diameter !== false,
    validate_tool_length: d.validate_tool_length !== false,
    units: (d.units as string) || 'in',
    control_version: ((d.control_version as string) || 'AUTO') as 'AUTO' | 'C00' | 'D00',
    opcua_port: (cfg.opcua_port as number) ?? 4840,
    opcua_username: (cfg.opcua_username as string) ?? '',
    opcua_password: '',
    opcua_channel: (cfg.channel as string) ?? '0',
  };
}

export const MachineEditPanel: React.FC<MachineEditPanelProps> = ({
  machine,
  pendingEditSwitch,
  pendingCollapse,
  onEditEnd,
  onCancelEditSwitch,
  onCancelCollapse,
  onDelete,
}) => {
  const { isBetaMode } = useBetaMode();
  const [showSaveConfirmModal, setShowSaveConfirmModal] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState(false);
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [isEditTesting, setIsEditTesting] = useState(false);
  const [editTestResult, setEditTestResult] = useState<ConnectionTestResult | null>(null);

  const [editFormData, setEditFormData] = useState<EditFormData>(() => makeFormDataFromMachine(machine));
  const [editMachineName, setEditMachineName] = useState(machine.machine_name || '');
  const [originalFormData, setOriginalFormData] = useState<EditFormData | null>(null);
  const [originalMachineName, setOriginalMachineName] = useState<string | null>(null);

  const isHeidenhain = editFormData.controller_type === 'heidenhain';

  useEffect(() => {
    const fetchMachineConfig = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`);
        if (response.ok) {
          const d = await response.json();
          const fetched = makeFormDataFromApi(d);
          setOriginalFormData(fetched);
          setOriginalMachineName(d.name || '');
          setEditMachineName(d.name || '');
          setEditFormData(fetched);
        }
      } catch (error) {
        console.error('Error fetching machine configuration:', error);
      }
    };
    fetchMachineConfig();
  }, [machine.machine_id]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleEditCancel();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  });

  const editFormValid =
    editMachineName &&
    editFormData.ip_address &&
    (isHeidenhain
      ? editFormData.opcua_username
      : editFormData.ftp_username && editFormData.ftp_password);

  const hasUnsavedChanges = () => {
    if (!originalFormData || originalMachineName === null) return false;
    if (editMachineName !== originalMachineName) return true;
    return JSON.stringify(editFormData) !== JSON.stringify(originalFormData);
  };

  const performEditCancel = () => {
    onEditEnd();
    setEditError(null);
    setEditSuccess(false);
    setEditTestResult(null);
    if (originalFormData && originalMachineName !== null) {
      setEditMachineName(originalMachineName);
      setEditFormData(originalFormData);
    } else {
      setEditMachineName(machine.machine_name || '');
      setEditFormData(makeFormDataFromMachine(machine));
    }
  };

  const handleEditCancel = () => {
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
      return;
    }
    performEditCancel();
  };

  const handleEditSave = async () => {
    if (!editFormValid) {
      setEditError('Please fill in all required fields');
      return;
    }

    setIsEditSaving(true);
    setEditError(null);
    setEditSuccess(false);

    try {
      const payload: Record<string, unknown> = {
        controller_type: editFormData.controller_type,
        model: defaultModelForController(editFormData.controller_type),
        ip_address: editFormData.ip_address,
        poll_interval_seconds: editFormData.poll_interval_seconds,
        enabled: editFormData.enabled,
        units: editFormData.units,
        diameter_tolerance: editFormData.diameter_tolerance,
        length_tolerance_plus: editFormData.length_tolerance_plus,
        length_tolerance_minus: editFormData.length_tolerance_minus,
        tolerance_x: editFormData.tolerance_x,
        tolerance_y: editFormData.tolerance_y,
        tolerance_z: editFormData.tolerance_z,
        use_machine_tool_tolerances: editFormData.use_machine_tool_tolerances,
        use_machine_wcs_tolerances: editFormData.use_machine_wcs_tolerances,
        validate_tool_diameter: editFormData.validate_tool_diameter,
        validate_tool_length: editFormData.validate_tool_length,
      };

      if (isHeidenhain) {
        payload.controller_config = {
          opcua_port: editFormData.opcua_port,
          opcua_username: editFormData.opcua_username,
          ...(editFormData.opcua_password ? { opcua_password: editFormData.opcua_password } : {}),
          channel: editFormData.opcua_channel,
        };
      } else {
        Object.assign(payload, {
          ftp_username: editFormData.ftp_username,
          ftp_password: editFormData.ftp_password,
          ftp_port: editFormData.ftp_port,
          path: editFormData.path,
          tool_poll_interval_seconds: editFormData.tool_poll_interval_seconds,
          part_display_mode: editFormData.part_display_mode,
          control_version: editFormData.control_version === 'AUTO' ? null : editFormData.control_version,
        });
      }

      const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Update failed: ${response.statusText}`);
      }

      setEditSuccess(true);
      setTimeout(() => {
        onEditEnd();
        setEditSuccess(false);
      }, 1500);
    } catch (error) {
      console.error('Edit error:', error);
      setEditError(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsEditSaving(false);
    }
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
      const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}/test`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        if (result.overall_status === 'online') {
          setEditTestResult(result);
        } else {
          const errors = [];
          if (!result.opcua?.success) {
            errors.push(`OPC UA: ${result.opcua?.error || 'Connection failed'}`);
          }
          if (!result.telnet?.success) {
            errors.push(`Telnet: ${result.telnet?.error || 'Connection failed'}`);
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

  useEffect(() => {
    if (!pendingEditSwitch) return;
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
    } else {
      performEditCancel();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingEditSwitch]);

  useEffect(() => {
    if (!pendingCollapse) return;
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
    } else {
      performEditCancel();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCollapse]);

  return (
    <div className="machine-card edit-mode">
      <div className="machine-card-header">
        <div className="machine-header-edit-row">
          <input
            type="text"
            value={editMachineName}
            onChange={(e) => setEditMachineName(e.target.value)}
            className="machine-name-edit"
            disabled={isEditSaving}
            placeholder="MACHINE NAME"
          />
          <div className="form-checkbox machine-header-checkbox">
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
        <div className="machine-header-actions">
        </div>
      </div>

      <div className="machine-card-divider">
        ├{'─'.repeat(30)}┤
      </div>

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

        <div className="form-row-inline">
          <div style={{ flex: '0 0 auto', minWidth: '220px' }}>
            <label>CONTROLLER:</label>
            <Select
              value={editFormData.controller_type}
              onChange={(value) =>
                setEditFormData({
                  ...editFormData,
                  controller_type: value as ControllerType,
                })
              }
              disabled={isEditSaving}
              options={[
                { value: 'brother', label: 'Brother CNC' },
                { value: 'heidenhain', label: 'Heidenhain TNC (OPC UA)' },
              ]}
            />
          </div>
          <div style={{ flex: '0 0 auto', minWidth: '200px' }}>
            <label>UNITS:</label>
            <Select
              value={editFormData.units}
              onChange={(value) => setEditFormData({ ...editFormData, units: value })}
              disabled={isEditSaving}
              options={[
                { value: 'in', label: 'INCHES (in)' },
                { value: 'mm', label: 'MILLIMETERS (mm)' },
              ]}
            />
          </div>
          {!isHeidenhain && (
            <>
              <div style={{ flex: '0 0 auto', minWidth: '260px' }}>
                <label>CONTROL TYPE:</label>
                <Select
                  value={editFormData.control_version}
                  onChange={(value) =>
                    setEditFormData({
                      ...editFormData,
                      control_version: value as 'AUTO' | 'C00' | 'D00',
                    })
                  }
                  disabled={isEditSaving}
                  options={[
                    ...((isBetaMode || editFormData.control_version === 'AUTO')
                      ? [{ value: 'AUTO', label: 'AUTO DETECT (beta)' }]
                      : []),
                    { value: 'C00', label: 'C00' },
                    { value: 'D00', label: 'D00' },
                  ]}
                />
              </div>
              <div style={{ flex: '0 0 auto', minWidth: '260px' }}>
                <label>PARTS DISPLAY:</label>
                <Select
                  value={editFormData.part_display_mode}
                  onChange={(value) =>
                    setEditFormData({
                      ...editFormData,
                      part_display_mode: value as 'cycle' | 'parts',
                    })
                  }
                  disabled={isEditSaving}
                  options={[
                    { value: 'parts', label: 'PARTS COUNTER' },
                    { value: 'cycle', label: 'CYCLE COUNT' },
                  ]}
                />
              </div>
            </>
          )}
        </div>

        <div className="form-sections-horizontal">
          <div className="network-config-section">
            <div className="network-config-header">NETWORK CONFIGURATION</div>

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

            {isHeidenhain ? (
              <>
                <div className="form-row-inline">
                  <div>
                    <label>OPC UA PORT:</label>
                    <input
                      type="number"
                      min="1"
                      max="65535"
                      value={editFormData.opcua_port}
                      onChange={(e) => setEditFormData({ ...editFormData, opcua_port: parseInt(e.target.value) })}
                      disabled={isEditSaving}
                    />
                  </div>
                  <div>
                    <label>CHANNEL:</label>
                    <input
                      type="text"
                      value={editFormData.opcua_channel}
                      onChange={(e) => setEditFormData({ ...editFormData, opcua_channel: e.target.value })}
                      placeholder="0"
                      disabled={isEditSaving}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <label>OPC UA USER:</label>
                  <input
                    type="text"
                    value={editFormData.opcua_username}
                    onChange={(e) => setEditFormData({ ...editFormData, opcua_username: e.target.value })}
                    disabled={isEditSaving}
                  />
                </div>
                <div className="form-row">
                  <label>OPC UA PASS:</label>
                  <input
                    type="password"
                    value={editFormData.opcua_password}
                    onChange={(e) => setEditFormData({ ...editFormData, opcua_password: e.target.value })}
                    placeholder="Leave blank to keep existing"
                    disabled={isEditSaving}
                  />
                </div>
              </>
            ) : (
              <>
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
                    placeholder="/"
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
              </>
            )}

            <div className="form-row-inline">
              <div>
                <label>POLL INTERVAL (s):</label>
                <div className="input-with-metric">
                  <input
                    type="number"
                    min="1"
                    max="300"
                    value={editFormData.poll_interval_seconds}
                    onChange={(e) => setEditFormData({ ...editFormData, poll_interval_seconds: parseInt(e.target.value) })}
                    disabled={isEditSaving}
                  />
                  {machine.response_time_ms !== undefined && (
                    <span className="input-metric">{(machine.response_time_ms / 1000).toFixed(1)}s</span>
                  )}
                </div>
              </div>
              {!isHeidenhain && (
                <div>
                  <label>TOOL POLL INTERVAL (s):</label>
                  <div className="input-with-metric">
                    <input
                      type="number"
                      min="1"
                      max="600"
                      value={editFormData.tool_poll_interval_seconds}
                      onChange={(e) => setEditFormData({ ...editFormData, tool_poll_interval_seconds: parseInt(e.target.value) })}
                      disabled={isEditSaving}
                    />
                    {machine.tool_response_time_ms !== undefined && (
                      <span className="input-metric">{(machine.tool_response_time_ms / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {!isHeidenhain && (
          <div className="tolerances-section">
            <div className="tolerances-header">VALIDATION TOLERANCES ({editFormData.units === 'mm' ? 'mm' : 'inches'})</div>
            {/* Tool and WCS tolerance groups unchanged from original */}
            <div className="tolerance-group">
              <div className="tolerance-group-header">
                <div className="tolerance-group-label">TOOL TOLERANCES</div>
                <div className="tolerance-override-toggle" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div>
                    <input
                      type="checkbox"
                      id={`validate-tool-diameter-${machine.machine_id}`}
                      checked={editFormData.validate_tool_diameter}
                      onChange={(e) => setEditFormData({ ...editFormData, validate_tool_diameter: e.target.checked })}
                      disabled={isEditSaving}
                    />
                    <label htmlFor={`validate-tool-diameter-${machine.machine_id}`}>
                      Validate diameter
                    </label>
                  </div>
                  <div>
                    <input
                      type="checkbox"
                      id={`validate-tool-length-${machine.machine_id}`}
                      checked={editFormData.validate_tool_length}
                      onChange={(e) => setEditFormData({ ...editFormData, validate_tool_length: e.target.checked })}
                      disabled={isEditSaving}
                    />
                    <label htmlFor={`validate-tool-length-${machine.machine_id}`}>
                      Validate length
                    </label>
                  </div>
                </div>
                <div className="tolerance-override-toggle">
                  <input
                    type="checkbox"
                    id={`use-machine-tool-tolerances-${machine.machine_id}`}
                    checked={editFormData.use_machine_tool_tolerances}
                    onChange={(e) => setEditFormData({ ...editFormData, use_machine_tool_tolerances: e.target.checked })}
                    disabled={isEditSaving}
                  />
                  <label htmlFor={`use-machine-tool-tolerances-${machine.machine_id}`}>
                    Use machine settings
                  </label>
                </div>
              </div>
              <div className={`tolerance-group-content ${!editFormData.use_machine_tool_tolerances ? 'disabled' : ''}`}>
                <div className="tolerance-subgroup">
                  <div className="tolerance-group-label">TOOL DIAMETER</div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>(±):</label>
                    <input
                      type="number"
                      step="0.00001"
                      value={editFormData.diameter_tolerance}
                      onChange={(e) => setEditFormData({ ...editFormData, diameter_tolerance: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_tool_tolerances}
                    />
                  </div>
                </div>
                <div className="tolerance-subgroup">
                  <div className="tolerance-group-label">TOOL LENGTH</div>
                  <div className="tolerance-group-row">
                    <div className="tolerance-field tolerance-field-inline">
                      <label>(+):</label>
                      <input
                        type="number"
                        step="0.0001"
                        value={editFormData.length_tolerance_plus}
                        onChange={(e) => setEditFormData({ ...editFormData, length_tolerance_plus: parseFloat(e.target.value) })}
                        disabled={isEditSaving || !editFormData.use_machine_tool_tolerances}
                      />
                    </div>
                    <div className="tolerance-field tolerance-field-inline">
                      <label>(-):</label>
                      <input
                        type="number"
                        step="0.0001"
                        value={editFormData.length_tolerance_minus}
                        onChange={(e) => setEditFormData({ ...editFormData, length_tolerance_minus: parseFloat(e.target.value) })}
                        disabled={isEditSaving || !editFormData.use_machine_tool_tolerances}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="tolerance-group">
              <div className="tolerance-group-header">
                <div className="tolerance-group-label">WCS OFFSET</div>
                <div className="tolerance-override-toggle">
                  <input
                    type="checkbox"
                    id={`use-machine-wcs-tolerances-${machine.machine_id}`}
                    checked={editFormData.use_machine_wcs_tolerances}
                    onChange={(e) => setEditFormData({ ...editFormData, use_machine_wcs_tolerances: e.target.checked })}
                    disabled={isEditSaving}
                  />
                  <label htmlFor={`use-machine-wcs-tolerances-${machine.machine_id}`}>
                    Use machine settings
                  </label>
                </div>
              </div>
              <div className={`tolerance-group-content ${!editFormData.use_machine_wcs_tolerances ? 'disabled' : ''}`}>
                <div className="tolerance-group-row">
                  <div className="tolerance-field tolerance-field-inline">
                    <label>X (±):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={editFormData.tolerance_x}
                      onChange={(e) => setEditFormData({ ...editFormData, tolerance_x: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_wcs_tolerances}
                    />
                  </div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>Y (±):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={editFormData.tolerance_y}
                      onChange={(e) => setEditFormData({ ...editFormData, tolerance_y: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_wcs_tolerances}
                    />
                  </div>
                  <div className="tolerance-field tolerance-field-inline">
                    <label>Z (±):</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={editFormData.tolerance_z}
                      onChange={(e) => setEditFormData({ ...editFormData, tolerance_z: parseFloat(e.target.value) })}
                      disabled={isEditSaving || !editFormData.use_machine_wcs_tolerances}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          )}
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
            className="form-button delete"
            onClick={() => onDelete?.(machine)}
            disabled={isEditSaving}
          >
            [ DELETE ]
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

      <SaveConfirmModal
        isOpen={showSaveConfirmModal}
        onClose={() => {
          setShowSaveConfirmModal(false);
          if (pendingEditSwitch) onCancelEditSwitch?.();
          if (pendingCollapse) onCancelCollapse?.();
        }}
        onConfirm={() => {
          setShowSaveConfirmModal(false);
          performEditCancel();
        }}
        onSave={() => {
          setShowSaveConfirmModal(false);
          handleEditSave();
        }}
        machineName={machine.machine_name || 'Unknown'}
      />
    </div>
  );
};
