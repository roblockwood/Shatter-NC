import { TabletScreensaverSetupSection } from './TabletScreensaverSetupSection';
import { TabletSetupPanel } from './TabletSetupPanel';
import './tablet.css';

/** Configure CNC and/or compressor kiosk IDs (`/tablet/setup`). */
export const TabletSetupPage = () => {
  return (
    <div className="tablet-route tablet-setup-page">
      <section className="tablet-setup-section" aria-labelledby="tablet-setup-cnc-heading">
        <h2 id="tablet-setup-cnc-heading" className="tablet-setup-section-heading">
          CNC machine
        </h2>
        <TabletSetupPanel kind="machine" />
      </section>
      <section className="tablet-setup-section" aria-labelledby="tablet-setup-comp-heading">
        <h2 id="tablet-setup-comp-heading" className="tablet-setup-section-heading">
          Air compressor
        </h2>
        <TabletSetupPanel kind="compressor" />
      </section>
      <TabletScreensaverSetupSection />
    </div>
  );
};
