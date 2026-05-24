"""CNC controller adapters for multi-vendor machine polling."""

from app.controllers.base import get_capabilities_for_controller
from app.controllers.registry import get_adapter_for_machine

__all__ = ["get_adapter_for_machine", "get_capabilities_for_controller"]
