"""API endpoints for real-time machine status.

Routes are split across focused sub-modules:
  _status_reads.py  — GET status, running-log, counters, alarms/live, tools
  _status_tools.py  — POST refresh, PUT/DELETE ATC writes, life, offset
  _status_files.py  — GET programs/position/download/metadata/view, POST upload
  _probe.py         — GET probe/catalog, POST probe/write|start|collect|poison

All routes and all public import paths are preserved unchanged.
"""
from fastapi import APIRouter
import app.api._status_state as _state
import app.api._status_reads as _reads
import app.api._status_tools as _tools
import app.api._status_files as _files
import app.api._probe as _probe

# Re-export models so existing callers can still do:
#   from app.api.status import ColorChangeRequest
from app.api._status_state import (  # noqa: F401
    ColorChangeRequest,
    BatchColorChangeRequest,
    ColorChangeResult,
    BatchColorChangeResponse,
)

router = APIRouter()
router.include_router(_reads.router)
router.include_router(_tools.router)
router.include_router(_files.router)
router.include_router(_probe.router)

# Module-level alias kept for backwards compatibility (tests inspect status.polling_service)
polling_service = _state.polling_service


def set_polling_service(service) -> None:
    """Inject the polling service (called from main.py at startup)."""
    _state.set_polling_service(service)
    global polling_service
    polling_service = service
