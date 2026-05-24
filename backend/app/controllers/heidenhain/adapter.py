"""Heidenhain OPC UA controller adapter."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set

from app.controllers.base import HEIDENHAIN_V1_CAPABILITIES
from app.controllers.heidenhain.opcua_client import HeidenhainOpcUaClient
from app.models.machine import Machine

logger = logging.getLogger(__name__)


def _config_value(machine: Machine, key: str, default: Any = None) -> Any:
    config = getattr(machine, "controller_config", None) or {}
    if isinstance(config, dict):
        return config.get(key, default)
    return default


class HeidenhainOpcUaAdapter:
    """Collects Heidenhain TNC data via OPC UA NC Server."""

    def __init__(self, machine: Machine):
        self.machine = machine
        self._client: Optional[HeidenhainOpcUaClient] = None

    def capabilities(self) -> Set[str]:
        return set(HEIDENHAIN_V1_CAPABILITIES)

    def _build_client(self) -> HeidenhainOpcUaClient:
        return HeidenhainOpcUaClient(
            ip_address=self.machine.ip_address,
            port=int(_config_value(self.machine, "opcua_port", 4840)),
            username=_config_value(self.machine, "opcua_username"),
            password=_config_value(self.machine, "opcua_password"),
            channel=str(_config_value(self.machine, "channel", "0")),
            timeout=10.0,
            endpoint_url=_config_value(self.machine, "opcua_endpoint_url"),
            endpoint_path=_config_value(self.machine, "opcua_endpoint_path"),
            auto_discover_endpoint=_config_value(self.machine, "opcua_auto_discover", True),
        )

    async def _ensure_client(self) -> HeidenhainOpcUaClient:
        if self._client is None:
            self._client = self._build_client()
        try:
            await self._client.connect()
        except Exception as first_exc:
            logger.warning(
                "Heidenhain OPC UA connect failed for machine %s (%s), retrying: %s",
                self.machine.id,
                self.machine.name,
                first_exc or type(first_exc).__name__,
            )
            await self.close()
            self._client = self._build_client()
            await self._client.connect()
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def test_connection(self) -> Dict[str, Any]:
        client = self._build_client()
        try:
            return await client.test_connection()
        finally:
            await client.disconnect()

    async def poll_slow(self, *, skip_if_operating: bool = False) -> Optional[Dict[str, Any]]:
        return None

    async def poll_fast(self, *, ws_tool_cache: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = await self._ensure_client()
        snapshot = await client.read_monitor_snapshot()

        return {
            "ip_address": self.machine.ip_address,
            "timestamp": datetime.now().isoformat(),
            "units": self.machine.units,
            "program_name": snapshot.get("program_name", "----"),
            "status": snapshot.get("status", "standby"),
            "alarms": snapshot.get("alarms", []),
            "controller_type": "heidenhain",
            "vendor_data": snapshot.get("vendor_data", {}),
        }
