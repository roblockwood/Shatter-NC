import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import type { Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import type { PaneLayout, PaneId } from '../../types/layout';
import { fetchCompressorLayout, saveCompressorLayout } from '../../api/layout';
import { getDefaultCompressorLayout } from '../../utils/layoutUtils';
import { useExpandedMachine } from '../../contexts/ExpandedMachineContext';
import './LayoutManager.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

interface PaneComponent {
  id: PaneId;
  component: React.ReactNode;
}

const COMPRESSOR_PANE_NAMES: Partial<Record<PaneId, string>> = {
  compressorPanel: 'Panel',
  compressorOverview: 'Overview',
  compressorAlarms: 'Alarms',
  compressorStatusTimeline: 'Status timeline',
  compressorPsiTimeline: 'PSI',
  compressorTempTimeline: 'Temperature',
  compressorStatusHistory: 'Status history',
};

interface CompressorLayoutManagerProps {
  compressorId: number;
  panes: PaneComponent[];
  isEditMode?: boolean;
}

export const CompressorLayoutManager: React.FC<CompressorLayoutManagerProps> = ({
  compressorId,
  panes,
  isEditMode = false,
}) => {
  const [layout, setLayout] = useState<PaneLayout[]>(getDefaultCompressorLayout());
  const [isLoading, setIsLoading] = useState(true);
  const { showPaneList, setOnResetToDefault } = useExpandedMachine();
  const saveTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingLayoutRef = React.useRef<PaneLayout[] | null>(null);
  const prevEditRef = React.useRef(false);

  useEffect(() => {
    const loadLayout = async () => {
      try {
        setIsLoading(true);
        const loadedLayout = await fetchCompressorLayout(compressorId);
        setLayout(loadedLayout);
      } catch (error) {
        console.error('Error loading compressor layout:', error);
        setLayout(getDefaultCompressorLayout());
      } finally {
        setIsLoading(false);
      }
    };
    loadLayout();
  }, [compressorId]);

  const debouncedSave = useCallback(
    (newLayout: PaneLayout[]) => {
      pendingLayoutRef.current = newLayout;
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      const id = compressorId;
      saveTimeoutRef.current = setTimeout(async () => {
        saveTimeoutRef.current = null;
        const toSave = pendingLayoutRef.current;
        pendingLayoutRef.current = null;
        if (!toSave) return;
        try {
          await saveCompressorLayout(id, toSave);
        } catch (error) {
          console.error('Error saving compressor layout:', error);
        }
      }, 500);
    },
    [compressorId]
  );

  useEffect(() => {
    const id = compressorId;
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = null;
      }
      const pending = pendingLayoutRef.current;
      pendingLayoutRef.current = null;
      if (pending) {
        void saveCompressorLayout(id, pending).catch((error) => {
          console.error('Error saving compressor layout:', error);
        });
      }
    };
  }, [compressorId]);

  useEffect(() => {
    if (prevEditRef.current && !isEditMode) {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = null;
      }
      const pending = pendingLayoutRef.current;
      pendingLayoutRef.current = null;
      if (pending) {
        void saveCompressorLayout(compressorId, pending).catch((error) => {
          console.error('Error saving compressor layout:', error);
        });
      }
    }
    prevEditRef.current = isEditMode;
  }, [isEditMode, compressorId]);

  const visibleLayout = useMemo(() => layout.filter((pane) => pane.visible !== false), [layout]);

  const gridLayout = useMemo(
    () =>
      visibleLayout.map((pane) => ({
        i: pane.i,
        x: pane.x,
        y: pane.y,
        w: pane.w,
        h: pane.h,
        minW: pane.minW,
        minH: pane.minH,
        static: !isEditMode,
      })),
    [visibleLayout, isEditMode]
  );

  const handleLayoutChange = useCallback(
    (currentLayout: Layout[]) => {
      const layoutMap = new Map<string, PaneLayout>();
      layout.forEach((pane) => {
        layoutMap.set(pane.i, pane);
      });

      const updatedLayout: PaneLayout[] = currentLayout.map((item) => {
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

      layout.forEach((pane) => {
        if (pane.visible === false && !updatedLayout.find((p) => p.i === pane.i)) {
          updatedLayout.push({ ...pane });
        }
      });

      setLayout(updatedLayout);
      if (isEditMode) {
        debouncedSave(updatedLayout);
      }
    },
    [debouncedSave, isEditMode, layout]
  );

  const handleResetToDefault = useCallback(() => {
    const defaultLayout = getDefaultCompressorLayout();
    setLayout(defaultLayout);
    debouncedSave(defaultLayout);
  }, [debouncedSave]);

  useEffect(() => {
    if (isEditMode) {
      setOnResetToDefault(() => handleResetToDefault);
    } else {
      setOnResetToDefault(null);
    }
  }, [isEditMode, handleResetToDefault, setOnResetToDefault]);

  const handleToggleVisibility = useCallback(
    (paneId: PaneId) => {
      const visibleCount = layout.filter((p) => p.visible !== false).length;
      const targetPane = layout.find((p) => p.i === paneId);
      if (targetPane && targetPane.visible !== false && visibleCount <= 1) {
        return;
      }
      const updatedLayout = layout.map((pane) => {
        if (pane.i === paneId) {
          return { ...pane, visible: pane.visible === false ? true : false };
        }
        return pane;
      });
      setLayout(updatedLayout);
      if (isEditMode) {
        debouncedSave(updatedLayout);
      }
    },
    [layout, isEditMode, debouncedSave]
  );

  const paneMap = useMemo(() => {
    const map = new Map<PaneId, PaneComponent>();
    panes.forEach((pane) => {
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
    <div className={`layout-manager ${isEditMode ? 'edit-mode' : ''}`} data-edit-mode={isEditMode}>
      {isEditMode && showPaneList && (
        <div className="pane-list-panel">
          <div className="pane-list-header">PANES</div>
          <div className="pane-list-items">
            {layout.map((pane) => {
              const isVisible = pane.visible !== false;
              const paneName = COMPRESSOR_PANE_NAMES[pane.i as PaneId] || pane.i;
              return (
                <label key={pane.i} className="pane-list-item">
                  <input
                    type="checkbox"
                    checked={isVisible}
                    onChange={() => handleToggleVisibility(pane.i as PaneId)}
                    disabled={isVisible && layout.filter((p) => p.visible !== false).length <= 1}
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
          draggableHandle={isEditMode ? '.drag-handle' : ''}
          draggableCancel=".visibility-toggle-btn"
          onLayoutChange={handleLayoutChange}
          margin={[16, 16]}
          containerPadding={[0, 0]}
          preventCollision={false}
          compactType="vertical"
        >
          {visibleLayout.map((pane) => {
            const paneComponent = paneMap.get(pane.i as PaneId);
            if (!paneComponent) {
              return <div key={pane.i} />;
            }
            return (
              <div key={pane.i} className="layout-pane-wrapper" data-pane-id={pane.i}>
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
                      title={pane.visible !== false ? 'Hide pane' : 'Show pane'}
                      data-pane-visible={pane.visible !== false}
                    >
                      {pane.visible !== false ? '👁️' : '👁️‍🗨️'}
                    </button>
                  </div>
                )}
                <div className="layout-pane-content">{paneComponent.component}</div>
              </div>
            );
          })}
        </ResponsiveGridLayout>
      </div>
    </div>
  );
};
