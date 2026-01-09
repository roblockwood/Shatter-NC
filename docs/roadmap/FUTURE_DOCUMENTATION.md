# Future Documentation Plan

This document outlines planned documentation that will be created as the project matures.

---

## Phase 4 - Advanced Topics (Future)

These documents cover specialized subsystems and advanced features. They are lower priority because the core concepts are already covered in existing documentation.

### 1. WEBSOCKET_PROTOCOL.md (~450 lines)

**Status:** Planned

**Purpose:** Detailed WebSocket communication protocol specification

**Sections:**
- Connection lifecycle (connect, authenticate, disconnect)
- Message format specification
  - `initial_status` - Bulk machine data on connect
  - `status_update` - Real-time machine updates
  - Future: `alarm_update`, `tool_change`, `program_start`
- Client implementation examples
- Server implementation (WebSocketManager)
- Broadcasting flow diagrams
- Performance considerations (throttling, compression)
- Error handling and auto-reconnect logic

**Why Future:**
- WebSocket basics already covered in [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) and [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md)
- Protocol is simple with only 2 message types currently
- Will expand when additional message types are added

**Related Files:**
- [backend/app/services/websocket.py](../backend/app/services/websocket.py)
- [frontend/src/hooks/useWebSocket.ts](../frontend/src/hooks/useWebSocket.ts)

---

### 2. TESTING_GUIDE.md (~600 lines)

**Status:** Planned (tests not yet implemented)

**Purpose:** Comprehensive testing strategy and guidelines

**Sections:**

**Backend Testing:**
- Unit tests with pytest
  - Testing services (PollingService, ProgramService)
  - Testing parsers (G-code, POSNI)
  - Testing validators
- Integration tests with pytest-asyncio
  - API endpoint testing
  - Database integration
  - FTP client mocking
- Fixtures and test data
- Coverage requirements

**Frontend Testing:**
- Component tests with Vitest + React Testing Library
  - UI component tests (Modal, StatusIndicator)
  - Feature component tests (MachineCard, ValidationResultModal)
- Integration tests
  - Mock Service Worker (MSW) for API mocking
  - WebSocket mocking
- E2E tests (future: Playwright or Cypress)
  - Critical user flows
  - Dashboard workflows
  - File browser workflows

**Manual Testing Checklists:**
- Dashboard features
- File browser features
- Validation workflows
- Deployment workflows

**CI/CD Integration:**
- GitHub Actions workflow
- Pre-commit hooks
- Coverage reporting

**Contributing Tests:**
- Writing good tests
- Test naming conventions
- When to write unit vs integration tests

**Why Future:**
- No tests currently implemented
- Testing infrastructure needs to be set up first
- Will be created alongside test implementation

**Priority:** HIGH (should be implemented soon)

---

### 3. COMPONENT_LIBRARY.md (~700 lines)

**Status:** Planned

**Purpose:** Complete UI component reference with usage examples

**Sections:**

**UI Components (Reusable Primitives):**

**Modal**
- Props: `isOpen`, `onClose`, `title`, `children`, `footer`
- Features: Escape key handling, click-outside-to-close, terminal borders
- Usage examples with code
- Styling customization
- Location: [Modal.tsx](../frontend/src/components/ui/Modal.tsx)

**StatusIndicator**
- Props: `status`, `label`, `blink`, `className`
- Status types: `online`, `offline`, `warning`, `error`, `idle`, `running`
- Icon mappings: `●` (online), `○` (offline), `✕` (error), etc.
- Usage examples
- Location: [StatusIndicator.tsx](../frontend/src/components/ui/StatusIndicator.tsx)

**ProgressBar**
- Props: `percent`, `label`
- Terminal-style ASCII progress bar
- Usage examples
- Location: [ProgressBar.tsx](../frontend/src/components/ui/ProgressBar.tsx)

**TerminalBox**
- Props: `content`, `title`, `maxHeight`
- Scrollable code/text display
- Line numbers
- Location: [TerminalBox.tsx](../frontend/src/components/ui/TerminalBox.tsx)

**Feature Components (Domain-Specific):**

**MachineCard**
- Complex component with multiple modes
- Props: `machine`, `editMode`, `onDelete`
- Features:
  - Status display with color coding
  - Edit mode with inline form
  - Tool modal integration
  - Validation integration
  - Polling graph
- State management breakdown
- Location: [MachineCard.tsx](../frontend/src/components/MachineCard.tsx)

**ValidationResultModal**
- Props: `isOpen`, `onClose`, `result`, `filename`, `machineId`, etc.
- Complex upload workflow
- Validation result display
- O-number assignment
- Auto-close behavior
- Location: [ValidationResultModal.tsx](../frontend/src/components/ValidationResultModal.tsx)

**AddMachineCard**
- Props: `onAdd`, `onCancel`, `fullWidth`
- Two states: collapsed (+) and expanded (form)
- Form validation
- Location: [AddMachineCard.tsx](../frontend/src/components/AddMachineCard.tsx)

**ToolListModal**
- Displays machine ATC tools
- Current tool highlighting
- Terminal table layout

**SummaryModal & SummaryPopup**
- Three summary types: running, online, offline
- Time range selector
- Auto-refresh every 2 seconds
- Modal vs popup variants

**DeleteConfirmModal**
- Dramatic nuclear bomb ASCII art (5 variants)
- Random art selection
- Escape key handling

**Component Guidelines:**
- When to create new components
- Component composition patterns
- Prop naming conventions
- TypeScript interface patterns
- Styling with terminal aesthetic

**Why Future:**
- Components are already documented in [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md)
- Detailed reference needed when component library grows larger
- Will be valuable when creating design system documentation

---

### 4. PARSERS.md (~500 lines)

**Status:** Planned

**Purpose:** G-code and POSNI parser implementation details

**Sections:**

**G-code Parser:**

**Tool Extraction:**
- Parsing `T##` commands for tool numbers
- Extracting diameter from `D##` offsets
- Extracting length from `H##` offsets
- Handling tool changes (M06)
- Example G-code snippets

**WCS Detection:**
- Identifying WCS offset number (G54-G59)
- Extracting expected coordinates from:
  - G-code comments: `(WCS G54: X10.0000 Y-5.0000 Z2.0000)`
  - Parameter lines: `#5221=10.0000 (G54 X)`
- Parsing multiple WCS references

**Runtime Estimation:**
- Feed rate calculations
- Rapid move time estimation
- Spindle operations
- Dwell time (G04)
- Accuracy limitations

**Implementation:**
- Line-by-line parsing
- State machine for modal commands
- Regular expressions vs custom parser
- Performance considerations
- Location: [gcode_parser.py](../backend/app/parsers/gcode_parser.py)

**POSNI Parser:**

**Position Data Extraction:**
- Parsing machine position files (POSNI format)
- Extracting X, Y, Z coordinates
- Work coordinate offsets
- Machine coordinate systems
- Tool offsets

**Coordinate Parsing:**
- Decimal format handling
- Unit conversion (inches/mm)
- Coordinate system transformations

**Usage Examples:**
```python
from app.parsers.posni_parser import parse_posni

position_data = parse_posni(content)
# Returns: { 'x': 10.0000, 'y': -5.0000, 'z': 2.0000, ... }
```

**Implementation:**
- Location: [posni_parser.py](../backend/app/parsers/posni_parser.py)

**Adding New Parsers:**

**When to Add a Parser:**
- New file format support (e.g., Mazak, Okuma formats)
- Additional data extraction needs
- Different G-code dialects

**Parser Architecture:**
- Interface/protocol definition
- Error handling patterns
- Testing strategies
- Registration system

**Example: Adding a Mazak Parser:**
```python
class MazakParser(BaseParser):
    def parse_program(self, content: str) -> ProgramMetadata:
        # Implementation
        pass
```

**Why Future:**
- Parsers are working and stable
- Detailed documentation needed when:
  - Adding support for new machine types
  - Extending parser capabilities
  - Debugging complex parsing issues
- Currently covered at high level in [PROGRAM_VALIDATION.md](./PROGRAM_VALIDATION.md)

---

## Implementation Timeline

**Phase 4 documentation will be created based on:**

1. **User demand** - If users request specific advanced topics
2. **Feature expansion** - When new message types, parsers, or components are added
3. **Testing implementation** - TESTING_GUIDE.md should be created when tests are written
4. **Contributor onboarding** - When external contributors need detailed component/parser docs

**Estimated Timeline:**
- **Q2 2025**: TESTING_GUIDE.md (alongside test implementation)
- **Q3 2025**: COMPONENT_LIBRARY.md (if component library expands significantly)
- **Q4 2025**: WEBSOCKET_PROTOCOL.md (if additional message types added)
- **2026**: PARSERS.md (if additional parser formats needed)

---

## Contributing to Phase 4 Documentation

If you'd like to contribute any of these documents:

1. Check if the topic is still relevant (code may have changed)
2. Follow the documentation standards in [CONTRIBUTING.md](../CONTRIBUTING.md)
3. Reference existing architecture docs to avoid duplication
4. Include code examples with file references: `[file.py:123-145](path/to/file.py#L123-L145)`
5. Submit PR with the new documentation

---

## Current Documentation Status

**Completed (Phase 1-3):**
- ✅ BACKEND_ARCHITECTURE.md - Backend services and architecture
- ✅ API_REFERENCE.md - Complete API endpoint reference
- ✅ DATABASE_SCHEMA.md - PostgreSQL + TimescaleDB schema
- ✅ FRONTEND_ARCHITECTURE.md - React components and architecture
- ✅ DASHBOARD_WORKFLOWS.md - Dashboard user workflows
- ✅ FILE_BROWSER_WORKFLOWS.md - File browser workflows
- ✅ ENVIRONMENT_VARIABLES.md - Configuration reference
- ✅ DOCKER_DEPLOYMENT.md - Deployment guide
- ✅ DEVELOPMENT_GUIDE.md - Development setup
- ✅ CONTRIBUTING.md - Contribution guidelines

**Existing Specialized Docs:**
- ✅ CNC_CLIENTS.md - HTTP/FTP client libraries
- ✅ PROGRAM_VALIDATION.md - Validation algorithm
- ✅ UX_DESIGN_GUIDE.md - UI/UX design system
- ✅ BRANDING.md - Brand identity
- ✅ DASHBOARD_SUMMARIES.md - Summary feature guide

**Future (Phase 4):**
- 📋 WEBSOCKET_PROTOCOL.md - Planned
- 📋 TESTING_GUIDE.md - Planned (high priority)
- 📋 COMPONENT_LIBRARY.md - Planned
- 📋 PARSERS.md - Planned

---

## Questions or Suggestions?

If you have suggestions for additional documentation topics or think any Phase 4 document should be prioritized, please:
- Open an issue: https://github.com/anthropics/claude-code/issues
- Discuss in pull requests
- Contact the maintainers

---

*Last Updated: 2025-01-15*
