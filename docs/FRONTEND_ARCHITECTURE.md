# Frontend Architecture

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Application Entry Point](#application-entry-point)
- [Routing Architecture](#routing-architecture)
- [Pages](#pages)
  - [Dashboard](#dashboard)
  - [File Browser](#file-browser)
- [Component Library](#component-library)
  - [UI Components](#ui-components)
  - [Feature Components](#feature-components)
- [Custom Hooks](#custom-hooks)
- [State Management](#state-management)
- [Styling Architecture](#styling-architecture)
- [API Communication](#api-communication)
- [Real-Time Updates](#real-time-updates)
- [Performance Optimizations](#performance-optimizations)
- [Type Safety](#type-safety)
- [Design Patterns](#design-patterns)
- [Build and Development](#build-and-development)

---

## Overview

The Shatter CNC platform frontend is a single-page application (SPA) built with React and TypeScript, designed to provide real-time fleet monitoring and file management for CNC machines. The application emphasizes a terminal aesthetic with ASCII characters, monospace fonts, and a retro command-line interface look.

**Key Characteristics:**
- Real-time WebSocket updates for machine status
- Terminal-inspired UI with box-drawing characters
- Type-safe TypeScript throughout
- Minimal state management (no Redux/MobX)
- Component-based architecture
- Fast development with Vite HMR

**Target Users:**
- CNC machine operators
- Production managers
- Manufacturing engineers

---

## Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.2.0 | UI framework |
| **TypeScript** | 5.9.3 | Type safety and developer experience |
| **Vite** | 7.2.4 | Build tool and development server |
| **React Router** | 7.9.6 | Client-side routing |

### Supporting Libraries

| Library | Version | Usage |
|---------|---------|-------|
| **@tanstack/react-query** | 5.90.11 | Installed but not heavily used (future use) |
| **zustand** | 5.0.9 | Installed but not heavily used (future use) |

**Location:** [package.json](../frontend/package.json)

### Why This Stack?

1. **React 19** - Latest React with improved performance and concurrent rendering
2. **TypeScript** - Catches errors at compile time, improves maintainability
3. **Vite** - Extremely fast HMR, optimized production builds
4. **No Heavy State Management** - Simple app with minimal state complexity, WebSocket handles most state updates

---

## Project Structure

```
frontend/
├── src/
│   ├── components/           # Reusable and feature components
│   │   ├── ui/               # Core UI components (Modal, StatusIndicator, etc.)
│   │   │   ├── Modal.tsx
│   │   │   ├── StatusIndicator.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── TerminalBox.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── PollingOscilloscope.tsx
│   │   │   └── StatusOscilloscope.tsx
│   │   ├── machine-detail/   # Machine detail view panes
│   │   │   ├── AlarmPane.tsx
│   │   │   ├── ColorPicker.tsx
│   │   │   ├── CurrentProgramPane.tsx
│   │   │   ├── CycleHistoryPane.tsx
│   │   │   ├── LayoutManager.tsx
│   │   │   ├── PanelPane.tsx
│   │   │   ├── StatusTimeline.tsx
│   │   │   └── ToolsPane.tsx
│   │   ├── modals/           # Modal components
│   │   │   ├── summary/      # Summary modal components
│   │   │   │   ├── MachineStatusRow.tsx
│   │   │   │   ├── OnlineSummaryRow.tsx
│   │   │   │   ├── OfflineSummaryRow.tsx
│   │   │   │   ├── RunningSummaryRow.tsx
│   │   │   │   └── TimeRangeSelector.tsx
│   │   │   ├── SummaryModal.tsx
│   │   │   └── SummaryPopup.tsx
│   │   ├── MachineCard.tsx   # Machine status card component
│   │   ├── AddMachineCard.tsx
│   │   ├── ValidationResultModal.tsx
│   │   ├── ToolListModal.tsx
│   │   ├── ToolDetailModal.tsx
│   │   ├── DeleteConfirmModal.tsx
│   │   ├── SaveConfirmModal.tsx
│   │   ├── UploadConfirmationModal.tsx
│   │   ├── AsciiEmptyState.tsx
│   │   ├── AsciiLoadingScreen.tsx
│   │   └── BetaRoute.tsx
│   ├── pages/                # Top-level page components
│   │   ├── Dashboard.tsx     # Fleet monitoring page
│   │   └── FileBrowser.tsx   # File management page
│   ├── hooks/                # Custom React hooks
│   │   ├── useWebSocket.ts   # WebSocket connection management
│   │   └── useBetaMode.ts    # Beta mode activation hook
│   ├── contexts/              # React contexts
│   │   └── WebSocketContext.tsx  # WebSocket context provider
│   ├── styles/               # Global styles
│   │   └── terminal.css      # Terminal aesthetic styles
│   ├── config/               # Configuration
│   │   └── api.ts            # API base URL configuration
│   ├── App.tsx               # Root application component
│   ├── App.css               # Application-level styles
│   ├── main.tsx              # Application entry point
│   └── index.css             # Global CSS reset
├── public/                   # Static assets
├── index.html                # HTML entry point
├── vite.config.ts            # Vite configuration
├── tsconfig.json             # TypeScript configuration
└── package.json              # Dependencies and scripts
```

**Design Decision:**
- **Flat component structure** - All components in `/components` with `/ui` subfolder for reusable UI primitives
- **No deep nesting** - Easy to find components, avoids over-abstraction
- **Minimal hooks** - Only one custom hook (`useWebSocket`), keeping complexity low

---

## Application Entry Point

### main.tsx

The application entry point sets up React 19's `createRoot` and enables Strict Mode.

**Location:** [main.tsx:1-11](../frontend/src/main.tsx#L1-L11)

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/terminal.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

**Key Points:**
- **StrictMode** - Enables development warnings and checks
- **Style imports** - Global terminal styles loaded before App
- **Type assertion** - `!` asserts `getElementById` returns non-null

---

## Routing Architecture

### App.tsx

The root component sets up React Router with a simple two-page application.

**Location:** [App.tsx:1-57](../frontend/src/App.tsx#L1-L57)

```typescript
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { FileBrowser } from './pages/FileBrowser';

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
          <Link to="/" className={`nav-link ${isActive('/') ? 'active' : ''}`}>
            [ DASHBOARD ]
          </Link>
          <Link to="/files" className={`nav-link ${isActive('/files') ? 'active' : ''}`}>
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
```

**Routes:**
- `/` - Dashboard (fleet monitoring)
- `/files` - File Browser (FTP file management)
- `/tools` - Tool Management (beta feature, requires beta mode activation)

**Design Decisions:**
1. **BrowserRouter** - Clean URLs without hash (`/files` not `/#/files`)
2. **Simple routing** - 3 main routes, no nested routes
3. **Beta mode routing** - Tool Management route protected by `BetaRoute` component
4. **Active link highlighting** - `useLocation` hook detects current route
5. **Terminal aesthetic** - Box-drawing characters (`╠═╣`) for dividers
6. **Inline Navigation component** - Keeps related code together

---

## Pages

### Dashboard

Fleet monitoring page showing real-time status of all configured CNC machines.

**Location:** [Dashboard.tsx](../frontend/src/pages/Dashboard.tsx)

**Key Features:**
- Real-time WebSocket connection for machine status updates
- Fleet overview bar with aggregate statistics (MACHINES, RUNNING, ONLINE counts)
- Machine cards with status, cycle time, power hours, part counts
- Edit mode for adding/deleting machines
- Summary modals (Running Summary, Online/Offline Summary)
- Polling graph visualization (30-char width, 1-hour window)
- Empty state when no machines configured

**Component Structure:**

```typescript
export const Dashboard = () => {
  // WebSocket connection
  const { machines, isConnected, removeMachine, addMachine } = useWebSocket(WS_URL);

  // UI state
  const [editMode, setEditMode] = useState(false);
  const [showAddMachine, setShowAddMachine] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [machineToDelete, setMachineToDelete] = useState<MachineStatus | null>(null);
  const [showRunningSummary, setShowRunningSummary] = useState(false);
  const [showOnlineSummary, setShowOnlineSummary] = useState(false);

  // Aggregate statistics
  const onlineCount = machines.filter(m => m.is_online === true).length;
  const runningCount = machines.filter(m =>
    m.is_online === true && m.status?.includes('Running')
  ).length;

  // Render machine cards
  return (
    <div className="dashboard">
      <FleetOverviewBar />
      <div className="machines-grid">
        {machines.map(machine => (
          <MachineCard
            key={machine.machine_id}
            machine={machine}
            editMode={editMode}
            onDelete={handleDeleteClick}
          />
        ))}
        {editMode && <AddMachineCard onAdd={handleAddMachine} />}
      </div>
    </div>
  );
};
```

**Data Flow:**
1. `useWebSocket(WS_URL)` establishes WebSocket connection
2. Receives `initial_status` message with all machines
3. Receives `status_update` messages for individual machines
4. Updates machine cards in real-time
5. User actions (add/delete) trigger API calls and WebSocket updates

**Related Documentation:**
- See [DASHBOARD_WORKFLOWS.md](./DASHBOARD_WORKFLOWS.md) for detailed user workflows

---

### File Browser

FTP file management page with G-code validation and deployment.

**Location:** [FileBrowser.tsx](../frontend/src/pages/FileBrowser.tsx)

**Key Features:**
- FTP directory browsing with breadcrumb navigation
- File upload with automatic G-code validation
- File download and viewing
- Program validation against machine state (tools, WCS offsets)
- Program deployment to O-numbers (O2000-O3999)
- Re-validation feature for deployed programs
- Deployment history tracking

**Component Structure:**

```typescript
export const FileBrowser = () => {
  // Machine selection
  const [selectedMachine, setSelectedMachine] = useState<MachineConfig | null>(null);

  // File listing
  const [programs, setPrograms] = useState<Program[]>([]);
  const [currentPath, setCurrentPath] = useState('/PROGRAM');

  // Validation state
  const [validationResults, setValidationResults] = useState<ValidationResults | null>(null);
  const [showValidationModal, setShowValidationModal] = useState(false);

  // Deployment state
  const [deployments, setDeployments] = useState<Deployment[]>([]);

  // File operations
  const handleNavigate = async (path: string) => { /* ... */ };
  const handleUpload = async (file: File) => { /* ... */ };
  const handleDownload = async (filename: string) => { /* ... */ };
  const handleValidate = async (filename: string) => { /* ... */ };
  const handleDeploy = async (oNumber: number) => { /* ... */ };

  return (
    <div className="file-browser">
      <MachineSelector machines={machines} onSelect={setSelectedMachine} />
      <BreadcrumbPath path={currentPath} onNavigate={handleNavigate} />
      <FileList programs={programs} onAction={handleAction} />
      <ValidationResultModal
        result={validationResults}
        onDeploy={handleDeploy}
      />
    </div>
  );
};
```

**Data Flow:**
1. User selects machine from dropdown
2. Fetch FTP directory listing via API
3. User clicks file → triggers validation
4. Validation process: download file → parse G-code → query machine → validate
5. Display validation results modal with errors/warnings
6. User deploys valid program to O-number
7. Deployment recorded in database and displayed in history

**Related Documentation:**
- See [FILE_BROWSER_WORKFLOWS.md](./FILE_BROWSER_WORKFLOWS.md) for detailed user workflows
- See [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) for validation algorithm

---

### Tool Management

Tool usage tracking and speed/feed analysis page.

**Location:** [ToolManagement.tsx](../frontend/src/pages/ToolManagement.tsx)

**Key Features:**
- Aggregated tool summary with usage statistics
- Detailed per-program speed/feed analysis
- Hierarchical display: Program → Operations with all 8 feedrate types
- Tool-related alarm tracking
- CSV/JSON export capabilities

**Component Structure:**

```typescript
export const ToolManagement = () => {
  // Data fetching
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [selectedTool, setSelectedTool] = useState<number | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Load tool summary on mount
  useEffect(() => {
    const fetchTools = async () => {
      const response = await fetch('/api/tools/summary');
      const data = await response.json();
      setTools(data.tools);
    };
    fetchTools();
  }, []);

  // Handle tool click → show detail modal
  const handleToolClick = (toolNumber: number) => {
    setSelectedTool(toolNumber);
    setShowDetailModal(true);
  };

  return (
    <div className="tool-management">
      <div className="tool-header">
        <h1>┌─ TOOL MANAGEMENT ─┐</h1>
        <div className="summary-stats">
          <span>TOTAL TOOLS: {tools.length}</span>
          <span>TOTAL PROGRAMS: {totalPrograms}</span>
        </div>
      </div>

      <table className="tools-table">
        <thead>
          <tr>
            <th>TOOL</th>
            <th>DIAMETER</th>
            <th>DESCRIPTION</th>
            <th>PROGRAMS</th>
            <th>RUNTIME</th>
            <th>OPERATIONS</th>
          </tr>
        </thead>
        <tbody>
          {tools.map(tool => (
            <tr key={tool.tool_number} onClick={() => handleToolClick(tool.tool_number)}>
              <td>T{tool.tool_number}</td>
              <td>{tool.diameter}"</td>
              <td>{tool.description}</td>
              <td>{tool.programs_using}</td>
              <td>{formatRuntime(tool.estimated_runtime_seconds)}</td>
              <td>{tool.operation_types.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {showDetailModal && (
        <ToolDetailModal
          toolNumber={selectedTool}
          onClose={() => setShowDetailModal(false)}
        />
      )}
    </div>
  );
};
```

**Data Flow:**
1. Component mounts → fetch `/api/tools/summary`
2. Display tool list with aggregated statistics
3. User clicks tool → open detail modal
4. Detail modal fetches `/api/tools/{tool_number}`
5. Display hierarchical program → operations structure
6. User can export data to CSV/JSON

**Terminal Aesthetic:**
- ASCII border characters for headers and tables
- Monospace fonts throughout
- Green-on-black terminal color scheme
- Hover effects with border highlighting

---

#### ToolDetailModal

Modal component for detailed tool analysis with per-program operations.

**Location:** [ToolDetailModal.tsx](../frontend/src/components/ToolDetailModal.tsx)

**Key Features:**
- Fetches detailed tool data on mount
- Displays hierarchical program → operations structure
- Shows all 8 feedrate types per operation
- Includes tool-related alarm history
- Loading and error states

**Component Structure:**

```typescript
export const ToolDetailModal = ({ toolNumber, onClose }: Props) => {
  const [toolDetail, setToolDetail] = useState<ToolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchToolDetail = async () => {
      try {
        const response = await fetch(`/api/tools/${toolNumber}`);
        const data = await response.json();
        setToolDetail(data);
      } catch (err) {
        setError('Failed to load tool details');
      } finally {
        setLoading(false);
      }
    };
    fetchToolDetail();
  }, [toolNumber]);

  const renderContent = () => {
    if (loading) return <div>LOADING...</div>;
    if (error) return <div className="error">{error}</div>;

    return (
      <>
        {/* Tool Specifications */}
        <div className="detail-section">
          <div className="spec-grid">
            <div className="spec-item">
              <div className="spec-label">TOOL NUMBER</div>
              <div className="spec-value">T{toolDetail.tool_number}</div>
            </div>
            <div className="spec-item">
              <div className="spec-label">DIAMETER</div>
              <div className="spec-value">{toolDetail.diameter}"</div>
            </div>
            <div className="spec-item">
              <div className="spec-label">DESCRIPTION</div>
              <div className="spec-value">{toolDetail.description}</div>
            </div>
            {/* ... more specs ... */}
          </div>
        </div>

        {/* Programs & Operations - Hierarchical Structure */}
        <div className="detail-section">
          <div className="detail-section-header">
            ┌─ PROGRAMS & OPERATIONS ─────────────────┐
          </div>
          <div className="detail-section-content no-padding">
            {toolDetail.programs.map((prog) => (
              <div key={prog.program_id} className="program-section">
                {/* Program Header */}
                <div className="program-header">
                  <span className="text-info">{prog.filename}</span>
                  <span className="text-dim"> v{prog.version}</span>
                  <span className="separator"> │ </span>
                  <span>RUNS: {prog.production_runs}</span>
                  <span className="separator"> │ </span>
                  <span className="text-dim">
                    LAST RUN: {prog.last_run ? formatDate(prog.last_run) : 'Never'}
                  </span>
                </div>

                {/* Operations Table - All 8 Feedrate Types */}
                {prog.operations.length > 0 && (
                  <table className="operations-table">
                    <thead>
                      <tr>
                        <th>OPERATION</th>
                        <th>SPINDLE</th>
                        <th>CUTTING</th>
                        <th>PLUNGE</th>
                        <th>FINISH</th>
                        <th>ENTRY</th>
                        <th>EXIT</th>
                        <th>DIRECT</th>
                        <th>TRANS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prog.operations.map((op, idx) => (
                        <tr key={idx}>
                          <td className="text-info">{op.operation_name || 'UNKNOWN'}</td>
                          <td>{formatValue(op.spindle_speed)}</td>
                          <td>{formatValue(op.feedrate_cutting)}</td>
                          <td>{formatValue(op.feedrate_plunge)}</td>
                          <td>{formatValue(op.feedrate_finish)}</td>
                          <td>{formatValue(op.feedrate_entry)}</td>
                          <td>{formatValue(op.feedrate_exit)}</td>
                          <td>{formatValue(op.feedrate_direct)}</td>
                          <td>{formatValue(op.feedrate_transition)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
          <div className="detail-section-footer">
            └──────────────────────────────────────────┘
          </div>
        </div>

        {/* Alarms Section */}
        {toolDetail.alarms.length > 0 && (
          <div className="detail-section">
            <div className="detail-section-header">
              ┌─ TOOL-RELATED ALARMS ───────────────────┐
            </div>
            {/* ... alarm display ... */}
          </div>
        )}
      </>
    );
  };

  return (
    <div className="tool-detail-modal-overlay" onClick={onClose}>
      <div className="tool-detail-modal" onClick={e => e.stopPropagation()}>
        <div className="tool-detail-modal-header">
          <h2 className="tool-detail-modal-title">
            TOOL T{toolNumber} ANALYSIS
          </h2>
          <button className="tool-detail-modal-close" onClick={onClose}>
            [X]
          </button>
        </div>
        <div className="tool-detail-modal-content">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};
```

**Data Structure (Hierarchical):**

```typescript
interface ToolDetail {
  tool_number: number;
  diameter: number;
  description: string;
  programs: ProgramUsage[];  // Programs contain operations
  alarms: ToolAlarm[];
}

interface ProgramUsage {
  program_id: number;
  filename: string;
  version: number;
  production_runs: number;
  last_run: string | null;
  operations: OperationStats[];  // Nested within program
}

interface OperationStats {
  operation_name: string | null;
  spindle_speed: number | null;
  feedrate_cutting: number | null;
  feedrate_plunge: number | null;
  feedrate_finish: number | null;
  feedrate_entry: number | null;
  feedrate_exit: number | null;
  feedrate_direct: number | null;
  feedrate_transition: number | null;
}
```

**Critical Design: No Aggregation**

Operations are **NOT** aggregated across programs. The same operation name (e.g., "ADAPTIVE1") may appear in multiple programs with different speed/feed values. This preserves per-program context and allows comparison of machining parameters across different parts.

**Styling:**

CSS file: [ToolDetailModal.css](../frontend/src/components/ToolDetailModal.css)

Key features:
- Fixed modal overlay with centered content
- Scrollable content area with custom scrollbar
- Program section headers with metadata
- Wide operations table (9 columns) with right-aligned numeric values
- Responsive breakpoints for smaller screens
- Terminal aesthetic with monospace fonts and borders

**Performance:**
- Modal lazy-loads data only when opened
- Single API call per tool detail view
- Minimal re-renders (data fetched once on mount)

---

## Component Library

### UI Components

Reusable, low-level UI primitives following the terminal aesthetic.

#### Modal

Generic modal component with terminal-style borders and Escape key handling.

**Location:** [Modal.tsx:1-54](../frontend/src/components/ui/Modal.tsx#L1-L54)

```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer }) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-border-top">
            ╔{'═'.repeat(30)}╗
          </div>
          <div className="modal-title">
            {title}
            <button className="modal-close" onClick={onClose}>[✕]</button>
          </div>
          <div className="modal-border-middle">
            ╠{'═'.repeat(30)}╣
          </div>
        </div>
        <div className="modal-body">{children}</div>
        <div className="modal-footer">
          {footer || <div className="modal-border-bottom">╚{'═'.repeat(30)}╝</div>}
        </div>
      </div>
    </div>
  );
};
```

**Features:**
- **Overlay click to close** - Clicking outside modal closes it
- **Escape key handling** - Press Escape to close
- **Event propagation prevention** - Clicking modal content doesn't close
- **Terminal borders** - Box-drawing characters (`╔═╗╠╣╚╝`)
- **Optional footer** - Custom footer or default border

**Usage:**
```typescript
<Modal isOpen={showModal} onClose={() => setShowModal(false)} title="VALIDATION RESULTS">
  <div>Modal content here</div>
</Modal>
```

---

#### StatusIndicator

Visual status indicator with icon and optional label.

**Location:** [StatusIndicator.tsx:1-40](../frontend/src/components/ui/StatusIndicator.tsx#L1-L40)

```typescript
type Status = 'online' | 'offline' | 'warning' | 'error' | 'idle' | 'running';

interface StatusIndicatorProps {
  status: Status;
  label?: string;
  blink?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  blink = false,
  className = '',
}) => {
  const statusConfig = {
    online: { icon: '●', color: 'var(--color-success)', text: 'ONLINE' },
    running: { icon: '►', color: 'var(--color-success)', text: 'RUNNING' },
    offline: { icon: '○', color: 'var(--color-offline)', text: 'OFFLINE' },
    idle: { icon: '◌', color: 'var(--color-info)', text: 'IDLE' },
    warning: { icon: '◐', color: 'var(--color-warning)', text: 'WARNING' },
    error: { icon: '✕', color: 'var(--color-error)', text: 'ERROR' },
  };

  const config = statusConfig[status];

  return (
    <span className={`status-indicator ${blink ? 'status-blink' : ''} ${className}`}
          style={{ color: config.color }}>
      <span className="status-icon">{config.icon}</span>
      {label !== undefined && <span className="status-label"> {label}</span>}
      {label === undefined && <span className="status-label"> [{config.text}]</span>}
    </span>
  );
};
```

**Status Types:**
- `online` - Green filled circle (`●`)
- `running` - Green play triangle (`►`)
- `offline` - Gray hollow circle (`○`)
- `idle` - Blue hollow circle (`◌`)
- `warning` - Yellow half-filled circle (`◐`)
- `error` - Red X mark (`✕`)

**Usage:**
```typescript
<StatusIndicator status="running" />
<StatusIndicator status="error" label="ALARM ACTIVE" blink />
```

---

#### Other UI Components

**ProgressBar** - Progress indicator for file uploads
- Location: [ProgressBar.tsx](../frontend/src/components/ui/ProgressBar.tsx)
- Features: Percentage display, terminal-style bar

**TerminalBox** - Scrollable code/text display
- Location: [TerminalBox.tsx](../frontend/src/components/ui/TerminalBox.tsx)
- Features: Monospace font, line numbers, syntax highlighting (future)

**Select** - Dropdown select component
- Location: [Select.tsx](../frontend/src/components/ui/Select.tsx)
- Features: Terminal-styled select dropdown

**PollingOscilloscope** - Visual polling status indicator
- Location: [PollingOscilloscope.tsx](../frontend/src/components/ui/PollingOscilloscope.tsx)
- Features: ASCII oscilloscope visualization of polling patterns

**StatusOscilloscope** - Visual status timeline indicator
- Location: [StatusOscilloscope.tsx](../frontend/src/components/ui/StatusOscilloscope.tsx)
- Features: ASCII visualization of status changes over time

---

### Feature Components

Domain-specific components built from UI primitives.

#### MachineCard

Complex component displaying machine status with edit mode and validation.

**Location:** [MachineCard.tsx:1-679](../frontend/src/components/MachineCard.tsx#L1-L679)

**Props:**
```typescript
interface MachineCardProps {
  machine: MachineStatus;
  editMode?: boolean;
  onDelete?: (machine: MachineStatus) => void;
}
```

**Features:**
1. **Status Display:**
   - Machine name with color-coded status (green = running, red = offline, gray = idle)
   - Status, cycle time, power-on hours
   - Part counters, current tool
   - Alarm indicator with tooltip

2. **Edit Mode:**
   - Network configuration (IP, FTP credentials, ports)
   - Validation tolerances (tool diameter, length, WCS offsets)
   - Poll interval and enabled checkbox
   - Test connection button
   - Save/Cancel buttons

3. **Tool Modal:**
   - View all tools in ATC (Automatic Tool Changer)
   - Tool number, name, diameter, length

4. **Upload & Validate:**
   - File input for G-code upload
   - Automatic validation on upload
   - Validation results modal

5. **Polling Graph:**
   - 30-character ASCII visualization
   - 1-hour time window
   - Shows polling success/failure pattern

**State Management:**
```typescript
const [showToolModal, setShowToolModal] = useState(false);
const [showValidationModal, setShowValidationModal] = useState(false);
const [validationResult, setValidationResult] = useState<any>(null);
const [isEditing, setIsEditing] = useState(false);
const [editFormData, setEditFormData] = useState({ /* ... */ });
```

**Key Code Sections:**

**Fetching Full Machine Configuration** [MachineCard.tsx:86-117](../frontend/src/components/MachineCard.tsx#L86-L117):
```typescript
useEffect(() => {
  const fetchMachineConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`);
      if (response.ok) {
        const fullMachineData = await response.json();
        setEditFormData({
          ip_address: fullMachineData.ip_address || '',
          // ... other fields
        });
      }
    } catch (error) {
      console.error('Error fetching machine configuration:', error);
    }
  };
  fetchMachineConfig();
}, [machine.machine_id]);
```

**Edit Save Handler** [MachineCard.tsx:121-153](../frontend/src/components/MachineCard.tsx#L121-L153):
```typescript
const handleEditSave = async () => {
  if (!editFormValid) {
    setEditError('Please fill in all required fields');
    return;
  }

  setIsEditSaving(true);
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines/${machine.machine_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editFormData),
    });

    if (!response.ok) {
      throw new Error(`Update failed: ${response.statusText}`);
    }

    setEditSuccess(true);
    setTimeout(() => {
      setIsEditing(false);
      setEditSuccess(false);
    }, 1500);
  } catch (error) {
    setEditError(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsEditSaving(false);
  }
};
```

**Status Type Detection** [MachineCard.tsx:221-226](../frontend/src/components/MachineCard.tsx#L221-L226):
```typescript
const getStatusType = () => {
  if (!machine.is_online) return 'offline';
  if (machine.status?.includes('Error')) return 'error';
  if (machine.status?.includes('Running')) return 'running';
  return 'idle';
};
```

**Design Decisions:**
1. **Inline edit mode** - Transforms card into edit form, no separate page
2. **Optimistic UI** - Shows success message before closing edit mode
3. **Validation on upload** - Automatically validates uploaded G-code
4. **Color-coded states** - Green (running), red (offline/error), gray (idle)

---

#### ValidationResultModal

Displays G-code validation results with tool and WCS offset validation.

**Location:** [ValidationResultModal.tsx](../frontend/src/components/ValidationResultModal.tsx)

**Features:**
- Tool validation results (diameter, length tolerance checks)
- WCS offset validation (X, Y, Z tolerance checks)
- Warnings and errors summary
- Deploy button (enabled only if valid)
- O-number input for deployment
- Re-validate button for deployed programs

**Related Documentation:**
- See [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md) for validation algorithm details

---

#### ToolListModal

Modal displaying all tools in the machine's ATC.

**Location:** [ToolListModal.tsx](../frontend/src/components/ToolListModal.tsx)

**Features:**
- Scrollable tool list
- Tool number, name, diameter, length
- Current tool highlighted
- Terminal-style table layout

---

#### AddMachineCard

Card displayed in edit mode for adding new machines.

**Location:** [AddMachineCard.tsx](../frontend/src/components/AddMachineCard.tsx)

**Features:**
- Machine name input
- Network configuration (IP, FTP credentials, ports)
- Validation tolerances
- Test connection before adding
- Add/Cancel buttons

---

#### SummaryModal & SummaryPopup

Modals for displaying aggregate statistics and summaries.

**Location:**
- [SummaryModal.tsx](../frontend/src/components/SummaryModal.tsx)
- [SummaryPopup.tsx](../frontend/src/components/SummaryPopup.tsx)

**Features:**
- Running Summary - Machine utilization over time ranges
- Online/Offline Summary - Connection health over time
- Time range selector (Last Hour, Last 4 Hours, Last 8 Hours, Last 24 Hours, Last Week)
- Machine-specific rows with time calculations

**Related Documentation:**
- See [DASHBOARD_SUMMARIES.md](./DASHBOARD_SUMMARIES.md) for detailed summary feature guide

---

#### Machine Detail Panes

Components for the machine detail view (accessed from machine cards).

**Location:** `frontend/src/components/machine-detail/`

**Components:**
- **AlarmPane** - Displays active alarms with severity-based sorting and color coding
- **ColorPicker** - Color selection component for ATC tool colors
- **CurrentProgramPane** - Shows current program information and deployment details
- **CycleHistoryPane** - Displays cycle time history and trends
- **LayoutManager** - Manages pane layout configuration for machine detail view
- **PanelPane** - Displays panel status information
- **StatusTimeline** - Visual timeline of machine status changes
- **ToolsPane** - Tool management interface with ATC and tool table views

**Related Documentation:**
- See [TOOLS_PANE_DATA_COVERAGE.md](./TOOLS_PANE_DATA_COVERAGE.md) for tools pane details

---

#### Additional Modal Components

**ToolDetailModal** - Detailed tool information modal
- Location: [ToolDetailModal.tsx](../frontend/src/components/ToolDetailModal.tsx)
- Features: Tool usage history, speed/feed analysis, machine usage statistics

**SaveConfirmModal** - Confirmation modal for saving changes
- Location: [SaveConfirmModal.tsx](../frontend/src/components/SaveConfirmModal.tsx)

**UploadConfirmationModal** - Confirmation modal for file uploads
- Location: [UploadConfirmationModal.tsx](../frontend/src/components/UploadConfirmationModal.tsx)

**AsciiEmptyState** - Empty state component with ASCII art
- Location: [AsciiEmptyState.tsx](../frontend/src/components/AsciiEmptyState.tsx)

**AsciiLoadingScreen** - Loading screen with ASCII animation
- Location: [AsciiLoadingScreen.tsx](../frontend/src/components/AsciiLoadingScreen.tsx)

**BetaRoute** - Route wrapper for beta features requiring activation
- Location: [BetaRoute.tsx](../frontend/src/components/BetaRoute.tsx)
- Features: Protects beta routes, requires rapid logo clicks to activate

---

## Custom Hooks

### useWebSocket

Custom hook for managing WebSocket connection and machine state.

**Location:** [useWebSocket.ts](../frontend/src/hooks/useWebSocket.ts)

**Note:** This hook is typically used via `WebSocketContext` rather than directly. See [State Management](#state-management) section for context usage.

**Purpose:**
- Establish WebSocket connection to backend
- Receive real-time machine status updates
- Manage machine state (Map of machine_id → MachineStatus)
- Auto-reconnect on disconnect
- Provide machine add/remove functions

**Hook Interface:**

```typescript
export const useWebSocket = (url: string) => {
  const [machines, setMachines] = useState<Map<number, MachineStatus>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Connection management
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[WS] Connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleMessage(message);
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected. Reconnecting in 5s...');
        setIsConnected(false);
        setTimeout(connect, 5000); // Auto-reconnect
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  // Message handling
  const handleMessage = (message: any) => {
    if (message.type === 'initial_status') {
      // Bulk update on connect
      const machineMap = new Map<number, MachineStatus>();
      message.machines.forEach((machine: MachineStatus) => {
        machineMap.set(machine.machine_id, machine);
      });
      setMachines(machineMap);
    } else if (message.type === 'status_update') {
      // Single machine update
      setMachines(prev => {
        const updated = new Map(prev);
        updated.set(message.data.machine_id, message.data);
        return updated;
      });
    }
  };

  // Machine management
  const removeMachine = (machineId: number) => {
    setMachines(prev => {
      const updated = new Map(prev);
      updated.delete(machineId);
      return updated;
    });
  };

  const addMachine = (machine: MachineStatus) => {
    setMachines(prev => {
      const updated = new Map(prev);
      updated.set(machine.machine_id, machine);
      return updated;
    });
  };

  return {
    machines: Array.from(machines.values()),
    isConnected,
    removeMachine,
    addMachine,
  };
};
```

**Message Types:**

1. **initial_status** - Sent on WebSocket connect
```json
{
  "type": "initial_status",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "machines": [
    {
      "machine_id": 1,
      "machine_name": "HAAS-VF2",
      "is_online": true,
      "status": "Running",
      "cycle_time": "0123:45:30.5",
      "power_on_hours": "12345:30:15.0",
      "counters": [{ "counter_number": 1, "count": 1250 }],
      "tools": [...],
      "current_tool": 5,
      "alarms": [],
      "poll_timestamp": "2025-01-15T10:30:00.000Z"
    }
  ]
}
```

2. **status_update** - Sent every 5 seconds per machine
```json
{
  "type": "status_update",
  "timestamp": "2025-01-15T10:30:05.000Z",
  "data": {
    "machine_id": 1,
    "machine_name": "HAAS-VF2",
    "is_online": true,
    "status": "Running",
    // ... same structure as initial_status machine
  }
}
```

**Design Decisions:**

1. **Map for machine storage** - O(1) lookup by machine_id, efficient updates
2. **Auto-reconnect** - 5-second delay on disconnect ensures resilience
3. **Ref for WebSocket** - Prevents recreation on every render
4. **Immutable state updates** - `new Map(prev)` ensures React detects changes
5. **Array return** - Convert Map to Array for easy iteration in components

**Performance:**
- Single WebSocket connection shared across all components
- Efficient Map-based state updates
- No unnecessary re-renders (only when machines change)

**Related Documentation:**
- See [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) for full protocol spec

---

### useBetaMode

Hook for accessing and managing beta mode state.

**Location:** [useBetaMode.ts](../frontend/src/hooks/useBetaMode.ts)

**Purpose:**
- Access beta mode state from context
- Activate/deactivate beta mode via rapid logo clicks
- Enable beta features (e.g., Tool Management page)

**Hook Interface:**
```typescript
export const useBetaMode = () => {
  return useBetaModeContext();
};

export const useBetaModeActivator = (
  isBetaMode: boolean,
  onActivate: () => void,
  onDeactivate: () => void
) => {
  // Tracks rapid clicks (10 clicks within 5 seconds)
  // Returns click handler function
};
```

**Usage:**
```typescript
const { isBetaMode, activateBetaMode, deactivateBetaMode } = useBetaMode();
const handleLogoClick = useBetaModeActivator(isBetaMode, activateBetaMode, deactivateBetaMode);
```

**Beta Mode Activation:**
- Requires 10 rapid clicks on the logo within 5 seconds
- Toggles beta mode on/off
- Enables access to beta routes (e.g., `/tools`)

---

## State Management

### Approach

The application uses a **minimal state management** approach:

1. **WebSocket State** - Managed by `useWebSocket` hook
   - Single source of truth for machine data
   - Shared across Dashboard components via props

2. **Component State** - Local `useState` for UI state
   - Modal visibility
   - Form inputs
   - Loading states
   - Error messages

3. **No Global State Library** - No Redux, MobX, or Zustand usage
   - Simple data flow: WebSocket → Hook → Props → Components
   - Prop drilling is acceptable for this app size

**Why No Redux?**

- **Simple data model** - Only machines and files
- **WebSocket as source of truth** - Backend pushes updates, no complex client-side state
- **Few state interactions** - Components mostly read state, few writes
- **Reduced complexity** - No actions, reducers, selectors to maintain

**Future Considerations:**

If the app grows, consider:
- **Zustand** (already installed) - Lightweight alternative to Redux
- **TanStack Query** (already installed) - Server state caching and synchronization
- **Context API** - For deeply nested components

---

## Styling Architecture

### Terminal Aesthetic

The application follows a strict terminal/command-line aesthetic:

**Design Principles:**
1. **Monospace fonts** - All text in monospace (Courier New, monospace)
2. **ASCII-only** - Box-drawing characters, no modern Unicode emoji
3. **Retro color palette** - Green text, amber warnings, red errors
4. **Text glow effects** - CSS text-shadow for CRT monitor effect
5. **High contrast** - Dark background, bright text

**Color Palette:**

Defined in CSS variables:

```css
:root {
  --color-bg: #0a0a0a;           /* Almost black background */
  --color-text: #00ff00;         /* Bright green text */
  --color-muted: #808080;        /* Gray for secondary text */
  --color-success: #00ff00;      /* Green for success */
  --color-error: #ff0000;        /* Red for errors */
  --color-warning: #ffaa00;      /* Amber for warnings */
  --color-info: #00aaff;         /* Blue for info */
  --color-offline: #505050;      /* Dark gray for offline */
}
```

**Location:** [terminal.css](../frontend/src/styles/terminal.css)

**Typography:**

```css
body {
  font-family: 'Courier New', 'Courier', monospace;
  font-size: 14px;
  line-height: 1.5;
  background-color: var(--color-bg);
  color: var(--color-text);
}

.text-glow {
  text-shadow: 0 0 5px currentColor;
}

.text-glow-strong {
  text-shadow: 0 0 10px currentColor, 0 0 20px currentColor;
}
```

**Box-Drawing Characters:**

Used extensively for borders and dividers:

```
╔═══════════════╗    Top border
║   CONTENT     ║    Side borders
╠═══════════════╣    Middle divider
║   CONTENT     ║
╚═══════════════╝    Bottom border

├───────────────┤    Horizontal divider
```

**CSS Modules:**

The app uses **global CSS** (not CSS Modules):
- Component-specific CSS files (e.g., `MachineCard.css`)
- Global styles in `terminal.css` and `index.css`
- Class naming convention: BEM-like (`machine-card`, `machine-card-header`)

**Responsive Design:**

Currently **desktop-focused**:
- Fixed widths for many components
- Grid layout for machine cards
- Future: Add media queries for tablet/mobile support

---

## API Communication

### API Configuration

**Location:** [api.ts](../frontend/src/config/api.ts)

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_URL = `ws://${new URL(API_BASE_URL).host}/api/ws`;
```

**Environment Variables:**
- `VITE_API_URL` - Override API base URL (default: `http://localhost:8000`)

### API Client Pattern

The app uses **native fetch API** with async/await:

**Example: Fetching Machines**
```typescript
const fetchMachines = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    setMachines(data);
  } catch (error) {
    console.error('Failed to fetch machines:', error);
    setError(error instanceof Error ? error.message : 'Unknown error');
  }
};
```

**Example: Creating a Machine**
```typescript
const createMachine = async (machineData: MachineConfig) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/machines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(machineData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to create machine');
    }

    const newMachine = await response.json();
    addMachine(newMachine);
  } catch (error) {
    setError(error instanceof Error ? error.message : 'Unknown error');
  }
};
```

**Error Handling:**

All API calls follow this pattern:
1. Check `response.ok` (status 200-299)
2. Parse error response JSON if available
3. Catch network errors
4. Display user-friendly error messages

**No API Client Library:**
- No Axios or other HTTP libraries
- Native fetch is sufficient for this app
- Future: Consider TanStack Query for caching and retries

**Related Documentation:**
- See [API_REFERENCE.md](./API_REFERENCE.md) for all API endpoints

---

## Real-Time Updates

### WebSocket Integration

The application uses WebSocket for **real-time machine status updates**.

**Architecture:**

```
Backend (FastAPI)
  └─ WebSocketManager
      └─ broadcasts status_update every 5 seconds
          ↓
Frontend (React)
  └─ useWebSocket hook
      └─ receives messages
          └─ updates machine Map
              └─ Dashboard re-renders with new data
```

**Connection Flow:**

1. **Component Mount** - Dashboard calls `useWebSocket(WS_URL)`
2. **WebSocket Connect** - `new WebSocket(url)` establishes connection
3. **Initial Status** - Backend sends `initial_status` with all machines
4. **Continuous Updates** - Backend sends `status_update` every 5 seconds per machine
5. **Auto-Reconnect** - On disconnect, reconnect after 5 seconds

**Update Frequency:**

- **Poll interval:** 5 seconds (configurable per machine)
- **WebSocket broadcast:** Immediately after poll completes
- **UI update:** Real-time (React re-renders on state change)

**Throttling:**

Currently **no throttling**:
- All status updates immediately re-render components
- Future: Consider debouncing for performance if updates are too frequent

**Connection Status Indicator:**

The Dashboard displays connection status:
```typescript
{isConnected ? (
  <span className="text-success">● WS CONNECTED</span>
) : (
  <span className="text-error blink">○ WS DISCONNECTED</span>
)}
```

**Design Decisions:**

1. **Single WebSocket connection** - Shared across all components
2. **No message queue** - Process messages immediately
3. **Immutable updates** - Always create new Map instance for React change detection
4. **Auto-reconnect** - Resilient to network interruptions

**Related Documentation:**
- See [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) for message format spec
- See [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md) for WebSocketManager implementation

---

## Performance Optimizations

### Current Optimizations

1. **Vite Fast Refresh** - Sub-second HMR during development
2. **Production Build** - Tree shaking, code splitting, minification
3. **WebSocket Connection Reuse** - Single connection for all components
4. **Map-based State** - O(1) machine lookup by ID
5. **Conditional Rendering** - Only render visible components

### Future Optimizations

**React.memo** - Memoize components to prevent unnecessary re-renders:
```typescript
export const MachineCard = React.memo<MachineCardProps>(({ machine, editMode, onDelete }) => {
  // Component implementation
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if machine changed
  return prevProps.machine.poll_timestamp === nextProps.machine.poll_timestamp;
});
```

**useMemo** - Memoize expensive calculations:
```typescript
const onlineCount = useMemo(() =>
  machines.filter(m => m.is_online === true).length,
  [machines]
);
```

**useCallback** - Stabilize callback references:
```typescript
const handleDelete = useCallback((machine: MachineStatus) => {
  removeMachine(machine.machine_id);
}, [removeMachine]);
```

**Code Splitting** - Lazy load routes:
```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'));
const FileBrowser = lazy(() => import('./pages/FileBrowser'));

<Suspense fallback={<AsciiLoadingScreen />}>
  <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/files" element={<FileBrowser />} />
  </Routes>
</Suspense>
```

**Virtual Scrolling** - For large file lists (1000+ files):
```typescript
import { FixedSizeList } from 'react-window';
```

**Debouncing** - Throttle WebSocket updates if too frequent:
```typescript
const debouncedUpdate = useMemo(() =>
  debounce((machine: MachineStatus) => {
    setMachines(prev => {
      const updated = new Map(prev);
      updated.set(machine.machine_id, machine);
      return updated;
    });
  }, 100),
  []
);
```

**Current Performance:**
- **Dashboard initial load:** <500ms
- **WebSocket connect:** <100ms
- **Machine card re-render:** <16ms (60fps)
- **File listing (100 files):** <200ms

**Performance Monitoring:**

Enable React DevTools Profiler:
```bash
npm run dev -- --profile
```

---

## Type Safety

### TypeScript Configuration

**Location:** [tsconfig.json](../frontend/tsconfig.json)

**Key Settings:**
- `"strict": true` - Enable all strict type checking
- `"noUncheckedIndexedAccess": true` - Catch potential undefined access
- `"esModuleInterop": true` - Better CJS/ESM compatibility

### Type Definitions

**Machine Status Interface:**

```typescript
interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  tools?: Tool[];
  current_tool?: number;
  alarms?: Alarm[];
  error?: string;
  poll_timestamp: string;
  ip_address?: string;
  ftp_username?: string;
  ftp_password?: string;
  ftp_port?: number;
  http_port?: number;
  path?: string;
  poll_interval_seconds?: number;
  enabled?: boolean;
}
```

**Tool Interface:**

```typescript
interface Tool {
  tool_number: number;
  tool_name?: string;
  diameter?: number;
  length?: number;
}
```

**Validation Results Interface:**

```typescript
interface ValidationResults {
  valid: boolean;
  tools: { [key: number]: ToolValidation };
  wcs_offset?: WCSValidation;
  warnings: string[];
  errors: string[];
}

interface ToolValidation {
  used_in_program: boolean;
  exists_in_machine: boolean;
  diameter_match?: boolean;
  length_match?: boolean;
  expected_diameter?: number;
  actual_diameter?: number;
  expected_length?: number;
  actual_length?: number;
}

interface WCSValidation {
  wcs_number: number;
  exists: boolean;
  x_match?: boolean;
  y_match?: boolean;
  z_match?: boolean;
  expected_x?: number;
  actual_x?: number;
  expected_y?: number;
  actual_y?: number;
  expected_z?: number;
  actual_z?: number;
}
```

**Type Guards:**

```typescript
function isMachineOnline(machine: MachineStatus): machine is MachineStatus & { is_online: true } {
  return machine.is_online === true;
}

const onlineMachines = machines.filter(isMachineOnline);
// Type: Array<MachineStatus & { is_online: true }>
```

**Generic Components:**

```typescript
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string | number;
}

export const List = <T,>({ items, renderItem, keyExtractor }: ListProps<T>) => {
  return (
    <div>
      {items.map(item => (
        <div key={keyExtractor(item)}>
          {renderItem(item)}
        </div>
      ))}
    </div>
  );
};
```

**Benefits:**
- Catch errors at compile time
- Autocomplete in IDE
- Self-documenting code
- Safer refactoring

---

## Design Patterns

### Component Patterns

**1. Container/Presentational Pattern**

```typescript
// Container component (logic)
const MachineCardContainer = ({ machineId }: { machineId: number }) => {
  const [machine, setMachine] = useState<MachineStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMachine(machineId).then(setMachine).finally(() => setLoading(false));
  }, [machineId]);

  if (loading) return <LoadingSpinner />;
  if (!machine) return <ErrorMessage />;

  return <MachineCardPresentation machine={machine} />;
};

// Presentational component (display only)
const MachineCardPresentation = ({ machine }: { machine: MachineStatus }) => {
  return (
    <div className="machine-card">
      <h2>{machine.machine_name}</h2>
      <p>Status: {machine.status}</p>
    </div>
  );
};
```

**2. Compound Components Pattern**

```typescript
const Modal = ({ isOpen, onClose, children }: ModalProps) => {
  if (!isOpen) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content">{children}</div>
    </div>
  );
};

Modal.Header = ({ children }: { children: React.ReactNode }) => (
  <div className="modal-header">{children}</div>
);

Modal.Body = ({ children }: { children: React.ReactNode }) => (
  <div className="modal-body">{children}</div>
);

Modal.Footer = ({ children }: { children: React.ReactNode }) => (
  <div className="modal-footer">{children}</div>
);

// Usage
<Modal isOpen={true} onClose={handleClose}>
  <Modal.Header>Title</Modal.Header>
  <Modal.Body>Content</Modal.Body>
  <Modal.Footer>Actions</Modal.Footer>
</Modal>
```

**3. Render Props Pattern**

```typescript
const DataFetcher = ({ url, render }: { url: string; render: (data: any) => React.ReactNode }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(url).then(res => res.json()).then(setData).finally(() => setLoading(false));
  }, [url]);

  if (loading) return <LoadingSpinner />;
  return <>{render(data)}</>;
};

// Usage
<DataFetcher url="/api/machines" render={(machines) => (
  <div>
    {machines.map(m => <MachineCard key={m.machine_id} machine={m} />)}
  </div>
)} />
```

**4. Custom Hook Pattern**

```typescript
const useMachines = () => {
  const [machines, setMachines] = useState<MachineStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/machines`)
      .then(res => res.json())
      .then(setMachines)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const addMachine = (machine: MachineStatus) => {
    setMachines(prev => [...prev, machine]);
  };

  const removeMachine = (machineId: number) => {
    setMachines(prev => prev.filter(m => m.machine_id !== machineId));
  };

  return { machines, loading, error, addMachine, removeMachine };
};

// Usage
const Dashboard = () => {
  const { machines, loading, error, addMachine, removeMachine } = useMachines();
  // ...
};
```

### State Management Patterns

**1. Lifting State Up**

```typescript
// Parent component manages state
const Dashboard = () => {
  const [selectedMachine, setSelectedMachine] = useState<number | null>(null);

  return (
    <>
      <MachineList onSelect={setSelectedMachine} />
      <MachineDetails machineId={selectedMachine} />
    </>
  );
};
```

**2. Derived State**

```typescript
const Dashboard = () => {
  const { machines } = useWebSocket(WS_URL);

  // Derive state from props/state instead of storing separately
  const onlineCount = machines.filter(m => m.is_online).length;
  const runningCount = machines.filter(m => m.status?.includes('Running')).length;

  return <FleetOverview online={onlineCount} running={runningCount} />;
};
```

**3. Controlled Components**

```typescript
const AddMachineForm = ({ onSubmit }: { onSubmit: (data: MachineConfig) => void }) => {
  const [name, setName] = useState('');
  const [ipAddress, setIpAddress] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, ip_address: ipAddress });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={e => setName(e.target.value)} />
      <input value={ipAddress} onChange={e => setIpAddress(e.target.value)} />
      <button type="submit">Add Machine</button>
    </form>
  );
};
```

---

## Build and Development

### Development Server

**Start development server:**
```bash
cd frontend
npm run dev
```

**Configuration:** [vite.config.ts](../frontend/vite.config.ts)

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
});
```

**Features:**
- **Hot Module Replacement (HMR)** - Instant updates without full reload
- **Fast Refresh** - Preserves component state during edits
- **TypeScript checking** - Real-time type errors in terminal
- **Source maps** - Debug original TypeScript code in browser

**Environment Variables:**

Create `.env.local`:
```bash
VITE_API_URL=http://localhost:8000
```

**Access in code:**
```typescript
const apiUrl = import.meta.env.VITE_API_URL;
```

### Production Build

**Build for production:**
```bash
cd frontend
npm run build
```

**Output:** `frontend/dist/`

**Build Configuration:**
- **Minification** - Terser for JavaScript, cssnano for CSS
- **Code splitting** - Separate vendor and app bundles
- **Tree shaking** - Remove unused code
- **Source maps** - Optional (disabled by default for security)

**Build artifacts:**
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js       # Main app bundle
│   ├── vendor-[hash].js      # Third-party libraries
│   └── index-[hash].css      # Compiled CSS
```

**Preview production build:**
```bash
npm run preview
```

**Deployment:**
- Serve `dist/` folder with any static file server
- Nginx, Apache, Caddy, or cloud storage (S3, Netlify, Vercel)

**Dockerfile:**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Related Documentation:**
- See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for full deployment guide
- See [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) for local development setup

---

## Summary

The Shatter CNC frontend is a **React 19 + TypeScript single-page application** with a **terminal aesthetic**, designed for **real-time fleet monitoring** of CNC machines.

**Key Architectural Decisions:**

1. **React 19** - Latest features, improved performance
2. **TypeScript** - Type safety, better developer experience
3. **Vite** - Fast development, optimized builds
4. **Minimal state management** - No Redux, simple WebSocket hook
5. **Terminal aesthetic** - Box-drawing characters, monospace fonts, retro colors
6. **Real-time WebSocket** - Live machine status updates
7. **Component composition** - Reusable UI primitives, feature-specific components

**Performance Characteristics:**

- Initial load: <500ms
- WebSocket latency: <100ms
- UI updates: Real-time (60fps)
- Build size: ~200KB gzipped

**Future Enhancements:**

1. Add React.memo/useMemo for performance
2. Implement code splitting for larger app
3. Add TanStack Query for server state caching
4. Add Zustand for complex state management
5. Implement virtual scrolling for large lists
6. Add mobile responsive design

**Related Documentation:**

- [DASHBOARD_WORKFLOWS.md](./DASHBOARD_WORKFLOWS.md) - Dashboard feature workflows
- [FILE_BROWSER_WORKFLOWS.md](./FILE_BROWSER_WORKFLOWS.md) - File browser workflows
- [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) - WebSocket message protocol
- [COMPONENT_LIBRARY.md](./COMPONENT_LIBRARY.md) - Detailed component reference
- [API_REFERENCE.md](./API_REFERENCE.md) - Backend API endpoints
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Development setup
