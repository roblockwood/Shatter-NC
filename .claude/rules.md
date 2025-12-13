# Shatter - Development Rules

This document defines the mandatory development practices and requirements for the Shatter project.

## 0. Project Context Check (AUTOMATIC)

**When the project is first loaded into context:**

1. **Run the project status skill** - Execute the `check-project-status` skill to understand the current development environment
2. **Report findings concisely** - Provide a brief status report to help orient the session
3. **Reference documentation** - Use @docs/DEVELOPMENT_GUIDE.md to understand the 4 deployment options

**The skill will check:**
- Docker status and running services
- Active deployment configuration (Full Docker, Hybrid, or Fully Local)
- Service health (frontend, backend, database, Redis)
- Which docker-compose file is being used
- Port accessibility

**Purpose:** This ensures Claude understands the current development environment before making suggestions or modifications.

**Note:** This check is automatic and doesn't require user confirmation. Keep the report concise (3-5 lines) unless issues are detected.

## 1. UX Design Review (MANDATORY)

**Before implementing ANY new UI components:**

1. **Review the UX Design Guide** - Read [docs/UX_DESIGN_GUIDE.md](docs/UX_DESIGN_GUIDE.md) completely
2. **Check design compliance** - Verify the new UI element matches the terminal aesthetic:
   - Uses box-drawing characters (┌ ┐ └ ┘ ─ │)
   - Uses monospace fonts (IBM Plex Mono, JetBrains Mono, etc.)
   - Follows color palette (green phosphor #00ff00 on black #0a0a0a)
   - Uses ASCII characters only - **NO EMOJI** (use /, -, |, *, etc.)
   - Maintains terminal/retro aesthetic
3. **Prompt user if unclear** - If the design guide doesn't specify how to handle a new UI element, ask the user:
   > "The UX Design Guide doesn't specify styling for [component type]. Should this follow [suggested pattern] or would you prefer a different approach?"

### Examples of UI Elements Requiring Review:
- New buttons, forms, or input fields
- Modal dialogs or popups
- Tables, charts, or data visualizations
- Progress indicators or loading states
- Status badges or indicators
- Navigation elements
- Error/success messages

### Design Guide Quick Reference:
```
Color Palette:
  Background:     #0a0a0a
  Primary Text:   #00ff00 (green phosphor)
  Error:          #ff0000
  Success:        #00ff00
  Warning:        #ffaa00

Typography:
  Font: IBM Plex Mono, JetBrains Mono, Fira Code
  Sizes: 10px (metadata), 12px (labels), 14px (body), 16px (headings)

Components:
  Buttons:     [ BUTTON TEXT ]
  Progress:    ████████░░ 80%
  Status:      ● ONLINE  /  ○ OFFLINE
  Borders:     ┌─────┐
               │     │
               └─────┘
```

## 2. Feature Documentation (MANDATORY)

**When implementing a new feature or significant change:**

### Create Feature Documentation

1. **Location**: Add documentation to `docs/[FEATURE_NAME].md`
2. **Follow existing patterns**: Use [docs/CNC_CLIENTS.md](docs/CNC_CLIENTS.md) or [docs/PROGRAM_VALIDATION.md](docs/PROGRAM_VALIDATION.md) as templates
3. **Required sections**:
   - **Overview** - What the feature does and why it exists
   - **How It Works** - Step-by-step flow with code references
   - **API Endpoints** (if applicable) - Request/response examples
   - **Frontend/Backend Details** - Key implementation details with file paths and line numbers
   - **Design Decisions** - Why specific approaches were chosen
   - **Error Handling** - How errors are caught and displayed
   - **Testing** - How to test the feature
   - **Limitations** - Known constraints or edge cases

### Documentation Quality Standards

- **Include code examples** - Show actual usage, not just descriptions
- **Reference file paths** - Use format: `backend/app/api/programs.py:123-145`
- **Show API payloads** - Include JSON request/response examples
- **Explain trade-offs** - Document why specific design decisions were made
- **Keep it current** - Update documentation when code changes

### Examples of Features Requiring Documentation:
- New API endpoints
- Database schema changes
- New UI workflows or pages
- Authentication/authorization changes
- Background jobs or polling services
- Validation logic
- File upload/download mechanisms
- WebSocket or real-time features

## 3. README.md Updates (MANDATORY)

**After completing a feature or significant milestone:**

### Update the Features Section

Add or update feature bullets in the "Features" section of [README.md](README.md):

```markdown
## Features

- 🔴 **Real-time Monitoring** - Live status, cycle times, alarms, and counters for all machines
- 📁 **Smart File Transfer** - G-code validation, tool verification, and multi-machine deployment
- ✅ **Program Validation** - Re-validate deployed files against current machine state
  ↑ Add new features here
```

### Update the Documentation Section

Add links to new documentation:

```markdown
## Documentation

- [Project Plan](STATUS.md) - Comprehensive development roadmap
- [API Endpoints](API_QUICK_REFERENCE.md) - REST API documentation
- [CNC Communication](webserver_endpoints.md) - Brother CNC protocol details
- [CNC Clients](docs/CNC_CLIENTS.md) - HTTP and FTP client libraries
- [Program Validation](docs/PROGRAM_VALIDATION.md) - File validation workflow
  ↑ Add new docs here
```

### Update Development Status (if applicable)

If completing a major phase or milestone:

```markdown
## Development Status

🚧 **In Active Development** - Phase 2: Production Monitoring

Recent additions:
- Program validation and re-validation (Dec 2024)
- Live polling graph visualization (Dec 2024)

See [STATUS.md](STATUS.md) for detailed development phases and progress.
```

### When to Update README:
- ✅ After implementing a complete feature (not individual commits)
- ✅ After creating new documentation
- ✅ After completing a development phase
- ✅ When adding new API endpoints that users need to know about
- ❌ Not for bug fixes or minor tweaks (unless they fix a documented limitation)
- ❌ Not for internal refactoring (unless it changes user-facing behavior)

## 4. Code References in Documentation

**When documenting code, always include file references:**

### Correct Format:
```markdown
The validation handler is defined in [FileBrowser.tsx:590-657](frontend/src/pages/FileBrowser.tsx#L590-L657).

The FTP client downloads files in [ftp_client.py:225](backend/app/clients/ftp_client.py#L225).
```

### Markdown Link Syntax:
- Single line: `[filename.py:42](path/to/filename.py#L42)`
- Line range: `[filename.py:42-51](path/to/filename.py#L42-L51)`
- Folder: `[src/utils/](src/utils/)`

This makes documentation clickable in GitHub and VS Code.

## 5. Testing Before Documentation

**Before documenting a feature as "complete":**

1. **Test the happy path** - Verify the feature works as intended
2. **Test error cases** - Verify error handling displays correctly
3. **Test edge cases** - Check boundaries, empty states, etc.
4. **Verify UI matches design guide** - Check colors, fonts, ASCII characters
5. **Check mobile/responsive** (if applicable) - Terminal UI should adapt

## 6. Git Commit Messages

**Follow conventional commit format:**

```
feat: add program validation for deployed files
^--^  ^----------------------------------^
│     │
│     └─> Summary in present tense
│
└──────> Type: feat, fix, docs, style, refactor, test, chore
```

### Commit Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Formatting, missing semicolons, etc.
- `refactor:` - Code change that neither fixes a bug nor adds a feature
- `test:` - Adding tests
- `chore:` - Updating build tasks, package manager configs, etc.

### Commit Body (optional but recommended for features):
```
feat: add program validation for deployed files

- Created validate-file endpoint to download and validate files via FTP
- Added deploy-validated endpoint to save validation results
- Implemented auto-save behavior and scroll-to-results UX
- Added comprehensive documentation in docs/PROGRAM_VALIDATION.md

Closes #42
```

## 7. File Organization

### Backend Structure:
```
backend/
├── app/
│   ├── api/          # API route handlers
│   ├── clients/      # External service clients (FTP, HTTP)
│   ├── models/       # Database models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── utils/        # Helper functions
```

### Frontend Structure:
```
frontend/
├── src/
│   ├── pages/        # Page components
│   ├── components/   # Reusable UI components
│   ├── hooks/        # Custom React hooks
│   ├── utils/        # Helper functions
│   └── types/        # TypeScript type definitions
```

### Documentation Structure:
```
docs/
├── CNC_CLIENTS.md           # Client library docs
├── PROGRAM_VALIDATION.md    # Feature-specific docs
├── UX_DESIGN_GUIDE.md       # UI/UX standards
├── BRANDING.md              # Brand guidelines
└── [FEATURE_NAME].md        # New feature docs
```

## 8. When to Ask vs. When to Proceed

### Ask the User When:
- ✅ New UI element not covered in UX_DESIGN_GUIDE.md
- ✅ Multiple valid implementation approaches exist
- ✅ Significant architectural decision needed
- ✅ Breaking change to existing functionality
- ✅ Unclear requirements or specifications
- ✅ Design pattern doesn't match existing code

### Proceed Without Asking When:
- ✅ Following established patterns from existing code
- ✅ Fixing obvious bugs or errors
- ✅ Implementing clearly specified requirements
- ✅ Refactoring that doesn't change behavior
- ✅ Adding tests or documentation
- ✅ Following UX_DESIGN_GUIDE.md exactly

## 9. Quality Checklist

Before marking a task as complete:

- [ ] Code follows UX_DESIGN_GUIDE.md (if UI changes)
- [ ] Feature documentation created in `docs/`
- [ ] README.md updated with new feature and docs link
- [ ] Code tested (happy path + error cases)
- [ ] File paths and line numbers referenced in docs
- [ ] API endpoints documented with request/response examples
- [ ] Error handling implemented and documented
- [ ] No emoji in UI - ASCII characters only
- [ ] Commit message follows conventional format
- [ ] Related issues referenced/closed in commit

## 10. Documentation Examples

### Good Documentation:
```markdown
# Program Validation

## How It Works

When you click **VALIDATE** on an O-number file:

1. **Frontend initiates** - handleValidate() called in [FileBrowser.tsx:590-657](frontend/src/pages/FileBrowser.tsx#L590-L657)

2. **Backend downloads file** - validate-file endpoint in [programs.py:123](backend/app/api/programs.py#L123) uses FTP client

3. **Backend validates** - Calls validate_program() to check tools and WCS offsets

### API Endpoints

#### Validate File on Machine

```http
POST /api/programs/machines/{machine_id}/programs/validate-file?file_path=/O2000.NC
```

**Response:**
```json
{
  "validation": {
    "valid": true,
    "errors": [],
    "tools": {...}
  },
  "gcode_content": "G0 X0 Y0\n..."
}
```
```

### Bad Documentation:
```markdown
# Validation

The validation feature validates files.

It uses the backend API to validate.

The frontend shows the results.
```

## Summary

1. **UX First** - Always review UX_DESIGN_GUIDE.md before creating UI
2. **Document Everything** - Create feature docs in `docs/` following existing patterns
3. **Update README** - Add features and doc links to README.md
4. **Test Thoroughly** - Verify functionality before documenting
5. **Reference Code** - Include file paths and line numbers
6. **ASCII Only** - No emoji in UI (terminal aesthetic)
7. **Ask When Unclear** - Prompt user for design decisions
8. **Commit Properly** - Use conventional commit format

These rules ensure consistency, maintainability, and quality across the Shatter project.
