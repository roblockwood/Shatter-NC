---
name: machine-testing
description: Handle Telnet connection management when testing on CNC machines. Ensures connection availability and restoration.
allowed-tools: Read, Write, Terminal, Codebase Search
---

# Machine Testing Skill

## Purpose

When testing on CNC machines via Telnet, the Shatter backend may hold the Telnet connection (single connection limit per machine). This skill ensures:

1. **Connection Availability**: Stops the dev container to free up the Telnet connection
2. **Test Execution**: Runs the test with a fresh connection
3. **Connection Restoration**: Restarts the dev container after testing

## When to Use

Use this skill whenever the user requests:
- Testing on a machine
- Testing a parser/schema on a machine
- Testing Telnet commands on a machine
- Any direct machine testing that requires Telnet access

## Workflow

### 1. Pre-Test: Stop Dev Container

**Stop the backend dev container to free up the Telnet connection:**

```bash
# Stop the backend service (frees up Telnet connection)
docker-compose -f docker-compose.dev.yml stop backend

# Or if using docker directly:
# docker stop shatter-nc-backend-1
```

**Why**: The backend Docker container holds the Telnet connection. Stopping it ensures the connection is fully released for testing.

### 2. Execute Test

Run the test with a fresh connection:

```python
from app.clients.telnet_client import get_or_create_connection

# Get fresh connection for testing
ip_address = "192.168.1.100"  # or from user request
port = 10000

client = await get_or_create_connection(
    ip_address=ip_address,
    port=port,
    timeout=15  # Longer timeout for testing
)

# Perform test operations
# ...
```

### 3. Post-Test: Restart Dev Container

**Restart the backend dev container after testing:**

```bash
# Restart the backend service
docker-compose -f docker-compose.dev.yml start backend

# Or if using docker directly:
# docker start shatter-nc-backend-1
```

**Note**: The backend will automatically reconnect to the machine when it needs Telnet data.

## Implementation Pattern

When creating test scripts or performing ad-hoc testing:

**Before running the test script:**

1. Stop the dev container:
   ```bash
   docker-compose -f docker-compose.dev.yml stop backend
   ```

2. Run the test script:
   ```python
   async def test_on_machine(ip_address: str, port: int = 10000):
       """Test function - assumes dev container is stopped."""
       # Get fresh connection for testing
       client = await get_or_create_connection(ip_address, port, timeout=15)
       # ... perform test operations ...
       return test_results
   ```

3. After testing, restart the dev container:
   ```bash
   docker-compose -f docker-compose.dev.yml start backend
   ```

**Alternative (if you prefer programmatic connection management):**

```python
from app.clients.telnet_client import close_connection, get_or_create_connection

async def test_on_machine(ip_address: str, port: int = 10000):
    """Test function that handles connection management programmatically."""
    try:
        # Step 1: Close existing connection
        print("Closing any existing Telnet connection from Shatter backend...")
        await close_connection(ip_address, port)
        await asyncio.sleep(0.5)
        
        # Step 2: Run test
        client = await get_or_create_connection(ip_address, port, timeout=15)
        # ... perform test operations ...
        
        return test_results
    finally:
        # Step 3: Clean up
        print("Cleaning up test connection...")
        await close_connection(ip_address, port)
        print("Note: The Shatter backend will automatically reconnect when needed.")
```

## Key Points

- **Single Connection Limit**: Brother CNC machines only allow one active Telnet connection
- **Container Management**: **Recommended approach**: Stop the dev container before testing, restart after
- **Connection Pooling**: Shatter backend uses connection pooling to reuse connections
- **Auto-Reconnect**: Backend will automatically reconnect when it needs Telnet data after restart
- **No Service Disruption**: Stopping the container temporarily doesn't break anything - it reconnects on restart

## Example Usage

**User Request**: "Test the MEM parser on machine 192.168.1.100"

**Assistant Action**:
1. **Stop dev container**: `docker-compose -f docker-compose.dev.yml stop backend`
2. Create test script that uses fresh connection
3. Run test with fresh connection
4. **Restart dev container**: `docker-compose -f docker-compose.dev.yml start backend`
5. Report results

## Error Handling

- If connection close fails: Log warning but continue (connection may not exist)
- If test fails: Still clean up connection in finally block
- If machine is busy (CM7500): Report clear error message to user

## Notes

- **Recommended**: Stop the dev container before testing (`docker-compose -f docker-compose.dev.yml stop backend`)
- **Alternative**: Use `close_connection()` from `app.clients.telnet_client` if you prefer programmatic management
- Always use `get_or_create_connection()` for test connections
- **After testing**: Restart the dev container (`docker-compose -f docker-compose.dev.yml start backend`)
- The backend's connection pool will automatically recreate connections when needed after restart

