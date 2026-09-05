"""Background polling for Kaeser compressors directly via SC2/Connect (no sidecar, no MQTT)."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import SessionLocal
from app.models.compressor import Compressor
from app.models.event import CompressorStatusEvent
from app.services.compressor_status_sample_writer import record_compressor_status_sample_throttled
from app.services.compressor_telemetry_sample import telemetry_fields_from_operational
from app.integrations.kaeser_sc2.client import KaeserSc2Client

logger = logging.getLogger(__name__)


class CompressorPoller:
    """One compressor: periodic Kaeser poll + status snapshot."""

    def __init__(
        self,
        compressor: Compressor,
        websocket_manager,
    ):
        self.compressor = compressor
        self.websocket_manager = websocket_manager
        self.last_fast_poll_time: Optional[datetime] = None
        self.consecutive_failures = 0
        self.last_status: Optional[str] = None
        self._log_lock = asyncio.Lock()
        self._client: Optional[KaeserSc2Client] = None

    def _get_client(self) -> KaeserSc2Client:
        # Create once; session is reused between polls.
        if self._client is None:
            self._client = KaeserSc2Client(
                base_url=self.compressor.kaeser_connect_base_url or "",
                username=self.compressor.kaeser_username or "",
                password=self.compressor.kaeser_password or "",
                verify_tls=False,
            )
        return self._client

    async def poll(self) -> Dict[str, Any]:
        poll_start = time.time()
        poll_ts = datetime.now(timezone.utc)
        cid = self.compressor.id

        bundle, err = await self._get_client().fetch_bundle()

        response_ms = int((time.time() - poll_start) * 1000)
        from app.integrations.kaeser_sc2.sidecar_mapper import build_compressor_status_payload

        operational = None
        if bundle and isinstance(bundle.get("operational"), dict):
            operational = bundle["operational"]
        status_data = build_compressor_status_payload(
            compressor_id=self.compressor.id,
            compressor_name=self.compressor.name,
            ip_address=self.compressor.ip_address,
            enabled=self.compressor.enabled,
            poll_interval_seconds=self.compressor.poll_interval_seconds,
            operational=operational,
            rest_bundle=bundle,
            rest_error=err,
            last_operational_mqtt_at=None,
            poll_timestamp=poll_ts,
            response_time_ms=response_ms,
        )

        is_online = status_data.get("is_online", False)

        if not is_online:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        asyncio.create_task(
            self._log_events_async(status_data, poll_ts, response_ms, success=is_online)
        )
        asyncio.create_task(self._record_poll_sample_async(status_data, response_ms, success=is_online))
        return status_data

    async def _record_poll_sample_async(
        self, status_data: Dict[str, Any], response_time_ms: int, success: bool
    ) -> None:
        """Timeline hypertable: one throttled row per poll so the oscilloscope fills without MQTT."""
        status = status_data.get("status") or ("offline" if not success else "unknown")
        metrics: Dict[str, Any] = {
            "source": "poll",
            "is_online": success,
            "response_time_ms": response_time_ms,
        }
        err = status_data.get("error")
        if err:
            metrics["error"] = err
        m = status_data.get("metrics")
        if isinstance(m, dict):
            op = m.get("operational")
            if isinstance(op, dict):
                metrics.update(telemetry_fields_from_operational(op))
        try:
            await asyncio.to_thread(
                record_compressor_status_sample_throttled,
                self.compressor.id,
                status,
                metrics,
            )
        except Exception:
            logger.exception("Compressor poll status sample failed %s", self.compressor.id)

    async def _log_events_async(
        self, status_data: Dict[str, Any], poll_timestamp: datetime, response_time_ms: int, success: bool
    ):
        async with self._log_lock:
            db: Session = SessionLocal()
            try:
                if success:
                    row = db.query(Compressor).filter(Compressor.id == self.compressor.id).first()
                    if row:
                        row.last_seen_at = poll_timestamp
                        db.add(row)

                current = status_data.get("status")
                if self.last_status != current:
                    prev = self.last_status
                    if self.last_status is None:
                        prev = current
                    ev = CompressorStatusEvent(
                        time=poll_timestamp,
                        compressor_id=self.compressor.id,
                        status=current or "unknown",
                        previous_status=prev,
                        metrics={
                            "response_time_ms": response_time_ms,
                            "is_online": success,
                            "error": status_data.get("error"),
                        },
                    )
                    db.add(ev)
                    self.last_status = current

                db.commit()
            except Exception as e:
                logger.error("Compressor event log failed %s: %s", self.compressor.id, e)
                db.rollback()
            finally:
                db.close()


class CompressorPollingService:
    """Manages Kaeser SC2 polling for all enabled compressors."""

    def __init__(self, websocket_manager, mqtt_publisher=None):
        self.websocket_manager = websocket_manager
        self.mqtt_publisher = mqtt_publisher
        self.pollers: Dict[int, CompressorPoller] = {}
        self.polling_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.polling_task = asyncio.create_task(self._poll_loop())
        logger.info("Compressor polling service started")

    async def stop(self):
        self.is_running = False
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
            self.polling_task = None
        logger.info("Compressor polling service stopped")

    async def _poll_loop(self):
        while self.is_running:
            try:
                await self._poll_all()
                db = SessionLocal()
                try:
                    q = db.query(Compressor).filter(Compressor.enabled == True).all()
                    min_iv = min((c.poll_interval_seconds for c in q), default=30)
                finally:
                    db.close()
                await asyncio.sleep(min_iv)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Compressor poll loop error: %s", e)
                await asyncio.sleep(5)

    async def _poll_all(self):
        db = SessionLocal()
        try:
            compressors = db.query(Compressor).filter(Compressor.enabled == True).all()
            ids = {c.id for c in compressors}

            for cid in list(self.pollers.keys()):
                if cid not in ids:
                    del self.pollers[cid]

            for c in compressors:
                if c.id not in self.pollers:
                    self.pollers[c.id] = CompressorPoller(c, self.websocket_manager)
                else:
                    self.pollers[c.id].compressor = c

            now = datetime.now(timezone.utc)
            to_poll = []
            for c in compressors:
                poller = self.pollers.get(c.id)
                if not poller:
                    continue
                if poller.last_fast_poll_time is None:
                    to_poll.append(c)
                else:
                    elapsed = (now - poller.last_fast_poll_time).total_seconds()
                    if elapsed >= c.poll_interval_seconds:
                        to_poll.append(c)

            if not to_poll:
                return

            tasks = [self.pollers[c.id].poll() for c in to_poll]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                c = to_poll[i]
                poller = self.pollers[c.id]
                poller.last_fast_poll_time = datetime.now(timezone.utc)

                if isinstance(result, Exception):
                    logger.error("Compressor poll failed %s: %s", c.id, result)
                    offline = {
                        "asset_kind": "compressor",
                        "compressor_id": c.id,
                        "compressor_name": c.name,
                        "ip_address": c.ip_address,
                        "enabled": c.enabled,
                        "poll_interval_seconds": c.poll_interval_seconds,
                        "is_online": False,
                        "status": "offline",
                        "alarms": [],
                        "metrics": {},
                        "poll_timestamp": datetime.now(timezone.utc).isoformat(),
                        "last_successful_poll_at": None,
                        "response_time_ms": 0,
                        "error": str(result),
                    }
                    await self.websocket_manager.broadcast_compressor_status(offline)
                    if self.mqtt_publisher:
                        try:
                            topic = f"{settings.MQTT_PUBLISH_TOPIC_PREFIX}/compressors/{c.id}/poll"
                            await self.mqtt_publisher.publish_json(topic, offline, retain=True, qos=1)
                        except Exception:
                            pass
                    continue

                await self.websocket_manager.broadcast_compressor_status(result)
                if self.mqtt_publisher:
                    try:
                        topic = f"{settings.MQTT_PUBLISH_TOPIC_PREFIX}/compressors/{c.id}/poll"
                        await self.mqtt_publisher.publish_json(topic, result, retain=True, qos=1)
                    except Exception:
                        pass
        finally:
            db.close()
