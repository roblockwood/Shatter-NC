import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { FileBrowser } from './pages/FileBrowser';
import { ToolManagement } from './pages/ToolManagement';
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
import { DemoMonitorFrame } from './components/DemoMonitorFrame';
import { IS_DEMO_MODE } from './config/demo';
import { ProbeUiPreviewPage } from './pages/ProbeUiPreviewPage';
import './App.css';

// Get version from environment variable (set at build time via Vite)
const APP_VERSION = import.meta.env.VITE_APP_VERSION || '0.1.0';
const RELEASE_CHANNEL = import.meta.env.VITE_RELEASE_CHANNEL || '';
const IS_BETA_BUILD = RELEASE_CHANNEL === 'beta';

function Navigation() {
  const location = useLocation();
  const { isBetaMode, activateBetaMode, deactivateBetaMode } = useBetaMode();
  const handleLogoClick = useBetaModeActivator(isBetaMode, activateBetaMode, deactivateBetaMode);

  const isActive = (path: string) => location.pathname === path;

  // Tablet kiosk routes are fullscreen and should not show the standard header/nav chrome.
  if (location.pathname.startsWith('/tablet')) {
    return null;
  }
  if (location.pathname.startsWith('/probe-preview')) {
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
                ? 'BETA: Tools, Notify, Sync — click rapidly to disable'
                : 'Click rapidly to enable beta (Tools, Notify, Sync)'
            }
          >
            SHATTER v{APP_VERSION}
            {IS_BETA_BUILD && (
              <span
                className="release-channel-beta"
                title="Integration build (beta branch image — not a stable release)"
              >
                {' '}[BETA]
              </span>
            )}
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
          {isBetaMode && !IS_DEMO_MODE && (
            <Link
              to="/notifications"
              className={`nav-link ${isActive('/notifications') ? 'active' : ''}`}
            >
              [ NOTIFY ]
            </Link>
          )}
          {isBetaMode && !IS_DEMO_MODE && (
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
        <Router basename={import.meta.env.BASE_URL}>
          <DemoMonitorFrame>
            <div className="app">
              <Navigation />

              <div className="app-content">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/files" element={<FileBrowser />} />
                <Route path="/sync" element={<Navigate to="/" replace />} />
                <Route path="/probe-preview" element={<ProbeUiPreviewPage />} />
                <Route
                  path="/notifications"
                  element={
                    <BetaRoute>
                      <NotificationSettings />
                    </BetaRoute>
                  }
                />
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
          </DemoMonitorFrame>
        </Router>
      </ExpandedMachineProvider>
    </WebSocketProvider>
  );
}

export default App;
