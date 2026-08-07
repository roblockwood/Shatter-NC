import { IS_DEMO_MODE, demoInstallUrl } from '../config/demo';
import './DemoBanner.css';

export function DemoBanner() {
  if (!IS_DEMO_MODE) return null;

  return (
    <div className="demo-banner" role="status">
      <span className="demo-banner-label">DEMO MODE</span>
      <span className="demo-banner-text">Sample data only — not connected to real machines.</span>
      <a className="demo-banner-link" href={demoInstallUrl()}>
        Install Shatter →
      </a>
    </div>
  );
}
