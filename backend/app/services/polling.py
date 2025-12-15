"""Background polling service for CNC machines."""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.machine import Machine
from app.models.event import MachineStatusEvent, AlarmEvent, ProductionRun, PollingEvent
from app.clients.http_client import CNCHttpClient
from app.db.base import SessionLocal

logger = logging.getLogger(__name__)


class MachinePoller:
    """Handles polling for a single machine."""

    def __init__(self, machine: Machine, websocket_manager):
        self.machine = machine
        self.websocket_manager = websocket_manager
        self.last_poll_time: Optional[datetime] = None
        self.consecutive_failures = 0
        self.is_online = False
        self.last_status: Optional[str] = None  # Track status transitions in-memory

    async def poll(self) -> Dict[str, Any]:
        """Poll machine status and return data."""
        poll_start_time = time.time()
        poll_timestamp = datetime.utcnow()

        try:
            logger.debug(f"Polling machine {self.machine.id} ({self.machine.name}) at {self.machine.ip_address}")
            http_client = CNCHttpClient(
                self.machine.ip_address,
                port=self.machine.http_port,
                timeout=5,
            )

            # Get comprehensive status
            status_data = http_client.get_status_overview()

            # Calculate response time
            response_time_ms = int((time.time() - poll_start_time) * 1000)

            # Add metadata
            status_data.update({
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": poll_timestamp.isoformat(),
                "is_online": True,
                "response_time_ms": response_time_ms,
            })

            # Update machine health
            self.is_online = True
            self.consecutive_failures = 0
            self.last_poll_time = poll_timestamp

            logger.debug(f"Successfully polled machine {self.machine.id} ({self.machine.name}) in {response_time_ms}ms")

            # Log events to database (non-blocking, in background)
            # Only log status events if we have a status (machine is online)
            if status_data.get("status"):
                asyncio.create_task(self._log_events_async(status_data, poll_timestamp, response_time_ms, success=True))

            return status_data

        except Exception as e:
            self.consecutive_failures += 1
            self.is_online = False

            # Calculate response time (or error time)
            response_time_ms = int((time.time() - poll_start_time) * 1000)

            logger.error(
                f"Error polling machine {self.machine.id} ({self.machine.name}): {e} "
                f"(failures: {self.consecutive_failures})"
            )

            # Log polling event for failed poll
            asyncio.create_task(self._log_polling_event(
                poll_timestamp,
                success=False,
                response_time_ms=response_time_ms,
                error_message=str(e)
            ))

            # Create offline status data for logging
            offline_status_data = {
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": poll_timestamp.isoformat(),
                "is_online": False,
                "status": "off",  # Set status to "off" when machine is not responding
                "error": str(e),
                "consecutive_failures": self.consecutive_failures,
                "response_time_ms": response_time_ms,
            }

            # Log status event for offline transition (non-blocking)
            asyncio.create_task(self._log_events_async(offline_status_data, poll_timestamp, response_time_ms, success=False))

            return offline_status_data

    async def _log_events_async(self, status_data: Dict[str, Any], poll_timestamp: datetime, response_time_ms: int, success: bool):
        """
        Log events to database in background (non-blocking).

        Events logged:
        - Polling event (success/failure with response time)
        - Status transitions (running → stopped, etc.)
        - Alarms (only when status == 'alarm')
        - Production run start/end
        - Updates machine.last_seen_at to track successful polls
        """
        db = SessionLocal()
        try:
            # Log polling event
            polling_event = PollingEvent(
                time=poll_timestamp,
                machine_id=self.machine.id,
                success=success,
                response_time_ms=response_time_ms,
            )
            db.add(polling_event)

            # Update last_seen_at to track successful polling (only when online)
            if success and status_data.get("is_online", True):
                machine = db.query(Machine).filter(Machine.id == self.machine.id).first()
                if machine:
                    machine.last_seen_at = poll_timestamp
                    db.add(machine)

            current_status = status_data.get("status")

            # Log status transition (Option A: in-memory tracking)
            if self.last_status != current_status:
                await self._log_status_event(db, status_data, current_status)
                self.last_status = current_status

            # Log alarms only when status indicates alarm (Q3)
            if current_status == "alarm":
                await self._log_alarms(db, status_data)

            # Log production run start/end (Q4)
            await self._log_production_run(db, status_data)

            db.commit()
        except Exception as e:
            logger.error(f"Error logging events for machine {self.machine.id}: {e}")
            db.rollback()
        finally:
            db.close()

    async def _log_status_event(self, db: Session, status_data: Dict[str, Any], current_status: str):
        """Log machine status change event."""
        try:
            event = MachineStatusEvent(
                time=datetime.utcnow(),
                machine_id=self.machine.id,
                status=current_status,
                previous_status=self.last_status,
                program_name=status_data.get("program_name"),
                o_number=status_data.get("o_number"),
                metrics={
                    "cycle_time_seconds": status_data.get("cycle_time_seconds"),
                    "cutting_time_seconds": status_data.get("cutting_time_seconds"),
                    "power_on_hours": status_data.get("power_on_hours"),
                }
            )
            db.add(event)
            logger.debug(f"Logged status event for machine {self.machine.id}: {self.last_status} → {current_status}")
        except Exception as e:
            logger.error(f"Failed to log status event: {e}")
            raise

    async def _log_alarms(self, db: Session, status_data: Dict[str, Any]):
        """
        Log alarm events.

        Fetches active alarms from machine and logs any new ones to database.
        """
        try:
            # Get alarms from machine
            http_client = CNCHttpClient(
                self.machine.ip_address,
                port=self.machine.http_port,
                timeout=5,
            )
            alarms = http_client.get_alarms()

            if not alarms:
                logger.debug(f"No alarms found for machine {self.machine.id}")
                return

            # Log each alarm that isn't already in the database
            for alarm in alarms:
                alarm_code = alarm.get("code", "UNKNOWN")

                # Check if this alarm is already logged and still active
                existing = db.query(AlarmEvent).filter(
                    AlarmEvent.machine_id == self.machine.id,
                    AlarmEvent.alarm_code == alarm_code,
                    AlarmEvent.cleared_at.is_(None)
                ).first()

                if not existing:
                    # New alarm - log it
                    event = AlarmEvent(
                        time=datetime.utcnow(),
                        machine_id=self.machine.id,
                        alarm_code=alarm_code,
                        alarm_message=alarm.get("message", ""),
                        alarm_type=alarm.get("type"),
                        severity=alarm.get("severity"),
                    )
                    db.add(event)
                    logger.info(f"Logged alarm for machine {self.machine.id}: {alarm_code} - {alarm.get('message', '')}")

        except Exception as e:
            logger.error(f"Failed to log alarms for machine {self.machine.id}: {e}")
            # Don't raise - alarm logging shouldn't block production run tracking

    async def _log_production_run(self, db: Session, status_data: Dict[str, Any]):
        """
        Track production run start/end.

        - Detects when program starts running (status == 'running')
        - Detects when program stops running (status in ['stopped', 'idle', 'alarm'])
        """
        try:
            current_status = status_data.get("status")
            program_name = status_data.get("program_name")

            # Check for active production run
            active_run = db.query(ProductionRun).filter(
                ProductionRun.machine_id == self.machine.id,
                ProductionRun.ended_at.is_(None)
            ).first()

            # Start new production run
            if current_status == "running" and program_name and program_name != "----":
                if not active_run:
                    run = ProductionRun(
                        machine_id=self.machine.id,
                        program_name=program_name,
                        o_number=status_data.get("o_number"),
                        started_at=datetime.utcnow(),
                    )
                    db.add(run)
                    logger.debug(f"Started production run for machine {self.machine.id}: {program_name}")

            # End active production run
            elif current_status in ["stopped", "idle", "alarm"] and active_run:
                active_run.ended_at = datetime.utcnow()
                active_run.duration_seconds = int(
                    (active_run.ended_at - active_run.started_at).total_seconds()
                )
                active_run.completion_status = "completed" if current_status == "stopped" else current_status
                logger.debug(f"Ended production run for machine {self.machine.id}: {active_run.program_name}")

        except Exception as e:
            logger.error(f"Failed to log production run for machine {self.machine.id}: {e}")
            # Don't raise - production run logging shouldn't block other events

    async def _log_polling_event(self, poll_timestamp: datetime, success: bool, response_time_ms: int, error_message: Optional[str] = None):
        """Log a polling event (success or failure)."""
        db = SessionLocal()
        try:
            polling_event = PollingEvent(
                time=poll_timestamp,
                machine_id=self.machine.id,
                success=success,
                response_time_ms=response_time_ms,
                error_message=error_message,
            )
            db.add(polling_event)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log polling event for machine {self.machine.id}: {e}")
            db.rollback()
        finally:
            db.close()


class PollingService:
    """Manages background polling for all machines."""

    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.pollers: Dict[int, MachinePoller] = {}
        self.polling_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self):
        """Start the polling service."""
        if self.is_running:
            logger.warning("Polling service already running")
            return

        self.is_running = True
        self.polling_task = asyncio.create_task(self._poll_loop())
        logger.info("Polling service started")

    async def stop(self):
        """Stop the polling service."""
        self.is_running = False
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        logger.info("Polling service stopped")

    async def _poll_loop(self):
        """Main polling loop."""
        while self.is_running:
            try:
                await self._poll_all_machines()

                # Wait for next polling interval (default 5 seconds)
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(5)

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
                    self.pollers[machine.id] = MachinePoller(machine, self.websocket_manager)
                    logger.info(f"Added poller for machine {machine.id} ({machine.name})")
                else:
                    # Always update machine reference with fresh DB data to catch config changes
                    # (e.g., IP address updates)
                    old_ip = self.pollers[machine.id].machine.ip_address
                    self.pollers[machine.id].machine = machine
                    if old_ip != machine.ip_address:
                        logger.info(f"Updated machine {machine.id} ({machine.name}) IP: {old_ip} -> {machine.ip_address}")

            # Poll all machines concurrently
            poll_tasks = [
                self.pollers[machine.id].poll()
                for machine in machines
            ]

            results = await asyncio.gather(*poll_tasks, return_exceptions=True)

            # Broadcast results to WebSocket clients
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Polling task failed: {result}")
                    continue

                # Broadcast to all connected clients
                await self.websocket_manager.broadcast_status(result)

            logger.debug(f"Polled {len(machines)} machines")

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

    def get_all_status(self) -> Dict[int, Dict[str, Any]]:
        """Get status for all machines."""
        return {
            machine_id: self.get_machine_status(machine_id)
            for machine_id in self.pollers.keys()
        }
