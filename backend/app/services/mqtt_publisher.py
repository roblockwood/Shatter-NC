"""Optional MQTT publisher (retained snapshots) for telemetry fanout.

This is intentionally best-effort: Shatter must continue to function when the broker
is unavailable or not configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MqttPublishStatus:
    enabled: bool
    configured: bool
    connected: bool
    last_error: Optional[str]
    last_publish_at: Optional[str]


class MqttPublisher:
    def __init__(self) -> None:
        self._client: Any | None = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._last_error: str | None = None
        self._last_publish_at: str | None = None

    def configured(self) -> bool:
        return bool(settings.MQTT_PUBLISH_HOST and settings.MQTT_PUBLISH_HOST.strip())

    def enabled(self) -> bool:
        return self.configured()

    def status(self) -> MqttPublishStatus:
        return MqttPublishStatus(
            enabled=self.enabled(),
            configured=self.configured(),
            connected=self._connected if self.enabled() else False,
            last_error=self._last_error,
            last_publish_at=self._last_publish_at,
        )

    async def start(self) -> None:
        # Lazy connect on first publish; keep start as a no-op so startup doesn't block.
        return

    async def stop(self) -> None:
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.__aexit__(None, None, None)
                except Exception:
                    pass
            self._client = None
            self._connected = False

    async def _ensure_connected(self) -> Any | None:
        if not self.enabled():
            return None

        async with self._lock:
            if self._client is not None and self._connected:
                return self._client

            try:
                from aiomqtt import Client
            except Exception as e:
                self._last_error = f"aiomqtt import failed: {e}"
                logger.warning(self._last_error)
                return None

            try:
                host = (settings.MQTT_PUBLISH_HOST or "").strip()
                port = settings.MQTT_PUBLISH_PORT
                username = settings.MQTT_PUBLISH_USERNAME or None
                password = settings.MQTT_PUBLISH_PASSWORD or None

                client = Client(hostname=host, port=port, username=username, password=password)
                await client.__aenter__()
                self._client = client
                self._connected = True
                self._last_error = None
                logger.info("MQTT publisher connected %s:%s", host, port)
                return client
            except Exception as e:
                self._connected = False
                self._client = None
                self._last_error = str(e)
                logger.warning("MQTT publisher connect failed: %s", e)
                return None

    async def publish_json(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        retain: bool = True,
        qos: int = 1,
    ) -> None:
        client = await self._ensure_connected()
        if client is None:
            return

        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        try:
            await client.publish(topic, body, qos=qos, retain=retain)
            self._last_publish_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            # Best-effort: record error and drop connection so next publish reconnects.
            self._last_error = str(e)
            logger.debug("MQTT publish failed topic=%s err=%s", topic, e)
            async with self._lock:
                try:
                    if self._client is not None:
                        await self._client.__aexit__(None, None, None)
                except Exception:
                    pass
                self._client = None
                self._connected = False

