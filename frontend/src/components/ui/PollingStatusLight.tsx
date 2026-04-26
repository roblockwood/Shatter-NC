import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { freshnessFromAgeMs, type PollingFreshness } from './pollingFreshness';
import './PollingStatusLight.css';

export type { PollingFreshness };

function parseTime(value: Date | number | string | null | undefined): number | null {
  if (value == null) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (value instanceof Date) {
    const t = value.getTime();
    return isNaN(t) ? null : t;
  }
  const t = new Date(value).getTime();
  return isNaN(t) ? null : t;
}

interface PollingStatusLightProps {
  /** Last successful update time for this pane's data source (ISO string, epoch ms, or Date). */
  lastUpdatedAt: Date | number | string | null | undefined;
  /** Typical spacing between updates for this pane (e.g. fast poll 5000, history 60000). */
  expectedIntervalMs?: number;
  /** Accessible / tooltip context */
  ariaLabel?: string;
  className?: string;
  /** Extra monospace lines under freshness in the hover tooltip (e.g. ONLINE + status). */
  tooltipDetailLines?: string[];
}

const HOVER_SHOW_MS = 50;

/**
 * Small colored dot: green/yellow/red by recency of last successful update.
 * Themed hover popover (portal + fixed) shows last successful time + age (live while open).
 */
export const PollingStatusLight: React.FC<PollingStatusLightProps> = ({
  lastUpdatedAt,
  expectedIntervalMs = 10_000,
  ariaLabel = 'Data freshness',
  className = '',
  tooltipDetailLines,
}) => {
  const [freshness, setFreshness] = useState<PollingFreshness>('unknown');
  const [tooltipLines, setTooltipLines] = useState<{
    timeLine: string;
    ageLine: string;
    emptyMessage: string | null;
  }>({ timeLine: '', ageLine: '', emptyMessage: 'No successful update yet' });

  const [hoverOpen, setHoverOpen] = useState(false);
  const [tipPos, setTipPos] = useState<{ top: number; left: number } | null>(null);
  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const anchorRef = useRef<HTMLSpanElement>(null);

  const recompute = useCallback(() => {
    const t = parseTime(lastUpdatedAt);
    if (t == null) {
      setFreshness((prev) => (prev === 'unknown' ? prev : 'unknown'));
      setTooltipLines((prev) =>
        prev.emptyMessage === 'No successful update yet'
          ? prev
          : { timeLine: '', ageLine: '', emptyMessage: 'No successful update yet' },
      );
      return;
    }
    const ageMs = Date.now() - t;
    const next = freshnessFromAgeMs(ageMs, expectedIntervalMs);
    setFreshness((prev) => (prev === next ? prev : next));
    const timeLine = new Date(t).toLocaleString();
    const ageSec = Math.max(0, Math.floor(ageMs / 1000));
    const ageLine = `${ageSec}s ago`;
    setTooltipLines((prev) => {
      if (prev.timeLine === timeLine && prev.ageLine === ageLine && prev.emptyMessage === null) return prev;
      return { timeLine, ageLine, emptyMessage: null };
    });
  }, [lastUpdatedAt, expectedIntervalMs]);

  useEffect(() => {
    const raf = window.requestAnimationFrame(() => recompute());
    return () => window.cancelAnimationFrame(raf);
  }, [recompute]);

  useEffect(() => {
    const id = window.setInterval(() => {
      window.requestAnimationFrame(recompute);
    }, 8000);
    return () => window.clearInterval(id);
  }, [recompute]);

  /** Tighter refresh while hover tooltip is open so “Ns ago” feels live */
  useEffect(() => {
    if (!hoverOpen) return;
    const raf = window.requestAnimationFrame(() => recompute());
    const id = window.setInterval(() => recompute(), 1000);
    return () => {
      window.cancelAnimationFrame(raf);
      window.clearInterval(id);
    };
  }, [hoverOpen, recompute]);

  useLayoutEffect(() => {
    if (!hoverOpen) return;
    const update = () => {
      const el = anchorRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      setTipPos({
        top: r.top,
        left: r.left + r.width / 2,
      });
    };
    update();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [
    hoverOpen,
    tooltipLines.timeLine,
    tooltipLines.ageLine,
    tooltipLines.emptyMessage,
    tooltipDetailLines,
  ]);

  useEffect(() => {
    if (!hoverOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setHoverOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [hoverOpen]);

  const clearShowTimer = () => {
    if (showTimerRef.current != null) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
  };

  const handleEnter = () => {
    clearShowTimer();
    recompute();
    showTimerRef.current = setTimeout(() => setHoverOpen(true), HOVER_SHOW_MS);
  };

  const handleLeave = () => {
    clearShowTimer();
    setHoverOpen(false);
  };

  const cls =
    freshness === 'fresh'
      ? 'polling-status-light polling-status-light--fresh'
      : freshness === 'waning'
        ? 'polling-status-light polling-status-light--waning'
        : freshness === 'stale'
          ? 'polling-status-light polling-status-light--stale'
          : 'polling-status-light polling-status-light--unknown';

  const t = parseTime(lastUpdatedAt);
  const describedById = useId();
  const displayTipPos = hoverOpen ? tipPos : null;

  const tooltipEl =
    hoverOpen && displayTipPos != null ? (
      <div
        id={describedById}
        role="tooltip"
        className="polling-status-light-tooltip"
        style={{
          position: 'fixed',
          top: displayTipPos.top,
          left: displayTipPos.left,
          transform: 'translate(-50%, calc(-100% - 8px))',
        }}
      >
        <div className="polling-status-light-tooltip__label">Last successful update</div>
        {t == null ? (
          <div className="polling-status-light-tooltip__empty">
            {tooltipLines.emptyMessage ?? 'No successful update yet'}
          </div>
        ) : (
          <>
            <div className="polling-status-light-tooltip__time">{tooltipLines.timeLine}</div>
            <div className="polling-status-light-tooltip__age">{tooltipLines.ageLine}</div>
          </>
        )}
        {tooltipDetailLines != null && tooltipDetailLines.length > 0 && (
          <div className="polling-status-light-tooltip__extra-block">
            {tooltipDetailLines.map((line, i) => (
              <div key={i} className="polling-status-light-tooltip__extra">
                {line}
              </div>
            ))}
          </div>
        )}
      </div>
    ) : null;

  return (
    <>
      <span
        ref={anchorRef}
        className={`polling-status-light-anchor ${className}`.trim()}
        onMouseEnter={handleEnter}
        onMouseLeave={handleLeave}
        role="img"
        aria-label={`${ariaLabel}: ${freshness}`}
        aria-describedby={hoverOpen && displayTipPos != null ? describedById : undefined}
      >
        <span className={cls} aria-hidden />
      </span>
      {tooltipEl != null ? createPortal(tooltipEl, document.body) : null}
    </>
  );
};
