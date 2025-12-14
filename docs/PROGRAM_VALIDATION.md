# Program Validation

Shatter includes file validation for NC programs already deployed on CNC machines. This allows re-validation against current machine state without re-uploading files.

## Why Re-Validation?

Tool inventory and work offsets change over time. A program uploaded weeks ago may have been validated against tools that have since been removed or modified. Re-validation ensures:

- **Current tool availability** - Verifies all required tools are still in the ATC
- **Accurate WCS offsets** - Checks work coordinate systems match expected values
- **Up-to-date validation** - Reflects the machine's current state, not historical state

## How Validation Works

### 1. User Initiates Validation

In the File Browser, users can click the **VALIDATE** button on any O-number file (O####.nc pattern).

```
File Browser → Select O-number file → [ VALIDATE ]
```

### 2. Backend Downloads and Validates

When validation is triggered:

**Step 1: Download File via FTP**
```python
# POST /api/programs/machines/{machine_id}/programs/validate-file?file_path=/O2000.NC

# Backend downloads the file from the machine
ftp_client = CNCFtpClient(...)
file_bytes = await ftp_client.download_file(file_path)
gcode_content = file_bytes.decode('utf-8', errors='replace')
```

**Step 2: Call Existing Validation Logic**
```python
# Uses EXACT SAME validation as upload
request = ProgramValidateRequest(gcode_content=gcode_content)
validation_result = await validate_program(machine_id, request, db)
```

**Step 3: Return Results with Content**
```python
# Returns validation results AND file content
return ProgramValidationWithContentResponse(
    validation=validation_result,
    gcode_content=gcode_content  # Cached to avoid re-downloading
)
```

### 3. Frontend Displays Results

The validation results temporarily replace deployment info in the details card:

```
*FRESH* VALIDATION RESULTS  (shown in green)

STATUS: ✓ PASSED / ✕ FAILED
DEPLOYED: [timestamp]
VALIDATED BY: [logic]

[Tool Details Table]
[WCS Offset Table]
```

### 4. Auto-Save to Database

After validation completes, results are automatically saved:

```typescript
// Frontend automatically creates new deployment record
const deployResponse = await fetch(
  `/api/programs/machines/${machine_id}/programs/deploy-validated`,
  {
    method: 'POST',
    body: JSON.stringify({
      deployed_filename: program.name,
      gcode_content: validationData.gcode_content,  // Already downloaded!
      validation_results: validationData.validation
    })
  }
);
```

**Backend creates new deployment record:**
```python
# POST /api/programs/machines/{machine_id}/programs/deploy-validated

# Creates/retrieves program by content hash
result = service.upload_program(
    gcode_content=request.gcode_content,
    original_filename=request.deployed_filename,
    machine_id=machine_id,
    deployed_filename=request.deployed_filename,
    validate=False,  # Already validated
    validation_results=request.validation_results
)

return result["deployment"]
```

This creates a new `ProgramDeployment` record with:
- Current timestamp
- Fresh validation results
- Link to program by content hash
- Previous deployment marked as `is_current = False`

### 5. Visual Feedback

After validation saves:

1. **Deployment details refresh** - Shows new deployment record with fresh validation
2. **Page auto-scrolls** - Smoothly scrolls to deployment section
3. **Green title indicator** - "*FRESH* VALIDATION RESULTS" shown in green (#4ade80)
4. **Timestamp updated** - New deployment timestamp reflects validation time

## Validation Process Details

### What Gets Validated

The validation logic checks:

#### Machine Data Fetching

**Always Fetched (Even When Not in NC):**
- **Tool list** - All available tools from machine via HTTP endpoint
- **WCS offsets** - All work offsets (G54-G59) from POSNI1.NC file via FTP

**Rationale:**
- Provides reference data even when NC program doesn't specify tools/WCS
- Shows machine actual values for comparison
- Helps operators understand what's available on the machine

**Display Behavior:**
- **Tools not in NC**: Shows machine tools with "N/A" status, actual values displayed
- **WCS not in NC**: Shows "XYZ NOT PARSED" with machine G54 values for reference

**Implementation:** [programs.py:124-207](../backend/app/api/programs.py#L124-L207)

#### Tool Validation
- **Tool availability** - Each tool called by the program (T1, T2, etc.) must exist in machine's ATC
- **Tool metadata** - Compares tool number, diameter, corner radius, description
- **Tool status** - Marks as `found`, `missing`, `mismatch`, or `not_in_nc` (available but not referenced)

Example tool validation result:
```json
{
  "T1": {
    "status": "found",
    "program_tool": {
      "tool_number": 1,
      "diameter": 0.5,
      "corner_radius": 0.0,
      "description": "1/2 FLAT ENDMILL"
    },
    "machine_tool": {
      "tool_number": 1,
      "diameter": 0.5,
      "corner_radius": 0.0,
      "description": "1/2 FLAT ENDMILL"
    }
  }
}
```

#### WCS Offset Validation
- **Coordinate systems** - Validates G54, G55, G56, G57, G58, G59 offsets
- **Tolerance checking** - Allows configurable tolerance for X/Y/Z offsets
- **Offset matching** - Compares program expectations vs machine reality
- **Missing WCS in NC** - If WCS not specified in program, displays machine G54 data with "XYZ NOT PARSED" status

Example WCS validation result:
```json
{
  "G54": {
    "status": "match",
    "program_wcs": {
      "x": 0.0,
      "y": 0.0,
      "z": -5.0,
      "tolerance": 0.001
    },
    "machine_wcs": {
      "x": 0.0,
      "y": 0.0,
      "z": -5.0
    }
  }
}
```

#### Overall Validation Status
```json
{
  "valid": true,  // Overall pass/fail
  "errors": [],   // Blocking issues (missing tools, WCS mismatches)
  "warnings": [], // Non-blocking issues
  "tools": {...}, // Tool validation details
  "wcs": {...}    // WCS validation details
}
```

### Validation Logic Sharing

**CRITICAL:** Validation uses the EXACT same code path as upload validation.

```python
# Both flows call the same function:
@router.post("/machines/{machine_id}/programs/validate")
async def validate_program(
    machine_id: int,
    request: ProgramValidateRequest,
    db: Session = Depends(get_db)
) -> ProgramValidationResponse:
    """Shared validation logic used by both upload and re-validation."""
    # ... validation implementation ...
```

This ensures:
- **Consistency** - Same validation rules for upload and re-validation
- **No duplication** - Single source of truth
- **Easy maintenance** - Update validation once, applies everywhere

## API Endpoints

### Validate File on Machine

Downloads a file from the machine via FTP and validates it against current machine state.

```http
POST /api/programs/machines/{machine_id}/programs/validate-file?file_path=/O2000.NC
```

**Response:**
```json
{
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "tools": {...},
    "wcs": {...}
  },
  "gcode_content": "G0 X0 Y0\n..."
}
```

### Deploy Validated Program

Creates a deployment record for a file already on the machine with pre-computed validation results.

```http
POST /api/programs/machines/{machine_id}/programs/deploy-validated
Content-Type: application/json

{
  "deployed_filename": "O2000.NC",
  "gcode_content": "G0 X0 Y0\n...",
  "validation_results": {...}
}
```

**Response:**
```json
{
  "id": 123,
  "program_id": 45,
  "machine_id": 1,
  "deployed_filename": "O2000.NC",
  "deployed_path": "/O2000.NC",
  "deployed_at": "2025-12-12T18:30:00Z",
  "validation_passed": true,
  "validation_results": {...},
  "is_current": true,
  "replaced_at": null
}
```

## Frontend Flow (FileBrowser.tsx)

### State Management

```typescript
// Validation state
const [freshValidation, setFreshValidation] = useState<FreshValidationState | null>(null);
const [validationLoading, setValidationLoading] = useState(false);
const [validationError, setValidationError] = useState<string | null>(null);

interface FreshValidationState {
  validation: ValidationResults;
  gcode_content: string;
  timestamp: number;
}
```

### Validation Handler

```typescript
const handleValidate = async (program: Program) => {
  // Step 1: Download and validate
  setValidationLoading(true);
  const validationData = await fetch(
    `/api/programs/machines/${machineId}/programs/validate-file?file_path=${filePath}`,
    { method: 'POST' }
  );

  // Step 2: Show fresh validation temporarily
  setFreshValidation({
    validation: validationData.validation,
    gcode_content: validationData.gcode_content,
    timestamp: Date.now()
  });

  // Step 3: Auto-save to database
  await fetch(
    `/api/programs/machines/${machineId}/programs/deploy-validated`,
    {
      method: 'POST',
      body: JSON.stringify({
        deployed_filename: program.name,
        gcode_content: validationData.gcode_content,
        validation_results: validationData.validation
      })
    }
  );

  // Step 4: Refresh and scroll to results
  await fetchDeploymentDetail(program);
  setFreshValidation(null);
  deploymentSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
};
```

### UI Components

**VALIDATE Button** (lines 1136-1150 in FileBrowser.tsx)
```typescript
{selectedProgram.name.match(/^O\d{4}\.NC$/i) && (
  validationLoading ? (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span>{renderProgressBar()}</span>
      <span className="text-muted">Downloading and validating...</span>
    </div>
  ) : (
    <button
      className="terminal-button"
      onClick={() => handleValidate(selectedProgram)}
    >
      [ VALIDATE ]
    </button>
  )
)}
```

**Deployment Section with Fresh Validation** (lines 874-884)
```typescript
<div className="detail-section" ref={deploymentSectionRef}>
  <div className="deployment-info-header">
    <div className="section-title">
      {freshValidation ? (
        <span style={{ color: '#4ade80' }}>*FRESH* VALIDATION RESULTS</span>
      ) : (
        'DEPLOYMENT INFO'
      )}
    </div>
  </div>
  {/* Validation results display */}
</div>
```

## Design Decisions

### Content Caching

The backend returns `gcode_content` alongside validation results to avoid re-downloading for deployment:

```python
return ProgramValidationWithContentResponse(
    validation=validation_result,
    gcode_content=gcode_content  # Cache for deployment
)
```

This ensures:
- **Atomic operation** - Deploy exactly what was validated
- **Performance** - No duplicate FTP downloads
- **Consistency** - Same content for validation and deployment

### Deployment History

Each validation creates a new deployment record:

- **Previous deployment** marked as `is_current = False`, `replaced_at` timestamp set
- **New deployment** created with fresh validation results
- **History preserved** - All past validations remain queryable
- **Audit trail** - Can see when/how validation results changed over time

### Auto-Save Behavior

Validation results are automatically saved to the database (no manual "DEPLOY" button):

**Why?**
- Validation is expensive (FTP download + computation)
- Results should be preserved for historical tracking
- Avoids user forgetting to save important validation data
- Deployment record creation is lightweight (no file transfer)

## Error Handling

### FTP Errors
```json
{
  "detail": "File not found on machine: /O2000.NC"
}
```

### Validation Failures
```typescript
{
  validationError && (
    <div className="validation-error">
      <span className="text-error">X {validationError}</span>
      <button onClick={() => handleValidate(selectedProgram)}>
        [ RETRY ]
      </button>
      <button onClick={() => setValidationError(null)}>
        [ DISMISS ]
      </button>
    </div>
  )
}
```

### Connection Timeouts
Default FTP timeout is 30 seconds. If exceeded:
```json
{
  "detail": "FTP connection timeout after 30 seconds"
}
```

## Limitations

- **O-number files only** - VALIDATE button only appears for files matching O####.nc pattern
- **FTP required** - Machine must have working FTP server
- **No offline validation** - Must download file from machine (can't validate arbitrary content)
- **Synchronous operation** - Frontend blocks during validation (shows progress indicator)

## Testing

### Backend Testing
```bash
# Test validation endpoint
curl -X POST "http://localhost:8000/api/programs/machines/1/programs/validate-file?file_path=/O2000.NC"

# Test deployment endpoint
curl -X POST "http://localhost:8000/api/programs/machines/1/programs/deploy-validated" \
  -H "Content-Type: application/json" \
  -d '{"deployed_filename": "O2000.NC", "gcode_content": "...", "validation_results": {...}}'
```

### Frontend Testing
1. Navigate to File Browser
2. Select machine with deployed O-number file
3. Click file to view details
4. Click [ VALIDATE ] button
5. Observe progress indicator
6. Verify results display with green "*FRESH* VALIDATION RESULTS" title
7. Verify page auto-scrolls to deployment section
8. Verify new deployment record appears in database

## Runtime Formatting

Estimated runtime displays in HH:MM:SS format with whole seconds:

```typescript
const formatRuntime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);  // Rounded to whole seconds
  return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};
```

Example: `0:12:52` (not `0:12:52.36567083026512`)
