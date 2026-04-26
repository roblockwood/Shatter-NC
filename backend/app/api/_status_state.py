"""Shared state and Pydantic models for status API sub-routers.

Holds ``polling_service`` (injected at startup via ``set_polling_service``)
and the request/response models that span multiple sub-modules.

Sub-routers access the live service at request time via module reference:

    import app.api._status_state as _state
    # Inside a route handler:
    if _state.polling_service:
        await _state.polling_service.refresh_tool_data(machine_id)
"""
from typing import List, Optional
from pydantic import BaseModel

# Injected at startup by main.py → status.set_polling_service()
polling_service = None


def set_polling_service(service) -> None:
    """Inject the polling service from main.py."""
    global polling_service
    polling_service = service


class ColorChangeRequest(BaseModel):
    """Request to change a single tool color."""

    pot_number: int
    tool_number: int
    color: int


class BatchColorChangeRequest(BaseModel):
    """Request to change multiple tool colors."""

    changes: List[ColorChangeRequest]


class ColorChangeResult(BaseModel):
    """Result of a single color change operation."""

    pot_number: int
    tool_number: int
    color: int
    success: bool
    error_code: Optional[str] = None
    message: Optional[str] = None


class BatchColorChangeResponse(BaseModel):
    """Response from batch color change operation."""

    results: List[ColorChangeResult]
    total: int
    successful: int
    failed: int
