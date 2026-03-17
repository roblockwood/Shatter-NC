/**
 * Utility functions for layout configuration management
 */
import type { PaneLayout, LayoutConfig } from '../types/layout';
import { DEFAULT_LAYOUT } from '../types/layout';

/**
 * Get the default layout configuration
 */
export function getDefaultLayout(): PaneLayout[] {
  return JSON.parse(JSON.stringify(DEFAULT_LAYOUT)); // Deep copy
}

/**
 * Merge custom layout with defaults, ensuring all panes are present
 */
export function mergeLayoutWithDefaults(
  custom: PaneLayout[] | null | undefined,
  defaultLayout: PaneLayout[] = DEFAULT_LAYOUT
): PaneLayout[] {
  if (!custom || !Array.isArray(custom) || custom.length === 0) {
    return getDefaultLayout();
  }

  // Create a map of custom panes by ID
  const customMap = new Map<string, PaneLayout>();
  custom.forEach(pane => {
    customMap.set(pane.i, pane);
  });

  // Legacy: treat saved 'cycleHistory' as 'productionRuns' for position/size
  const productionRunsFromCycle = customMap.get('cycleHistory');
  if (productionRunsFromCycle && !customMap.get('productionRuns')) {
    customMap.set('productionRuns', {
      ...productionRunsFromCycle,
      i: 'productionRuns' as const,
    });
  }

  // Merge: use custom if exists, otherwise use default
  const merged: PaneLayout[] = [];
  defaultLayout.forEach(defaultPane => {
    const customPane = customMap.get(defaultPane.i);
    if (customPane) {
      // Validate custom pane has required fields
      merged.push({
        i: customPane.i,
        x: customPane.x ?? defaultPane.x,
        y: customPane.y ?? defaultPane.y,
        w: customPane.w ?? defaultPane.w,
        h: customPane.h ?? defaultPane.h,
        minW: customPane.minW ?? defaultPane.minW,
        minH: customPane.minH ?? defaultPane.minH,
        static: customPane.static ?? defaultPane.static,
        visible: customPane.visible !== undefined ? customPane.visible : (defaultPane.visible !== undefined ? defaultPane.visible : true),
      });
    } else {
      // Use default pane
      merged.push({ ...defaultPane });
    }
  });

  // Add any extra panes from custom that aren't in defaults (for future extensibility).
  // Exclude legacy 'cycleHistory' — it was replaced by 'productionRuns'.
  custom.forEach(customPane => {
    if (customPane.i === 'cycleHistory') return;
    if (!defaultLayout.find(p => p.i === customPane.i)) {
      merged.push(customPane);
    }
  });

  return merged;
}

/**
 * Validate layout configuration
 */
export function validateLayout(layout: PaneLayout[]): boolean {
  if (!Array.isArray(layout) || layout.length === 0) {
    return false;
  }

  // Check all required fields are present
  for (const pane of layout) {
    if (!pane.i || typeof pane.x !== 'number' || typeof pane.y !== 'number' ||
        typeof pane.w !== 'number' || typeof pane.h !== 'number') {
      return false;
    }

    // Validate bounds
    if (pane.x < 0 || pane.y < 0 || pane.w <= 0 || pane.h <= 0) {
      return false;
    }
  }

  return true;
}

/**
 * Convert layout config from API format to PaneLayout array
 */
export function layoutConfigToPanes(config: LayoutConfig | null | undefined): PaneLayout[] {
  if (!config || !config.panes) {
    return getDefaultLayout();
  }
  return mergeLayoutWithDefaults(config.panes);
}

/**
 * Convert PaneLayout array to layout config for API
 */
export function panesToLayoutConfig(panes: PaneLayout[], gridCols?: number): LayoutConfig {
  return {
    panes,
    gridCols: gridCols ?? 12,
  };
}


