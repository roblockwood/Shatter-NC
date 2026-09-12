"""Background polling service for CNC machines.

MachinePoller (single-machine logic) lives in _machine_poller.py.
This module provides PollingService (multi-machine coordinator) and
re-exports MachinePoller so existing imports continue to work.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.machine import Machine
from app.clients.http_client import CNCHttpClient
from app.core.config import settings
from app.db.base import SessionLocal
from app.services._machine_poller import MachinePoller  # noqa: F401 (re-export)

logger = logging.getLogger(__name__)


class PollingService:
    """Manages background polling for all machines."""

    def __init__(self, websocket_manager, mqtt_publisher=None, notification_service=None):
        self.websocket_manager = websocket_manager
        self.mqtt_publisher = mqtt_publisher
        self.notification_service = notification_service
        self.pollers: Dict[int, MachinePoller] = {}
        self.polling_task: Optional[asyncio.Task] = None
        self.tool_polling_task: Optional[asyncio.Task] = None  # Separate task for slow tool polling
        self.is_running = False
        # Ref-counted pause so probe exclusive holds can nest safely.
        self._polling_pause_counts: Dict[int, int] = {}
        self._polling_pause_reasons: Dict[int, str] = {}

    def pause_machine_polling(self, machine_id: int, reason: str = "probe") -> int:
        """Increment pause refcount for a machine. Returns new count."""
        count = self._polling_pause_counts.get(machine_id, 0) + 1
        self._polling_pause_counts[machine_id] = count
        self._polling_pause_reasons[machine_id] = reason
        logger.info(
            "Paused polling for machine %s (count=%s, reason=%s)",
            machine_id,
            count,
            reason,
        )
        return count

    def resume_machine_polling(self, machine_id: int) -> int:
        """Decrement pause refcount. Returns remaining count (0 = resumed)."""
        count = self._polling_pause_counts.get(machine_id, 0)
        if count <= 0:
            self._polling_pause_counts.pop(machine_id, None)
            self._polling_pause_reasons.pop(machine_id, None)
            logger.debug(
                "resume_machine_polling called with no pause for machine %s",
                machine_id,
            )
            return 0
        count -= 1
        if count <= 0:
            self._polling_pause_counts.pop(machine_id, None)
            reason = self._polling_pause_reasons.pop(machine_id, None)
            logger.info(
                "Resumed polling for machine %s (was paused for %s)",
                machine_id,
                reason,
            )
            return 0
        self._polling_pause_counts[machine_id] = count
        logger.info(
            "Decremented polling pause for machine %s (count=%s)",
            machine_id,
            count,
        )
        return count

    def is_machine_polling_paused(self, machine_id: int) -> bool:
        return self._polling_pause_counts.get(machine_id, 0) > 0

    async def start(self):
        """Start the polling service."""
        if self.is_running:
            logger.warning("Polling service already running")
            return

        self.is_running = True
        
        # Pre-populate control version cache for all enabled machines (non-blocking)
        # This avoids detecting control version on every poll
        asyncio.create_task(self._prepopulate_control_versions())
        
        self.polling_task = asyncio.create_task(self._poll_loop())
        self.tool_polling_task = asyncio.create_task(self._tool_poll_loop())  # Start slow polling loop
        logger.info("Polling service started (fast and slow polling loops)")

    async def stop(self):
        """Stop the polling service."""
        self.is_running = False
        
        # Stop fast polling loop
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        
        # Stop slow tool polling loop
        if self.tool_polling_task:
            self.tool_polling_task.cancel()
            try:
                await self.tool_polling_task
            except asyncio.CancelledError:
                pass

        logger.info("Polling service stopped (fast and slow polling loops)")

    async def _poll_loop(self):
        """Main polling loop with per-machine intervals."""
        while self.is_running:
            try:
                await self._poll_all_machines()

                # Calculate minimum poll interval across all enabled machines
                # Use this for loop sleep to check machines frequently enough
                db = SessionLocal()
                try:
                    machines = db.query(Machine).filter(Machine.enabled == True).all()
                    if machines:
                        min_interval = min(m.poll_interval_seconds for m in machines)
                    else:
                        min_interval = 5  # Default if no machines
                finally:
                    db.close()
                
                # Sleep for minimum interval (ensures we check machines frequently enough)
                await asyncio.sleep(min_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(5)  # Use default on error

    async def _poll_all_machines(self):
        """Poll all enabled machines concurrently."""
        db = SessionLocal()
        try:
            # Get all enabled machines
            machines = db.query(Machine).filter(Machine.enabled == True).all()

            if not machines:
                logger.debug("No enabled machines to poll")
                return

            # Update pollers for current machines
            current_machine_ids = {m.id for m in machines}

            # Remove pollers for deleted/disabled machines
            for machine_id in list(self.pollers.keys()):
                if machine_id not in current_machine_ids:
                    del self.pollers[machine_id]
                    logger.info(f"Removed poller for machine {machine_id}")

            # Add pollers for new machines
            for machine in machines:
                if machine.id not in self.pollers:
                    poller = MachinePoller(
                        machine, self.websocket_manager, notification_service=self.notification_service
                    )
                    poller.seed_last_status_from_db()
                    self.pollers[machine.id] = poller
                    logger.info(f"Added poller for machine {machine.id} ({machine.name})")
                else:
                    # Always update machine reference with fresh DB data to catch config changes
                    # (e.g., IP address updates)
                    old_ip = self.pollers[machine.id].machine.ip_address
                    self.pollers[machine.id].machine = machine
                    if old_ip != machine.ip_address:
                        logger.info(f"Updated machine {machine.id} ({machine.name}) IP: {old_ip} -> {machine.ip_address}")

            # Poll machines whose interval has elapsed (per-machine intervals)
            now = datetime.utcnow()
            machines_to_poll = []
            for machine in machines:
                if self.is_machine_polling_paused(machine.id):
                    logger.debug(
                        "Skipping fast poll for machine %s (polling paused)",
                        machine.id,
                    )
                    continue
                poller = self.pollers.get(machine.id)
                if not poller:
                    continue
                
                # Check if machine's poll interval has elapsed
                interval_seconds = machine.poll_interval_seconds
                if poller.last_fast_poll_time is None:
                    # Never polled before - poll now
                    machines_to_poll.append(machine)
                else:
                    elapsed = (now - poller.last_fast_poll_time).total_seconds()
                    if elapsed >= interval_seconds:
                        machines_to_poll.append(machine)
            
            if not machines_to_poll:
                logger.debug(f"No machines ready for polling (intervals not elapsed)")
                return
            
            # Poll machines whose intervals have elapsed (concurrently)
            poll_tasks = [
                self.pollers[machine.id].poll()
                for machine in machines_to_poll
            ]

            results = await asyncio.gather(*poll_tasks, return_exceptions=True)

            # Broadcast results to WebSocket clients
            for i, result in enumerate(results):
                machine = machines_to_poll[i]

                if isinstance(result, Exception):
                    logger.error(f"Polling task failed for machine {machine.id} ({machine.name}): {result}")

                    poller = self.pollers.get(machine.id)
                    if poller:
                        fail_ts = datetime.utcnow()
                        offline_status = poller._finalize_poll_failure(result, fail_ts, time.time())
                        if self.websocket_manager:
                            await self.websocket_manager.broadcast_status(offline_status)
                        if self.mqtt_publisher:
                            try:
                                topic = f"{settings.MQTT_PUBLISH_TOPIC_PREFIX}/machines/{machine.id}/poll"
                                await self.mqtt_publisher.publish_json(topic, offline_status, retain=True, qos=1)
                            except Exception:
                                pass
                    continue

                # Broadcast successful poll results
                await self.websocket_manager.broadcast_status(result)
                if self.mqtt_publisher:
                    try:
                        topic = f"{settings.MQTT_PUBLISH_TOPIC_PREFIX}/machines/{machine.id}/poll"
                        await self.mqtt_publisher.publish_json(topic, result, retain=True, qos=1)
                    except Exception:
                        pass

            logger.debug(f"Polled {len(machines_to_poll)} of {len(machines)} machines (per-machine intervals)")

        finally:
            db.close()

    async def _tool_poll_loop(self):
        """Slow polling loop for tool table and ATC magazine data."""
        while self.is_running:
            try:
                await self._poll_all_tool_data()

                # Calculate minimum tool poll interval across all enabled machines
                # Use this for loop sleep to check machines frequently enough
                db = SessionLocal()
                try:
                    machines = db.query(Machine).filter(Machine.enabled == True).all()
                    if machines:
                        min_interval = min(m.tool_poll_interval_seconds for m in machines)
                    else:
                        min_interval = 30  # Default if no machines
                finally:
                    db.close()
                
                # Sleep for minimum interval (ensures we check machines frequently enough)
                await asyncio.sleep(min_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in tool polling loop: {e}")
                await asyncio.sleep(30)  # Use default on error

    async def _poll_all_tool_data(self):
        """Poll tool data for machines whose tool poll interval has elapsed."""
        db = SessionLocal()
        try:
            # Get all enabled machines
            machines = db.query(Machine).filter(Machine.enabled == True).all()

            if not machines:
                logger.debug("No enabled machines for tool data polling")
                return

            # Update pollers for current machines (same logic as fast polling)
            current_machine_ids = {m.id for m in machines}

            # Remove pollers for deleted/disabled machines
            for machine_id in list(self.pollers.keys()):
                if machine_id not in current_machine_ids:
                    del self.pollers[machine_id]

            # Add pollers for new machines
            for machine in machines:
                if machine.id not in self.pollers:
                    poller = MachinePoller(machine, self.websocket_manager)
                    poller.seed_last_status_from_db()
                    self.pollers[machine.id] = poller
                else:
                    # Always update machine reference with fresh DB data to catch config changes
                    self.pollers[machine.id].machine = machine

            # Poll machines whose tool poll interval has elapsed
            now = datetime.utcnow()
            machines_to_poll = []
            for machine in machines:
                if self.is_machine_polling_paused(machine.id):
                    logger.debug(
                        "Skipping tool poll for machine %s (polling paused)",
                        machine.id,
                    )
                    continue
                poller = self.pollers.get(machine.id)
                if not poller:
                    continue
                
                # Check if machine's tool poll interval has elapsed
                interval_seconds = machine.tool_poll_interval_seconds
                if poller.last_tool_poll_time is None:
                    # Never polled tool data before - poll now
                    machines_to_poll.append(machine)
                else:
                    elapsed = (now - poller.last_tool_poll_time).total_seconds()
                    if elapsed >= interval_seconds:
                        machines_to_poll.append(machine)
            
            if not machines_to_poll:
                logger.debug(f"No machines ready for tool data polling (intervals not elapsed)")
                return
            
            # Poll tool data for machines whose intervals have elapsed (concurrently)
            poll_tasks = [
                self.pollers[machine.id].poll_tool_data()
                for machine in machines_to_poll
            ]

            results = await asyncio.gather(*poll_tasks, return_exceptions=True)

            # Update last tool poll time and broadcast tool data updates
            for i, (machine, result) in enumerate(zip(machines_to_poll, results)):
                poller = self.pollers.get(machine.id)
                if not poller:
                    continue
                
                if isinstance(result, Exception):
                    logger.error(f"Tool data polling failed for machine {machine.id}: {result}")
                    continue
                
                # Update last tool poll time on success
                if result:  # Only update if we got data back
                    poller.last_tool_poll_time = now
                    
                    # Broadcast tool data update (merge with existing status data)
                    if self.websocket_manager:
                        # Get existing status and merge tool data
                        existing_status = self.websocket_manager.get_machine_status(machine.id) or {}
                        merged_status = {**existing_status, **result}
                        merged_status["machine_id"] = machine.id
                        merged_status["machine_name"] = machine.name
                        merged_status["is_online"] = poller.display_online()
                        
                        # Broadcast the merged status
                        await self.websocket_manager.broadcast_status(merged_status)
                        
                        logger.debug(f"Polled tool data for machine {machine.id} ({machine.name})")

            logger.debug(f"Polled tool data for {len(machines_to_poll)} of {len(machines)} machines")

        finally:
            db.close()

    def get_machine_status(self, machine_id: int) -> Optional[Dict[str, Any]]:
        """Get current status for a specific machine."""
        poller = self.pollers.get(machine_id)
        if not poller:
            return None

        return {
            "machine_id": machine_id,
            "is_online": poller.is_online,
            "last_poll_time": poller.last_poll_time.isoformat() if poller.last_poll_time else None,
            "consecutive_failures": poller.consecutive_failures,
        }

    async def refresh_tool_data(self, machine_id: int) -> Dict[str, Any]:
        """
        Immediately refresh tool data for a specific machine.
        
        Args:
            machine_id: Machine ID to refresh tool data for
            
        Returns:
            Dictionary containing refreshed tool data
            
        Raises:
            ValueError: If machine is not being polled
        """
        poller = self.pollers.get(machine_id)
        if not poller:
            raise ValueError(f"Machine {machine_id} is not being polled")

        if self.is_machine_polling_paused(machine_id):
            logger.info(
                "Skipping refresh_tool_data for machine %s (polling paused)",
                machine_id,
            )
            return {}
        
        # Poll tool data immediately
        tool_data = await poller.poll_tool_data()
        
        # Update last tool poll time
        poller.last_tool_poll_time = datetime.utcnow()
        
        # Merge with existing status and broadcast
        if tool_data and self.websocket_manager:
            existing_status = self.websocket_manager.get_machine_status(machine_id) or {}
            merged_status = {**existing_status, **tool_data}
            merged_status["machine_id"] = machine_id
            merged_status["machine_name"] = poller.machine.name
            merged_status["is_online"] = poller.display_online()
            
            # Broadcast the merged status
            await self.websocket_manager.broadcast_status(merged_status)
        
        return tool_data

    async def _prepopulate_control_versions(self):
        """
        Pre-populate control version cache for all enabled machines on startup.
        This avoids detecting control version on every poll (saves ~1200ms per poll).
        """
        db = SessionLocal()
        try:
            machines = db.query(Machine).filter(Machine.enabled == True).all()
            if not machines:
                logger.debug("No enabled machines to pre-populate control versions for")
                return
            
            logger.info(f"Pre-populating control version cache for {len(machines)} enabled machine(s)...")
            
            from app.clients.telnet_client import create_fresh_connection

            # Detect control version for each machine (concurrently)
            async def detect_for_machine(m):
                telnet_client = None
                try:
                    telnet_client = await create_fresh_connection(
                        ip_address=m.ip_address,
                        port=10000,
                        timeout=10
                    )
                    # This will detect and cache the control version
                    control_version = await telnet_client.detect_control_type(verbose=False)
                    if control_version:
                        logger.info(f"Pre-populated control version for machine {m.id} ({m.name}): {control_version}")
                    else:
                        logger.warning(f"Failed to detect control version for machine {m.id} ({m.name})")
                except Exception as e:
                    logger.warning(f"Failed to pre-populate control version for machine {m.id} ({m.name}): {e}")
                finally:
                    if telnet_client:
                        await telnet_client.disconnect()
            
            # Create tasks with proper closure (use default argument to capture machine)
            tasks = []
            for machine in machines:
                async def detect(m=machine):  # Default argument captures current value
                    await detect_for_machine(m)
                tasks.append(detect())
            
            # Run all detections concurrently (each will use its own lock)
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Control version cache pre-population complete")
        except Exception as e:
            logger.error(f"Error during control version cache pre-population: {e}")
        finally:
            db.close()

    def get_all_status(self) -> Dict[int, Dict[str, Any]]:
        """Get status for all machines."""
        return {
            machine_id: self.get_machine_status(machine_id)
            for machine_id in self.pollers.keys()
        }
