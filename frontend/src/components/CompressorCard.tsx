import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { SaveConfirmModal } from './SaveConfirmModal';
import { AlarmPane } from './machine-detail/AlarmPane';
import { CompressorLayoutManager } from './machine-detail/CompressorLayoutManager';
import { CompressorOverviewPane } from './machine-detail/CompressorOverviewPane';
import { CompressorPanelPane } from './machine-detail/CompressorPanelPane';
import { CompressorStatusHistoryPane } from './machine-detail/CompressorStatusHistoryPane';
import { CompressorStatusTimelinePane } from './machine-detail/CompressorStatusTimelinePane';
import { CompressorTelemetrySeriesPane } from './machine-detail/CompressorTelemetrySeriesPane';
import { PANE_IDS } from '../types/layout';
import { useExpandedMachine } from '../contexts/ExpandedMachineContext';
import type { CompressorStatus } from '../hooks/useWebSocket';
import { API_BASE, getApiErrorMessage } from '../config/api';
import {
  asRecord,
  readCompressorControllerStatus,
  readOutletTempLine,
  readPressureLine,
} from '../utils/compressorTelemetry';
import './MachineCard.css';

interface CompressorCardProps {
  compressor: CompressorStatus;
  editMode?: boolean;
  isExpanded?: boolean;
  isEditing?: boolean;
  canEdit?: boolean;
  onExpand?: () => void;
  onCollapse?: () => void;
  onEditStart?: () => void;
  onEditEnd?: () => void;
  pendingCollapse?: boolean;
  onCancelCollapse?: () => void;
  onDelete?: (compressor: CompressorStatus) => void;
  isAnyAssetEditing?: boolean;
}

interface EditForm {
  name: string;
  ip_address: string;
  poll_interval_seconds: number;
  enabled: boolean;
  kaeser_connect_base_url: string;
  kaeser_username: string;
  kaeser_password: string;
}

function statusDisplay(c: CompressorStatus): string {
  if (!c.is_online) return 'OFFLINE';
  const s = (c.status || '').toLowerCase();
  if (s === 'offline') return 'OFFLINE';
  if (s.includes('error')) return 'ERROR';
  return 'ONLINE';
}

function statusValueClass(c: CompressorStatus): string {
  const d = statusDisplay(c);
  if (d === 'OFFLINE' || d === 'ERROR') return 'text-error';
  return 'text-success';
}

function findCompressorPane(paneId: string): HTMLElement | null {
  return document.querySelector(`[data-pane-id="${paneId}"]`) as HTMLElement | null;
}

const HOVER_PANEL_W = 560;
const HOVER_PANEL_H = 480;
const HOVER_STATUS_TIMELINE_W = 620;
const HOVER_STATUS_TIMELINE_H = 340;
const HOVER_TELEMETRY_W = 560;
const HOVER_TELEMETRY_H = 440;

function computeFixedHoverPosition(
  rect: DOMRect,
  paneWidth: number,
  paneHeight: number
): { top: number; left: number } {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = rect.right + 8;
  let top = rect.top;
  if (left + paneWidth > viewportWidth) {
    left = rect.left - paneWidth - 8;
  }
  if (top + paneHeight > viewportHeight) {
    top = Math.max(8, viewportHeight - paneHeight - 8);
  }
  if (top < 8) top = 8;
  return { top, left };
}

export const CompressorCard: React.FC<CompressorCardProps> = ({
  compressor,
  editMode = false,
  isExpanded = false,
  isEditing: isEditingProp = false,
  canEdit = true,
  pendingCollapse = false,
  onCancelCollapse,
  onExpand,
  onCollapse,
  onEditStart,
  onEditEnd,
  onDelete,
  isAnyAssetEditing = false,
}) => {
  const [isEditingLocal, setIsEditingLocal] = useState(false);
  const isEditing = isEditingProp !== undefined ? isEditingProp : isEditingLocal;

  const startEditing = () => {
    if (!canEdit) {
      return;
    }
    if (isEditingProp !== undefined) {
      onEditStart?.();
    } else {
      setIsEditingLocal(true);
    }
  };

  const stopEditing = () => {
    if (isEditingProp !== undefined) {
      onEditEnd?.();
    } else {
      setIsEditingLocal(false);
    }
  };

  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState(false);
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [showSaveConfirmModal, setShowSaveConfirmModal] = useState(false);
  const [editCompressorName, setEditCompressorName] = useState(compressor.compressor_name);
  const [editFormData, setEditFormData] = useState<EditForm>({
    name: compressor.compressor_name,
    ip_address: compressor.ip_address,
    poll_interval_seconds: compressor.poll_interval_seconds ?? 1,
    enabled: compressor.enabled !== false,
    kaeser_connect_base_url: compressor.kaeser_connect_base_url ?? '',
    kaeser_username: compressor.kaeser_username ?? '',
    kaeser_password: '',
  });

  useEffect(() => {
    if (isEditing) {
      setEditCompressorName(compressor.compressor_name);
      setEditFormData({
        name: compressor.compressor_name,
        ip_address: compressor.ip_address,
        poll_interval_seconds: compressor.poll_interval_seconds ?? 1,
        enabled: compressor.enabled !== false,
        kaeser_connect_base_url: compressor.kaeser_connect_base_url ?? '',
        kaeser_username: compressor.kaeser_username ?? '',
        kaeser_password: '',
      });
    }
  }, [
    isEditing,
    compressor.compressor_id,
    compressor.compressor_name,
    compressor.ip_address,
    compressor.poll_interval_seconds,
    compressor.enabled,
    compressor.kaeser_connect_base_url,
    compressor.kaeser_username,
  ]);

  const {
    setExpandedMachine,
    setExpandedAssetKind,
    layoutEditMode,
    setLayoutEditMode,
    setOnCollapse,
    setOnToggleLayoutEdit,
  } = useExpandedMachine();

  const toggleLayoutEdit = useCallback(() => {
    setLayoutEditMode((prev) => !prev);
  }, [setLayoutEditMode]);

  const hasUnsavedChanges = () => {
    if (!isEditing) return false;
    return (
      editCompressorName !== compressor.compressor_name ||
      editFormData.ip_address !== compressor.ip_address ||
      editFormData.poll_interval_seconds !== (compressor.poll_interval_seconds ?? 1) ||
      editFormData.enabled !== (compressor.enabled !== false) ||
      editFormData.kaeser_connect_base_url.trim() !== (compressor.kaeser_connect_base_url ?? '').trim() ||
      editFormData.kaeser_username.trim() !== (compressor.kaeser_username ?? '').trim() ||
      editFormData.kaeser_password.trim().length > 0
    );
  };

  const performEditCancel = () => {
    setEditCompressorName(compressor.compressor_name);
    setEditFormData({
      name: compressor.compressor_name,
      ip_address: compressor.ip_address,
      poll_interval_seconds: compressor.poll_interval_seconds ?? 1,
      enabled: compressor.enabled !== false,
      kaeser_connect_base_url: compressor.kaeser_connect_base_url ?? '',
      kaeser_username: compressor.kaeser_username ?? '',
      kaeser_password: '',
    });
    setEditError(null);
    setEditSuccess(false);
    stopEditing();
  };

  const handleEditCancel = () => {
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
    } else {
      performEditCancel();
    }
  };

  const handleEditSave = async () => {
    setIsEditSaving(true);
    setEditError(null);
    setEditSuccess(false);
    try {
      const kUrl = editFormData.kaeser_connect_base_url.trim();
      const kUser = editFormData.kaeser_username.trim();
      const kPass = editFormData.kaeser_password.trim();
      const body: Record<string, unknown> = {
        name: editCompressorName.trim(),
        ip_address: editFormData.ip_address,
        poll_interval_seconds: editFormData.poll_interval_seconds,
        enabled: editFormData.enabled,
        kaeser_connect_base_url: kUrl || null,
        kaeser_username: kUser || null,
      };
      if (!kUrl && !kUser) {
        body.kaeser_password = '';
      } else if (kPass) {
        body.kaeser_password = kPass;
      }
      const response = await fetch(`${API_BASE}/compressors/${compressor.compressor_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (response.ok) {
        setEditSuccess(true);
        stopEditing();
        setTimeout(() => setEditSuccess(false), 2000);
      } else {
        const err = await response.json().catch(() => ({}));
        setEditError(getApiErrorMessage(err.detail) || 'Update failed');
      }
    } catch (e) {
      setEditError(e instanceof Error ? e.message : 'Update failed');
    } finally {
      setIsEditSaving(false);
    }
  };

  useEffect(() => {
    if (!pendingCollapse || !isEditing) return;
    if (hasUnsavedChanges()) {
      setShowSaveConfirmModal(true);
    } else {
      performEditCancel();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCollapse, isEditing]);

  useEffect(() => {
    if (isEditing) {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') handleEditCancel();
      };
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
    if (isExpanded && !editMode) {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onCollapse?.();
      };
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded, isEditing, editMode, onCollapse]);

  const handleCardClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (
      target.closest('button') ||
      target.closest('input') ||
      target.closest('.card-action-btn') ||
      target.closest('.layout-manager') ||
      target.closest('.react-grid-item') ||
      target.closest('.drag-handle') ||
      target.closest('.react-resizable-handle') ||
      target.closest('.layout-pane-wrapper') ||
      isEditing ||
      editMode ||
      layoutEditMode
    ) {
      return;
    }
    if (isExpanded) {
      onCollapse?.();
    } else {
      onExpand?.();
    }
  };

  const hasRegisteredExpandedContextRef = useRef(false);
  useEffect(() => {
    if (!isExpanded) {
      hasRegisteredExpandedContextRef.current = false;
      return;
    }
    if (hasRegisteredExpandedContextRef.current) return;
    setExpandedMachine({ id: compressor.compressor_id, name: compressor.compressor_name });
    setExpandedAssetKind('compressor');
    if (onCollapse) {
      setOnCollapse(() => onCollapse);
    }
    setOnToggleLayoutEdit(() => toggleLayoutEdit);
    hasRegisteredExpandedContextRef.current = true;
  }, [
    isExpanded,
    compressor.compressor_id,
    compressor.compressor_name,
    onCollapse,
    setExpandedAssetKind,
    setExpandedMachine,
    setOnCollapse,
    setOnToggleLayoutEdit,
    toggleLayoutEdit,
  ]);

  const kUrlE = editFormData.kaeser_connect_base_url.trim();
  const kUserE = editFormData.kaeser_username.trim();
  const kPassE = editFormData.kaeser_password.trim();
  const kaeserTrioAttempted = Boolean(kUrlE || kUserE || kPassE);
  const kaeserComplete =
    !kaeserTrioAttempted ||
    Boolean(kUrlE && kUserE && (kPassE || compressor.kaeser_credentials_configured));
  const kaeserPartialEdit = kaeserTrioAttempted && !kaeserComplete;

  const editFormValid =
    editCompressorName.trim().length > 0 &&
    editFormData.ip_address.trim().length > 0 &&
    !kaeserPartialEdit;

  const pollTs = compressor.last_successful_poll_at || compressor.poll_timestamp;

  const { psiLine, tempLine, controllerDetail } = useMemo(() => {
    const metrics = compressor.metrics || {};
    const operational = asRecord(metrics.operational);
    const online = compressor.is_online;
    return {
      psiLine: online ? readPressureLine(operational) : '—',
      tempLine: online ? readOutletTempLine(operational) : '—',
      controllerDetail: readCompressorControllerStatus(compressor),
    };
  }, [compressor]);

  const [showStatusPanelPreview, setShowStatusPanelPreview] = useState(false);
  const [statusPanelPreviewPosition, setStatusPanelPreviewPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const statusPanelBlockRef = useRef<HTMLDivElement>(null);
  const statusPanelHoverPaneRef = useRef<HTMLDivElement>(null);
  const statusPanelLeaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [showPsiPreview, setShowPsiPreview] = useState(false);
  const [psiPreviewPosition, setPsiPreviewPosition] = useState<{ top: number; left: number } | null>(
    null
  );
  const psiBlockRef = useRef<HTMLDivElement>(null);
  const psiHoverPaneRef = useRef<HTMLDivElement>(null);
  const psiLeaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [showTempPreview, setShowTempPreview] = useState(false);
  const [tempPreviewPosition, setTempPreviewPosition] = useState<{ top: number; left: number } | null>(
    null
  );
  const tempBlockRef = useRef<HTMLDivElement>(null);
  const tempHoverPaneRef = useRef<HTMLDivElement>(null);
  const tempLeaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [showStatusTimelinePreview, setShowStatusTimelinePreview] = useState(false);
  const [statusTimelinePreviewPosition, setStatusTimelinePreviewPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const statusTimelineBlockRef = useRef<HTMLDivElement>(null);
  const statusTimelineHoverPaneRef = useRef<HTMLDivElement>(null);
  const statusTimelineLeaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const openStatusPanelPreview = useCallback(() => {
    if (statusPanelLeaveTimerRef.current) {
      clearTimeout(statusPanelLeaveTimerRef.current);
      statusPanelLeaveTimerRef.current = null;
    }
    if (statusPanelBlockRef.current) {
      setStatusPanelPreviewPosition(
        computeFixedHoverPosition(
          statusPanelBlockRef.current.getBoundingClientRect(),
          HOVER_PANEL_W,
          HOVER_PANEL_H
        )
      );
    }
    setShowStatusPanelPreview(true);
  }, []);

  const scheduleCloseStatusPanelPreview = useCallback(() => {
    if (statusPanelLeaveTimerRef.current) clearTimeout(statusPanelLeaveTimerRef.current);
    statusPanelLeaveTimerRef.current = setTimeout(() => {
      setShowStatusPanelPreview(false);
      statusPanelLeaveTimerRef.current = null;
    }, 140);
  }, []);

  const openPsiPreview = useCallback(() => {
    if (psiLeaveTimerRef.current) {
      clearTimeout(psiLeaveTimerRef.current);
      psiLeaveTimerRef.current = null;
    }
    if (psiBlockRef.current) {
      setPsiPreviewPosition(
        computeFixedHoverPosition(
          psiBlockRef.current.getBoundingClientRect(),
          HOVER_TELEMETRY_W,
          HOVER_TELEMETRY_H
        )
      );
    }
    setShowPsiPreview(true);
  }, []);

  const scheduleClosePsiPreview = useCallback(() => {
    if (psiLeaveTimerRef.current) clearTimeout(psiLeaveTimerRef.current);
    psiLeaveTimerRef.current = setTimeout(() => {
      setShowPsiPreview(false);
      psiLeaveTimerRef.current = null;
    }, 140);
  }, []);

  const openTempPreview = useCallback(() => {
    if (tempLeaveTimerRef.current) {
      clearTimeout(tempLeaveTimerRef.current);
      tempLeaveTimerRef.current = null;
    }
    if (tempBlockRef.current) {
      setTempPreviewPosition(
        computeFixedHoverPosition(
          tempBlockRef.current.getBoundingClientRect(),
          HOVER_TELEMETRY_W,
          HOVER_TELEMETRY_H
        )
      );
    }
    setShowTempPreview(true);
  }, []);

  const scheduleCloseTempPreview = useCallback(() => {
    if (tempLeaveTimerRef.current) clearTimeout(tempLeaveTimerRef.current);
    tempLeaveTimerRef.current = setTimeout(() => {
      setShowTempPreview(false);
      tempLeaveTimerRef.current = null;
    }, 140);
  }, []);

  const openStatusTimelinePreview = useCallback(() => {
    if (statusTimelineLeaveTimerRef.current) {
      clearTimeout(statusTimelineLeaveTimerRef.current);
      statusTimelineLeaveTimerRef.current = null;
    }
    if (statusTimelineBlockRef.current) {
      setStatusTimelinePreviewPosition(
        computeFixedHoverPosition(
          statusTimelineBlockRef.current.getBoundingClientRect(),
          HOVER_STATUS_TIMELINE_W,
          HOVER_STATUS_TIMELINE_H
        )
      );
    }
    setShowStatusTimelinePreview(true);
  }, []);

  const scheduleCloseStatusTimelinePreview = useCallback(() => {
    if (statusTimelineLeaveTimerRef.current) clearTimeout(statusTimelineLeaveTimerRef.current);
    statusTimelineLeaveTimerRef.current = setTimeout(() => {
      setShowStatusTimelinePreview(false);
      statusTimelineLeaveTimerRef.current = null;
    }, 140);
  }, []);

  useEffect(() => {
    return () => {
      if (statusPanelLeaveTimerRef.current) clearTimeout(statusPanelLeaveTimerRef.current);
      if (psiLeaveTimerRef.current) clearTimeout(psiLeaveTimerRef.current);
      if (tempLeaveTimerRef.current) clearTimeout(tempLeaveTimerRef.current);
      if (statusTimelineLeaveTimerRef.current) clearTimeout(statusTimelineLeaveTimerRef.current);
    };
  }, []);

  const focusCompressorPane = useCallback(
    (
      paneId: string,
      highlightClass: 'status-pane-highlight' | 'program-pane-highlight' | 'cycle-pane-highlight'
    ) => {
      setTimeout(() => {
        const paneElement = findCompressorPane(paneId);
        if (paneElement) {
          paneElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
          paneElement.classList.add(highlightClass);
          setTimeout(() => paneElement.classList.remove(highlightClass), 2000);
        }
      }, 300);
    },
    []
  );

  if (isExpanded && !isEditing && !editMode) {
    return (
      <div className="machine-card expanded" onClick={handleCardClick}>
        <div className="machine-card-expanded-content">
          <CompressorLayoutManager
            compressorId={compressor.compressor_id}
            isEditMode={layoutEditMode}
            panes={[
              {
                id: PANE_IDS.COMPRESSOR_PANEL,
                component: <CompressorPanelPane compressor={compressor} />,
              },
              {
                id: PANE_IDS.COMPRESSOR_OVERVIEW,
                component: <CompressorOverviewPane compressor={compressor} />,
              },
              {
                id: PANE_IDS.COMPRESSOR_ALARMS,
                component: (
                  <AlarmPane
                    machineId={compressor.compressor_id}
                    currentAlarms={compressor.alarms}
                    pollTimestamp={pollTs}
                    pollIntervalSeconds={compressor.poll_interval_seconds ?? 5}
                  />
                ),
              },
              {
                id: PANE_IDS.COMPRESSOR_STATUS_TIMELINE,
                component: (
                  <CompressorStatusTimelinePane
                    compressorId={compressor.compressor_id}
                    liveStatus={compressor.status}
                    isOnline={compressor.is_online}
                    pollTimestamp={compressor.last_successful_poll_at || compressor.poll_timestamp}
                  />
                ),
              },
              {
                id: PANE_IDS.COMPRESSOR_PSI_TIMELINE,
                component: (
                  <CompressorTelemetrySeriesPane
                    series="psi"
                    compressorId={compressor.compressor_id}
                    liveOperational={asRecord(compressor.metrics?.operational)}
                    isOnline={compressor.is_online}
                    pollTimestamp={compressor.last_successful_poll_at || compressor.poll_timestamp}
                  />
                ),
              },
              {
                id: PANE_IDS.COMPRESSOR_TEMP_TIMELINE,
                component: (
                  <CompressorTelemetrySeriesPane
                    series="temp"
                    compressorId={compressor.compressor_id}
                    liveOperational={asRecord(compressor.metrics?.operational)}
                    isOnline={compressor.is_online}
                    pollTimestamp={compressor.last_successful_poll_at || compressor.poll_timestamp}
                  />
                ),
              },
              {
                id: PANE_IDS.COMPRESSOR_STATUS_HISTORY,
                component: (
                  <CompressorStatusHistoryPane
                    compressorId={compressor.compressor_id}
                    liveStatus={compressor.status}
                    isOnline={compressor.is_online}
                  />
                ),
              },
            ]}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className={`machine-card ${isExpanded ? 'expanded' : ''} ${isEditing ? 'edit-mode' : ''} ${
        isAnyAssetEditing && !isEditing ? 'hidden-when-editing' : ''
      }`}
      onClick={handleCardClick}
    >
      <div className="machine-card-header">
        {isEditing ? (
          <div className="machine-header-edit-row">
            <input
              type="text"
              value={editCompressorName}
              onChange={(e) => setEditCompressorName(e.target.value)}
              className="machine-name-edit"
              disabled={isEditSaving}
              placeholder="COMPRESSOR NAME"
            />
            <div className="form-checkbox machine-header-checkbox">
              <input
                type="checkbox"
                id={`enabled-comp-${compressor.compressor_id}`}
                checked={editFormData.enabled}
                onChange={(e) => setEditFormData({ ...editFormData, enabled: e.target.checked })}
                disabled={isEditSaving}
              />
              <label htmlFor={`enabled-comp-${compressor.compressor_id}`}>ENABLED</label>
            </div>
          </div>
        ) : (
          <span
            className={`machine-name ${
              !compressor.is_online ? 'text-error' : compressor.is_online ? 'text-glow' : 'text-muted'
            }`}
          >
            {compressor.compressor_name}
          </span>
        )}
        <div className="machine-header-actions" />
      </div>

      <div className="machine-card-divider">├{'─'.repeat(30)}┤</div>

      {isEditing ? (
        <div className="machine-edit-form">
          {editError && <div className="form-error text-error">{editError}</div>}
          {kaeserPartialEdit && (
            <div className="form-error text-error">
              Kaeser URL, user, and password must all be set together (password can stay empty if already saved).
            </div>
          )}
          {editSuccess && <div className="form-success text-success">Compressor updated.</div>}
          <div className="network-config-section">
            <div className="network-config-header">SIDECAR</div>
            <div className="form-row">
              <label>SC2 host:</label>
              <input
                type="text"
                value={editFormData.ip_address}
                onChange={(e) => setEditFormData({ ...editFormData, ip_address: e.target.value })}
                disabled={isEditSaving}
              />
            </div>
            <div className="form-row">
              <label>Kaeser URL:</label>
              <input
                type="text"
                value={editFormData.kaeser_connect_base_url}
                onChange={(e) =>
                  setEditFormData({ ...editFormData, kaeser_connect_base_url: e.target.value })
                }
                placeholder="https://192.168.86.101"
                disabled={isEditSaving}
              />
            </div>
            <div className="form-row">
              <label>Kaeser user:</label>
              <input
                type="text"
                value={editFormData.kaeser_username}
                onChange={(e) => setEditFormData({ ...editFormData, kaeser_username: e.target.value })}
                autoComplete="off"
                disabled={isEditSaving}
              />
            </div>
            <div className="form-row">
              <label>Kaeser password:</label>
              <input
                type="password"
                value={editFormData.kaeser_password}
                onChange={(e) => setEditFormData({ ...editFormData, kaeser_password: e.target.value })}
                placeholder={compressor.kaeser_credentials_configured ? '(unchanged if empty)' : ''}
                autoComplete="new-password"
                disabled={isEditSaving}
              />
            </div>
            <div className="form-row">
              <label>POLL (s):</label>
              <input
                type="number"
                min={1}
                max={300}
                value={editFormData.poll_interval_seconds}
                onChange={(e) =>
                  setEditFormData({
                    ...editFormData,
                    poll_interval_seconds: parseInt(e.target.value, 10) || 1,
                  })
                }
                disabled={isEditSaving}
              />
            </div>
          </div>
          <div className="form-actions">
            <button
              type="button"
              className="form-button delete"
              onClick={(e) => {
                e.stopPropagation();
                onDelete?.(compressor);
              }}
              disabled={isEditSaving}
            >
              [ DELETE ]
            </button>
            <button
              type="button"
              className="form-button cancel"
              onClick={(e) => {
                e.stopPropagation();
                handleEditCancel();
              }}
              disabled={isEditSaving}
            >
              [ CANCEL ]
            </button>
            <button
              type="button"
              className="form-button save"
              onClick={(e) => {
                e.stopPropagation();
                handleEditSave();
              }}
              disabled={!editFormValid || isEditSaving}
            >
              {isEditSaving ? '[ SAVING... ]' : '[ SAVE ]'}
            </button>
          </div>
        </div>
      ) : (
        <div className="machine-card-content">
          <div
            ref={statusPanelBlockRef}
            className="compressor-card-hover-metric-block"
            onMouseEnter={openStatusPanelPreview}
            onMouseLeave={() => scheduleCloseStatusPanelPreview()}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) onExpand?.();
              focusCompressorPane(PANE_IDS.COMPRESSOR_PANEL, 'program-pane-highlight');
            }}
          >
            <div className="machine-row machine-row-hoverable" style={{ cursor: 'pointer' }}>
              <span className="label">STATUS:</span>
              <span className={`value ${statusValueClass(compressor)}`}>{statusDisplay(compressor)}</span>
            </div>
            {showStatusPanelPreview && statusPanelPreviewPosition && (
              <div
                ref={statusPanelHoverPaneRef}
                className="tools-hover-pane compressor-card-hover-wrap compressor-card-hover-wrap--panel"
                style={{
                  top: `${statusPanelPreviewPosition.top}px`,
                  left: `${statusPanelPreviewPosition.left}px`,
                }}
                onMouseEnter={openStatusPanelPreview}
                onMouseLeave={scheduleCloseStatusPanelPreview}
                onClick={(e) => e.stopPropagation()}
              >
                <CompressorPanelPane compressor={compressor} />
              </div>
            )}
          </div>

          <div
            ref={statusTimelineBlockRef}
            className="compressor-card-hover-metric-block"
            onMouseEnter={openStatusTimelinePreview}
            onMouseLeave={() => scheduleCloseStatusTimelinePreview()}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) onExpand?.();
              focusCompressorPane(PANE_IDS.COMPRESSOR_STATUS_TIMELINE, 'status-pane-highlight');
            }}
          >
            <div className="machine-row machine-row-hoverable" style={{ cursor: 'pointer' }}>
              <span className="label">OPERATION:</span>
              <span
                className="value compressor-card-operation-value"
                title={controllerDetail || undefined}
              >
                {controllerDetail || '—'}
              </span>
            </div>
            {showStatusTimelinePreview && statusTimelinePreviewPosition && (
              <div
                ref={statusTimelineHoverPaneRef}
                className="status-hover-pane compressor-card-hover-wrap compressor-card-hover-wrap--timeline"
                style={{
                  top: `${statusTimelinePreviewPosition.top}px`,
                  left: `${statusTimelinePreviewPosition.left}px`,
                }}
                onMouseEnter={openStatusTimelinePreview}
                onMouseLeave={scheduleCloseStatusTimelinePreview}
                onClick={(e) => e.stopPropagation()}
              >
                <CompressorStatusTimelinePane
                  compressorId={compressor.compressor_id}
                  liveStatus={compressor.status}
                  isOnline={compressor.is_online}
                  pollTimestamp={compressor.last_successful_poll_at || compressor.poll_timestamp}
                />
              </div>
            )}
          </div>

          <div
            ref={psiBlockRef}
            className="compressor-card-hover-metric-block"
            onMouseEnter={() => {
              if (psiBlockRef.current) {
                setPsiPreviewPosition(
                  computeFixedHoverPosition(
                    psiBlockRef.current.getBoundingClientRect(),
                    HOVER_TELEMETRY_W,
                    HOVER_TELEMETRY_H
                  )
                );
              }
              setShowPsiPreview(true);
            }}
            onMouseLeave={() => scheduleClosePsiPreview()}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) onExpand?.();
              focusCompressorPane(PANE_IDS.COMPRESSOR_PSI_TIMELINE, 'status-pane-highlight');
            }}
          >
            <div className="machine-row machine-row-hoverable" style={{ cursor: 'pointer' }}>
              <span className="label">PSI:</span>
              <span className="value">{psiLine}</span>
            </div>
            {showPsiPreview && psiPreviewPosition && (
              <div
                ref={psiHoverPaneRef}
                className="tools-hover-pane compressor-card-hover-wrap compressor-card-hover-wrap--telemetry"
                style={{
                  top: `${psiPreviewPosition.top}px`,
                  left: `${psiPreviewPosition.left}px`,
                }}
                onMouseEnter={openPsiPreview}
                onMouseLeave={scheduleClosePsiPreview}
                onClick={(e) => e.stopPropagation()}
              >
                <CompressorTelemetrySeriesPane
                  series="psi"
                  compressorId={compressor.compressor_id}
                  liveOperational={asRecord(compressor.metrics?.operational)}
                  isOnline={compressor.is_online}
                  pollTimestamp={compressor.last_successful_poll_at || compressor.poll_timestamp}
                />
              </div>
            )}
          </div>

          <div
            ref={tempBlockRef}
            className="compressor-card-hover-metric-block"
            onMouseEnter={() => {
              if (tempBlockRef.current) {
                setTempPreviewPosition(
                  computeFixedHoverPosition(
                    tempBlockRef.current.getBoundingClientRect(),
                    HOVER_TELEMETRY_W,
                    HOVER_TELEMETRY_H
                  )
                );
              }
              setShowTempPreview(true);
            }}
            onMouseLeave={() => scheduleCloseTempPreview()}
            onClick={(e) => {
              e.stopPropagation();
              if (!isExpanded) onExpand?.();
              focusCompressorPane(PANE_IDS.COMPRESSOR_TEMP_TIMELINE, 'status-pane-highlight');
            }}
          >
            <div className="machine-row machine-row-hoverable" style={{ cursor: 'pointer' }}>
              <span className="label">TEMP:</span>
              <span className="value">{tempLine}</span>
            </div>
            {showTempPreview && tempPreviewPosition && (
              <div
                ref={tempHoverPaneRef}
                className="tools-hover-pane compressor-card-hover-wrap compressor-card-hover-wrap--telemetry"
                style={{
                  top: `${tempPreviewPosition.top}px`,
                  left: `${tempPreviewPosition.left}px`,
                }}
                onMouseEnter={openTempPreview}
                onMouseLeave={scheduleCloseTempPreview}
                onClick={(e) => e.stopPropagation()}
              >
                <CompressorTelemetrySeriesPane
                  series="temp"
                  compressorId={compressor.compressor_id}
                  liveOperational={asRecord(compressor.metrics?.operational)}
                  isOnline={compressor.is_online}
                  pollTimestamp={compressor.last_successful_poll_at || compressor.poll_timestamp}
                />
              </div>
            )}
          </div>

          <div className="machine-card-divider-thin">{'─'.repeat(32)}</div>
          <div className="machine-footer">
            <button
              type="button"
              className="machine-edit-footer-btn"
              onClick={(e) => {
                e.stopPropagation();
                startEditing();
              }}
              title={canEdit ? 'Edit compressor' : 'Finish editing the other asset first'}
            >
              [edit]
            </button>
            <div className="machine-timestamp">
              {compressor.is_online ? 'LAST UPDATE' : 'LAST SEEN'}: {new Date(pollTs).toLocaleTimeString()}
            </div>
          </div>
        </div>
      )}

      <SaveConfirmModal
        isOpen={showSaveConfirmModal}
        onClose={() => {
          setShowSaveConfirmModal(false);
          if (pendingCollapse) onCancelCollapse?.();
        }}
        onConfirm={() => {
          setShowSaveConfirmModal(false);
          performEditCancel();
        }}
        onSave={() => {
          setShowSaveConfirmModal(false);
          void handleEditSave();
        }}
        machineName={editCompressorName.trim() || compressor.compressor_name || 'Compressor'}
      />
    </div>
  );
};
