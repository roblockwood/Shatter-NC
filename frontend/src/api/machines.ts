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

