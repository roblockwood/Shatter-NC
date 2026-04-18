import { TabletSetupPanel } from './TabletSetupPanel';
import './tablet.css';

/** Configure this browser’s tablet machine id (`/tablet/setup`). */
export const TabletSetupPage = () => {
  return (
    <div className="tablet-route">
      <TabletSetupPanel />
    </div>
  );
};
