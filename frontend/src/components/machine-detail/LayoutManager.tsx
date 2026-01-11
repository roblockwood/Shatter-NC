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
      } catch (error) {
        console.error('Error loading layout:', error);
        const defaultLayout = getDefaultLayout();
        setLayout(defaultLayout);
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
          cols={{ lg: 24, md: 24, sm: 24, xs: 24, xxs: 24 }}
          rowHeight={50}
          isDraggable={isEditMode}
          isResizable={isEditMode}
          draggableHandle={isEditMode ? ".drag-handle" : ""}
          onLayoutChange={handleLayoutChange}
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

