"""Merge MQTT + REST data from kaeser-sc2-api sidecars; dispatch WebSocket updates."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

from app.clients.kaeser_sidecar_rest import fetch_maintenance_bundle
from app.core.config import settings
from app.integrations.kaeser_sc2.sidecar_mapper import build_compressor_status_payload, infer_status
from app.services.compressor_status_sample_writer import record_compressor_status_sample_throttled
from app.services.compressor_telemetry_sample import telemetry_fields_from_operational

if TYPE_CHECKING:
    from app.models.compressor import Compressor
    from app.services.websocket import WebSocketManager

logger = logging.getLogger(__name__)


@dataclass
class _CompressorSidecarState:
    operational: Optional[Dict[str, Any]] = None
    rest_bundle: Optional[Dict[str, Any]] = None
    rest_error: Optional[str] = None
    sidecar_mqtt_online: Optional[bool] = None
    last_operational_mqtt_at: Optional[datetime] = None
    last_rest_at: Optional[datetime] = None


class KaeserSidecarBridge:
    """Per-compressor state from MQTT; periodic REST enrichment; thread-safe async updates."""

    def __init__(self, websocket_manager: "WebSocketManager"):
        self._ws = websocket_manager
        self._lock = asyncio.Lock()
        self._states: Dict[int, _CompressorSidecarState] = {}
        self._root_to_id: Dict[str, int] = {}
        self._compressors: Dict[int, "Compressor"] = {}
        self._http: Optional[httpx.AsyncClient] = None
        self._mqtt_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._http = httpx.AsyncClient()
        host = settings.MQTT_BROKER_HOST
        if host:
            self._mqtt_task = asyncio.create_task(self._mqtt_loop(), name="compressor-mqtt")
            logger.info("Compressor MQTT subscriber starting (broker=%s:%s)", host, settings.MQTT_BROKER_PORT)
        else:
            logger.info("MQTT_BROKER_HOST unset — compressor status via REST only")

    async def stop(self) -> None:
        self._running = False
        if self._mqtt_task:
            self._mqtt_task.cancel()
            try:
                await self._mqtt_task
            except asyncio.CancelledError:
                pass
            self._mqtt_task = None
        if self._http:
            await self._http.aclose()
            self._http = None

    def sync_compressors(self, compressors: List["Compressor"]) -> None:
        self._compressors = {c.id: c for c in compressors}
        self._root_to_id = {c.mqtt_topic_root.strip(): c.id for c in compressors if c.mqtt_topic_root}

    async def refresh_rest(self, compressor: "Compressor") -> None:
        if not self._http:
            return
        bundle, err = await fetch_maintenance_bundle(compressor.sidecar_rest_base_url, self._http)
        async with self._lock:
            st = self._states.setdefault(compressor.id, _CompressorSidecarState())
            st.last_rest_at = datetime.now(timezone.utc)
            st.rest_error = err
            if bundle is not None:
                st.rest_bundle = bundle
                op = bundle.get("operational")
                if isinstance(op, dict):
                    st.operational = op

    async def build_status(
        self,
        compressor: "Compressor",
        poll_timestamp: datetime,
        response_time_ms: int,
    ) -> Dict[str, Any]:
        async with self._lock:
            st = self._states.setdefault(compressor.id, _CompressorSidecarState())
            payload = build_compressor_status_payload(
                compressor_id=compressor.id,
                compressor_name=compressor.name,
                ip_address=compressor.ip_address,
                enabled=compressor.enabled,
                poll_interval_seconds=compressor.poll_interval_seconds,
                sidecar_rest_base_url=compressor.sidecar_rest_base_url,
                mqtt_topic_root=compressor.mqtt_topic_root,
                operational=st.operational,
                rest_bundle=st.rest_bundle,
                rest_error=st.rest_error,
                last_operational_mqtt_at=st.last_operational_mqtt_at,
                poll_timestamp=poll_timestamp,
                response_time_ms=response_time_ms,
            )
            if st.sidecar_mqtt_online is not None:
                payload.setdefault("metrics", {})["sidecar_mqtt_session"] = (
                    "online" if st.sidecar_mqtt_online else "offline"
                )
            return payload

    async def _handle_mqtt_payload(self, topic_str: str, payload: bytes) -> None:
        parts = topic_str.split("/")
        if len(parts) < 2:
            return
        root, sub = parts[0], parts[1]
        cid = self._root_to_id.get(root)
        if cid is None:
            return
        try:
            body = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("Ignoring non-JSON MQTT message topic=%s", topic_str)
            return

        async with self._lock:
            st = self._states.setdefault(cid, _CompressorSidecarState())
            if sub == "status":
                state = body.get("state") if isinstance(body, dict) else None
                st.sidecar_mqtt_online = state == "online"
                return
            if sub == "operational-data":
                inner: Optional[Dict[str, Any]] = None
                if isinstance(body, dict):
                    if "operational-data" in body and isinstance(body["operational-data"], dict):
                        inner = body["operational-data"]
                    elif "compressorState" in body or "powerState" in body:
                        # Alternate publishers: flat operational object
                        inner = body
                if inner is not None:
                    st.operational = inner
                    st.last_operational_mqtt_at = datetime.now(timezone.utc)
                    led_part = (st.rest_bundle or {}).get("led_data") if st.rest_bundle else None
                    asyncio.create_task(
                        self._maybe_record_mqtt_sample(cid, inner, led_part),
                        name=f"compressor-sample-{cid}",
                    )
            # Other subtopics update rest_bundle slices for UI metrics (optional merge)
            elif sub == "maintenance-timers" and isinstance(body, dict):
                if st.rest_bundle is None:
                    st.rest_bundle = {}
                st.rest_bundle["maintence"] = body.get("maintenance-timers", body)
            elif sub == "messages" and isinstance(body, dict):
                if st.rest_bundle is None:
                    st.rest_bundle = {}
                st.rest_bundle["messages"] = body.get("messages", body)
            elif sub == "operating-hours" and isinstance(body, dict):
                if st.rest_bundle is None:
                    st.rest_bundle = {}
                st.rest_bundle["operatingHours"] = body.get("operating-hours", body)
            elif sub == "led-data" and isinstance(body, dict):
                if st.rest_bundle is None:
                    st.rest_bundle = {}
                st.rest_bundle["led_data"] = body.get("led-data", body)
                if st.operational is not None:
                    ld = st.rest_bundle.get("led_data")
                    asyncio.create_task(
                        self._maybe_record_mqtt_sample(cid, st.operational, ld),
                        name=f"compressor-sample-{cid}-led",
                    )

        comp = self._compressors.get(cid)
        if comp and sub == "operational-data":
            t0 = datetime.now(timezone.utc)
            payload_out = await self.build_status(comp, t0, 0)
            await self._ws.broadcast_compressor_status(payload_out)
        elif comp and sub == "led-data":
            t0 = datetime.now(timezone.utc)
            payload_out = await self.build_status(comp, t0, 0)
            if payload_out.get("is_online"):
                await self._ws.broadcast_compressor_status(payload_out)

    async def _maybe_record_mqtt_sample(
        self,
        compressor_id: int,
        operational: Dict[str, Any],
        led_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        status = infer_status(operational, led_data)
        metrics: Dict[str, Any] = {
            "source": "mqtt",
            "powerState": operational.get("powerState"),
            "compressorState": operational.get("compressorState"),
        }
        if isinstance(led_data, dict):
            inner = led_data.get("led-data") if isinstance(led_data.get("led-data"), dict) else led_data
            if isinstance(inner, dict):
                metrics["led_load"] = inner.get("load")
                metrics["led_idle"] = inner.get("idle")
        metrics.update(telemetry_fields_from_operational(operational))
        try:
            await asyncio.to_thread(
                record_compressor_status_sample_throttled,
                compressor_id,
                status,
                metrics,
            )
        except Exception:
            logger.exception("Failed to record compressor %s status sample", compressor_id)

    async def _mqtt_loop(self) -> None:
        try:
            from aiomqtt import Client, MqttError
        except ImportError:
            logger.error("aiomqtt not installed; pip install aiomqtt")
            return

        host = settings.MQTT_BROKER_HOST
        port = settings.MQTT_BROKER_PORT
        user = settings.MQTT_USER or None
        password = settings.MQTT_PASSWORD or None

        while self._running:
            try:
                async with Client(
                    hostname=host,
                    port=port,
                    username=user,
                    password=password,
                    timeout=10,
                    keepalive=60,
                ) as client:
                    await client.subscribe("#")
                    logger.info("Subscribed MQTT # for compressor sidecars")
                    async for message in client.messages:
                        if not self._running:
                            break
                        t = str(message.topic)
                        await self._handle_mqtt_payload(t, message.payload)
            except asyncio.CancelledError:
                break
            except MqttError as e:
                logger.warning("MQTT error, reconnect in 5s: %s", e)
                await asyncio.sleep(5)
            except Exception as e:
                logger.exception("MQTT loop error: %s", e)
                await asyncio.sleep(5)
