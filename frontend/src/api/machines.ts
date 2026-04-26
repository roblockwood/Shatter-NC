/**
 * API functions for machine operations
 */
import { API_BASE_URL } from '../config/api';

export interface RefreshProgramNameResponse {
  success: boolean;
  message: string;
  program_name: string | null;
  raw_content?: string;
}

/**
 * Manually refresh the active program name from mem.nc for a machine
 */
export async function refreshProgramName(machineId: number): Promise<RefreshProgramNameResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/refresh-program-name`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to refresh program name: ${response.statusText} - ${errorText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error refreshing program name:', error);
    throw error;
  }
}

interface ToolEntry {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}

export interface RefreshToolDataResponse {
  machine_id: number;
  machine_name: string;
  tool_data: {
    tools?: Array<ToolEntry>;
    tool_table?: Array<ToolEntry>;
    current_tool?: number;
    tools_timestamp?: string;
    tool_table_timestamp?: string;
  };
  refreshed_at: string;
}

/**
 * Manually refresh tool data (tool table and ATC magazine) for a machine
 */
export async function refreshToolData(machineId: number): Promise<RefreshToolDataResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/status/tools/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to refresh tool data: ${response.statusText} - ${errorText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error refreshing tool data:', error);
    throw error;
  }
}

