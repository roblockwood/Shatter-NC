# Schema Definition Template

Use this template when providing schema specifications for Phase 4 parser generation.

## Schema Specification: [DATA_TYPE]

### Basic Information

- **Data Type**: [TOLNn, POSNn, MEM, ATCTL, etc.]
- **File Pattern**: [Filename pattern, e.g., "TOLNI1.NC", "TOLNM1.NC", "MEM.NC"]
- **Description**: [Brief description of what this data represents]

---

### Control Version Variants

Document how the format differs between control versions (C00, D00, etc.):

- **C00 Control**: [Description of C00 format, any specific differences]
- **D00 Control**: [Description of D00 format, any specific differences]
- **Other Variants**: [List any other control versions with format differences, or "None" if no variation]

---

### Unit Handling

Specify how units are determined and handled:

- **Unit Detection Method**: [Choose one]
  - `filename_based`: Units determined by filename (e.g., TOLNI1 = inches, TOLNM1 = mm)
  - `embedded_in_file`: Units indicated in file content (describe how)
  - `machine_config`: Use `machine.units` from database configuration
- **Filename Patterns** (if filename_based):
  - Inches: `[pattern]` (e.g., `TOLNI1.NC`)
  - Millimeters: `[pattern]` (e.g., `TOLNM1.NC`)
- **Unit Conversion**: [yes | no]
  - `yes`: Values need conversion based on units
  - `no`: Values stored in native units (no conversion needed)

---

### Field Definitions

For each field in the data file, provide:

```yaml
field_name:
  position: [line_number, column_start, column_end] OR [regex_pattern]
  data_type: [int | float | string | enum]
  required: [true | false]
  description: [What this field represents]
  validation: [optional validation rules, e.g., "range(1, 1000)", "positive", "non-empty"]
  example: [example value]
```

**Field Position Formats:**
- **Fixed Width**: `[line_number, column_start, column_end]` (e.g., `[0, 0, 4]` for columns 0-4 on line 0)
- **Delimited**: `[line_number, field_index]` (e.g., `[0, 2]` for 3rd field on line 0)
- **Regex**: `[regex_pattern]` (e.g., `r"T(\d+)"` to extract tool number from "T1")

**Example Field Definitions:**

```yaml
tool_number:
  position: [0, 0, 4]
  data_type: int
  required: true
  description: Tool number (1-999)
  validation: range(1, 1000)
  example: 1

diameter:
  position: [0, 10, 20]
  data_type: float
  required: true
  description: Tool diameter in machine units
  validation: positive
  example: 0.25

tool_name:
  position: [0, 25, 55]
  data_type: string
  required: false
  description: Tool name/description
  validation: max_length(30)
  example: ".250 3FL"
```

---

### Line Format Specification

- **Line Structure**: [fixed_width | delimited | regex]
  - `fixed_width`: Each line has fixed character positions
  - `delimited`: Fields separated by delimiter (space, comma, tab, etc.)
  - `regex`: Lines match regex pattern
- **Delimiter**: [if delimited, specify delimiter character(s), e.g., "space", "comma", "tab", "|"]
- **Line Length**: [if fixed_width, specify character count per line, e.g., 80]
- **Header Lines**: [number of header lines to skip, if any, e.g., 0, 1, 2]
- **Footer Lines**: [number of footer lines to skip, if any, e.g., 0, 1]
- **Empty Line Handling**: [skip | error | treat_as_data]
- **Comment Lines**: [pattern for comment lines to skip, e.g., "#", "//", or "none"]

---

### Sample Lines

Provide 3-5 actual sample lines from the data file:

```
[Paste actual sample lines here]
```

**Example:**
```
0001    0.2500    3.4494    0.0000
0002    0.5000    4.0000    0.0000
0003    0.1250    2.5000    0.0000
0004    0.7500    5.0000    0.0000
0005    1.0000    6.0000    0.0000
```

**Important**: Sample lines must match the field position definitions above.

---

### Control Version Differences

If format differs between control versions, document differences:

**C00 vs D00 Differences:**
- [List specific differences, e.g., "D00 has additional field at position X", or "No differences"]

---

### Edge Cases

Document any special cases to handle:

- **Empty Fields**: [How to handle, e.g., "treat as 0", "skip field", "raise error"]
- **Missing Lines**: [How to handle, e.g., "skip", "raise error"]
- **Malformed Data**: [How to handle, e.g., "log warning and skip", "raise error"]
- **Optional Sections**: [Any optional sections that may or may not be present]

---

### Validation Rules

Specify validation that should be applied:

- **Required Fields**: [List fields that must be present]
- **Value Ranges**: [Any min/max constraints]
- **Format Validation**: [Any format requirements, e.g., "tool_number must be 1-999"]

---

## Complete Example

```markdown
## Schema Specification: TOLNn (Tool Table)

### Basic Information
- **Data Type**: TOLNn (Tool Offset Table)
- **File Pattern**: TOLNI1.NC (inches), TOLNM1.NC (millimeters)
- **Description**: Tool table containing tool number, diameter, length, and offset data for ATC

### Control Version Variants
- **C00 Control**: Fixed-width format, 80 characters per line
- **D00 Control**: Same format as C00 (no variation)

### Unit Handling
- **Unit Detection Method**: filename_based
  - Inches: `TOLNI1.NC`
  - Millimeters: `TOLNM1.NC`
- **Unit Conversion**: no (values stored in native units)

### Field Definitions

```yaml
tool_number:
  position: [0, 0, 4]
  data_type: int
  required: true
  description: Tool number (1-999)
  validation: range(1, 1000)
  example: 1

diameter:
  position: [0, 10, 20]
  data_type: float
  required: true
  description: Tool diameter in machine units
  validation: positive
  example: 0.25

length:
  position: [0, 25, 35]
  data_type: float
  required: true
  description: Tool length offset
  validation: any
  example: 3.4494

corner_radius:
  position: [0, 40, 50]
  data_type: float
  required: false
  description: Tool corner radius
  validation: non_negative
  example: 0.0
```

### Line Format Specification

- **Line Structure**: fixed_width
- **Line Length**: 80 characters
- **Header Lines**: 0
- **Footer Lines**: 0
- **Empty Line Handling**: skip
- **Comment Lines**: none

### Sample Lines

```
0001    0.2500    3.4494    0.0000
0002    0.5000    4.0000    0.0000
0003    0.1250    2.5000    0.0000
0004    0.7500    5.0000    0.0000
0005    1.0000    6.0000    0.0000
```

### Control Version Differences

- **C00 vs D00**: No differences

### Edge Cases

- **Empty Fields**: Treat as 0.0 for numeric fields
- **Missing Lines**: Skip (tool numbers may not be sequential)
- **Malformed Data**: Log warning and skip line
- **Optional Sections**: None

### Validation Rules

- **Required Fields**: tool_number, diameter, length
- **Value Ranges**: tool_number: 1-999, diameter: > 0, length: any
- **Format Validation**: tool_number must be 4-digit zero-padded integer
```

---

## Notes

- **Be Specific**: Provide exact column positions, not approximations
- **Include Examples**: Sample lines help verify field positions
- **Document Variations**: If format differs by control version, document all variations
- **Test Positions**: Verify field positions match sample lines before submitting

---

**After providing schema specification, the parser will be generated automatically using the Phase 4 workflow.**

