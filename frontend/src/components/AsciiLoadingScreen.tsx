import { useEffect, useState } from 'react';
import './AsciiLoadingScreen.css';

export const AsciiLoadingScreen = () => {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setFrame((prev) => (prev + 1) % 4);
    }, 150);
    return () => clearInterval(interval);
  }, []);

  const spinnerFrames = ['/', '─', '\\', '│'];

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
      <div className="loading-spinner">
        [{spinnerFrames[frame]}] LOADING...
      </div>
    </div>
  );
};
