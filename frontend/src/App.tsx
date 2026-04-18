import { useEffect, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { FileBrowser } from './pages/FileBrowser';
import { TabletCompressorShell } from './pages/tablet/TabletCompressorShell';
import { TabletCompressorRedirectToDefaultPane } from './pages/tablet/TabletCompressorRedirectToDefaultPane';
import { TabletEntry } from './pages/tablet/TabletEntry';
import { TabletMachineShell } from './pages/tablet/TabletMachineShell';
import { TabletRedirectToDefaultPane } from './pages/tablet/TabletRedirectToDefaultPane';
import { TabletSetupPage } from './pages/tablet/TabletSetupPage';
import { ToolManagement } from './pages/ToolManagement';
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

function isTabletKioskPath(pathname: string): boolean {
  return pathname === '/tablet' || pathname.startsWith('/tablet/');
}

function AppLayout() {
  const location = useLocation();
  const hideChrome = isTabletKioskPath(location.pathname);

  return (
    <div className="app">
      {!hideChrome && <Navigation />}
      <div className={`app-content${hideChrome ? ' app-content--tablet-kiosk' : ''}`}>
        <Routes>
          <Route path="/tablet/setup" element={<TabletSetupPage />} />
          <Route path="/tablet/compressor/:compressorId/:paneSlug" element={<TabletCompressorShell />} />
          <Route path="/tablet/compressor/:compressorId" element={<TabletCompressorRedirectToDefaultPane />} />
          <Route path="/tablet/:machineId/:paneSlug" element={<TabletMachineShell />} />
          <Route path="/tablet/:machineId" element={<TabletRedirectToDefaultPane />} />
          <Route path="/tablet" element={<TabletEntry />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/files" element={<FileBrowser />} />
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
  );
}

function App() {
  useEffect(() => {
    document.title = `Shatter v${APP_VERSION}`;
  }, []);

  const routerBasename = useMemo(() => {
    const raw = import.meta.env.BASE_URL || '/';
    const trimmed = raw.replace(/\/$/, '');
    return trimmed === '' ? '/' : trimmed;
  }, []);

  return (
    <WebSocketProvider>
      <ExpandedMachineProvider>
        <Router basename={routerBasename}>
          <AppLayout />
        </Router>
      </ExpandedMachineProvider>
    </WebSocketProvider>
  );
}

export default App;
