import { useCallback, useEffect, useRef, useState } from 'react';
import { ShatterAsciiLogo } from '../../components/ShatterAsciiLogo';
import { TABLET_SCREENSAVER_IDLE_MS_DEFAULT } from './tabletScreensaverStorage';
import './TabletScreensaver.css';

const SPINNER_FRAMES = ['/', '─', '\\', '│'];

type TabletScreensaverProps = {
  /** When true, fullscreen saver is shown */
  active: boolean;
  onActiveChange: (next: boolean) => void;
  /** Time with no pointer/keyboard activity before auto-opening (default 5 min) */
  idleMs?: number;
};

const DEFAULT_IDLE_MS = TABLET_SCREENSAVER_IDLE_MS_DEFAULT;

function useWakeLock(enabled: boolean) {
  const sentinelRef = useRef<WakeLockSentinel | null>(null);

  useEffect(() => {
    if (!enabled || !('wakeLock' in navigator)) return;

    let cancelled = false;

    const request = async () => {
      try {
        const wl = await navigator.wakeLock!.request('screen');
        if (cancelled) {
          wl.release().catch(() => {});
          return;
        }
        sentinelRef.current = wl;
        wl.addEventListener('release', () => {
          sentinelRef.current = null;
        });
      } catch {
        /* kiosk may deny — ignore */
      }
    };

    void request();

    const onVisibility = () => {
      if (document.visibilityState === 'visible' && enabled && sentinelRef.current == null) {
        void request();
      }
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', onVisibility);
      sentinelRef.current?.release().catch(() => {});
      sentinelRef.current = null;
    };
  }, [enabled]);
}

function useIdleArm(idleMs: number, onIdle: () => void, paused: boolean) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onIdleRef = useRef(onIdle);
  onIdleRef.current = onIdle;

  const arm = useCallback(() => {
    if (paused) return;
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      onIdleRef.current();
    }, idleMs);
  }, [idleMs, paused]);

  useEffect(() => {
    if (paused) {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    arm();

    let lastMoveArm = 0;
    const MOVE_GAP_MS = 750;

    const handler = (ev: Event) => {
      const t = ev.type;
      if (t === 'mousemove' || t === 'touchmove' || t === 'wheel') {
        const n = Date.now();
        if (n - lastMoveArm < MOVE_GAP_MS) return;
        lastMoveArm = n;
      }
      arm();
    };

    const opts: AddEventListenerOptions = { capture: true, passive: true };
    const names: (keyof WindowEventMap)[] = [
      'mousedown',
      'mouseup',
      'mousemove',
      'keydown',
      'keyup',
      'touchstart',
      'touchend',
      'touchmove',
      'wheel',
      'pointerdown',
      'pointermove',
      'scroll',
      'click',
    ];
    names.forEach((n) => window.addEventListener(n, handler as EventListener, opts));

    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      names.forEach((n) => window.removeEventListener(n, handler as EventListener, opts));
    };
  }, [paused, arm]);
}

export function TabletScreensaver({
  active,
  onActiveChange,
  idleMs = DEFAULT_IDLE_MS,
}: TabletScreensaverProps) {
  useWakeLock(active);
  useIdleArm(idleMs, () => onActiveChange(true), active);

  const bounceRef = useRef<HTMLDivElement>(null);
  const [spin, setSpin] = useState(0);

  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => setSpin((s) => (s + 1) % 4), 150);
    return () => clearInterval(id);
  }, [active]);

  useEffect(() => {
    if (!active) return;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
    const slow = reduceMotion ? 0.35 : 1;

    let pos = { x: 32, y: 32 };
    let vel = { vx: (70 + Math.random() * 40) * slow, vy: (55 + Math.random() * 35) * slow };
    let last = performance.now();
    let raf = 0;

    const placeRandom = () => {
      const el = bounceRef.current;
      const vv = window.visualViewport;
      const vw = Math.min(vv?.width ?? window.innerWidth, window.innerWidth);
      const vh = Math.min(vv?.height ?? window.innerHeight, window.innerHeight);
      const w = el ? Math.min(el.offsetWidth, vw) : 400;
      const h = el ? Math.min(el.offsetHeight, vh) : 200;
      const maxX = Math.max(8, vw - w - 8);
      const maxY = Math.max(8, vh - h - 8);
      pos = {
        x: 8 + Math.random() * maxX,
        y: 8 + Math.random() * maxY,
      };
    };

    placeRandom();

    const loop = (now: number) => {
      const el = bounceRef.current;
      if (!el) {
        raf = requestAnimationFrame(loop);
        return;
      }
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      const vv = window.visualViewport;
      const vw = Math.min(vv?.width ?? window.innerWidth, window.innerWidth);
      const vh = Math.min(vv?.height ?? window.innerHeight, window.innerHeight);
      const w = Math.min(el.offsetWidth, vw);
      const h = Math.min(el.offsetHeight, vh);

      pos.x += vel.vx * dt;
      pos.y += vel.vy * dt;

      if (pos.x <= 0) {
        pos.x = 0;
        vel.vx = Math.abs(vel.vx);
      } else if (pos.x + w >= vw) {
        pos.x = vw - w;
        vel.vx = -Math.abs(vel.vx);
      }
      if (pos.y <= 0) {
        pos.y = 0;
        vel.vy = Math.abs(vel.vy);
      } else if (pos.y + h >= vh) {
        pos.y = vh - h;
        vel.vy = -Math.abs(vel.vy);
      }

      el.style.transform = `translate(${Math.round(pos.x)}px, ${Math.round(pos.y)}px)`;
      raf = requestAnimationFrame(loop);
    };

    raf = requestAnimationFrame(loop);

    const onResize = () => {
      placeRandom();
      const el = bounceRef.current;
      if (el) {
        el.style.transform = `translate(${Math.round(pos.x)}px, ${Math.round(pos.y)}px)`;
      }
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
  }, [active]);

  const dismiss = () => onActiveChange(false);

  if (!active) return null;

  return (
    <div
      className="tablet-screensaver"
      role="dialog"
      aria-modal="true"
      aria-label="Screensaver"
      tabIndex={-1}
      onClick={dismiss}
      onKeyDown={(e) => {
        if (e.key === 'Escape') dismiss();
      }}
    >
      <div ref={bounceRef} className="tablet-screensaver-bounce">
        <ShatterAsciiLogo variant="screensaver" />
        <div className="tablet-screensaver-spinner" aria-hidden>
          [{SPINNER_FRAMES[spin]}] SHATTER · TAP ANYWHERE
        </div>
      </div>
      <p className="tablet-screensaver-hint">Tap anywhere to return</p>
    </div>
  );
}
