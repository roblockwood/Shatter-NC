import './AsciiLoadingScreen.css';

interface AsciiEmptyStateProps {
  onAddMachine: () => void;
}

export const AsciiEmptyState = ({ onAddMachine }: AsciiEmptyStateProps) => {
  return (
    <div className="ascii-loading-screen">
      <div className="ascii-logo">
        <pre className="ascii-art">
{` ███████╗██╗  ██╗ █████╗ ████████╗████████╗███████╗██████╗
 ██╔════╝██║  ██║██╔══██╗╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗
 ███████╗███████║███████║   ██║      ██║   █████╗  ██████╔╝
 ╚════██║██╔══██║██╔══██║   ██║      ██║   ██╔══╝  ██╔══██╗
 ███████║██║  ██║██║  ██║   ██║      ██║   ███████╗██║  ██║
 ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝`}
        </pre>
      </div>
      <div className="empty-state-message clickable" onClick={onAddMachine}>
        [ CLICK HERE TO ADD YOUR FIRST MACHINE ]
      </div>
    </div>
  );
};
