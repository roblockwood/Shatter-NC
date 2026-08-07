import type { ReactNode } from 'react';
import { IS_DEMO_MODE } from '../config/demo';
import { DemoBanner } from './DemoBanner';
import './DemoMonitorFrame.css';

export function DemoMonitorFrame({ children }: { children: ReactNode }) {
  if (!IS_DEMO_MODE) {
    return children;
  }

  return (
    <div className="demo-monitor-stage">
      <DemoBanner />

      <div className="demo-monitor" role="presentation">
        <div className="demo-monitor-bezel">
          <div className="demo-monitor-brand">
            <span className="demo-monitor-led" aria-hidden="true" />
            <span className="demo-monitor-model">SHOP TERMINAL</span>
          </div>
          <div className="demo-monitor-screen">
            <div className="demo-monitor-screen-inner">{children}</div>
            <div className="demo-monitor-scanlines" aria-hidden="true" />
          </div>
        </div>
        <div className="demo-monitor-stand">
          <div className="demo-monitor-neck" />
          <div className="demo-monitor-base" />
        </div>
      </div>
    </div>
  );
}
