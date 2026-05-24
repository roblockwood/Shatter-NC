import { useCallback, useRef } from 'react';
import type { TouchEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { TABLET_NAV_ITEMS, type TabletPaneSlug } from './tabletPaneConfig';

/** Ignore small movements; avoid fighting vertical scroll */
const MIN_SWIPE_PX = 72;
const HORIZONTAL_DOMINANCE = 1.25;

/**
 * Horizontal swipe on the pane area: left → next pane, right → previous (wraps).
 * Nav order follows filtered `navItems` when provided.
 */
export function useTabletPaneSwipe(
  machineId: number,
  currentSlug: TabletPaneSlug,
  navItems: { slug: TabletPaneSlug }[] = TABLET_NAV_ITEMS,
) {
  const navigate = useNavigate();
  const startRef = useRef<{ x: number; y: number } | null>(null);
  const slugOrder: TabletPaneSlug[] = navItems.map((n) => n.slug);

  const onTouchStart = useCallback((e: TouchEvent) => {
    if (e.touches.length !== 1) {
      return;
    }
    startRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }, []);

  const onTouchEnd = useCallback(
    (e: TouchEvent) => {
      const start = startRef.current;
      startRef.current = null;
      if (!start || e.changedTouches.length !== 1) {
        return;
      }

      const dx = e.changedTouches[0].clientX - start.x;
      const dy = e.changedTouches[0].clientY - start.y;
      const adx = Math.abs(dx);
      const ady = Math.abs(dy);

      if (adx < MIN_SWIPE_PX) {
        return;
      }
      if (adx < ady * HORIZONTAL_DOMINANCE) {
        return;
      }

      const idx = slugOrder.indexOf(currentSlug);
      if (idx < 0) {
        return;
      }

      if (dx < 0) {
        const next = slugOrder[(idx + 1) % slugOrder.length];
        navigate(`/tablet/${machineId}/${next}`);
      } else {
        const prev = slugOrder[(idx - 1 + slugOrder.length) % slugOrder.length];
        navigate(`/tablet/${machineId}/${prev}`);
      }
    },
    [currentSlug, machineId, navigate, slugOrder]
  );

  const onTouchCancel = useCallback(() => {
    startRef.current = null;
  }, []);

  return { onTouchStart, onTouchEnd, onTouchCancel };
}
