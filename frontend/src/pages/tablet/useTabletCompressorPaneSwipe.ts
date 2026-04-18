import { useCallback, useRef } from 'react';
import type { TouchEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TABLET_COMPRESSOR_NAV_ITEMS,
  type TabletCompressorPaneSlug,
} from './tabletCompressorPaneConfig';

const SLUG_ORDER: TabletCompressorPaneSlug[] = TABLET_COMPRESSOR_NAV_ITEMS.map((n) => n.slug);

const MIN_SWIPE_PX = 72;
const HORIZONTAL_DOMINANCE = 1.25;

/** Horizontal swipe on compressor tablet pane area: left → next, right → previous (wraps). */
export function useTabletCompressorPaneSwipe(compressorId: number, currentSlug: TabletCompressorPaneSlug) {
  const navigate = useNavigate();
  const startRef = useRef<{ x: number; y: number } | null>(null);

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

      const idx = SLUG_ORDER.indexOf(currentSlug);
      if (idx < 0) {
        return;
      }

      const base = `/tablet/compressor/${compressorId}`;
      if (dx < 0) {
        const next = SLUG_ORDER[(idx + 1) % SLUG_ORDER.length];
        navigate(`${base}/${next}`);
      } else {
        const prev = SLUG_ORDER[(idx - 1 + SLUG_ORDER.length) % SLUG_ORDER.length];
        navigate(`${base}/${prev}`);
      }
    },
    [compressorId, currentSlug, navigate]
  );

  const onTouchCancel = useCallback(() => {
    startRef.current = null;
  }, []);

  return { onTouchStart, onTouchEnd, onTouchCancel };
}
