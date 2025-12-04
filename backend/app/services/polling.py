"""Background polling service for CNC machines."""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.machine import Machine
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

    async def poll(self) -> Dict[str, Any]:
        """Poll machine status and return data."""
        try:
            http_client = CNCHttpClient(
                self.machine.ip_address,
                port=self.machine.http_port,
                timeout=5,
            )

            # Get comprehensive status
            status_data = http_client.get_status_overview()

            # Add metadata
            status_data.update({
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": datetime.utcnow().isoformat(),
                "is_online": True,
            })

            # Update machine health
            self.is_online = True
            self.consecutive_failures = 0
            self.last_poll_time = datetime.utcnow()

            logger.debug(f"Successfully polled machine {self.machine.id} ({self.machine.name})")
            return status_data

        except Exception as e:
            self.consecutive_failures += 1
            self.is_online = False

            logger.error(
                f"Error polling machine {self.machine.id} ({self.machine.name}): {e} "
                f"(failures: {self.consecutive_failures})"
            )

            return {
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": datetime.utcnow().isoformat(),
                "is_online": False,
                "error": str(e),
                "consecutive_failures": self.consecutive_failures,
            }


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
                    # Update machine reference in case config changed
                    self.pollers[machine.id].machine = machine

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
