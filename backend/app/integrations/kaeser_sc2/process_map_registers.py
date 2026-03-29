"""
MVP Modbus read blocks for SIGMA CONTROL 2 (Process Map 7_7601_PA_27E, software >= 6.4.1).

PDU addresses are 0-based (pymodbus). Validate and adjust against your machine's options
and the official process map before relying on decoded process values in production.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Holding registers (function 03) — first block for raw telemetry / commissioning.
# Replace start/count after validating against the process map for your compressor model.
MVP_HOLDING_PDU_START: int = 0
MVP_HOLDING_REGISTER_COUNT: int = 32

# Input registers (function 04)
MVP_INPUT_PDU_START: int = 0
MVP_INPUT_REGISTER_COUNT: int = 32


def registers_to_dict(regs: Optional[List[int]], prefix: str) -> Dict[str, Any]:
    """Serialize register list for API/WS (compact)."""
    if regs is None:
        return {}
    return {f"{prefix}_{i}": v for i, v in enumerate(regs)}


def build_mvp_metrics(
    holding: Optional[List[int]],
    input_regs: Optional[List[int]],
    modbus_error: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if holding is not None:
        out["holding_registers"] = holding
    if input_regs is not None:
        out["input_registers"] = input_regs
    if modbus_error:
        out["modbus_error"] = modbus_error
    return out


def infer_operational_status(
    is_online: bool,
    holding: Optional[List[int]],
    input_regs: Optional[List[int]],
) -> str:
    """
    High-level status until process-map decoding is fully wired.
    - offline: no Modbus connectivity
    - online: successful read; sub-states (load/idle/standby) come from mapped registers later
    """
    if not is_online:
        return "offline"
    return "online"


def map_alarms_for_ui(holding: Optional[List[int]], input_regs: Optional[List[int]]) -> List[Dict[str, Any]]:
    """
    Placeholder: return empty alarms until warning/alarm words are mapped from the process map.
    AlarmPane expects { code, message, ... }.
    """
    return []
