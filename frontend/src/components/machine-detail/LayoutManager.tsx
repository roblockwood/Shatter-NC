import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import type { Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import type { PaneLayout, PaneId } from '../../types/layout';
import { fetchMachineLayout, saveMachineLayout } from '../../api/layout';
import { getDefaultLayout } from '../../utils/layoutUtils';
import { useExpandedMachine } from '../../contexts/ExpandedMachineContext';
import './LayoutManager.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

interface PaneComponent {
  id: PaneId;
  component: React.ReactNode;
}

// Human-readable pane names
const PANE_NAMES: Record<PaneId, string> = {
  statusTimeline: 'Status Timeline',
  alarms: 'Alarms',
  currentProgram: 'Current Program',
  tools: 'Tools',
  productionRuns: 'Production Runs',
  statusHistory: 'Status History',
  panel: 'Panel',
  fileManager: 'File Manager',
};

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
  onEditModeChange: _onEditModeChange,
}) => {
  const [layout, setLayout] = useState<PaneLayout[]>(getDefaultLayout());
  const [isLoading, setIsLoading] = useState(true);
  const { 
    showPaneList, 
    setOnResetToDefault
  } = useExpandedMachine();
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

  // Filter visible panes for rendering
  const visibleLayout = useMemo(() => {
    return layout.filter(pane => pane.visible !== false);
  }, [layout]);

  // Convert PaneLayout[] to react-grid-layout Layout format (only visible panes)
  const gridLayout = useMemo(() => {
    const result = visibleLayout.map(pane => ({
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
  }, [visibleLayout, isEditMode]);

  // Handle layout change
  const handleLayoutChange = useCallback(
    (currentLayout: Layout[]) => {
      // Create a map of the current layout state to preserve visibility and other properties
      const layoutMap = new Map<string, PaneLayout>();
      layout.forEach(pane => {
        layoutMap.set(pane.i, pane);
      });

      // Merge the new positions/sizes from react-grid-layout with existing pane properties
      const updatedLayout: PaneLayout[] = currentLayout.map(item => {
        const existingPane = layoutMap.get(item.i);
        return {
          i: item.i as PaneId,
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h,
          minW: item.minW ?? existingPane?.minW,
          minH: item.minH ?? existingPane?.minH,
          static: item.static,
          visible: existingPane?.visible !== undefined ? existingPane.visible : true,
        };
      });

      // Add back any panes that are hidden (not in currentLayout but in layout state)
      layout.forEach(pane => {
        if (pane.visible === false && !updatedLayout.find(p => p.i === pane.i)) {
          updatedLayout.push({ ...pane });
        }
      });

      setLayout(updatedLayout);
      // Save when layout changes (debounced) - only if in edit mode
      if (isEditMode) {
        debouncedSave(updatedLayout);
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

  // Expose handlers to context
  useEffect(() => {
    if (isEditMode) {
      setOnResetToDefault(() => handleResetToDefault);
    } else {
      setOnResetToDefault(null);
    }
  }, [isEditMode, handleResetToDefault, setOnResetToDefault]);

  // Toggle pane visibility
  const handleToggleVisibility = useCallback(
    (paneId: PaneId) => {
      // Prevent hiding all panes
      const visibleCount = layout.filter(p => p.visible !== false).length;
      const targetPane = layout.find(p => p.i === paneId);
      
      if (targetPane && targetPane.visible !== false && visibleCount <= 1) {
        // Don't allow hiding the last visible pane
        return;
      }

      const updatedLayout = layout.map(pane => {
        if (pane.i === paneId) {
          return {
            ...pane,
            visible: pane.visible === false ? true : false,
          };
        }
        return pane;
      });

      setLayout(updatedLayout);
      // Save when visibility changes (debounced) - only if in edit mode
      if (isEditMode) {
        debouncedSave(updatedLayout);
      }
    },
    [layout, isEditMode, debouncedSave]
  );

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
      {isEditMode && showPaneList && (
        <div className="pane-list-panel">
          <div className="pane-list-header">PANES</div>
          <div className="pane-list-items">
            {layout
              .filter(pane => pane.i !== 'cycleHistory')
              .map(pane => {
              const isVisible = pane.visible !== false;
              const paneName = PANE_NAMES[pane.i as PaneId] || pane.i;
              return (
                <label key={pane.i} className="pane-list-item">
                  <input
                    type="checkbox"
                    checked={isVisible}
                    onChange={() => handleToggleVisibility(pane.i as PaneId)}
                    disabled={isVisible && layout.filter(p => p.visible !== false).length <= 1}
                  />
                  <span className={`pane-list-item-label ${!isVisible ? 'pane-hidden' : ''}`}>
                    {paneName}
                  </span>
                </label>
              );
            })}
          </div>
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
          draggableCancel=".visibility-toggle-btn"
          onLayoutChange={handleLayoutChange}
          margin={[16, 16]}
          containerPadding={[0, 0]}
          preventCollision={false}
          compactType="vertical"
        >
        {visibleLayout.map(pane => {
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
                  <button
                    type="button"
                    className="visibility-toggle-btn"
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleVisibility(pane.i as PaneId);
                    }}
                    title={pane.visible !== false ? "Hide pane" : "Show pane"}
                    data-pane-visible={pane.visible !== false}
                  >
                    {pane.visible !== false ? '👁️' : '👁️‍🗨️'}
                  </button>
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

