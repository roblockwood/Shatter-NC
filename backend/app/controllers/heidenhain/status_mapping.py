"""Map Heidenhain OPC UA state names to Shatter status strings."""
from __future__ import annotations

from typing import Optional

# NC program execution states (NCProgramStateMachineType)
EXEC_STATE_RUNNING = "Running"
EXEC_STATE_IDLE = "Idle"
EXEC_STATE_NOT_SELECTED = "NotSelected"
EXEC_STATE_STOPPED = "Stopped"
EXEC_STATE_INTERRUPTED = "Interrupted"
EXEC_STATE_ERROR = "Error"
EXEC_STATE_FINISHED = "Finished"

# NC connection states (NCStateMachineType)
NC_STATE_AVAILABLE = "NCIsAvailable"
NC_STATE_NOT_CONNECTED = "NCIsNotConnected"
NC_STATE_CONNECTED = "NCIsConnected"
NC_STATE_BOOTED = "NCIsBooted"
NC_STATE_INITIALIZING = "NCIsInitializing"
NC_STATE_SHUTTING_DOWN = "NCIsShuttingDown"
NC_STATE_NOT_AVAILABLE = "NCIsNotAvailable"


def map_exec_state_to_status(exec_state: Optional[str]) -> str:
    """Map NCProgramStateMachine CurrentState to Shatter status."""
    if not exec_state:
        return "standby"

    normalized = exec_state.strip()
    if normalized == EXEC_STATE_RUNNING:
        return "operating"
    if normalized in (EXEC_STATE_IDLE, EXEC_STATE_NOT_SELECTED, EXEC_STATE_FINISHED):
        return "standby"
    if normalized in (EXEC_STATE_STOPPED, EXEC_STATE_INTERRUPTED):
        return "stopped"
    if normalized == EXEC_STATE_ERROR:
        return "error"
    return "standby"


def map_nc_state_to_available(nc_state: Optional[str]) -> bool:
    """Return True when the control is fully available for operation."""
    if not nc_state:
        return False
    return nc_state.strip() == NC_STATE_AVAILABLE


def derive_status(
    nc_state: Optional[str],
    exec_state: Optional[str],
    *,
    has_errors: bool = False,
) -> str:
    """Combine NC connection state, program execution state, and active errors."""
    if not map_nc_state_to_available(nc_state):
        if nc_state and nc_state.strip() == NC_STATE_NOT_CONNECTED:
            raise ConnectionError("OPC UA server not connected to NC control")
        return "off"

    status = map_exec_state_to_status(exec_state)
    if has_errors and status not in ("operating", "off"):
        return "error"
    return status
