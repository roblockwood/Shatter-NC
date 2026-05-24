"""Controller adapter protocol and capability definitions."""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Set, runtime_checkable

CONTROLLER_TYPE_BROTHER = "brother"
CONTROLLER_TYPE_HEIDENHAIN = "heidenhain"

# Capability keys consumed by frontend pane gating.
CAP_STATUS = "status"
CAP_ALARMS = "alarms"
CAP_PROGRAM = "program"
CAP_STATUS_TIMELINE = "statusTimeline"
CAP_TOOLS = "tools"
CAP_TOOL_TABLE = "toolTable"
CAP_PANEL = "panel"
CAP_FILE_MANAGER = "fileManager"
CAP_COUNTERS = "counters"
CAP_UPLOAD = "upload"
CAP_PRODUCTION_RUNS = "productionRuns"

BROTHER_CAPABILITIES: Set[str] = {
    CAP_STATUS,
    CAP_ALARMS,
    CAP_PROGRAM,
    CAP_STATUS_TIMELINE,
    CAP_TOOLS,
    CAP_TOOL_TABLE,
    CAP_PANEL,
    CAP_FILE_MANAGER,
    CAP_COUNTERS,
    CAP_UPLOAD,
    CAP_PRODUCTION_RUNS,
}

HEIDENHAIN_V1_CAPABILITIES: Set[str] = {
    CAP_STATUS,
    CAP_ALARMS,
    CAP_PROGRAM,
    CAP_STATUS_TIMELINE,
}


def get_capabilities_for_controller(controller_type: Optional[str]) -> Set[str]:
    """Return capability set for a controller type (Brother = full set when unknown)."""
    normalized = (controller_type or CONTROLLER_TYPE_BROTHER).lower()
    if normalized == CONTROLLER_TYPE_HEIDENHAIN:
        return set(HEIDENHAIN_V1_CAPABILITIES)
    return set(BROTHER_CAPABILITIES)


def capabilities_as_list(controller_type: Optional[str]) -> list[str]:
    """Sorted capability list for JSON API / WebSocket payloads."""
    return sorted(get_capabilities_for_controller(controller_type))


@runtime_checkable
class CNCControllerAdapter(Protocol):
    """Protocol for vendor-specific CNC data collection."""

    def capabilities(self) -> Set[str]: ...

    async def poll_fast(self) -> Dict[str, Any]: ...

    async def poll_slow(self) -> Optional[Dict[str, Any]]: ...

    async def test_connection(self) -> Dict[str, Any]: ...

    async def close(self) -> None: ...
