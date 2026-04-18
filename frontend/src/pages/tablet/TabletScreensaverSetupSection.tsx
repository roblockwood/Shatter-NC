import { type FormEvent, useState } from 'react';
import {
  readStoredTabletScreensaverIdleMinutes,
  TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT,
  TABLET_SCREENSAVER_IDLE_MINUTES_MAX,
  TABLET_SCREENSAVER_IDLE_MINUTES_MIN,
  writeStoredTabletScreensaverIdleMinutes,
} from './tabletScreensaverStorage';
import './tablet.css';

/** Configure auto screensaver delay for both CNC and compressor tablet kiosks (`/tablet/setup`). */
export function TabletScreensaverSetupSection() {
  const [idleInput, setIdleInput] = useState(() =>
    String(readStoredTabletScreensaverIdleMinutes())
  );
  const [hint, setHint] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const n = Number.parseInt(idleInput.trim(), 10);
    if (!Number.isFinite(n)) {
      setHint(`Use a whole number between ${TABLET_SCREENSAVER_IDLE_MINUTES_MIN} and ${TABLET_SCREENSAVER_IDLE_MINUTES_MAX}.`);
      return;
    }
    writeStoredTabletScreensaverIdleMinutes(n);
    setIdleInput(String(readStoredTabletScreensaverIdleMinutes()));
    setHint('Saved. Applies when you open a tablet view (or immediately if one is already open).');
  };

  return (
    <section className="tablet-setup-section" aria-labelledby="tablet-setup-screensaver-heading">
      <h2 id="tablet-setup-screensaver-heading" className="tablet-setup-section-heading">
        Screensaver
      </h2>
      <div className="tablet-setup-panel">
        <p className="tablet-setup-intro">
          After this many minutes with no touch, pointer, or key activity, the idle screensaver opens
          automatically on CNC and compressor tablet views. Default {TABLET_SCREENSAVER_IDLE_MINUTES_DEFAULT}{' '}
          minutes.
        </p>
        <form className="tablet-setup-form" onSubmit={handleSubmit}>
          <label className="tablet-setup-label" htmlFor="tablet-screensaver-idle-min">
            IDLE MINUTES (1–{TABLET_SCREENSAVER_IDLE_MINUTES_MAX})
          </label>
          <input
            id="tablet-screensaver-idle-min"
            type="number"
            min={TABLET_SCREENSAVER_IDLE_MINUTES_MIN}
            max={TABLET_SCREENSAVER_IDLE_MINUTES_MAX}
            step={1}
            className="tablet-setup-input"
            value={idleInput}
            onChange={(e) => {
              setIdleInput(e.target.value);
              setHint(null);
            }}
            autoComplete="off"
          />
          {hint && (
            <p className="tablet-setup-list-hint" role="status">
              {hint}
            </p>
          )}
          <div className="tablet-setup-actions">
            <button type="submit" className="tablet-setup-btn primary">
              [ SAVE IDLE TIME ]
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
