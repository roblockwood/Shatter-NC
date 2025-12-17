/**
 * API functions for layout configuration
 */
import { API_BASE_URL } from '../config/api';
import type { PaneLayout } from '../types/layout';
import { layoutConfigToPanes, panesToLayoutConfig } from '../utils/layoutUtils';

/**
 * Fetch layout configuration for a specific machine
 */
export async function fetchMachineLayout(machineId: number): Promise<PaneLayout[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/layout`);
    if (!response.ok) {
      throw new Error(`Failed to fetch layout: ${response.statusText}`);
    }
    const data = await response.json();
    console.log('Fetched layout data:', data);
    const panes = layoutConfigToPanes(data.layout_config);
    console.log('Converted to panes:', panes);
    return panes;
  } catch (error) {
    console.error('Error fetching machine layout:', error);
    // Return default layout on error
    return layoutConfigToPanes(null);
  }
}

/**
 * Save layout configuration for a specific machine
 */
export async function saveMachineLayout(
  machineId: number,
  panes: PaneLayout[],
  gridCols: number = 12
): Promise<void> {
  try {
    const config = panesToLayoutConfig(panes, gridCols);
    console.log('Saving layout for machine', machineId, config);
    const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/layout`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to save layout: ${response.statusText} - ${errorText}`);
    }
    console.log('Layout saved successfully');
  } catch (error) {
    console.error('Error saving machine layout:', error);
    throw error;
  }
}

/**
 * Fetch global default layout configuration
 */
export async function fetchGlobalLayout(): Promise<PaneLayout[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/settings/layout`);
    if (!response.ok) {
      throw new Error(`Failed to fetch global layout: ${response.statusText}`);
    }
    const data = await response.json();
    return layoutConfigToPanes(data.layout_config);
  } catch (error) {
    console.error('Error fetching global layout:', error);
    // Return default layout on error
    return layoutConfigToPanes(null);
  }
}

/**
 * Save global default layout configuration
 */
export async function saveGlobalLayout(
  panes: PaneLayout[],
  gridCols: number = 12
): Promise<void> {
  try {
    const config = panesToLayoutConfig(panes, gridCols);
    const response = await fetch(`${API_BASE_URL}/api/settings/layout`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      throw new Error(`Failed to save global layout: ${response.statusText}`);
    }
  } catch (error) {
    console.error('Error saving global layout:', error);
    throw error;
  }
}


