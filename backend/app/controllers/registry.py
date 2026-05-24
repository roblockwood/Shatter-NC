"""Controller adapter registry."""
from __future__ import annotations

from typing import Optional

from app.controllers.base import CNCControllerAdapter, CONTROLLER_TYPE_BROTHER, CONTROLLER_TYPE_HEIDENHAIN
from app.controllers.brother_adapter import BrotherAdapter
from app.models.machine import Machine


def get_adapter_for_machine(
    machine: Machine,
    *,
    last_known_prd3_status: Optional[str] = None,
) -> CNCControllerAdapter:
    """Return the appropriate controller adapter for a machine."""
    controller_type = getattr(machine, "controller_type", None) or CONTROLLER_TYPE_BROTHER

    if controller_type == CONTROLLER_TYPE_HEIDENHAIN:
        from app.controllers.heidenhain.adapter import HeidenhainOpcUaAdapter

        return HeidenhainOpcUaAdapter(machine)

    return BrotherAdapter(machine, last_known_prd3_status=last_known_prd3_status)
