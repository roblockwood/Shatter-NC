import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { FileBrowser } from './pages/FileBrowser';
import { ToolManagement } from './pages/ToolManagement';
import { SyncConfig } from './pages/SyncConfig';
import { NotificationSettings } from './pages/NotificationSettings';
import { TabletEntry } from './pages/tablet/TabletEntry';
import { TabletSetupPage } from './pages/tablet/TabletSetupPage';
import { TabletMachineShell } from './pages/tablet/TabletMachineShell';
import { TabletRedirectToDefaultPane } from './pages/tablet/TabletRedirectToDefaultPane';
import { TabletCompressorShell } from './pages/tablet/TabletCompressorShell';
import { TabletCompressorRedirectToDefaultPane } from './pages/tablet/TabletCompressorRedirectToDefaultPane';
import { useBetaMode, useBetaModeActivator } from './hooks/useBetaMode';
import { BetaRoute } from './components/BetaRoute';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { ExpandedMachineProvider } from './contexts/ExpandedMachineContext';
import './App.css';

// Get version from environment variable (set at build time via Vite)
const APP_VERSION = import.meta.env.VITE_APP_VERSION || '0.1.0';

function Navigation() {
  const location = useLocation();
  const { isBetaMode, activateBetaMode, deactivateBetaMode } = useBetaMode();
  const handleLogoClick = useBetaModeActivator(isBetaMode, activateBetaMode, deactivateBetaMode);

  const isActive = (path: string) => location.pathname === path;

  // Tablet kiosk routes are fullscreen and should not show the standard header/nav chrome.
  if (location.pathname.startsWith('/tablet')) {
    return null;
  }

  return (
    <>
      <div className="app-header">
        <div className="app-title">
          <span
            className={`text-glow-strong ${isBetaMode ? 'beta-mode' : ''}`}
            onClick={handleLogoClick}
            style={{ cursor: 'pointer', userSelect: 'none' }}
            title={
              isBetaMode
                ? 'BETA: Tools + Kaeser compressors — click rapidly to disable'
                : 'Click rapidly to enable beta (Tools + compressors)'
            }
          >
            SHATTER v{APP_VERSION}
          </span>
        </div>
        <nav className="app-nav">
          <Link
            to="/"
            className={`nav-link ${isActive('/') ? 'active' : ''}`}
          >
            [ DASHBOARD ]
          </Link>
          <Link
            to="/files"
            className={`nav-link ${isActive('/files') ? 'active' : ''}`}
          >
            [ FILES ]
          </Link>
          <Link
            to="/sync"
            className={`nav-link ${isActive('/sync') ? 'active' : ''}`}
          >
            [ SYNC ]
          </Link>
          <Link
            to="/notifications"
            className={`nav-link ${isActive('/notifications') ? 'active' : ''}`}
          >
            [ NOTIFY ]
          </Link>
          {isBetaMode && (
            <Link
              to="/tools"
              className={`nav-link ${isActive('/tools') ? 'active' : ''}`}
            >
              [ TOOLS ]
            </Link>
          )}
        </nav>
      </div>

      <div className="app-divider">
        ╠{'═'.repeat(100)}╣
      </div>
    </>
  );
}

function App() {
  useEffect(() => {
    document.title = `Shatter v${APP_VERSION}`;
  }, []);

  return (
    <WebSocketProvider>
      <ExpandedMachineProvider>
        <Router>
          <div className="app">
            <Navigation />

            <div className="app-content">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/files" element={<FileBrowser />} />
                <Route path="/sync" element={<SyncConfig />} />
                <Route path="/notifications" element={<NotificationSettings />} />
                {/* Tablet kiosk routes */}
                <Route path="/tablet" element={<TabletEntry />} />
                <Route path="/tablet/setup" element={<TabletSetupPage />} />
                <Route path="/tablet/:machineId" element={<TabletRedirectToDefaultPane />} />
                <Route path="/tablet/:machineId/:paneSlug" element={<TabletMachineShell />} />
                <Route path="/tablet/compressor/:compressorId" element={<TabletCompressorRedirectToDefaultPane />} />
                <Route path="/tablet/compressor/:compressorId/:paneSlug" element={<TabletCompressorShell />} />
                <Route
                  path="/tools"
                  element={
                    <BetaRoute>
                      <ToolManagement />
                    </BetaRoute>
                  }
                />
              </Routes>
            </div>
          </div>
        </Router>
      </ExpandedMachineProvider>
    </WebSocketProvider>
  );
}

export default App;
