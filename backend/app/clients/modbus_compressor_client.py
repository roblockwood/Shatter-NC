"""Async Modbus TCP reads for Kaeser / SIGMA CONTROL 2 compressors."""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from app.integrations.kaeser_sc2.process_map_registers import (
    MVP_HOLDING_PDU_START,
    MVP_HOLDING_REGISTER_COUNT,
    MVP_INPUT_PDU_START,
    MVP_INPUT_REGISTER_COUNT,
)

logger = logging.getLogger(__name__)


async def read_sc2_mvp_registers(
    host: str,
    port: int,
    unit_id: int,
    timeout_seconds: float = 8.0,
) -> Tuple[Optional[List[int]], Optional[List[int]], Optional[str]]:
    """
    Read MVP holding and input register blocks. Returns (holding, input, error_message).
    On failure, returns (None, None, error string).
    """
    try:
        from pymodbus.client import AsyncModbusTcpClient
    except ImportError:
        return None, None, "pymodbus is not installed"

    client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout_seconds)
    try:
        connected = await client.connect()
        if not connected:
            return None, None, "Modbus TCP connect failed"

        holding: Optional[List[int]] = None
        input_regs: Optional[List[int]] = None

        hr = await client.read_holding_registers(
            address=MVP_HOLDING_PDU_START,
            count=MVP_HOLDING_REGISTER_COUNT,
            slave=unit_id,
        )
        if hr.isError():
            logger.warning("read_holding_registers error: %s", hr)
            return None, None, f"read_holding_registers failed: {hr}"

        holding = list(hr.registers)

        ir = await client.read_input_registers(
            address=MVP_INPUT_PDU_START,
            count=MVP_INPUT_REGISTER_COUNT,
            slave=unit_id,
        )
        if ir.isError():
            logger.warning("read_input_registers error: %s", ir)
            return holding, None, f"read_input_registers failed: {ir}"

        input_regs = list(ir.registers)
        return holding, input_regs, None
    except Exception as e:
        logger.exception("Modbus TCP error for %s:%s", host, port)
        return None, None, str(e)
    finally:
        try:
            client.close()
        except Exception:
            pass
