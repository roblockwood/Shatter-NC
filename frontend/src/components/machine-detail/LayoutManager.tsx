import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import type { Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import type { PaneLayout, PaneId } from '../../types/layout';
import { fetchMachineLayout, saveMachineLayout } from '../../api/layout';
import { getDefaultLayout } from '../../utils/layoutUtils';
import './LayoutManager.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

interface PaneComponent {
  id: PaneId;
  component: React.ReactNode;
}

interface LayoutManagerProps {
  machineId: number;
  panes: PaneComponent[];
  isEditMode?: boolean;
  onEditModeChange?: (editMode: boolean) => void;
}

export const LayoutManager: React.FC<LayoutManagerProps> = ({
  machineId,
  panes,
  isEditMode = false,
  onEditModeChange,
}) => {
  const [layout, setLayout] = useState<PaneLayout[]>(getDefaultLayout());
  const [isLoading, setIsLoading] = useState(true);
  const saveTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debug: Log edit mode changes
  useEffect(() => {
    console.log('LayoutManager edit mode:', isEditMode);
  }, [isEditMode]);

  // Load layout on mount
  useEffect(() => {
    const loadLayout = async () => {
      try {
        setIsLoading(true);
        const loadedLayout = await fetchMachineLayout(machineId);
        console.log('Loaded layout for machine', machineId, loadedLayout);
        setLayout(loadedLayout);
        previousLayoutRef.current = loadedLayout;
      } catch (error) {
        console.error('Error loading layout:', error);
        const defaultLayout = getDefaultLayout();
        setLayout(defaultLayout);
        previousLayoutRef.current = defaultLayout;
      } finally {
        setIsLoading(false);
      }
    };

    loadLayout();
  }, [machineId]);

  // Debounced save function
  const debouncedSave = useCallback(
    (newLayout: PaneLayout[]) => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      saveTimeoutRef.current = setTimeout(async () => {
        try {
          await saveMachineLayout(machineId, newLayout);
        } catch (error) {
          console.error('Error saving layout:', error);
        }
      }, 500); // 500ms debounce
    },
    [machineId]
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Convert PaneLayout[] to react-grid-layout Layout format
  const gridLayout = useMemo(() => {
    const result = layout.map(pane => ({
      i: pane.i,
      x: pane.x,
      y: pane.y,
      w: pane.w,
      h: pane.h,
      minW: pane.minW,
      minH: pane.minH,
      static: !isEditMode, // Make static when not in edit mode (allow dragging when in edit mode)
    }));
    console.log('Grid layout computed:', { isEditMode, items: result.map(r => ({ i: r.i, static: r.static })) });
    return result;
  }, [layout, isEditMode]);

  // Track previous layout to detect width changes
  const previousLayoutRef = React.useRef<PaneLayout[]>([]);

  // Calculate smart height adjustment based on width change
  const calculateSmartHeight = useCallback(
    (paneId: string, oldW: number, newW: number, oldH: number, minH: number): number => {
      // If width decreased, content will stack - increase height
      // If width increased, content will spread - decrease height
      const widthRatio = newW / oldW;
      
      // Heuristic: height adjustment factor (more aggressive for narrower widths)
      // When width shrinks by 50%, height might need to increase by ~40-50%
      // When width grows by 50%, height might decrease by ~20-30%
      let heightAdjustment = 0;
      
      if (widthRatio < 1) {
        // Width decreased - need more vertical space
        // Inverse relationship: 50% width = ~150% height needed
        heightAdjustment = oldH * (1 - widthRatio) * 1.2;
      } else if (widthRatio > 1) {
        // Width increased - can reduce vertical space
        // Less aggressive: 200% width = ~85% height needed
        heightAdjustment = -oldH * (widthRatio - 1) * 0.3;
      }
      
      const newH = Math.max(minH, Math.round(oldH + heightAdjustment));
      return newH;
    },
    []
  );

  // Handle resize events with smart height adjustment
  const handleResize = useCallback(
    (layout: Layout[], oldItem: Layout | null, newItem: Layout | null, placeholder: Layout | null, e: MouseEvent, element: HTMLElement) => {
      if (!newItem || !oldItem || !isEditMode) return;
      
      // Check if width changed significantly (more than 0.5 grid units)
      const widthChanged = Math.abs(newItem.w - oldItem.w) > 0.5;
      
      if (widthChanged) {
        const currentPane = layout.find(item => item.i === newItem.i);
        if (!currentPane) return;
        
        const previousPane = previousLayoutRef.current.find(p => p.i === currentPane.i);
        if (!previousPane) return;
        
        // Calculate new height based on width change
        const newH = calculateSmartHeight(
          currentPane.i,
          previousPane.w,
          currentPane.w,
          previousPane.h,
          currentPane.minH || 1
        );
        
        // Update the layout item
        currentPane.h = newH;
        
        // Update our layout state
        const updatedLayout: PaneLayout[] = layout.map(item => ({
          i: item.i as PaneId,
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.i === currentPane.i ? newH : item.h,
          minW: item.minW,
          minH: item.minH,
          static: item.static,
        }));
        
        setLayout(updatedLayout);
      }
    },
    [isEditMode, calculateSmartHeight]
  );

  // Handle layout change
  const handleLayoutChange = useCallback(
    (currentLayout: Layout[]) => {
      const newLayout: PaneLayout[] = currentLayout.map(item => ({
        i: item.i as PaneId,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        minW: item.minW,
        minH: item.minH,
        static: item.static,
      }));

      // Update previous layout ref for smart resizing
      previousLayoutRef.current = newLayout;

      setLayout(newLayout);
      // Save when layout changes (debounced) - only if in edit mode
      if (isEditMode) {
        debouncedSave(newLayout);
      }
    },
    [debouncedSave, isEditMode, layout]
  );

  // Reset to default layout
  const handleResetToDefault = useCallback(() => {
    const defaultLayout = getDefaultLayout();
    setLayout(defaultLayout);
    debouncedSave(defaultLayout);
  }, [debouncedSave]);

  // Create a map of pane components by ID
  const paneMap = useMemo(() => {
    const map = new Map<PaneId, PaneComponent>();
    panes.forEach(pane => {
      map.set(pane.id, pane);
    });
    return map;
  }, [panes]);

  if (isLoading) {
    return (
      <div className="layout-manager-loading">
        <div>LOADING LAYOUT...</div>
      </div>
    );
  }

  return (
    <div 
      className={`layout-manager ${isEditMode ? 'edit-mode' : ''}`}
      data-edit-mode={isEditMode}
    >
      {isEditMode && (
        <div className="layout-manager-controls">
          <button
            className="layout-control-btn"
            onClick={handleResetToDefault}
            title="Reset to default layout"
          >
            [RESET TO DEFAULT]
          </button>
          <button
            className="layout-control-btn"
            onClick={() => onEditModeChange?.(false)}
            title="Exit edit mode"
          >
            [SAVE & EXIT]
          </button>
        </div>
      )}

      <div className="layout-container">
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: gridLayout, md: gridLayout, sm: gridLayout, xs: gridLayout, xxs: gridLayout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 12, sm: 12, xs: 12, xxs: 12 }}
          rowHeight={50}
          isDraggable={isEditMode}
          isResizable={isEditMode}
          draggableHandle={isEditMode ? ".drag-handle" : ""}
          onLayoutChange={handleLayoutChange}
          onResize={handleResize}
          margin={[16, 16]}
          containerPadding={[0, 0]}
          preventCollision={false}
          compactType="vertical"
        >
        {layout.map(pane => {
          const paneComponent = paneMap.get(pane.i as PaneId);
          if (!paneComponent) {
            return <div key={pane.i} />;
          }

          return (
            <div 
              key={pane.i} 
              className="layout-pane-wrapper"
              data-pane-id={pane.i}
            >
              {isEditMode && (
                <div className="drag-handle" data-testid={`drag-handle-${pane.i}`}>
                  <span className="drag-handle-icon">☰</span>
                  <span className="drag-handle-label">{pane.i}</span>
                </div>
              )}
              <div className="layout-pane-content">
                {paneComponent.component}
              </div>
            </div>
          );
        })}
        </ResponsiveGridLayout>
      </div>
    </div>
  );
};

