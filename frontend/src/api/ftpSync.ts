import { API_BASE_URL, getApiErrorMessage } from '../config/api';

export type SyncDirection = 'upload' | 'download';
export type BrotherControlType = 'C00' | 'D00';

export interface FtpSyncConfig {
  id: number;
  machine_id: number;
  name: string;
  sync_direction: SyncDirection;
  source_folder: string;
  remote_folder: string;
  include_pattern: string;
  exclude_patterns: string;
  control_type: BrotherControlType;
  strict_brother_naming: boolean;
  require_onumber_filename: boolean;
  enabled: boolean;
  auto_validate: boolean;
  auto_register: boolean;
  debounce_seconds: number;
  created_at: string;
  updated_at?: string | null;
}

export interface FtpSyncConfigCreate {
  name: string;
  sync_direction: SyncDirection;
  source_folder: string;
  remote_folder: string;
  include_pattern: string;
  exclude_patterns: string;
  control_type: BrotherControlType;
  strict_brother_naming: boolean;
  require_onumber_filename: boolean;
  enabled: boolean;
  auto_validate: boolean;
  auto_register: boolean;
  debounce_seconds: number;
}

export interface FtpSyncRun {
  id: number;
  config_id: number;
  machine_id: number;
  trigger_source: string;
  status: string;
  total_files: number;
  success_files: number;
  failed_files: number;
  conflict_files: number;
  skipped_files: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface FtpSyncRunItem {
  id: number;
  relative_path: string;
  local_path: string;
  remote_path: string;
  content_hash?: string | null;
  status: string;
  error_message?: string | null;
  details: Record<string, unknown>;
}

export interface FtpSyncRunDetail extends FtpSyncRun {
  items: FtpSyncRunItem[];
}

export interface LocalFolderEntry {
  name: string;
  path: string;
}

export interface LocalFolderBrowseResponse {
  current_path: string;
  parent_path?: string | null;
  directories: LocalFolderEntry[];
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return getApiErrorMessage(data?.detail) || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function listSyncConfigs(machineId: number): Promise<FtpSyncConfig[]> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/configs`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function createSyncConfig(machineId: number, payload: FtpSyncConfigCreate): Promise<FtpSyncConfig> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function updateSyncConfig(machineId: number, configId: number, payload: Partial<FtpSyncConfigCreate>): Promise<FtpSyncConfig> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/configs/${configId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function deleteSyncConfig(machineId: number, configId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/configs/${configId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
}

export async function triggerSyncConfig(machineId: number, configId: number, relativePaths?: string[]): Promise<{ run_id: number }> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/configs/${configId}/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ relative_paths: relativePaths }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function listSyncRuns(machineId: number): Promise<FtpSyncRun[]> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/runs?limit=25`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function getSyncRun(machineId: number, runId: number): Promise<FtpSyncRunDetail> {
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/runs/${runId}`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function browseLocalFolders(machineId: number, path?: string): Promise<LocalFolderBrowseResponse> {
  const query = path ? `?path=${encodeURIComponent(path)}` : '';
  const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/ftp-sync/local-folders${query}`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}
