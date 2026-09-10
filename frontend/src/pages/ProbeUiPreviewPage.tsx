/**
 * Local-only UI preview for Probes glyph grid + cycle preview.
 * Open /probe-preview while vite is running — no backend required for layout/motion.
 */
import React, { useMemo, useState } from 'react';
import { ProbesPane } from '../components/machine-detail/ProbesPane';
import '../styles/terminal.css';

const MOCK_MACROS: Record<string, number> = {
  '900': 0,
  '901': 999,
  '902': 999,
  '903': 999,
  '904': 999,
  '905': 999,
  '906': 999,
  '907': 999,
  '908': 0,
  '920': 0,
};

export const ProbeUiPreviewPage: React.FC = () => {
  const [paneH, setPaneH] = useState(480);
  const pollAt = useMemo(() => new Date().toISOString(), []);

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0a0a',
        color: '#00ff00',
        fontFamily: "'IBM Plex Mono', monospace",
        padding: 16,
        boxSizing: 'border-box',
      }}
    >
      <div style={{ marginBottom: 12, maxWidth: 960 }}>
        <div style={{ fontWeight: 700, letterSpacing: '0.08em' }}>
          PROBES UI PREVIEW (local)
        </div>
        <div style={{ color: '#66ff66', fontSize: 12, marginTop: 4 }}>
          Glyph grid + param-scaled cycle preview. Arm/collect will fail without API — that is fine.
          Tweak pane height to see density.
        </div>
        <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center', marginTop: 8, fontSize: 12 }}>
          PANE H
          <input
            type="range"
            min={280}
            max={640}
            value={paneH}
            onChange={(e) => setPaneH(Number(e.target.value))}
          />
          {paneH}px
        </label>
      </div>

      <div
        style={{
          width: 'min(880px, 100%)',
          height: paneH,
          border: '1px solid #2a2a2a',
          boxShadow: '0 0 24px rgba(0,255,0,0.08)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <ProbesPane
          machineId={1}
          macros={MOCK_MACROS}
          machineStatus="standby"
          pollTimestamp={pollAt}
          pollIntervalSeconds={5}
        />
      </div>
    </div>
  );
};
