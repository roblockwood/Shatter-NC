"""Shared state and Pydantic models for status API sub-routers.

Holds ``polling_service`` (injected at startup via ``set_polling_service``)
and the request/response models that span multiple sub-modules.

Sub-routers access the live service at request time via module reference:

    import app.api._status_state as _state
    # Inside a route handler:
    if _state.polling_service:
        await _state.polling_service.refresh_tool_data(machine_id)
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator

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


# ---------------------------------------------------------------------------
# Unified tool changes batch (all write operation types)
# ---------------------------------------------------------------------------

ToolChangeOperationType = Literal[
    "color",
    "assignment",
    "type",
    "delete",
    "cap",
    "spindle",
    "offset",
    "life",
    "name",
]


class ToolChangeItem(BaseModel):
    """Single tooling write in a batch push."""

    operation_type: ToolChangeOperationType
    client_id: Optional[str] = Field(
        None, description="Optional UI correlation id for matching pending changes"
    )
    pot_number: Optional[int] = None
    tool_number: Optional[int] = None
    color: Optional[int] = None
    tool_type: Optional[int] = None
    offset_type: Optional[Literal["H", "D", "W"]] = None
    value: Optional[float] = None
    life_value: Optional[int] = None
    life_type: Optional[Literal["TIME", "COUNT"]] = "TIME"
    name_value: Optional[str] = None

    @model_validator(mode="after")
    def validate_payload(self) -> "ToolChangeItem":
        op = self.operation_type
        if op == "color":
            if self.pot_number is None or self.tool_number is None or self.color is None:
                raise ValueError("color requires pot_number, tool_number, and color")
        elif op == "assignment":
            if self.pot_number is None or self.tool_number is None:
                raise ValueError("assignment requires pot_number and tool_number")
        elif op == "type":
            if self.pot_number is None or self.tool_type is None:
                raise ValueError("type requires pot_number and tool_type")
        elif op == "delete":
            if self.pot_number is None:
                raise ValueError("delete requires pot_number")
        elif op == "cap":
            if self.pot_number is None:
                raise ValueError("cap requires pot_number")
        elif op == "spindle":
            if self.tool_number is None:
                raise ValueError("spindle requires tool_number")
        elif op == "offset":
            if self.tool_number is None or self.offset_type is None or self.value is None:
                raise ValueError("offset requires tool_number, offset_type, and value")
        elif op == "life":
            if self.tool_number is None or self.life_value is None:
                raise ValueError("life requires tool_number and life_value")
        elif op == "name":
            if self.tool_number is None or self.name_value is None:
                raise ValueError("name requires tool_number and name_value")
        return self


class BatchToolChangesRequest(BaseModel):
    changes: List[ToolChangeItem]


class ToolChangeResult(BaseModel):
    operation_type: ToolChangeOperationType
    success: bool
    client_id: Optional[str] = None
    pot_number: Optional[int] = None
    tool_number: Optional[int] = None
    color: Optional[int] = None
    tool_type: Optional[int] = None
    offset_type: Optional[str] = None
    value: Optional[float] = None
    life_value: Optional[int] = None
    life_type: Optional[str] = None
    name_value: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


class BatchToolChangesResponse(BaseModel):
    results: List[ToolChangeResult]
    total: int
    successful: int
    failed: int
