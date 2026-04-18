"""Normalize MONTR `operation_program_no` for machine status payloads."""
from typing import Any, Dict, Optional


def meaningful_montr_operation_program_no(program_info: Dict[str, Any]) -> Optional[str]:
    """
    Return active O-number from MONTR program_info, or None if absent / idle placeholder.

    MONTR often omits operation_program_no on transient reads; callers should merge from cache
    instead of broadcasting '----' which would clobber a known-good program name.
    """
    raw = program_info.get("operation_program_no")
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s == "----":
        return None
    return s


def is_placeholder_machine_program_name(value: Any) -> bool:
    """True for values that should not replace a previously known-good program name."""
    if value is None:
        return True
    if isinstance(value, str):
        t = value.strip()
        return t == "" or t == "----"
    return False


def is_meaningful_machine_program_name(value: Any) -> bool:
    return not is_placeholder_machine_program_name(value)
