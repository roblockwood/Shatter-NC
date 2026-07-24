# Per-Poll Connection Migration Plan

## Overview
This plan outlines the migration from persistent pooled telnet connections to opening/closing connections per poll operation. This change will eliminate Redis lock corruption issues and simplify connection management.

## Migration Phases

### Phase 1: Implement New Connection Factory
**Goal:** Add `create_fresh_connection()` function alongside existing code for gradual migration

**Changes:**
- Add `create_fresh_connection()` function to `backend/app/clients/telnet_client.py`
- Keep existing pooling logic intact
- Test new function works correctly

**Files Modified:**
- `backend/app/clients/telnet_client.py`

**Risk:** Low - additive change only

### Phase 2: Update Polling Service (Highest Priority)
**Goal:** Convert the polling service to use fresh connections

**Changes:**
- Update `MachinePoller.fetch_program_name()` to use `create_fresh_connection()`
- Update `MachinePoller.poll_tool_data()` to use `create_fresh_connection()`
- Update `MachinePoller.poll()` to use `create_fresh_connection()`
- Add proper try/finally blocks for connection cleanup
- Update `PollingService._prepopulate_control_versions()` to use fresh connections
- Remove connection pool cleanup from `PollingService.stop()`

**Files Modified:**
- `backend/app/services/polling.py`

**Risk:** Medium - affects core monitoring functionality, test thoroughly

### Phase 3: Update API Endpoints
**Goal:** Convert all API endpoints to use fresh connections

**Changes:**
- Update all `get_or_create_connection()` calls in API files to use `create_fresh_connection()`
- Add proper try/finally blocks for connection cleanup
- Update error handling to account for connection failures

**Files Modified:**
- `backend/app/api/status.py`
- `backend/app/api/programs.py`
- `backend/app/api/machines.py`
- `backend/app/services/machine_state_validator.py`

**Risk:** Medium - affects external API functionality

### Phase 4: Remove Connection Pooling Infrastructure
**Goal:** Eliminate old pooling code and simplify locking

**Changes:**
- Remove global `_telnet_connections` dict and `_connections_lock`
- Remove `get_or_create_connection()`, `close_connection()`, and `close_all_connections()` functions
- Remove Redis locks from read operations (keep for write operations only)
- Update `main.py` shutdown logic to remove connection cleanup

**Files Modified:**
- `backend/app/clients/telnet_client.py`
- `backend/app/main.py`

**Risk:** High - removes core infrastructure, ensure all usages converted first

### Phase 5: Update Shutdown and Cleanup Logic
**Goal:** Remove all references to connection pooling cleanup

**Changes:**
- Remove connection cleanup from application shutdown
- Update any remaining references to pooling functions
- Ensure proper connection cleanup in all error paths

**Files Modified:**
- `backend/app/main.py`
- Any remaining files with cleanup logic

**Risk:** Low - cleanup only

### Phase 6: Testing and Performance Monitoring
**Goal:** Validate the migration and monitor performance impact

**Changes:**
- Test all polling functionality works correctly
- Monitor polling performance and adjust intervals if needed
- Add connection establishment metrics
- Validate that CNC machines handle connection churn properly
- Test concurrent operations (reads should be parallel, writes serialized)

**Files Modified:**
- Monitoring and testing scripts
- Possibly add connection metrics to existing monitoring

**Risk:** Low - validation phase

## Success Criteria

- All telnet operations work correctly with fresh connections
- No Redis lock corruption issues
- Polling performance remains acceptable (within 2x of current performance)
- CNC machines handle connection churn without issues
- Error handling properly cleans up connections in all cases
- Write operations (tool changes, etc.) still properly serialize using locks

## Rollback Plan

If issues arise, can rollback by:
1. Re-implement connection pooling functions
2. Revert to `get_or_create_connection()` calls
3. Restore Redis locks on read operations
4. Test thoroughly before re-attempting migration

## Performance Considerations

- Connection establishment overhead: ~100-300ms per poll
- May need to adjust polling intervals based on performance impact
- Monitor CNC machine responsiveness to frequent connections
- Consider connection pooling for high-frequency operations if needed

## Testing Strategy

- Unit tests for `create_fresh_connection()`
- Integration tests for polling with fresh connections
- Load testing to ensure performance is acceptable
- CNC machine testing to ensure no adverse effects
- Error scenario testing (network failures, machine offline, etc.)
