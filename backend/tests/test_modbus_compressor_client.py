"""Mocked Modbus TCP read path (no real hardware or listener)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_read_sc2_mvp_registers_success():
    mock_hr = MagicMock()
    mock_hr.isError.return_value = False
    mock_hr.registers = list(range(32))
    mock_ir = MagicMock()
    mock_ir.isError.return_value = False
    mock_ir.registers = list(range(100, 132))

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.read_holding_registers = AsyncMock(return_value=mock_hr)
    mock_client.read_input_registers = AsyncMock(return_value=mock_ir)
    mock_client.close = MagicMock()

    with patch("pymodbus.client.AsyncModbusTcpClient", return_value=mock_client):
        from app.clients.modbus_compressor_client import read_sc2_mvp_registers

        holding, input_regs, err = await read_sc2_mvp_registers("127.0.0.1", 502, 1)
        assert err is None
        assert holding is not None and len(holding) == 32
        assert input_regs is not None and len(input_regs) == 32
        mock_client.close.assert_called()


@pytest.mark.asyncio
async def test_read_sc2_mvp_registers_connect_failed():
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()

    with patch("pymodbus.client.AsyncModbusTcpClient", return_value=mock_client):
        from app.clients.modbus_compressor_client import read_sc2_mvp_registers

        holding, input_regs, err = await read_sc2_mvp_registers("127.0.0.1", 502, 1)
        assert holding is None and input_regs is None
        assert err == "Modbus TCP connect failed"
