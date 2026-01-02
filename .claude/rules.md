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

---

## 11. Phase 4: Schema Definition Workflow (MANDATORY)

**When defining a new CNC data file schema (TOLNn, POSNn, MEM, ATCTL, etc.):**

### Schema Input Requirements

**The user MUST provide schema specification. DO NOT proceed without complete schema information.**

#### Acceptable Schema Input Formats

The user can provide schema specification in one of these formats:

1. **Documentation References** (Preferred): Reference to documentation files containing schema information
   - Format: `@docs/path/to/doc.json:line-range` or `@docs/path/to/doc.json:line-range`
   - Example: `for c00 @docs/scrape/section_5_6_4_c00.json:4211-4215`
   - The assistant should extract schema information from the referenced documentation

2. **Structured Markdown** (Alternative): Complete schema specification in markdown format (see template below)

#### Documentation Reference Format

When user provides documentation references:
- Extract field definitions from the documentation
- Identify control version differences (C00 vs D00)
- Parse field positions, data types, and validation rules
- Create schema definition file based on extracted information
- If documentation is incomplete, ask for clarification on missing fields

#### Structured Markdown Format (Alternative)

If user provides markdown format, use this structure:

```markdown
## Schema Specification: [DATA_TYPE]

### Basic Information
- **Data Type**: [TOLNn, POSNn, MEM, ATCTL, etc.]
- **File Pattern**: [Filename pattern, e.g., "TOLNI1.NC", "TOLNM1.NC"]
- **Description**: [Brief description of what this data represents]

### Control Version Variants
- **C00 Control**: [Description of C00 format]
- **D00 Control**: [Description of D00 format]
- **Other Variants**: [List any other control versions with format differences]

### Unit Handling
- **Unit Detection Method**: [filename_based | embedded_in_file | machine_config]
  - If `filename_based`: Specify filename patterns (e.g., TOLNI1 = inches, TOLNM1 = mm)
  - If `embedded_in_file`: Describe how units are indicated in file content
  - If `machine_config`: Use machine.units from database
- **Unit Conversion**: [yes | no] - Whether values need conversion based on units

### Field Definitions

For each field, provide:

```yaml
field_name:
  position: [line_number, column_start, column_end] OR [regex_pattern]
  data_type: [int | float | string | enum]
  required: [true | false]
  description: [What this field represents]
  validation: [optional validation rules]
  example: [example value]
```

### Line Format Specification

- **Line Structure**: [fixed_width | delimited | regex]
- **Delimiter**: [if delimited, specify delimiter character(s)]
- **Line Length**: [if fixed_width, specify character count]
- **Header Lines**: [number of header lines to skip, if any]
- **Footer Lines**: [number of footer lines to skip, if any]
- **Sample Lines**: [Provide 3-5 sample lines from actual file]

### Example Schema Specification

```markdown
## Schema Specification: TOLNn (Tool Table)

### Basic Information
- **Data Type**: TOLNn (Tool Offset Table)
- **File Pattern**: TOLNI1.NC (inches), TOLNM1.NC (millimeters)
- **Description**: Tool table containing tool number, diameter, length, and offset data

### Control Version Variants
- **C00 Control**: Fixed-width format, 80 characters per line
- **D00 Control**: Same format as C00 (no variation)

### Unit Handling
- **Unit Detection Method**: filename_based
  - TOLNI1.NC = inches
  - TOLNM1.NC = millimeters
- **Unit Conversion**: no (values stored in native units)

### Field Definitions

```yaml
tool_number:
  position: [line_number, 0, 3]
  data_type: int
  required: true
  description: Tool number (1-999)
  validation: range(1, 1000)
  example: 1

diameter:
  position: [line_number, 10, 20]
  data_type: float
  required: true
  description: Tool diameter
  validation: positive
  example: 0.25

length:
  position: [line_number, 25, 35]
  data_type: float
  required: true
  description: Tool length offset
  validation: any
  example: 3.4494
```

### Line Format Specification

- **Line Structure**: fixed_width
- **Line Length**: 80 characters
- **Header Lines**: 0
- **Footer Lines**: 0
- **Sample Lines**:
  ```
  0001    0.2500    3.4494    0.0000
  0002    0.5000    4.0000    0.0000
  0003    0.1250    2.5000    0.0000
  ```
```

### Schema Extraction Process

**When user provides documentation references:**

1. **Read the referenced documentation files**
   - Extract field definitions from tables or notes
   - Identify control version (C00, D00, etc.)
   - Parse field names, positions, data types, and validation rules

2. **Map fields to CSV indices or positions**
   - For CSV/delimited formats: Map to field index (0-based)
   - For fixed-width formats: Map to column positions
   - Extract tool number from line prefix (e.g., T01 → tool_number=1)

3. **Identify control version differences**
   - Compare C00 and D00 field definitions
   - Note any field additions, removals, or changes
   - Document field index shifts if present

4. **Create schema definition file**
   - Location: `backend/app/schemas/cnc_data/[data_type]_schema.py`
   - Use `FieldDefinition` and `SchemaDefinition` dataclasses
   - Include both control versions in schema registry

5. **Verify against sample data**
   - Test field extraction with actual sample files
   - Confirm field positions match documentation
   - Adjust if discrepancies found

### Schema Validation Checklist

**Before proceeding with parser implementation, verify:**

- [ ] Data type and file pattern identified
- [ ] Control version variants extracted (at least C00 and D00)
- [ ] Unit handling method determined (usually filename_based for TOLNn)
- [ ] All key fields mapped (tool_number, diameter, length, etc.)
- [ ] Line format structure identified (fixed_width/delimited/regex)
- [ ] Field positions verified against sample data
- [ ] Control version differences documented

### If Schema Information is Incomplete

**If documentation is missing key information:**

1. **Ask for clarification** on missing fields:
   > "The documentation doesn't specify [missing field]. Can you clarify:
   > - [Specific question about the field]"

2. **Use sample data to infer** when safe:
   - Compare sample lines to documentation
   - Infer field positions from data patterns
   - Document assumptions made

3. **Do NOT make assumptions** about:
   - Critical field positions without verification
   - Control version differences without documentation
   - Unit handling without clear indication

### Schema Registry Structure

Once schema is validated, create schema definition file:

**Location**: `backend/app/schemas/cnc_data/[data_type]_schema.py`

**Structure**:
```python
"""
Schema definition for [DATA_TYPE] data files.

Control Versions:
- C00: [description]
- D00: [description]

Unit Handling:
- Method: [filename_based | embedded | machine_config]
- Conversion: [yes | no]
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class FieldDefinition:
    """Definition for a single field in the schema."""
    name: str
    position: tuple  # (line_offset, col_start, col_end) or regex pattern
    data_type: type  # int, float, str
    required: bool
    description: str
    validation: Optional[callable] = None

@dataclass
class SchemaDefinition:
    """Complete schema definition for a data type."""
    data_type: str
    file_pattern: str
    control_versions: Dict[str, Dict[str, Any]]  # {version: {field_defs}}
    unit_handling: Dict[str, Any]
    line_format: Dict[str, Any]
    sample_lines: List[str]

# Schema definitions per control version
C00_SCHEMA = SchemaDefinition(...)
D00_SCHEMA = SchemaDefinition(...)
```

### Parser Generation Workflow

1. **Validate Schema** - Ensure all required information provided
2. **Create Schema Definition** - Generate `[data_type]_schema.py` file
3. **Generate Parser** - Create parser class using schema
4. **Create Tests** - Generate test file with sample data
5. **Update Endpoints** - Integrate parser into API endpoints
6. **Document** - Update API documentation

### Error Handling

If schema doesn't match actual data:

- **Log warning** with schema mismatch details
- **Attempt fallback** to old parser (if exists)
- **Raise exception** if critical field missing
- **Document mismatch** for schema update

### Success Criteria

Schema definition is complete when:

- ✅ All fields defined with positions and types
- ✅ Control version variants documented
- ✅ Unit handling method specified
- ✅ Sample lines match field definitions
- ✅ Parser successfully extracts all fields
- ✅ Tests pass with sample data
- ✅ Endpoints updated and working

**This workflow ensures reliable, repeatable schema definition for all CNC data file types.**
