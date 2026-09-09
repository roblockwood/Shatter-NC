"""Fast-path macro variable writes (cached validation + single telnet session)."""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import logging

from app.models.machine import Machine
from app.services.machine_state_validator import (
    MachineStateValidator,
    macro_write_cache_max_age_seconds,
)

logger = logging.getLogger(__name__)


@dataclass
class MacroWriteOutcome:
    success: bool
    status_code: Optional[str]
    verified_value: Optional[float]
    status_data: Dict[str, Any]
    error_message: Optional[str] = None


def _cached_machine_status(machine_id: int) -> Dict[str, Any]:
    import app.api._status_state as status_state

    polling = status_state.polling_service
    if polling is None:
        return {}
    ws = getattr(polling, "websocket_manager", None)
    if ws is None:
        return {}
    return ws.get_machine_status(machine_id) or {}


async def execute_macro_write(
    db_machine: Machine,
    machine_id: int,
    macro_number: int,
    value: float,
) -> MacroWriteOutcome:
    """
    Write a macro variable using poller cache when fresh, otherwise one telnet session
    for minimal live validation (MEM + PRD3) and WRTMCNM with verify.
    """
    from app.clients.telnet_client import create_fresh_connection

    validator = MachineStateValidator()
    max_age = macro_write_cache_max_age_seconds(db_machine.poll_interval_seconds)
    cached = _cached_machine_status(machine_id)

    cache_safe, cache_error, status_data = validator.try_validate_macro_write_from_cache(
        cached_status=cached,
        machine_id=machine_id,
        machine_name=db_machine.name,
        max_age_seconds=max_age,
    )

    telnet_client = None
    try:
        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10,
        )

        # Cache may be stale (e.g. PRD3 still "operating" after cycle end) — confirm live
        # before rejecting; only skip live check when cache confirms safe.
        if cache_safe is not True:
            is_safe, live_error, status_data = await validator.validate_macro_write_live_minimal(
                telnet_client=telnet_client,
                control_version=db_machine.control_version,
                machine_id=machine_id,
                machine_name=db_machine.name,
            )
            if not is_safe:
                return MacroWriteOutcome(
                    success=False,
                    status_code=None,
                    verified_value=None,
                    status_data=status_data,
                    error_message=live_error or cache_error,
                )
        else:
            logger.debug(
                "Macro write for machine %s using cached poller status (age <= %ss)",
                machine_id,
                max_age,
            )

        success, status_code, verified_value = await telnet_client.write_macro_variable(
            macro_number=macro_number,
            value=value,
            verbose=False,
            verify=True,
        )

        return MacroWriteOutcome(
            success=success,
            status_code=status_code,
            verified_value=verified_value,
            status_data=status_data,
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()
