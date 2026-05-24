import React, { useEffect, useState } from 'react';
import './MachineSyncPanel.css';
import { SyncRunProgress } from './SyncRunProgress';
import { Select } from './ui/Select';
import {
  browseLocalFolders,
  createSyncConfig,
  deleteSyncConfig,
  getSyncRun,
  listSyncConfigs,
  listSyncRuns,
  triggerSyncConfig,
  updateSyncConfig,
} from '../api/ftpSync';
import type {
  FtpSyncConfig,
  FtpSyncConfigCreate,
  FtpSyncRun,
  FtpSyncRunDetail,
  LocalFolderBrowseResponse,
} from '../api/ftpSync';

const DEFAULT_FORM: FtpSyncConfigCreate = {
  name: 'Sync Job',
  sync_direction: 'upload',
  source_folder: '/tmp/shatter-sync',
  remote_folder: '/PROGRAM/SHATTER_SYNC',
  include_pattern: '*.NC',
  exclude_patterns: '.*,~*,*.tmp,*.temp,*.bak,*.swp,*.DS_Store',
  control_type: 'C00',
  strict_brother_naming: true,
  require_onumber_filename: true,
  enabled: true,
  auto_validate: true,
  auto_register: true,
  debounce_seconds: 3,
};

type SyncTab = 'create' | 'configs' | 'runs' | 'details';

interface MachineSyncPanelProps {
  machineId: number;
}

export const MachineSyncPanel: React.FC<MachineSyncPanelProps> = ({ machineId }) => {
  const [tab, setTab] = useState<SyncTab>('create');
  const [configs, setConfigs] = useState<FtpSyncConfig[]>([]);
  const [runs, setRuns] = useState<FtpSyncRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<FtpSyncRunDetail | null>(null);
  const [form, setForm] = useState<FtpSyncConfigCreate>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [editingConfigId, setEditingConfigId] = useState<number | null>(null);
  const [folderBrowser, setFolderBrowser] = useState<LocalFolderBrowseResponse | null>(null);
  const [folderLoading, setFolderLoading] = useState(false);
  const [showFolderPicker, setShowFolderPicker] = useState(false);

  useEffect(() => {
    refreshMachineData(machineId);
  }, [machineId]);

  useEffect(() => {
    const hasActiveRun = runs.some((run) => {
      const activeStatuses = ['queued', 'in_progress', 'processing'];
      return activeStatuses.includes(run.status);
    });

    if (!hasActiveRun) {
      return;
    }

    const pollInterval = setInterval(() => {
      listSyncRuns(machineId)
        .then((machineRuns) => {
          setRuns(machineRuns);
        })
        .catch(() => {
          // Silent fail on poll error
        });
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [machineId, runs]);

  async function refreshMachineData(id: number) {
    setLoading(true);
    setErrorMessage('');
    try {
      const [cfg, machineRuns] = await Promise.all([
        listSyncConfigs(id),
        listSyncRuns(id),
      ]);
      setConfigs(cfg);
      setRuns(machineRuns);
      if (selectedRun && selectedRun.machine_id !== id) {
        setSelectedRun(null);
      }
    } catch (err) {
      setErrorMessage(`Failed to load sync data: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadFolderBrowser(path?: string) {
    setFolderLoading(true);
    setErrorMessage('');
    try {
      const data = await browseLocalFolders(machineId, path);
      setFolderBrowser(data);
    } catch (err) {
      setErrorMessage(`Failed to browse local folders: ${String(err)}`);
    } finally {
      setFolderLoading(false);
    }
  }

  async function openFolderPicker() {
    setShowFolderPicker(true);
    await loadFolderBrowser();
  }

  function updateForm<K extends keyof FtpSyncConfigCreate>(key: K, value: FtpSyncConfigCreate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function startEditConfig(config: FtpSyncConfig) {
    setEditingConfigId(config.id);
    setForm({
      name: config.name,
      sync_direction: config.sync_direction,
      source_folder: config.source_folder,
      remote_folder: config.remote_folder,
      include_pattern: config.include_pattern,
      exclude_patterns: config.exclude_patterns,
      control_type: config.control_type,
      strict_brother_naming: config.strict_brother_naming,
      require_onumber_filename: config.require_onumber_filename,
      enabled: config.enabled,
      auto_validate: config.auto_validate,
      auto_register: config.auto_register,
      debounce_seconds: config.debounce_seconds,
    });
    setTab('create');
    setStatusMessage(`Editing config #${config.id}`);
    setErrorMessage('');
  }

  function cancelEditConfig() {
    setEditingConfigId(null);
    setForm(DEFAULT_FORM);
    setStatusMessage('Edit cancelled');
    setErrorMessage('');
  }

  async function onCreateConfig(e: React.FormEvent) {
    e.preventDefault();

    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const created = await createSyncConfig(machineId, form);
      setStatusMessage(`Created sync config #${created.id}`);
      setForm({ ...DEFAULT_FORM, name: `Sync Job ${created.id + 1}` });
      await refreshMachineData(machineId);
      setTab('configs');
    } catch (err) {
      setErrorMessage(`Create failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function onSaveConfig(e: React.FormEvent) {
    e.preventDefault();
    if (!editingConfigId) {
      return;
    }

    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const updated = await updateSyncConfig(machineId, editingConfigId, form);
      setStatusMessage(`Updated sync config #${updated.id}`);
      setEditingConfigId(null);
      setForm(DEFAULT_FORM);
      await refreshMachineData(machineId);
      setTab('configs');
    } catch (err) {
      setErrorMessage(`Update failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function onToggleConfig(config: FtpSyncConfig) {
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const updated = await updateSyncConfig(machineId, config.id, { enabled: !config.enabled });
      setStatusMessage(`Config ${updated.id} ${updated.enabled ? 'enabled' : 'disabled'}`);
      await refreshMachineData(machineId);
    } catch (err) {
      setErrorMessage(`Update failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteConfig(configId: number) {
    if (!window.confirm(`Delete sync config ${configId}?`)) {
      return;
    }

    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      await deleteSyncConfig(machineId, configId);
      setStatusMessage(`Deleted config ${configId}`);
      await refreshMachineData(machineId);
    } catch (err) {
      setErrorMessage(`Delete failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function onTriggerConfig(configId: number) {
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const result = await triggerSyncConfig(machineId, configId);
      setStatusMessage(`Triggered run ${result.run_id} for config ${configId}`);
      await refreshMachineData(machineId);
      setTab('runs');
    } catch (err) {
      setErrorMessage(`Trigger failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function onOpenRun(runId: number) {
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const detail = await getSyncRun(machineId, runId);
      setSelectedRun(detail);
      setTab('details');
      setStatusMessage(`Loaded run ${runId}`);
    } catch (err) {
      setErrorMessage(`Failed to load run detail: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  const createTabLabel = editingConfigId ? `EDIT CONFIG #${editingConfigId}` : 'CREATE CONFIG';

  return (
    <div className="machine-sync-panel">
      <div className="sync-toolbar">
        <button
          className="terminal-button"
          type="button"
          onClick={() => refreshMachineData(machineId)}
          disabled={loading}
        >
          [ REFRESH ]
        </button>
      </div>

      {statusMessage && <div className="sync-status">[ OK ] {statusMessage}</div>}
      {errorMessage && <div className="sync-error">[ ERROR ] {errorMessage}</div>}

      <div className="sync-tabs">
        <button
          type="button"
          className={`sync-tab${tab === 'create' ? ' active' : ''}`}
          onClick={() => setTab('create')}
        >
          [ {createTabLabel} ]
        </button>
        <button
          type="button"
          className={`sync-tab${tab === 'configs' ? ' active' : ''}`}
          onClick={() => setTab('configs')}
        >
          [ CONFIGS ]
        </button>
        <button
          type="button"
          className={`sync-tab${tab === 'runs' ? ' active' : ''}`}
          onClick={() => setTab('runs')}
        >
          [ RECENT RUNS ]
        </button>
        <button
          type="button"
          className={`sync-tab${tab === 'details' ? ' active' : ''}`}
          onClick={() => setTab('details')}
        >
          [ RUN DETAILS ]
        </button>
      </div>

      {tab === 'create' && (
        <section className="sync-panel sync-panel-full">
          <form className="sync-form" onSubmit={editingConfigId ? onSaveConfig : onCreateConfig}>
            <label>
              Name
              <input value={form.name} onChange={(e) => updateForm('name', e.target.value)} required />
            </label>

            <label>
              Direction
              <Select
                value={form.sync_direction}
                onChange={(value) => updateForm('sync_direction', value as 'upload' | 'download')}
                options={[
                  { value: 'upload', label: 'Upload (local → CNC)' },
                  { value: 'download', label: 'Download (CNC → local)' },
                ]}
              />
            </label>

            <label>
              Local Source Folder
              <div className="sync-input-row">
                <input value={form.source_folder} onChange={(e) => updateForm('source_folder', e.target.value)} required />
                <button
                  className="terminal-button-sm"
                  type="button"
                  onClick={openFolderPicker}
                >
                  [ SELECT FOLDER ]
                </button>
              </div>
            </label>

            <label>
              Remote CNC Folder
              <input value={form.remote_folder} onChange={(e) => updateForm('remote_folder', e.target.value)} required />
            </label>

            <label>
              Include Pattern
              <input value={form.include_pattern} onChange={(e) => updateForm('include_pattern', e.target.value)} required />
            </label>

            <label>
              Exclude Patterns
              <input value={form.exclude_patterns} onChange={(e) => updateForm('exclude_patterns', e.target.value)} />
            </label>

            <div className="sync-form-inline">
              <label>
                Control Type
                <Select
                  value={form.control_type}
                  onChange={(value) => updateForm('control_type', value as 'C00' | 'D00')}
                  options={[
                    { value: 'C00', label: 'C00' },
                    { value: 'D00', label: 'D00' },
                  ]}
                />
              </label>
              <label>
                Debounce Seconds
                <input
                  type="number"
                  min={0}
                  max={120}
                  value={form.debounce_seconds}
                  onChange={(e) => updateForm('debounce_seconds', Number(e.target.value))}
                />
              </label>
            </div>

            <div className="sync-checks">
              <label><input type="checkbox" checked={form.enabled} onChange={(e) => updateForm('enabled', e.target.checked)} /> Enabled</label>
              <label><input type="checkbox" checked={form.auto_validate} onChange={(e) => updateForm('auto_validate', e.target.checked)} /> Auto Validate</label>
              <label><input type="checkbox" checked={form.auto_register} onChange={(e) => updateForm('auto_register', e.target.checked)} /> Auto Register</label>
              <label><input type="checkbox" checked={form.strict_brother_naming} onChange={(e) => updateForm('strict_brother_naming', e.target.checked)} /> Strict Naming</label>
              <label><input type="checkbox" checked={form.require_onumber_filename} onChange={(e) => updateForm('require_onumber_filename', e.target.checked)} /> Require O####</label>
            </div>

            <div className="sync-form-actions">
              <button className="terminal-button primary" type="submit" disabled={loading}>
                {editingConfigId ? '[ SAVE CHANGES ]' : '[ CREATE CONFIG ]'}
              </button>
              {editingConfigId && (
                <button className="terminal-button" type="button" disabled={loading} onClick={cancelEditConfig}>
                  [ CANCEL ]
                </button>
              )}
            </div>
          </form>
        </section>
      )}

      {tab === 'configs' && (
        <section className="sync-panel sync-panel-full">
          <div className="config-list">
            {configs.length === 0 && <div className="sync-empty">No configs for this machine yet.</div>}
            {configs.map((config) => (
              <div key={config.id} className="config-card">
                <div className="config-main">
                  <div className="config-name">#{config.id} {config.name}</div>
                  <div className="config-meta">{config.sync_direction.toUpperCase()} | {config.control_type} | {config.enabled ? 'ENABLED' : 'DISABLED'}</div>
                  <div className="config-paths">{config.source_folder} → {config.remote_folder}</div>
                </div>
                <div className="config-actions">
                  <button className="terminal-button-sm" onClick={() => onTriggerConfig(config.id)} disabled={loading}>[ TRIGGER ]</button>
                  <button className="terminal-button-sm" onClick={() => startEditConfig(config)} disabled={loading}>[ EDIT ]</button>
                  <button className="terminal-button-sm" onClick={() => onToggleConfig(config)} disabled={loading}>[{config.enabled ? 'DISABLE' : 'ENABLE'}]</button>
                  <button className="terminal-button-sm danger" onClick={() => onDeleteConfig(config.id)} disabled={loading}>[ DELETE ]</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'runs' && (
        <section className="sync-panel sync-panel-full">
          <div className="run-list">
            {runs.length === 0 && <div className="sync-empty">No runs found.</div>}
            {runs.map((run) => (
              <div key={run.id} className="run-card">
                <div style={{ flex: 1 }}>
                  <div className="run-name">RUN #{run.id} | CFG {run.config_id}</div>
                  <SyncRunProgress run={run} />
                </div>
                <button className="terminal-button-sm" onClick={() => onOpenRun(run.id)} disabled={loading}>[ DETAILS ]</button>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'details' && (
        <section className="sync-panel sync-panel-full">
          {!selectedRun && <div className="sync-empty">Select a run from Recent Runs to inspect per-file results.</div>}
          {selectedRun && (
            <div className="run-detail">
              <div className="run-summary">RUN #{selectedRun.id} | {selectedRun.status}</div>
              <div className="run-items">
                {selectedRun.items.map((item) => (
                  <div key={item.id} className="run-item-row">
                    <div className="run-item-name">{item.relative_path}</div>
                    <div className="run-item-status">{item.status}</div>
                    {typeof item.details?.reason === 'string' && (
                      <div className="run-item-detail">reason: {item.details.reason}</div>
                    )}
                    {typeof item.details?.post_processing_reason === 'string' && (
                      <div className="run-item-detail">note: {item.details.post_processing_reason}</div>
                    )}
                    {item.error_message && <div className="run-item-error">{item.error_message}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {showFolderPicker && (
        <div className="sync-modal-backdrop" onClick={() => setShowFolderPicker(false)}>
          <div className="sync-modal" onClick={(e) => e.stopPropagation()}>
            <div className="sync-modal-header">
              <div className="panel-title">SELECT LOCAL SOURCE FOLDER</div>
              <button className="terminal-button-sm" type="button" onClick={() => setShowFolderPicker(false)}>
                [ CLOSE ]
              </button>
            </div>

            <div className="sync-folder-current">{folderBrowser?.current_path || '/'}</div>
            <div className="sync-folder-actions">
              <button
                className="terminal-button-sm"
                type="button"
                disabled={folderLoading || !folderBrowser?.parent_path}
                onClick={() => loadFolderBrowser(folderBrowser?.parent_path || undefined)}
              >
                [ UP ]
              </button>
              <button
                className="terminal-button-sm"
                type="button"
                disabled={folderLoading}
                onClick={() => loadFolderBrowser()}
              >
                [ ROOT ]
              </button>
              <button
                className="terminal-button-sm"
                type="button"
                disabled={folderLoading}
                onClick={() => {
                  if (!folderBrowser) {
                    return;
                  }
                  updateForm('source_folder', folderBrowser.current_path);
                  setShowFolderPicker(false);
                }}
              >
                [ USE CURRENT ]
              </button>
            </div>

            <div className="sync-folder-list modal-list">
              {folderLoading && <div className="sync-empty">Loading folders...</div>}
              {!folderLoading && folderBrowser && folderBrowser.directories.length === 0 && (
                <div className="sync-empty">No subfolders available.</div>
              )}
              {!folderLoading && folderBrowser?.directories.map((dir) => (
                <div key={dir.path} className="sync-folder-row">
                  <button
                    className="terminal-button-sm"
                    type="button"
                    onClick={() => loadFolderBrowser(dir.path)}
                  >
                    [ OPEN ]
                  </button>
                  <button
                    className="terminal-button-sm"
                    type="button"
                    onClick={() => {
                      updateForm('source_folder', dir.path);
                      setShowFolderPicker(false);
                    }}
                  >
                    [ SELECT ]
                  </button>
                  <span className="sync-folder-name">{dir.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
