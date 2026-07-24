import { API_BASE_URL } from '../config/api';

export type PollingDataPoint = {
  time: string;
  success: boolean;
  response_time_ms?: number;
};

export type StatusEvent = {
  time: string;
  status: string;
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
  status_history?: StatusEvent[];
};

export type RunningSummary = {
  time_range: string;
  total_machines: number;
  machines: RunningSummaryMachine[];
};

export type PollingStatsSummary = {
  total_polls: number;
  successful_polls: number;
  failed_polls: number;
  success_rate: number;
  avg_response_time_ms?: number;
  current_streak: number;
};

export type MachineStatusSummary = {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  uptime_8h_percent: number;
  current_status?: string;
  connection_health: string;
  online_duration_formatted: string;
  offline_duration_formatted: string;
  status_changed_at?: string;
  polling_history_8h: PollingDataPoint[];
  polling_summary: PollingStatsSummary;
};

export type MachinesSummary = {
  total_machines: number;
  online_count: number;
  offline_count: number;
  machines: MachineStatusSummary[];
};

export const summaryApi = {
  getRunning: async (timeRange: string = '24h'): Promise<RunningSummary> => {
    const response = await fetch(`${API_BASE_URL}/api/summary/running?time_range=${timeRange}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch running summary: ${response.statusText}`);
    }
    return response.json();
  },

  getMachines: async (timeRange: string = '8h'): Promise<MachinesSummary> => {
    const response = await fetch(`${API_BASE_URL}/api/summary/machines?time_range=${timeRange}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch machines summary: ${response.statusText}`);
    }
    return response.json();
  },
};
