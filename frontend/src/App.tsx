import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { FileBrowser } from './pages/FileBrowser';
import './App.css';

function Navigation() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      <div className="app-header">
        <div className="app-title">
          <span className="text-glow-strong">SHATTER v0.1.0</span>
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
        </nav>
      </div>

      <div className="app-divider">
        ╠{'═'.repeat(100)}╣
      </div>
    </>
  );
}

function App() {
  return (
    <Router>
      <div className="app">
        <Navigation />

        <div className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/files" element={<FileBrowser />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
