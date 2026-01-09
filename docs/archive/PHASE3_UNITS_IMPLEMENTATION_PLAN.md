# Phase 3: Units Implementation Plan

## Overview

This plan implements units support throughout the Shatter-NC codebase, allowing machines to be configured in either inches (`in`) or millimeters (`mm`). The implementation follows a "store raw, convert at display/validation" strategy.

**Status**: ✅ **IMPLEMENTATION COMPLETE** (Core features)

**Related**: [BACKEND_TELNET_MIGRATION_PLAN.md](./BACKEND_TELNET_MIGRATION_PLAN.md) - Phase 3 (archived - migration complete)

## Implementation Summary

✅ **Completed Tasks**:
- Unit converter utility created
- All parsers updated to accept and include units
- API endpoints updated to pass units to parsers
- Frontend formatting utility created
- All UI components updated to display correct units
- Machine status types updated to include units
- Polling service updated to pass units

⏳ **Remaining**:
- Validation logic unit conversion (Phase 3.1.6) - Can be deferred until G-code unit detection is implemented

---

## Implementation Strategy

### Core Principles

1. **Store Raw Values**: Parsers store values exactly as received from machine (no conversion)
2. **Pass Units Through**: Units are passed as parameters to parsers and included in API responses
3. **Convert at Display**: Unit conversion happens only when displaying to users
4. **Backward Compatible**: Default to `'in'` if units not specified (maintains existing behavior)

### Data Flow

```
Machine (DB) → API Endpoint → Parser (with units param) → Raw Values + Units Metadata
                                                                    ↓
                                                          API Response (includes units)
                                                                    ↓
                                                          Frontend (formatDimension utility)
                                                                    ↓
                                                          Display (with correct unit suffix)
```

---

## Phase 3.1: Backend - Parser Updates

**Goal**: Add units parameter support to parsers and include units metadata in outputs.

### Tasks

#### 3.1.1: Create Unit Converter Utility

**File**: `backend/app/utils/unit_converter.py`

**Implementation**:
- `convert_inches_to_mm(value: float) -> float`
- `convert_mm_to_inches(value: float) -> float`
- `convert_dimension(value: float, from_units: str, to_units: str) -> float`
- `format_dimension(value: float, units: str, decimals: int = 4) -> str`

**Tests**: Unit tests for conversion accuracy

---

#### 3.1.2: Update TOLNI Parser

**File**: `backend/app/parsers/tolni_parser.py`

**Changes**:
- Add `units: str = 'in'` parameter to `TOLNIParser.__init__()`
- Add `units: str = 'in'` parameter to `parse_tolni()` function
- Include `"units": self.units` in parser output dict
- Store raw values (no conversion)

**Example Output**:
```python
{
    "tools": [...],
    "total_tools": 10,
    "units": "in"  # or "mm"
}
```

---

#### 3.1.3: Update POSNI Parser

**File**: `backend/app/parsers/posni_parser.py`

**Changes**:
- Add `units: str = 'in'` parameter to `POSNIParser.__init__()`
- Add `units: str = 'in'` parameter to `parse_posni()` function
- Include `"units": self.units` in parser output dict
- Store raw values (no conversion)

**Example Output**:
```python
{
    "work_offsets": {...},
    "extended_offsets": {...},
    "units": "in"  # or "mm"
}
```

---

#### 3.1.4: Update HTTP Client Tool Parser

**File**: `backend/app/clients/http_client.py`

**Changes**:
- Add `units: str = 'in'` parameter to `get_tool_data()` method
- Add `units: str = 'in'` parameter to `_parse_tool_data()` method
- Include `"units": units` in parser output dict
- Store raw values (no conversion)

**Example Output**:
```python
{
    "tools": [...],
    "units": "in"  # or "mm"
}
```

---

#### 3.1.5: Update API Endpoints to Pass Units

**Files**:
- `backend/app/api/status.py`

**Changes**:

1. **`get_tools()` endpoint** (line ~173):
   ```python
   # Current:
   parsed = parse_tolni(tool_table_content.encode('utf-8'))
   
   # Updated:
   parsed = parse_tolni(tool_table_content.encode('utf-8'), units=db_machine.units)
   ```

2. **`get_tools()` endpoint - ATC source** (line ~207):
   ```python
   # Current:
   data = http_client.get_tool_data()
   
   # Updated:
   data = http_client.get_tool_data(units=db_machine.units)
   ```

3. **`get_position()` endpoint** (line ~317):
   ```python
   # Current:
   parsed = parse_posni(position_data.encode('utf-8'))
   
   # Updated:
   parsed = parse_posni(position_data.encode('utf-8'), units=db_machine.units)
   ```

4. **Include units in all responses**:
   - Add `"units": db_machine.units` to response dicts

---

#### 3.1.6: Update Validation Logic

**File**: `backend/app/api/programs.py`

**Changes**:

1. **Tool Validation** (`_validate_tool()` function):
   - Add `machine_units: str` parameter
   - Add `program_units: str` parameter (from G-code if available)
   - Convert values before comparison if units differ
   - Include units in validation result messages

2. **WCS Validation** (`_validate_wcs_offset()` function):
   - Add `machine_units: str` parameter
   - Add `program_units: str` parameter (from G-code if available)
   - Convert values before comparison if units differ
   - Include units in validation result messages

3. **Update validation calls**:
   ```python
   result = _validate_tool(
       tool,
       machine_tool_data,
       machine_units=machine.units,
       program_units='in',  # TODO: Extract from G-code if available
       use_machine_tolerances=machine.use_machine_tool_tolerances,
       ...
   )
   ```

**Note**: G-code unit detection (G20/G21) can be added later if needed.

---

#### 3.1.7: Update API Response Schemas

**Files**:
- `backend/app/schemas/machine.py` (already has units field ✅)
- Create/update response schemas for status endpoints

**Changes**:
- Ensure `units` field is included in all dimensional data responses
- Add units to tool/position response schemas

---

## Phase 3.2: Frontend - Display Updates

**Goal**: Update UI components to display units correctly based on machine configuration.

### Tasks

#### 3.2.1: Create Frontend Unit Formatting Utility

**File**: `frontend/src/utils/formatDimension.ts`

**Implementation**:
```typescript
export function formatDimension(
  value: number | null | undefined,
  units: 'in' | 'mm' = 'in',
  decimals: number = 4
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '────';
  }
  
  const formatted = value.toFixed(decimals);
  const suffix = units === 'in' ? '"' : ' mm';
  return `${formatted}${suffix}`;
}

export function getUnitSuffix(units: 'in' | 'mm'): string {
  return units === 'in' ? '"' : ' mm';
}
```

---

#### 3.2.2: Update ToolListModal

**File**: `frontend/src/components/ToolListModal.tsx`

**Changes**:
- Import `formatDimension` utility
- Add `units` prop to component (from machine data)
- Replace hardcoded `"` suffix with `formatDimension(tool.diameter, units)`
- Replace hardcoded `"` suffix with `formatDimension(tool.length, units)`

**Lines to update**: ~58, ~61

---

#### 3.2.3: Update ToolsPane

**File**: `frontend/src/components/machine-detail/ToolsPane.tsx`

**Changes**:
- Import `formatDimension` utility
- Add `units` prop to component (from machine data or API response)
- Replace hardcoded `"` suffix with `formatDimension(tool.diameter, units)` (line ~447)
- Replace hardcoded `"` suffix with `formatDimension(tool.length, units)` (line ~448)

**Note**: Check how ToolsPane receives machine data - may need to pass units from parent component.

---

#### 3.2.4: Update ToolDetailModal

**File**: `frontend/src/components/ToolDetailModal.tsx`

**Changes**:
- Import `formatDimension` utility
- Add `units` prop to component (from machine data)
- Replace hardcoded `"` suffix in diameter display (line ~162-165)
- Replace hardcoded `"` suffix in length display (line ~171-173)

---

#### 3.2.5: Update UploadConfirmationModal

**File**: `frontend/src/components/UploadConfirmationModal.tsx`

**Changes**:
- Import `formatDimension` utility
- Add `units` prop to component (from machine data)
- Replace hardcoded `"` suffixes in tool validation display
- Update WCS offset display to show units (if position data displayed)

**Note**: Validation results come from API - ensure API includes units in response.

---

#### 3.2.6: Update Machine Status Types

**Files**:
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/components/MachineCard.tsx`
- `frontend/src/api/machines.ts`

**Changes**:
- Add `units?: 'in' | 'mm'` to `MachineStatus` interface
- Ensure machine data includes units when fetched from API

---

#### 3.2.7: Create Position Display Component (if needed)

**File**: `frontend/src/components/machine-detail/PositionPane.tsx` (new or existing)

**Changes**:
- Display work offsets (G54-G59) with units
- Display extended offsets (X01-X48) with units
- Use `formatDimension` utility for all coordinate values

**Note**: Check if position display component already exists.

---

## Phase 3.3: Testing & Validation

**Goal**: Ensure units work correctly across all components.

### Tasks

#### 3.3.1: Backend Unit Tests

**Files**: `backend/tests/test_unit_converter.py` (new)

**Tests**:
- Conversion accuracy (inches ↔ mm)
- Edge cases (zero, negative, very large numbers)
- Rounding precision

---

#### 3.3.2: Parser Tests

**Files**: 
- `backend/tests/test_tolni_parser.py` (update)
- `backend/tests/test_posni_parser.py` (update)

**Tests**:
- Parser accepts units parameter
- Parser includes units in output
- Parser doesn't convert values (stores raw)

---

#### 3.3.3: API Integration Tests

**Files**: `backend/tests/test_status_api.py` (update or new)

**Tests**:
- API endpoints pass units to parsers
- API responses include units field
- Units match machine configuration

---

#### 3.3.4: Frontend Component Tests

**Files**: Frontend test files (if using Vitest)

**Tests**:
- `formatDimension` utility formats correctly
- Components display correct unit suffix
- Components handle null/undefined values

---

#### 3.3.5: Manual Testing Checklist

- [ ] Create machine with `units='in'`, verify displays show `"`
- [ ] Create machine with `units='mm'`, verify displays show ` mm`
- [ ] Update machine units, verify UI updates
- [ ] Verify tool table displays correct units
- [ ] Verify position data displays correct units
- [ ] Verify validation messages show correct units
- [ ] Test with real machine data (both unit types)

---

## Phase 3.4: Documentation Updates

**Goal**: Document units implementation for future reference.

### Tasks

#### 3.4.1: Update API Reference

**File**: `docs/API_REFERENCE.md`

**Changes**:
- Document `units` field in machine responses
- Document `units` field in tool/position responses
- Add examples showing both unit types

---

#### 3.4.2: Update Migration Plan

**File**: `docs/archive/BACKEND_TELNET_MIGRATION_PLAN.md` (archived - migration complete)

**Changes**:
- Mark Phase 3 as "In Progress" or "Complete"
- Update Phase 3 description to reflect manual selection approach
- Document completed tasks

---

#### 3.4.3: Update Development Guide

**File**: `docs/DEVELOPMENT_GUIDE.md`

**Changes**:
- Add section on units handling
- Document `formatDimension` utility usage
- Document unit conversion utilities

---

## Implementation Order

### Recommended Sequence

1. **Phase 3.1.1**: Create unit converter utility (foundation)
2. **Phase 3.1.2-3.1.4**: Update parsers (add units parameter)
3. **Phase 3.1.5**: Update API endpoints (pass units to parsers)
4. **Phase 3.1.6**: Update validation logic (handle unit conversion)
5. **Phase 3.2.1**: Create frontend formatting utility
6. **Phase 3.2.2-3.2.6**: Update UI components (one at a time)
7. **Phase 3.3**: Testing (throughout implementation)
8. **Phase 3.4**: Documentation (as features complete)

### Dependencies

- Backend parsers must be updated before API endpoints
- Frontend utility must be created before UI components
- API responses must include units before frontend can use them

---

## Open Questions & Future Enhancements

### Questions to Resolve

1. **G-code Unit Detection**: Should we detect G20/G21 in G-code and use that for validation? Or always use machine units?
   - **Recommendation**: Use machine units for now, add G-code detection later if needed

2. **Tolerance Units**: Tolerances are stored in inches. Should we convert them based on machine units?
   - **Recommendation**: Keep tolerances in machine's native units (may need migration for existing mm machines)

3. **Historical Data**: How to handle historical data that was stored without units?
   - **Recommendation**: Default to `'in'` for backward compatibility

### Future Enhancements

- G-code unit detection (G20/G21)
- Unit conversion in validation (if G-code units differ from machine)
- Export/import with unit conversion
- Unit-aware tolerance configuration UI

---

## Success Criteria

Phase 3 is complete when:

- ✅ All parsers accept and include units parameter
- ✅ All API endpoints pass units to parsers
- ✅ All API responses include units field
- ✅ All UI components display correct unit suffix
- ✅ Validation handles units correctly
- ✅ Unit tests pass
- ✅ Manual testing confirms correct display for both unit types
- ✅ Documentation updated

---

## Notes

- **Backward Compatibility**: Default to `'in'` maintains existing behavior
- **No Data Migration**: Existing data doesn't need conversion (stored as raw values)
- **Incremental Rollout**: Can implement one component at a time
- **Testing**: Test with real machine data in both unit configurations

---

## Related Files

### Backend
- `backend/app/utils/unit_converter.py` (new)
- `backend/app/parsers/tolni_parser.py`
- `backend/app/parsers/posni_parser.py`
- `backend/app/clients/http_client.py`
- `backend/app/api/status.py`
- `backend/app/api/programs.py`
- `backend/app/models/machine.py` (already has units ✅)
- `backend/app/schemas/machine.py` (already has units ✅)

### Frontend
- `frontend/src/utils/formatDimension.ts` (new)
- `frontend/src/components/ToolListModal.tsx`
- `frontend/src/components/machine-detail/ToolsPane.tsx`
- `frontend/src/components/ToolDetailModal.tsx`
- `frontend/src/components/UploadConfirmationModal.tsx`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/components/MachineCard.tsx`

### Documentation
- `docs/API_REFERENCE.md`
- `docs/archive/BACKEND_TELNET_MIGRATION_PLAN.md` (archived)
- `docs/DEVELOPMENT_GUIDE.md`

---

**Last Updated**: 2025-01-XX
**Status**: Planning Complete → Ready for Implementation

