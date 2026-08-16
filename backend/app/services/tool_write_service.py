"""Batch tooling writes: validate once, single telnet session, ordered dispatch."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.api._status_state import (
    BatchToolChangesResponse,
    ColorChangeRequest,
    ColorChangeResult,
    ToolChangeItem,
    ToolChangeResult,
)
from app.models.machine import Machine

logger = logging.getLogger(__name__)

COLOR_NAMES = {
    0: "None",
    1: "Blue",
    2: "Red",
    3: "Purple",
    4: "Green",
    5: "Light Blue",
    6: "Yellow",
    7: "White",
}

TOOL_TYPE_NAMES = {1: "Standard", 2: "Large", 3: "Medium"}
OFFSET_NAMES = {"H": "Length", "D": "Diameter", "W": "Wear"}

# Execution order: deletes → assignments/spindle → type/color → offsets/life → name (FTP)
_EXEC_ORDER = {
    "delete": 0,
    "assignment": 1,
    "cap": 1,
    "spindle": 2,
    "type": 3,
    "color": 4,
    "offset": 5,
    "life": 6,
    "name": 7,
}

# Strictest validator operation for mixed batches
_VALIDATOR_FOR_OP = {
    "color": "tool_color",
    "assignment": "tool_assignment",
    "cap": "tool_assignment",
    "type": "tool_type",
    "delete": "tool_delete",
    "spindle": "spindle_tool",
    "offset": "tool_offset",
    "life": "tool_life",
    "name": "tool_name",
}

_STRICT_OPS = frozenset({"assignment", "cap", "delete", "spindle"})
_CAP_TOOL_NUMBERS = frozenset({255, 999})
_STRICT_VALIDATOR_PRIORITY = (
    "assignment",
    "delete",
    "spindle",
    "type",
    "offset",
    "life",
    "name",
    "color",
)


def validation_operation_type(changes: List[ToolChangeItem]) -> str:
    """Pick the strictest MachineStateValidator operation_type for this batch."""
    ops = {c.operation_type for c in changes}
    if ops & _STRICT_OPS:
        for op in _STRICT_VALIDATOR_PRIORITY:
            if op in ops and op in _VALIDATOR_FOR_OP:
                return _VALIDATOR_FOR_OP[op]
    for op in ("offset", "life", "name", "color"):
        if op in ops:
            return _VALIDATOR_FOR_OP[op]
    return "tool_color"


def sort_changes_for_execution(changes: List[ToolChangeItem]) -> List[ToolChangeItem]:
    return sorted(changes, key=lambda c: (_EXEC_ORDER.get(c.operation_type, 99), c.pot_number or 0, c.tool_number or 0))


def pots_needing_preclear_before_assignments(
    changes: List[ToolChangeItem],
    atc_by_pot: Dict[int, int],
) -> List[int]:
    """Return pot numbers that must be cleared before assignment/cap ops in this batch.

    Covers tool moves/swaps: vacate target pots occupied by another tool and source
    pots for tools being assigned elsewhere. Skips pots already slated for delete.
    """
    assignment_ops = [c for c in changes if c.operation_type in ("assignment", "cap")]
    if not assignment_ops or not atc_by_pot:
        return []

    explicit_delete_pots = {
        c.pot_number
        for c in changes
        if c.operation_type == "delete" and c.pot_number is not None
    }

    assignment_targets: Dict[int, Optional[int]] = {}
    cap_targets: set[int] = set()
    for change in assignment_ops:
        pot = change.pot_number
        if pot is None:
            continue
        if change.operation_type == "assignment" and change.tool_number is not None:
            assignment_targets[pot] = change.tool_number
        elif change.operation_type == "cap":
            cap_targets.add(pot)

    pots_to_clear: set[int] = set()

    for pot, new_tool in assignment_targets.items():
        if pot in explicit_delete_pots:
            continue
        current = atc_by_pot.get(pot, 0)
        if current != 0 and current != new_tool:
            pots_to_clear.add(pot)

    for pot in cap_targets:
        if pot in explicit_delete_pots:
            continue
        current = atc_by_pot.get(pot, 0)
        if current > 0 and current not in _CAP_TOOL_NUMBERS:
            pots_to_clear.add(pot)

    tools_being_assigned = {t for t in assignment_targets.values() if t is not None}
    for pot, current_tool in atc_by_pot.items():
        if current_tool not in tools_being_assigned:
            continue
        target_pot = next(
            (p for p, t in assignment_targets.items() if t == current_tool),
            None,
        )
        if target_pot is not None and pot != target_pot and pot not in explicit_delete_pots:
            pots_to_clear.add(pot)

    return sorted(pots_to_clear)


async def _read_atc_pot_map(telnet_client) -> Dict[int, int]:
    """Map magazine pot number → current ATCTL tool number (0 = empty)."""
    from app.parsers.atctl_parser_v2 import parse_atctl_v2

    control = await telnet_client.detect_control_type() or "C00"
    raw = await telnet_client.get_atc_magazine_data(control_version=control, verbose=False)
    if not raw:
        return {}

    parsed = parse_atctl_v2(raw.encode("utf-8"), control_version=control)
    by_pot: Dict[int, int] = {}
    for tool in parsed.get("tools", []):
        pot = tool.get("pot_number")
        if pot is None or str(pot).upper() == "SPINDLE":
            continue
        try:
            by_pot[int(pot)] = int(tool.get("tool_number") or 0)
        except (TypeError, ValueError):
            continue
    return by_pot


async def _preclear_atc_pots(
    telnet_client,
    machine_id: int,
    pots: List[int],
    atc_by_pot: Dict[int, int],
) -> None:
    """CHGMAGD-clear pots before reassignment so targets are not occupied."""
    from app.clients.telnet_client import CNCTelnetClient
    from app.services.audit_logger import AuditLogger

    for pot in pots:
        current = atc_by_pot.get(pot, 0)
        if current == 0:
            continue
        ok, status = await telnet_client.remove_tool_from_pot(
            pot_number=pot,
            tool_number=current if current not in _CAP_TOOL_NUMBERS else None,
            verbose=False,
        )
        status_desc = CNCTelnetClient.get_status_description(status or "00") if not ok else None
        AuditLogger.log_tool_modification(
            machine_id=machine_id,
            operation_type="tool_delete",
            operation_details={"pot_number": pot, "tool_number": current, "preclear": True},
            success=ok,
            error_message=status_desc,
            machine_state=None,
        )
        if not ok:
            raise RuntimeError(f"Failed to pre-clear pot {pot} before assignment: {status_desc or status}")


def validate_change_ranges(change: ToolChangeItem) -> Optional[str]:
    """Return error message if ranges invalid, else None."""
    op = change.operation_type
    if op in ("color", "assignment", "type", "delete", "cap"):
        if change.pot_number is not None and not 1 <= change.pot_number <= 99:
            return f"Invalid pot number: {change.pot_number} (must be 1-99)"
    if op == "color" and change.color is not None and not 0 <= change.color <= 7:
        return f"Invalid color: {change.color} (must be 0-7)"
    if op == "assignment" and change.tool_number is not None and not 1 <= change.tool_number <= 999:
        return f"Invalid tool number: {change.tool_number} (must be 1-999)"
    if op == "type" and change.tool_type is not None and change.tool_type not in (1, 2, 3):
        return f"Invalid tool type: {change.tool_type} (must be 1-3)"
    if op == "spindle" and change.tool_number is not None and not 0 <= change.tool_number <= 999:
        return f"Invalid spindle tool: {change.tool_number} (must be 0-999)"
    if op == "offset":
        if change.tool_number is not None and not 1 <= change.tool_number <= 99:
            return f"Invalid tool number: {change.tool_number} (must be 1-99)"
        if change.offset_type not in ("H", "D", "W"):
            return f"Invalid offset_type: {change.offset_type}"
    if op == "life":
        if change.tool_number is not None and not 1 <= change.tool_number <= 99:
            return f"Invalid tool number: {change.tool_number} (must be 1-99)"
        if change.life_value is not None and not 0 <= change.life_value <= 999999:
            return f"Invalid life value: {change.life_value}"
    if op == "name":
        if change.tool_number is not None and not 1 <= change.tool_number <= 99:
            return f"Invalid tool number: {change.tool_number} (must be 1-99)"
        if change.name_value is not None and len(change.name_value.strip()) > 14:
            return f"Tool name too long: max 14 characters (got {len(change.name_value.strip())})"
    return None


def validate_batch_pot_conflicts(changes: List[ToolChangeItem]) -> Optional[str]:
    """Reject batches that assign the same pot more than once."""
    seen: Dict[int, str] = {}
    for change in changes:
        if change.operation_type not in ("assignment", "cap"):
            continue
        pot = change.pot_number
        if pot is None:
            continue
        if pot in seen:
            return f"Pot {pot} is assigned more than once in this batch ({seen[pot]} and {change.operation_type})"
        seen[pot] = change.operation_type
    return None


def _result_from_change(change: ToolChangeItem, **kwargs: Any) -> ToolChangeResult:
    return ToolChangeResult(
        operation_type=change.operation_type,
        client_id=change.client_id,
        pot_number=change.pot_number,
        tool_number=change.tool_number,
        color=change.color,
        tool_type=change.tool_type,
        offset_type=change.offset_type,
        value=change.value,
        life_value=change.life_value,
        life_type=change.life_type,
        name_value=change.name_value,
        **kwargs,
    )


_CAP_ATC_EMPTY = frozenset({0, 255, 999})


async def _verify_pot_has_tool(
    telnet_client,
    pot_number: int,
    expected_tool: int,
) -> Tuple[bool, Optional[int]]:
    actual = await telnet_client._read_pot_tool_number(pot_number, verbose=False)
    if actual is None:
        return False, None
    return actual == expected_tool, actual


async def _verify_pot_is_empty(telnet_client, pot_number: int) -> Tuple[bool, Optional[int]]:
    actual = await telnet_client._read_pot_tool_number(pot_number, verbose=False)
    if actual is None:
        return False, None
    return actual in _CAP_ATC_EMPTY, actual


async def _apply_single_change(telnet_client, change: ToolChangeItem) -> Tuple[bool, Optional[str], str, Dict[str, Any]]:
    """Execute one change; returns success, status_code, message, audit operation_details."""
    op = change.operation_type
    if op == "color":
        success, status = await telnet_client.change_atc_tool(
            operation_type="C",
            magazine_pos=change.pot_number,
            tool_num=change.tool_number,
            new_value=change.color,
            verbose=False,
        )
        name = COLOR_NAMES.get(change.color or 0, "Unknown")
        details = {
            "pot_number": change.pot_number,
            "tool_number": change.tool_number,
            "new_color": change.color,
            "new_color_name": name,
        }
        msg = f"Tool color changed to {name}" if success else ""
        audit_op = "tool_color"
        return success, status, msg, audit_op, details

    if op == "assignment":
        success, status = await telnet_client.assign_tool_to_pot(
            pot_number=change.pot_number,
            tool_number=change.tool_number,
            verbose=False,
        )
        msg = ""
        if success:
            verified, actual = await _verify_pot_has_tool(
                telnet_client, change.pot_number, change.tool_number
            )
            if not verified:
                success = False
                status = status or "verify"
                msg = (
                    f"Assignment not applied — pot {change.pot_number} shows tool {actual}, "
                    f"expected {change.tool_number}"
                )
            else:
                msg = f"Tool {change.tool_number} assigned to pot {change.pot_number}"
        details = {"pot_number": change.pot_number, "new_tool_number": change.tool_number}
        return success, status, msg, "tool_assignment", details

    if op == "cap":
        success, status = await telnet_client.set_cap_on_pot(
            pot_number=change.pot_number,
            verbose=False,
        )
        details = {"pot_number": change.pot_number}
        msg = f"Cap set on pot {change.pot_number}" if success else ""
        return success, status, msg, "tool_assignment", details

    if op == "type":
        success, status = await telnet_client.change_tool_type(
            pot_number=change.pot_number,
            tool_type=change.tool_type,
            verbose=False,
        )
        tname = TOOL_TYPE_NAMES.get(change.tool_type or 0, "Unknown")
        details = {
            "pot_number": change.pot_number,
            "new_tool_type": change.tool_type,
            "new_tool_type_name": tname,
        }
        msg = f"Tool type changed to {tname}" if success else ""
        return success, status, msg, "tool_type", details

    if op == "delete":
        success, status = await telnet_client.remove_tool_from_pot(
            pot_number=change.pot_number,
            tool_number=change.tool_number,
            verbose=False,
        )
        msg = ""
        if success:
            verified, actual = await _verify_pot_is_empty(telnet_client, change.pot_number)
            if not verified:
                success = False
                status = status or "verify"
                msg = f"Pot {change.pot_number} still contains tool {actual}"
            else:
                msg = f"Tool removed from pot {change.pot_number}"
        details = {"pot_number": change.pot_number, "tool_number": change.tool_number}
        return success, status, msg, "tool_delete", details

    if op == "spindle":
        success, status = await telnet_client.change_spindle_tool(
            tool_number=change.tool_number,
            verbose=False,
        )
        details = {"new_tool_number": change.tool_number}
        msg = f"Spindle tool set to {change.tool_number}" if success else ""
        return success, status, msg, "spindle_tool", details

    if op == "offset":
        success, status = await telnet_client.write_tool_offset(
            tool_number=change.tool_number,
            offset_type=change.offset_type,
            value=change.value,
            verbose=False,
        )
        oname = OFFSET_NAMES.get(change.offset_type or "", "Unknown")
        details = {
            "tool_number": change.tool_number,
            "offset_type": change.offset_type,
            "offset_type_name": oname,
            "new_value": change.value,
        }
        msg = f"Tool {change.tool_number} {oname} offset set to {change.value}" if success else ""
        return success, status, msg, "tool_offset", details

    if op == "life":
        life_type = change.life_type or "TIME"
        success, status = await telnet_client.write_tool_life(
            tool_number=change.tool_number,
            life_value=change.life_value,
            life_type=life_type,
            verbose=False,
        )
        details = {
            "tool_number": change.tool_number,
            "new_life_value": change.life_value,
            "life_type": life_type,
        }
        msg = f"Tool {change.tool_number} life set to {change.life_value}" if success else ""
        return success, status, msg, "tool_life", details

    return False, "01", "Unknown operation", "tool_color", {}


async def _apply_name_changes_batch(
    db_machine: Machine,
    machine_id: int,
    changes: List[ToolChangeItem],
    telnet_client,
) -> List[ToolChangeResult]:
    """Apply one or more name changes via a single TOLN FTP upload."""
    from app.services.audit_logger import AuditLogger
    from app.services.tool_name_write_service import write_tool_names_via_ftp
    from app.services.tolni_patch import normalize_tool_name

    updates = {c.tool_number: c.name_value or "" for c in changes if c.tool_number is not None}
    results: List[ToolChangeResult] = []

    try:
        old_names, verified = await write_tool_names_via_ftp(
            db_machine,
            updates,
            telnet_client=telnet_client,
        )
        for change in changes:
            tn = change.tool_number or 0
            new_name = normalize_tool_name(change.name_value or "")
            old_name = normalize_tool_name(old_names.get(tn, ""))
            ok = verified.get(tn, False)
            details = {
                "tool_number": tn,
                "old_name": old_name,
                "new_name": new_name,
            }
            msg = f"Tool {tn} name set to {new_name!r}" if ok else f"Tool {tn} name verify failed after upload"
            AuditLogger.log_tool_modification(
                machine_id=machine_id,
                operation_type="tool_name",
                operation_details=details,
                success=ok,
                error_message=None if ok else msg,
                machine_state=None,
            )
            if ok:
                results.append(_result_from_change(change, success=True, message=msg))
            else:
                results.append(
                    _result_from_change(
                        change,
                        success=False,
                        error_code="verify_failed",
                        message=msg,
                    )
                )
    except Exception as exc:
        logger.error("Tool name FTP write failed: %s", exc)
        for change in changes:
            AuditLogger.log_tool_modification(
                machine_id=machine_id,
                operation_type="tool_name",
                operation_details={
                    "tool_number": change.tool_number,
                    "new_name": normalize_tool_name(change.name_value or ""),
                },
                success=False,
                error_message=str(exc),
                machine_state=None,
            )
            results.append(
                _result_from_change(
                    change,
                    success=False,
                    error_code="ftp_error",
                    message=str(exc),
                )
            )

    return results


async def apply_tool_changes_batch(
    db_machine: Machine,
    machine_id: int,
    changes: List[ToolChangeItem],
    db: Session,
) -> BatchToolChangesResponse:
    from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
    from app.services.audit_logger import AuditLogger
    from app.services.machine_state_validator import MachineStateValidator

    for change in changes:
        err = validate_change_ranges(change)
        if err:
            raise ValueError(err)

    batch_err = validate_batch_pot_conflicts(changes)
    if batch_err:
        raise ValueError(batch_err)

    validator = MachineStateValidator()
    val_op = validation_operation_type(changes)
    is_safe, error_message, _status_data = await validator.validate_safe_for_write(
        machine_id=machine_id,
        operation_type=val_op,
        db=db,
    )
    if not is_safe:
        raise PermissionError(error_message or "Machine is not in a safe state for this operation")

    ordered = sort_changes_for_execution(changes)
    telnet_changes = [c for c in ordered if c.operation_type != "name"]
    name_changes = [c for c in ordered if c.operation_type == "name"]
    results: List[ToolChangeResult] = []
    successful = 0
    failed = 0

    telnet_client = None
    try:
        if telnet_changes:
            telnet_client = await create_fresh_connection(
                ip_address=db_machine.ip_address,
                port=10000,
                timeout=10,
            )

            if any(c.operation_type in ("assignment", "cap") for c in telnet_changes):
                atc_by_pot = await _read_atc_pot_map(telnet_client)
                preclear_pots = pots_needing_preclear_before_assignments(changes, atc_by_pot)
                if preclear_pots:
                    logger.info(
                        "Pre-clearing ATC pots %s before batch assignments (machine %s)",
                        preclear_pots,
                        machine_id,
                    )
                    await _preclear_atc_pots(
                        telnet_client, machine_id, preclear_pots, atc_by_pot
                    )

            for change in telnet_changes:
                try:
                    success, status_code, msg, audit_op, details = await _apply_single_change(
                        telnet_client, change
                    )
                    status_desc = (
                        CNCTelnetClient.get_status_description(status_code or "00") if not success else None
                    )
                    AuditLogger.log_tool_modification(
                        machine_id=machine_id,
                        operation_type=audit_op,
                        operation_details=details,
                        success=success,
                        error_message=status_desc,
                        machine_state=None,
                    )
                    if success:
                        results.append(_result_from_change(change, success=True, message=msg))
                        successful += 1
                    else:
                        error_msg = status_desc or f"Failed with status code {status_code}"
                        results.append(
                            _result_from_change(
                                change,
                                success=False,
                                error_code=status_code or "unknown",
                                message=error_msg,
                            )
                        )
                        failed += 1
                except Exception as exc:
                    results.append(
                        _result_from_change(
                            change,
                            success=False,
                            error_code="exception",
                            message=str(exc),
                        )
                    )
                    failed += 1
                    logger.error("Exception applying tool change %s: %s", change.operation_type, exc)

        if name_changes:
            if telnet_client is None:
                telnet_client = await create_fresh_connection(
                    ip_address=db_machine.ip_address,
                    port=10000,
                    timeout=10,
                )
            name_results = await _apply_name_changes_batch(
                db_machine, machine_id, name_changes, telnet_client
            )
            for result in name_results:
                results.append(result)
                if result.success:
                    successful += 1
                else:
                    failed += 1

    finally:
        if telnet_client:
            await telnet_client.disconnect()

    return BatchToolChangesResponse(
        results=results,
        total=len(changes),
        successful=successful,
        failed=failed,
    )


async def apply_tool_changes_batch_with_refresh(
    db_machine: Machine,
    machine_id: int,
    changes: List[ToolChangeItem],
    db: Session,
) -> BatchToolChangesResponse:
    """Apply batch and refresh tool data when any item succeeds."""
    import app.api._status_state as _state

    response = await apply_tool_changes_batch(db_machine, machine_id, changes, db)
    if response.successful > 0 and _state.polling_service:
        try:
            await _state.polling_service.refresh_tool_data(machine_id)
            logger.debug(
                "Refreshed tool data for machine %s after batch tool changes (%s successful)",
                machine_id,
                response.successful,
            )
        except Exception as exc:
            logger.warning(
                "Failed to refresh tool data after batch tool changes for machine %s: %s",
                machine_id,
                exc,
            )
    return response


async def apply_color_changes_batch(
    db_machine: Machine,
    machine_id: int,
    color_changes: List[ColorChangeRequest],
    db: Session,
) -> List[ColorChangeResult]:
    """Legacy color-only batch; delegates to unified batch orchestrator."""
    items = [
        ToolChangeItem(
            operation_type="color",
            pot_number=c.pot_number,
            tool_number=c.tool_number,
            color=c.color,
        )
        for c in color_changes
    ]
    batch = await apply_tool_changes_batch_with_refresh(db_machine, machine_id, items, db)
    return [
        ColorChangeResult(
            pot_number=r.pot_number or 0,
            tool_number=r.tool_number or 0,
            color=r.color or 0,
            success=r.success,
            error_code=r.error_code,
            message=r.message,
        )
        for r in batch.results
    ]
