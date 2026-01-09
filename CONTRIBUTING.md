# Contributing to Shatter CNC Management Platform

Thank you for considering contributing to the Shatter CNC Management Platform! This document provides guidelines and instructions for contributing to this project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Process](#development-process)
4. [Contribution Guidelines](#contribution-guidelines)
5. [Review Process](#review-process)
6. [Areas Needing Contribution](#areas-needing-contribution)
7. [Questions and Help](#questions-and-help)

---

## Code of Conduct

### Our Standards

We are committed to providing a welcoming and inclusive environment for all contributors. We expect all participants to:

- **Be Respectful**: Treat all contributors with respect and consideration
- **Be Inclusive**: Welcome diverse perspectives and experiences
- **Be Professional**: Focus on constructive feedback and technical discussions
- **Be Collaborative**: Work together to improve the project

### Unacceptable Behavior

- Harassment, discrimination, or personal attacks
- Trolling, insulting/derogatory comments
- Publishing private information without permission
- Other conduct that would be inappropriate in a professional setting

### Enforcement

Project maintainers have the right to remove, edit, or reject contributions that do not align with this Code of Conduct. Repeated violations may result in being banned from the project.

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Git** installed and basic familiarity with version control
- **Python 3.11+** for backend development
- **Node.js 18+** for frontend development
- **Docker** and **Docker Compose** for local testing (recommended)
- Read the [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) for setup instructions

### Finding Issues to Work On

1. **Browse Issues**: Check the [GitHub Issues](https://github.com/yourusername/S700_nc/issues) page
2. **Look for Labels**:
   - `good first issue` - Beginner-friendly tasks
   - `help wanted` - Maintainers are seeking contributions
   - `bug` - Bug fixes needed
   - `enhancement` - New features or improvements
   - `documentation` - Documentation improvements
3. **Ask Questions**: If you're unsure about an issue, comment and ask for clarification
4. **Check Roadmap**: Review [FUTURE_DOCUMENTATION.md](docs/roadmap/FUTURE_DOCUMENTATION.md) for planned features

---

## Development Process

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/S700_nc.git
cd S700_nc

# Add upstream remote to sync with main repository
git remote add upstream https://github.com/ORIGINAL_OWNER/S700_nc.git
```

### 2. Create a Feature Branch

```bash
# Sync with upstream main branch
git fetch upstream
git checkout main
git merge upstream/main

# Create a new branch for your feature/fix
git checkout -b feature/your-feature-name
# OR
git checkout -b fix/bug-description
```

**Branch Naming Conventions:**
- `feature/` - New features (e.g., `feature/alarm-notifications`)
- `fix/` - Bug fixes (e.g., `fix/polling-timeout`)
- `docs/` - Documentation changes (e.g., `docs/api-examples`)
- `refactor/` - Code refactoring (e.g., `refactor/polling-service`)
- `test/` - Test additions (e.g., `test/program-validation`)

### 3. Set Up Development Environment

Follow one of the setup options in [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md):

- **Option 1**: Full Docker (recommended for beginners)
- **Option 2**: Hybrid - Local Backend (better for backend debugging)
- **Option 3**: Hybrid - Local Frontend (better for UI work)
- **Option 4**: Fully Local (advanced)

### 4. Make Your Changes

- Write clean, readable code
- Follow the code style guidelines (see below)
- Add tests if applicable (see [Testing Requirements](#testing-requirements))
- Update documentation if needed (see [Documentation Requirements](#documentation-requirements))
- Follow UX design guidelines for UI changes (see [UX Design Requirements](#ux-design-requirements))

### 5. Test Your Changes

**Backend Testing:**
```bash
# Currently manual testing - automated tests planned
# Test API endpoints manually using Swagger UI
open http://localhost:8000/docs

# Or use curl/httpie
curl http://localhost:8000/api/machines
```

**Frontend Testing:**
```bash
# Test in development mode
cd frontend
npm run dev

# Build for production to check for errors
npm run build
```

**Integration Testing:**
```bash
# Test full stack with Docker
docker compose up --build

# Verify all services are healthy
docker compose ps
```

### 6. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "Add feature: alarm notifications with email integration"
```

**Commit Message Guidelines:**
- Use imperative mood: "Add feature" not "Added feature"
- First line: concise summary (50 chars or less)
- Second line: blank
- Third line+: detailed explanation if needed
- Reference issue numbers: "Fixes #123" or "Relates to #456"

**Examples:**
```
Add alarm notification system with email alerts

- Implement AlarmService for monitoring machine alarms
- Add email notification using SMTP
- Create alarm_events table for historical tracking
- Add API endpoints for alarm configuration

Fixes #123
```

```
Fix polling timeout causing machine disconnects

The polling interval was too aggressive for slow networks.
Increased timeout from 5s to 15s and added retry logic.

Fixes #456
```

### 7. Push to Your Fork

```bash
# Push your branch to your fork
git push origin feature/your-feature-name
```

### 8. Create Pull Request

1. **Go to GitHub**: Navigate to your fork on GitHub
2. **Click "Pull Request"**: GitHub will detect your recent push
3. **Select Base Branch**: Usually `main` on the upstream repository
4. **Fill Out PR Template**:
   - **Title**: Clear, concise description
   - **Description**: What changed and why
   - **Related Issues**: Link to issues this PR addresses
   - **Testing**: How you tested the changes
   - **Screenshots**: For UI changes (required)

**PR Template Example:**
```markdown
## Description
Implement alarm notification system with email alerts.

## Related Issues
Fixes #123

## Changes Made
- Added AlarmService for monitoring machine alarms
- Implemented email notifications using SMTP
- Created alarm_events TimescaleDB table
- Added API endpoints: POST /api/alarms/configure, GET /api/alarms/history

## Testing
- Tested alarm detection with simulated alarm conditions
- Verified email delivery using MailHog
- Tested API endpoints with Swagger UI
- Checked alarm_events table population

## Screenshots
(Attach screenshots for UI changes)
```

---

## Contribution Guidelines

### Code Style

#### Backend (Python)

**Follow PEP 8** with these specific guidelines:

- **Line Length**: Max 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Group into standard library, third-party, local imports
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings for public functions

**Example:**
```python
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.machine import Machine

def get_machines_by_status(
    db: Session,
    status: str,
    limit: int = 10
) -> List[Machine]:
    """
    Retrieve machines filtered by status.

    Args:
        db: Database session
        status: Machine status to filter by (online, offline, error)
        limit: Maximum number of results to return

    Returns:
        List of Machine objects matching the status

    Raises:
        ValueError: If status is not valid
    """
    valid_statuses = ["online", "offline", "error"]
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}")

    return db.query(Machine).filter(
        Machine.status == status
    ).limit(limit).all()
```

**Tools:**
- **Formatter**: `black` (planned - not yet enforced)
- **Linter**: `pylint` or `flake8` (planned - not yet enforced)
- **Type Checker**: `mypy` (planned - not yet enforced)

#### Frontend (TypeScript/React)

**Follow Standard TypeScript Guidelines:**

- **Line Length**: Max 100 characters
- **Indentation**: 2 spaces (no tabs)
- **Quotes**: Single quotes for strings, double for JSX attributes
- **Semicolons**: Use semicolons
- **Type Safety**: Avoid `any` types, use proper TypeScript types
- **Component Style**: Functional components with hooks (no class components)

**Example:**
```typescript
import { useState, useEffect } from 'react';

interface MachineCardProps {
  machineId: number;
  name: string;
  status: 'online' | 'offline' | 'error';
  onStatusChange?: (status: string) => void;
}

export const MachineCard: React.FC<MachineCardProps> = ({
  machineId,
  name,
  status,
  onStatusChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (status === 'error' && onStatusChange) {
      onStatusChange(status);
    }
  }, [status, onStatusChange]);

  return (
    <div className="machine-card">
      <h3>{name}</h3>
      <StatusIndicator status={status} />
      <button onClick={() => setIsExpanded(!isExpanded)}>
        {isExpanded ? 'Collapse' : 'Expand'}
      </button>
    </div>
  );
};
```

**Tools:**
- **Formatter**: Prettier (planned - configuration in `.prettierrc`)
- **Linter**: ESLint (planned - configuration in `.eslintrc`)
- **Type Checker**: Built into TypeScript compiler

### Documentation Requirements

**MANDATORY**: All contributions must include appropriate documentation updates.

See [.claude/rules.md](.claude/rules.md) for complete documentation standards.

#### When Documentation is Required

1. **New Features**: Document in:
   - Relevant workflow docs ([DASHBOARD_WORKFLOWS.md](docs/DASHBOARD_WORKFLOWS.md) or [FILE_BROWSER_WORKFLOWS.md](docs/FILE_BROWSER_WORKFLOWS.md))
   - [API_REFERENCE.md](docs/API_REFERENCE.md) for new endpoints
   - [FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) for new components
   - [BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md) for new services

2. **API Changes**: Update [API_REFERENCE.md](docs/API_REFERENCE.md) with:
   - Endpoint path and method
   - Request/response schemas with JSON examples
   - Error responses
   - Code references: `[file.py:123-145](path/to/file.py#L123-L145)`

3. **Database Changes**: Update [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) with:
   - New tables or columns
   - Relationships and foreign keys
   - Indexes
   - Data retention policies

4. **Configuration Changes**: Update [ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md):
   - New environment variables
   - Default values
   - Validation rules
   - Security implications

5. **Deployment Changes**: Update [DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md):
   - New Docker services
   - Volume changes
   - Health check modifications

#### Documentation Standards

From [.claude/rules.md](.claude/rules.md), all documentation must include:

1. **Code References**: Include file paths and line numbers
   - Format: `[file.py:123-145](path/to/file.py#L123-L145)`
   - Example: Implementation in [polling.py:45-78](backend/app/services/polling.py#L45-L78)

2. **API Endpoint Documentation**:
   ```markdown
   ### Get Machine Status
   **Method:** GET
   **Path:** `/api/machines/{id}/status`
   **Description:** Retrieve current status of a specific machine

   **Request Parameters:**
   - `id` (path, integer, required): Machine ID

   **Response (200 OK):**
   ```json
   {
     "machine_id": 1,
     "status": "online",
     "current_program": "O1234.nc",
     "tool_number": 5,
     "spindle_speed": 3000
   }
   ```

   **Error Responses:**
   - 404: Machine not found
   - 500: Connection error

   **Implementation:** [status.py:67-89](backend/app/api/status.py#L67-L89)
   ```

3. **Code Examples**: Show actual usage, not just descriptions
4. **Design Decisions**: Explain why specific approaches were chosen
5. **Error Handling**: Document how errors are caught and displayed
6. **Testing**: How to test the feature/component
7. **Limitations**: Known constraints or edge cases

#### Example: Documenting a New Feature

If you add a new alarm notification feature:

**1. Update [BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md):**
```markdown
### AlarmService

**Purpose:** Monitor machine alarms and send notifications

**Key Methods:**
- `check_alarms(machine_id: int)` - Query machine for active alarms
- `send_notification(alarm: Alarm)` - Send email notification
- `store_alarm_event(alarm: Alarm)` - Save to alarm_events table

**Location:** [alarm_service.py](backend/app/services/alarm_service.py)

**Lifecycle:**
- Started during application startup
- Runs every 10 seconds
- Stopped during graceful shutdown
```

**2. Update [API_REFERENCE.md](docs/API_REFERENCE.md):**
```markdown
## Alarms API

### Configure Alarm Notifications
**Method:** POST
**Path:** `/api/alarms/configure`
...
```

**3. Update [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md):**
```markdown
### alarm_events

TimescaleDB hypertable for storing alarm history.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | BigSerial | No | Primary key |
| machine_id | Integer | No | FK to machines.id |
| alarm_code | String(50) | No | Alarm code (e.g., "E001") |
...
```

### UX Design Requirements

**MANDATORY**: All UI changes must follow the UX design guidelines.

See [docs/UX_DESIGN_GUIDE.md](docs/UX_DESIGN_GUIDE.md) for complete design system.

#### Core UX Principles

1. **Terminal Aesthetic**: Monospace fonts, ASCII box-drawing, retro colors
2. **Minimal Design**: No unnecessary animations or effects
3. **Accessibility**: Keyboard navigation, clear status indicators
4. **Performance**: Fast load times, minimal re-renders

#### Typography

- **Primary Font**: `'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace`
- **Font Sizes**:
  - Body: `0.875rem` (14px)
  - Headings: `1rem` (16px) to `1.25rem` (20px)
  - Small text: `0.75rem` (12px)

#### Color Palette

**Status Colors:**
```css
/* Online/Success */
--status-online: #00ff00;

/* Offline/Inactive */
--status-offline: #888888;

/* Error/Critical */
--status-error: #ff0000;

/* Warning */
--status-warning: #ffaa00;

/* Running/Active */
--status-running: #00aaff;
```

**Background Colors:**
```css
--bg-primary: #0a0a0a;      /* Main background */
--bg-secondary: #1a1a1a;    /* Cards, modals */
--bg-tertiary: #2a2a2a;     /* Hover states */
```

#### Components

**Status Indicators:**
- Use `StatusIndicator` component from [StatusIndicator.tsx](frontend/src/components/ui/StatusIndicator.tsx)
- Icons: `●` (online), `○` (offline), `✕` (error), `▶` (running)
- Example:
  ```tsx
  <StatusIndicator status="online" label="Machine 01" />
  ```

**Modals:**
- Use `Modal` component from [Modal.tsx](frontend/src/components/ui/Modal.tsx)
- Terminal-style borders with box-drawing characters
- Escape key to close
- Click outside to close
- Example:
  ```tsx
  <Modal
    isOpen={isOpen}
    onClose={handleClose}
    title="Alarm History"
    footer={<button onClick={handleClose}>Close</button>}
  >
    {/* Modal content */}
  </Modal>
  ```

**Tables:**
- Use monospace alignment
- Box-drawing characters for borders: `─│┌┐└┘├┤┬┴┼`
- Example:
  ```
  ┌─────────┬──────────┬────────┐
  │ Tool #  │ Diameter │ Length │
  ├─────────┼──────────┼────────┤
  │ 1       │ 0.5000   │ 2.5000 │
  │ 2       │ 0.2500   │ 1.7500 │
  └─────────┴──────────┴────────┘
  ```

#### Prohibited Patterns

- **NO Emoji**: ASCII characters only (exception: nuclear bomb art in delete confirmation)
- **NO Rounded Corners**: Use sharp, terminal-style borders
- **NO Gradients**: Flat colors only
- **NO Custom Fonts**: Stick to monospace system fonts
- **NO Animations**: Except for subtle blink effects on critical statuses

#### UI Change Checklist

Before submitting a PR with UI changes:

- [ ] Follows terminal aesthetic (monospace, ASCII borders)
- [ ] Uses colors from [UX_DESIGN_GUIDE.md](docs/UX_DESIGN_GUIDE.md)
- [ ] Tested keyboard navigation
- [ ] Tested on different screen sizes
- [ ] No emoji used (except approved exceptions)
- [ ] Uses existing UI components where possible
- [ ] Screenshots included in PR
- [ ] Documented in [FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) if new component

### Testing Requirements

**Current Status:** Automated tests not yet implemented (see [FUTURE_DOCUMENTATION.md](docs/roadmap/FUTURE_DOCUMENTATION.md))

#### Manual Testing Checklist

Until automated tests are in place, perform manual testing:

**Backend:**
- [ ] Test API endpoints using Swagger UI (`http://localhost:8000/docs`)
- [ ] Verify database changes using `psql` or database client
- [ ] Check logs for errors: `docker compose logs -f backend`
- [ ] Test error handling with invalid inputs

**Frontend:**
- [ ] Test in development mode: `npm run dev`
- [ ] Test production build: `npm run build && npm run preview`
- [ ] Test in multiple browsers (Chrome, Firefox, Safari)
- [ ] Test responsive design (desktop, tablet, mobile)
- [ ] Test WebSocket reconnection (stop/start backend)
- [ ] Check browser console for errors

**Integration:**
- [ ] Test full stack with Docker: `docker compose up`
- [ ] Verify all services are healthy: `docker compose ps`
- [ ] Test workflows end-to-end (e.g., add machine → poll status → deploy program)

#### Future Testing (Planned)

When TESTING_GUIDE.md is implemented (see [FUTURE_DOCUMENTATION.md](docs/roadmap/FUTURE_DOCUMENTATION.md)):

**Backend:**
- Unit tests with `pytest`
- Integration tests with `pytest-asyncio`
- API endpoint tests with `httpx.AsyncClient`
- Test coverage minimum: 80%

**Frontend:**
- Component tests with Vitest + React Testing Library
- Integration tests with Mock Service Worker (MSW)
- E2E tests with Playwright (planned)

---

## Review Process

### What to Expect

1. **Initial Review**: Within 1-3 days of submitting PR
2. **Feedback**: Maintainers may request changes or ask questions
3. **Discussion**: Be open to feedback and willing to make adjustments
4. **Approval**: Once approved, your PR will be merged
5. **Thank You**: Your contribution will be acknowledged in release notes

### Review Criteria

Reviewers will check:

1. **Functionality**: Does it work as intended?
2. **Code Quality**: Is the code clean, readable, and maintainable?
3. **Documentation**: Are docs updated appropriately? (MANDATORY)
4. **UX Compliance**: Do UI changes follow [UX_DESIGN_GUIDE.md](docs/UX_DESIGN_GUIDE.md)? (MANDATORY)
5. **Testing**: Has it been tested adequately?
6. **No Regressions**: Does it break existing functionality?
7. **Performance**: Are there any performance concerns?

### Addressing Feedback

When reviewers request changes:

1. **Read Carefully**: Understand the feedback before making changes
2. **Ask Questions**: If unclear, ask for clarification
3. **Make Changes**: Update your branch and push
4. **Respond**: Reply to comments explaining your changes
5. **Request Re-Review**: Mark the PR as ready for re-review

**Example Response:**
```markdown
Thanks for the feedback! I've made the following changes:

1. Updated API endpoint to use POST instead of GET (security concern)
2. Added error handling for invalid machine IDs
3. Updated API_REFERENCE.md with new endpoint documentation

Ready for re-review!
```

---

## Areas Needing Contribution

### High Priority

**Testing Infrastructure** (Issue #TODO)
- Set up pytest for backend unit and integration tests
- Set up Vitest + React Testing Library for frontend component tests
- Create TESTING_GUIDE.md documentation
- Write initial test suite for critical paths

**Authentication System** (Issue #TODO)
- Implement user authentication with JWT
- Add role-based access control (RBAC)
- Create user management API endpoints
- Update database schema with users table
- Document in BACKEND_ARCHITECTURE.md and API_REFERENCE.md

**Alarm Notifications** (Issue #TODO)
- Monitor machine alarms in real-time
- Email notifications for critical alarms
- Alarm history tracking with TimescaleDB
- Alarm configuration per machine
- Document in BACKEND_ARCHITECTURE.md and DASHBOARD_WORKFLOWS.md

### Medium Priority

**Program Version Control** (Issue #TODO)
- Track program versions over time
- Compare program versions (diff view)
- Rollback to previous versions
- Document in FILE_BROWSER_WORKFLOWS.md

**Advanced Reporting** (Issue #TODO)
- Machine utilization reports
- Production run analytics
- Alarm frequency analysis
- Export reports to PDF/CSV
- Document in DASHBOARD_WORKFLOWS.md

**Multi-Machine Deployment** (Issue #TODO)
- Deploy program to multiple machines simultaneously
- Progress tracking for batch deployments
- Rollback failed deployments
- Document in FILE_BROWSER_WORKFLOWS.md

### Low Priority

**Search and Filtering** (Issue #TODO)
- Search machines by name, status, IP
- Filter programs by filename, machine, date
- Advanced filtering with multiple criteria

**Dark Mode Toggle** (Issue #TODO)
- User preference for dark/light terminal themes
- Persistent theme storage in localStorage

**Keyboard Shortcuts** (Issue #TODO)
- Global shortcuts for common actions (e.g., `/` to search)
- Modal shortcuts (Escape to close - already implemented)
- Document in UX_DESIGN_GUIDE.md

### Documentation Contributions

See [FUTURE_DOCUMENTATION.md](docs/roadmap/FUTURE_DOCUMENTATION.md) for planned documentation:

- **WEBSOCKET_PROTOCOL.md**: WebSocket message protocol specification
- **TESTING_GUIDE.md**: Comprehensive testing strategy (HIGH PRIORITY)
- **COMPONENT_LIBRARY.md**: Complete UI component reference
- **PARSERS.md**: G-code and POSNI parser details

---

## Questions and Help

### Getting Help

If you need help with contribution:

1. **Check Existing Docs**:
   - [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) - Setup and development
   - [BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md) - Backend architecture
   - [FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) - Frontend architecture
   - [API_REFERENCE.md](docs/API_REFERENCE.md) - API endpoints
   - [UX_DESIGN_GUIDE.md](docs/UX_DESIGN_GUIDE.md) - UI/UX guidelines

2. **Search Existing Issues**: Check if your question has been asked before

3. **Open a Discussion**: Use GitHub Discussions for general questions

4. **Ask in PR Comments**: If your question is specific to a PR, ask there

5. **Contact Maintainers**: Reach out directly for urgent or private matters

### Common Questions

**Q: I'm new to the project. Where should I start?**
A: Look for issues labeled `good first issue`. These are beginner-friendly tasks. Start with documentation contributions to familiarize yourself with the codebase.

**Q: How do I set up my development environment?**
A: See [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) for detailed setup instructions. We recommend Option 1 (Full Docker) for beginners.

**Q: Do I need to write tests for my contribution?**
A: Automated tests are not yet implemented. Perform thorough manual testing and document your test process in the PR description.

**Q: My PR hasn't been reviewed yet. What should I do?**
A: Reviews typically happen within 1-3 days. If it's been longer, add a polite comment asking for status update.

**Q: Can I work on a feature that's not in the issues list?**
A: Yes! Open an issue first to discuss your idea with maintainers before starting work. This ensures your contribution aligns with project goals.

**Q: I made a mistake in my commit. How do I fix it?**
A: You can amend your last commit with `git commit --amend`, or create a new commit with the fix. For more complex changes, ask for help in your PR.

**Q: How do I keep my fork up to date?**
A: Regularly sync with upstream:
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

---

## Thank You!

Thank you for contributing to the Shatter CNC Management Platform! Your contributions help make this project better for everyone.

**Remember:**
- Follow the [Code of Conduct](#code-of-conduct)
- Read and follow [rules.md](rules.md) for documentation standards
- Follow [UX_DESIGN_GUIDE.md](docs/UX_DESIGN_GUIDE.md) for UI changes
- Test thoroughly before submitting
- Be patient and respectful during the review process

We appreciate your time and effort! 🛠️

---

*Last Updated: 2025-01-15*
