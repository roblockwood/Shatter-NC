"""Heidenhain TNC OPC UA client (Core Information Model)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.controllers.heidenhain import browse_paths as bp
from app.controllers.heidenhain.endpoint import (
    DEFAULT_HEIDENHAIN_ENDPOINT_PATH,
    build_endpoint_url,
    resolve_endpoint_url,
)
from app.controllers.heidenhain.status_mapping import derive_status

logger = logging.getLogger(__name__)

HEIDENHAIN_NAMESPACE_URIS = (
    "http://heidenhain.com/UA/",
    "http://heidenhain.com/UA/NC/",
    "http://www.heidenhain.de/UA/",
    "http://www.heidenhain.de/UA/NC/",
)


class HeidenhainOpcUaClient:
    """Persistent OPC UA session for Heidenhain NC Server reads."""

    def __init__(
        self,
        ip_address: str,
        port: int = 4840,
        username: Optional[str] = None,
        password: Optional[str] = None,
        channel: str = "0",
        timeout: float = 10.0,
        endpoint_url: Optional[str] = None,
        endpoint_path: Optional[str] = None,
        auto_discover_endpoint: bool = True,
    ):
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.channel = str(channel)
        self.timeout = timeout
        self._endpoint_url_config = endpoint_url
        self._endpoint_path_config = endpoint_path
        self._auto_discover_endpoint = auto_discover_endpoint
        self._resolved_endpoint_url: Optional[str] = None
        self._client = None
        self._machine_node = None
        self._ns_index: Optional[int] = None

    @property
    def endpoint_url(self) -> str:
        if self._resolved_endpoint_url:
            return self._resolved_endpoint_url
        if self._endpoint_url_config:
            return self._endpoint_url_config.strip()
        path = (
            self._endpoint_path_config
            if self._endpoint_path_config is not None
            else DEFAULT_HEIDENHAIN_ENDPOINT_PATH
        )
        return build_endpoint_url(self.ip_address, self.port, path)

    async def _ensure_endpoint_url(self) -> str:
        if self._resolved_endpoint_url:
            return self._resolved_endpoint_url
        self._resolved_endpoint_url = await resolve_endpoint_url(
            self.ip_address,
            self.port,
            endpoint_url=self._endpoint_url_config,
            endpoint_path=self._endpoint_path_config,
            auto_discover=self._auto_discover_endpoint,
            timeout=self.timeout,
        )
        return self._resolved_endpoint_url

    async def connect(self) -> None:
        from asyncua import Client

        if self._client is not None:
            return

        connect_url = await self._ensure_endpoint_url()

        logger.info(
            "OPC UA connecting to %s (user=%s, channel=%s, timeout=%ss)",
            connect_url,
            self.username or "(anonymous)",
            self.channel,
            self.timeout,
        )

        client = Client(url=connect_url, timeout=self.timeout)
        if self.username:
            client.set_user(self.username)
        if self.password:
            client.set_password(self.password)

        try:
            await client.connect()
        except asyncio.TimeoutError as exc:
            raise ConnectionError(
                f"OPC UA connect timed out after {self.timeout}s at {connect_url}"
            ) from exc
        except Exception as exc:
            logger.warning(
                "OPC UA connect failed for %s: %s: %s",
                connect_url,
                type(exc).__name__,
                exc or "(no message)",
            )
            raise

        self._client = client
        self._machine_node = await self._resolve_machine_node()
        if self._machine_node is None:
            await self.disconnect()
            raise ConnectionError(
                f"Could not find Machine object on OPC UA server at {connect_url}"
            )

        logger.info("OPC UA connected to %s (Machine node resolved)", connect_url)

    async def disconnect(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._client = None
        self._machine_node = None
        self._ns_index = None
        self._resolved_endpoint_url = None

    async def _resolve_machine_node(self):
        client = self._client
        assert client is not None

        for uri in HEIDENHAIN_NAMESPACE_URIS:
            try:
                ns = await client.get_namespace_index(uri)
                self._ns_index = ns
                node = await client.nodes.objects.get_child([f"{ns}:{bp.MACHINE}"])
                logger.debug("Resolved Machine node via namespace %s (index %s)", uri, ns)
                return node
            except Exception as exc:
                logger.debug("Namespace %s failed for Machine node: %s: %s", uri, type(exc).__name__, exc)
                continue

        # Fallback: search Objects children by BrowseName
        try:
            children = await client.nodes.objects.get_children()
            for child in children:
                browse_name = await child.read_browse_name()
                if browse_name.Name == bp.MACHINE:
                    return child
        except Exception as exc:
            logger.debug("Browse fallback for Machine node failed: %s", exc)

        return None

    async def _get_child(self, parent, name: str):
        ns = self._ns_index
        if ns is not None:
            try:
                return await parent.get_child([f"{ns}:{name}"])
            except Exception:
                pass
        children = await parent.get_children()
        for child in children:
            browse_name = await child.read_browse_name()
            if browse_name.Name == name:
                return child
        raise KeyError(f"Child node '{name}' not found")

    async def _read_state_name(self, state_node) -> Optional[str]:
        try:
            current = await self._get_child(state_node, bp.NC_STATE_CURRENT)
            value = await current.read_value()
            if isinstance(value, dict):
                return value.get("Id") or value.get("Name")
            if hasattr(value, "Name"):
                return value.Name
            if hasattr(value, "Text"):
                return value.Text
            return str(value) if value is not None else None
        except Exception as exc:
            logger.debug("Failed to read state name: %s", exc)
            return None

    async def _read_program_name(self, channel_node) -> str:
        try:
            program = await self._get_child(channel_node, bp.PROGRAM)
            name_node = await self._get_child(program, bp.PROGRAM_NAME)
            value = await name_node.read_value()
            if value is None:
                return "----"
            text = str(value).strip()
            return text or "----"
        except Exception as exc:
            logger.debug("Failed to read program name: %s", exc)
            return "----"

    async def _read_operating_mode(self, channel_node) -> Optional[str]:
        try:
            mode_node = await self._get_child(channel_node, bp.OPERATING_MODE)
            value = await mode_node.read_value()
            if value is None:
                return None
            if hasattr(value, "name"):
                return value.name
            if hasattr(value, "Name"):
                return value.Name
            return str(value)
        except Exception:
            return None

    async def _read_alarms(self) -> List[Dict[str, Any]]:
        alarms: List[Dict[str, Any]] = []
        try:
            errors = await self._get_child(self._machine_node, bp.ERRORS)
            active = await self._get_child(errors, bp.ALL_ACTIVE_ERRORS)
            entries = await active.get_children()
            for entry in entries:
                alarm = await self._read_error_entry(entry)
                if alarm:
                    alarms.append(alarm)
        except Exception as exc:
            logger.debug("Failed to read alarms: %s", exc)
        return alarms

    async def _read_error_entry(self, entry_node) -> Optional[Dict[str, Any]]:
        try:
            props = await entry_node.get_children()
            data: Dict[str, Any] = {}
            for prop in props:
                browse_name = await prop.read_browse_name()
                try:
                    data[browse_name.Name] = await prop.read_value()
                except Exception:
                    continue

            message = data.get("Message") or data.get("Text") or data.get("Name")
            if not message and not data:
                return None

            code = data.get("Number") or data.get("Code") or data.get("Id")
            severity = data.get("Class") or data.get("Severity")
            return {
                "code": str(code) if code is not None else "",
                "message": str(message) if message is not None else "",
                "severity": str(severity) if severity is not None else "",
                "stop_level": 5 if str(severity) in ("Error", "EmergencyStop", "ProgramAbort") else 1,
                "source": "heidenhain",
            }
        except Exception:
            return None

    async def read_monitor_snapshot(self) -> Dict[str, Any]:
        """Read fast-poll monitoring data from the connected OPC UA server."""
        if self._machine_node is None:
            await self.connect()

        try:
            nc_state_node = await self._get_child(self._machine_node, bp.NC_STATE)
            nc_state = await self._read_state_name(nc_state_node)

            channels = await self._get_child(self._machine_node, bp.CHANNELS)
            channel_node = await self._get_child(channels, self.channel)

            program = await self._get_child(channel_node, bp.PROGRAM)
            exec_state_node = await self._get_child(program, bp.EXECUTION_STATE)
            exec_state = await self._read_state_name(exec_state_node)

            program_name = await self._read_program_name(channel_node)
            operating_mode = await self._read_operating_mode(channel_node)
            alarms = await self._read_alarms()

            has_errors = len(alarms) > 0
            status = derive_status(nc_state, exec_state, has_errors=has_errors)

            return {
                "status": status,
                "program_name": program_name,
                "alarms": alarms,
                "vendor_data": {
                    "nc_state": nc_state,
                    "exec_state": exec_state,
                    "operating_mode": operating_mode,
                },
            }
        except Exception as exc:
            logger.warning(
                "OPC UA read failed for %s channel %s: %s: %s",
                self.endpoint_url,
                self.channel,
                type(exc).__name__,
                exc or "(no message)",
            )
            raise

    async def test_connection(self) -> Dict[str, Any]:
        from datetime import datetime

        start = datetime.now()
        try:
            await self.connect()
            nc_state_node = await self._get_child(self._machine_node, bp.NC_STATE)
            nc_state = await self._read_state_name(nc_state_node)
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            return {
                "success": True,
                "latency_ms": round(latency_ms, 2),
                "nc_state": nc_state,
                "endpoint_url": self.endpoint_url,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            error = str(exc).strip() or type(exc).__name__
            logger.warning(
                "OPC UA test_connection failed for %s: %s",
                self.endpoint_url,
                error,
            )
            return {
                "success": False,
                "latency_ms": round(latency_ms, 2),
                "error": error,
                "error_type": type(exc).__name__,
                "endpoint_url": self.endpoint_url,
                "timestamp": datetime.now().isoformat(),
            }
