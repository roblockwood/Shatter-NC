import { API_BASE_URL } from '../config/api';

export type PollingDataPoint = {
  time: string;
  success: boolean;
  response_time_ms?: number;
};

export type RunningSummaryMachine = {
  machine_id: number;
  machine_name: string;
  current_status?: string;
  total_run_time_seconds: number;
  total_run_time_formatted: string;
  run_percentage: number;
  active_runs_count: number;
  last_run_start?: string;
  current_program?: string;
};

export type RunningSummary = {
  time_range: string;
  total_machines: number;
  machines: RunningSummaryMachine[];
};

export type OnlineSummaryMachine = {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  online_since?: string;
  online_duration_seconds: number;
  online_duration_formatted: string;
  last_seen_at?: string;
  connection_health: string;
  polling_history_8h: PollingDataPoint[];
};

export type OnlineSummary = {
  total_online: number;
  machines: OnlineSummaryMachine[];
};

export type OfflineSummaryMachine = {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  offline_since?: string;
  offline_duration_seconds: number;
  offline_duration_formatted: string;
  last_seen_at?: string;
  last_known_status?: string;
  enabled: boolean;
  polling_history_8h: PollingDataPoint[];
};

export type OfflineSummary = {
  total_offline: number;
  machines: OfflineSummaryMachine[];
};

export const summaryApi = {
  getRunning: async (timeRange: string = '24h'): Promise<RunningSummary> => {
    const response = await fetch(`${API_BASE_URL}/api/summary/running?time_range=${timeRange}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch running summary: ${response.statusText}`);
    }
    return response.json();
  },

  getOnline: async (): Promise<OnlineSummary> => {
    const response = await fetch(`${API_BASE_URL}/api/summary/online`);
    if (!response.ok) {
      throw new Error(`Failed to fetch online summary: ${response.statusText}`);
    }
    return response.json();
  },

  getOffline: async (): Promise<OfflineSummary> => {
    const response = await fetch(`${API_BASE_URL}/api/summary/offline`);
    if (!response.ok) {
      throw new Error(`Failed to fetch offline summary: ${response.statusText}`);
    }
    return response.json();
  },
};
