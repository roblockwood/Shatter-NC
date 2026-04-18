import { ShatterAsciiLogo } from './ShatterAsciiLogo';
import './AsciiLoadingScreen.css';

interface AsciiEmptyStateProps {
  onAddMachine: () => void;
}

export const AsciiEmptyState = ({ onAddMachine }: AsciiEmptyStateProps) => {
  return (
    <div className="ascii-loading-screen">
      <div className="ascii-logo">
        <ShatterAsciiLogo variant="empty" />
      </div>
      <div className="empty-state-message clickable" onClick={onAddMachine}>
        [ CLICK HERE TO ADD YOUR FIRST MACHINE ]
      </div>
    </div>
  );
};
