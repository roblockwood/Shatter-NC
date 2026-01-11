"""Background polling service for CNC machines."""
import asyncio
import logging
import time
from datetime import datetime, timedelta
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
        self.last_heartbeat_time: Optional[datetime] = None  # Track last heartbeat event
        self.heartbeat_interval_minutes = 5  # Log heartbeat every 5 minutes
        self.offline_threshold = 3  # Require 3 consecutive failures before logging offline
        self.logged_offline_status = False  # Track if we've already logged the offline transition
        
        # Cache for program_name from mem.nc (fetched on-demand, not during regular polling)
        self.cached_program_name: Optional[str] = None
        self.program_name_fetched = False  # Track if we've fetched program_name at least once

    async def fetch_program_name(self) -> Optional[str]:
        """
        Fetch program_name from MEM via Telnet (on-demand).
        
        Returns:
            program_name if successfully fetched, None otherwise
        """
        try:
            from app.clients.telnet_client import get_or_create_connection
            from app.parsers.mem_parser_v2 import parse_mem_v2
            
            # Use pooled connection
            telnet_client = await get_or_create_connection(
                ip_address=self.machine.ip_address,
                port=10000,
                timeout=10
            )
            
            mem_data = await telnet_client.get_memory_data(verbose=False)
            if mem_data:
                logger.debug(f"Machine {self.machine.id} - Raw MEM content: {repr(mem_data)}")
                parsed_mem = parse_mem_v2(mem_data.encode('utf-8'), control_version=None)
                program_name = parsed_mem.get("program_name")
                if program_name:
                    self.cached_program_name = program_name
                    self.program_name_fetched = True
                    logger.info(f"Machine {self.machine.id} - Fetched program_name from MEM via Telnet: {program_name}")
                    return program_name
                else:
                    logger.debug(f"Machine {self.machine.id} - MEM parsed but no program_name found. Content: {repr(mem_data)}")
            else:
                logger.debug(f"Machine {self.machine.id} - MEM file not found or empty")
        except Exception as e:
            logger.warning(f"Machine {self.machine.id} - Failed to fetch program_name from MEM via Telnet: {e}")
        
        return None

    async def poll(self) -> Dict[str, Any]:
        """Poll machine status and return data."""
        poll_start_time = time.time()
        poll_timestamp = datetime.utcnow()

        try:
            logger.debug(f"Polling machine {self.machine.id} ({self.machine.name}) at {self.machine.ip_address}")
            
            # Phase 5: Migrate to Telnet for MONTR and PRD3 data (replaces HTTP get_status_overview)
            from app.clients.telnet_client import get_or_create_connection
            from app.parsers.montr_parser_v2 import parse_montr_v2
            from app.parsers.alarm_parser_v2 import parse_alarm_v2
            from app.parsers.prd3_parser_v2 import parse_prd3_v2
            
            # Use pooled connection (reused across operations)
            telnet_client = await get_or_create_connection(
                ip_address=self.machine.ip_address,
                port=10000,
                timeout=10
            )
            
            # Detect control version once (cached in telnet_client)
            control_version = await telnet_client.detect_control_type()
            
            # Machine is online if we successfully connected and can perform Telnet operations
            # If we got here, we have a working Telnet connection
            is_online = True
            
            # Get MONTR data (replaces HTTP /running_log and /work_counter)
            montr_data = await telnet_client.get_monitor_data(verbose=False)
            if not montr_data:
                raise ConnectionError("Failed to fetch MONTR data - machine may be unreachable")
            
            parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=control_version)
            
            # Get PRD3 data (contains current status)
            prd3_data = await telnet_client.get_prd3_data(control_version=control_version, verbose=False)
            prd3_parsed = None
            if prd3_data:
                prd3_parsed = parse_prd3_v2(prd3_data.encode('utf-8'), control_version=control_version)
            
            # Get MEM data to check mode and operation_status (needed for frontend validation)
            mem_parsed = None
            try:
                from app.parsers.mem_parser_v2 import parse_mem_v2
                mem_data = await telnet_client.get_memory_data(verbose=False)
                if mem_data:
                    mem_parsed = parse_mem_v2(mem_data.encode('utf-8'), control_version=control_version)
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch MEM data: {e}")
                # Continue without MEM data - frontend will handle gracefully
            
            # Format response to match HTTP client format
            program_info = parsed.get("program_info", {})
            time_info = parsed.get("time_info", {})
            counters = parsed.get("counters", [])
            
            # Get status from PRD3 (more accurate than inferring from program presence)
            # PRD3 status codes: 1=off, 2=standby, 3=operating, 4=stopped, 5=error
            if prd3_parsed and prd3_parsed.get("current_status"):
                current_status_data = prd3_parsed["current_status"]
                status_code = current_status_data.get("current_status")  # Raw integer code (1-5)
                machine_status = current_status_data.get("status")  # Mapped string
                
                logger.debug(f"Machine {self.machine.id} - PRD3 status_code={status_code}, mapped_status={machine_status}")
                
                # If status is "off" (code 1), but machine is responding to Telnet, it's likely in standby
                # A truly powered-off machine wouldn't respond to Telnet requests
                if machine_status == "off":
                    # Check if machine is actually active (has power-on time, program info, etc.)
                    has_power_on_time = time_info.get("power_on_time", "000000000") != "000000000"
                    has_program = bool(program_info.get("operation_program_no"))
                    
                    if has_power_on_time or has_program:
                        logger.info(f"Machine {self.machine.id} - PRD3 reports 'off' but machine appears active (power_on_time={has_power_on_time}, program={has_program}), using 'standby'")
                        machine_status = "standby"
                
                # Update last known status when we successfully get PRD3 data
                self.last_status = machine_status
            else:
                # PRD3 data not available - use last known status instead of defaulting to "operating"
                if self.last_status:
                    machine_status = self.last_status
                    logger.warning(f"Machine {self.machine.id} - PRD3 data not available, using last known status: {machine_status}")
                else:
                    # No last status available - default to standby (safer than "operating")
                    machine_status = "standby"
                    logger.warning(f"Machine {self.machine.id} - PRD3 data not available and no last status, defaulting to: {machine_status}")
            
            # Format time strings (MONTR format: HHMMSSMMM, HTTP format: HHMM:SS.MMM)
            def format_time(time_str: str) -> str:
                """Convert HHMMSSMMM to HHMM:SS.MMM format."""
                if not time_str or len(time_str) != 9:
                    return time_str
                try:
                    hours = time_str[0:2]
                    minutes = time_str[2:4]
                    seconds = time_str[4:6]
                    milliseconds = time_str[6:9]
                    return f"{hours}{minutes}:{seconds}.{milliseconds}"
                except (ValueError, IndexError):
                    return time_str
            
            # is_online is already set to True after successful Telnet connection
            # PRD3 failure doesn't mean machine is offline - it just means we can't get status
            # Status will use last known value when PRD3 is unavailable
            
            status_data = {
                "ip_address": self.machine.ip_address,
                "timestamp": datetime.now().isoformat(),
                "units": self.machine.units,
                "program_name": program_info.get("operation_program_no", "----"),
                "cycle_time": format_time(time_info.get("total_operation_time", "000000000")),
                "cutting_time": format_time(time_info.get("operation_time", "000000000")),
                "non_cutting_time": "000000:00.0",  # Not in MONTR
                "power_on_hours": format_time(time_info.get("power_on_time", "000000000")),
                "operation_time": format_time(time_info.get("operation_time", "000000000")),
                "status": machine_status,  # From PRD3: off, standby, operating, stopped, error
                "is_online": is_online,  # True when any Telnet operation succeeds (machine is reachable)
                "counters": [
                    {
                        "counter_number": c.get("counter_number", i + 1),
                        "count": c.get("count", 0),
                        "current": c.get("current", 0),
                        "end": c.get("end", 0),
                        "end_warning": c.get("end_warning", 0),
                    }
                    for i, c in enumerate(counters)
                ],
            }
            
            # Get alarms from Telnet (Phase 5: Migrate to Telnet)
            try:
                from app.utils.alarm_code_lookup import enrich_alarm_with_lookup
                
                alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
                if alarm_data_raw:
                    alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=control_version)
                    # Convert to format expected by frontend (combine alarms and loading_alarms)
                    all_alarms = alarm_parsed.get("alarms", []) + alarm_parsed.get("loading_alarms", [])
                    # Enrich with lookup data (description, cause, solution, stop_level, reset_level)
                    enriched_alarms = [enrich_alarm_with_lookup(alarm, control_version) for alarm in all_alarms]
                    status_data["alarms"] = enriched_alarms
                else:
                    status_data["alarms"] = []
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch alarms: {e}")
                status_data["alarms"] = []
            
            # Get panel data from Telnet
            try:
                from app.parsers.panel_parser_v2 import parse_panel_v2
                
                panel_data_raw = await telnet_client.get_panel_data(verbose=False)
                if panel_data_raw:
                    panel_parsed = parse_panel_v2(panel_data_raw.encode('utf-8'), control_version=control_version)
                    status_data["panel"] = panel_parsed
                else:
                    status_data["panel"] = None
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch panel data: {e}")
                status_data["panel"] = None
            
            # Override status to 'error' if there are active alarms (unless machine is off)
            if status_data.get("alarms") and machine_status != "off":
                machine_status = "error"
                status_data["status"] = "error"
            
            # Add MEM mode and operation_status for frontend validation
            if mem_parsed:
                mode = mem_parsed.get("mode")
                operation_status = mem_parsed.get("operation_status")
                if mode is not None:
                    status_data["mem_mode"] = mode
                if operation_status is not None:
                    status_data["mem_operation_status"] = operation_status

            # Fetch tool data via Telnet (fresh data, same as API endpoint)
            try:
                from app.parsers.atctl_parser_v2 import parse_atctl_v2
                from app.parsers.tolni_parser_v2 import parse_tolni_v2
                
                # Reuse the same pooled connection from above
                
                # Get tool table data first (needed for both ATC merge and TABLE display)
                data_name = "TOLNI1" if self.machine.units == 'in' else "TOLNM1"
                tool_table_content = await telnet_client.get_tool_table_data(units=self.machine.units, verbose=False)
                
                if tool_table_content:
                    tool_table_parsed = parse_tolni_v2(
                        tool_table_content.encode('utf-8'),
                        units=self.machine.units,
                        control_version=None  # Auto-detect
                    )
                    
                    # Get ATC magazine data (pot/tool mappings) for merging
                    atc_data = await telnet_client.get_atc_magazine_data(control_version=None, verbose=False)
                    
                    # Start with pure TOLN (table) data
                    tool_table_tools = tool_table_parsed.get("tools", [])
                    
                    if atc_data:
                        atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=None)
                        
                        # Create reverse lookup: tool_number -> ATCTL data (for TABLE view)
                        # This includes: pot_number, group, tool_type, color
                        atc_lookup = {}
                        for atc_tool in atc_parsed.get("tools", []):
                            tool_num = atc_tool.get("tool_number")
                            pot_number = atc_tool.get("pot_number")
                            
                            # Extract current_tool from spindle
                            if pot_number and (str(pot_number).upper() == "SPINDLE" or pot_number == 0):
                                if tool_num and tool_num > 0 and tool_num != 255:
                                    status_data["current_tool"] = tool_num
                            
                            # Build lookup for ATCTL data (skip spindle and invalid tools)
                            if tool_num and tool_num > 0 and tool_num != 255:
                                if pot_number and str(pot_number).upper() != "SPINDLE":
                                    atc_lookup[tool_num] = {
                                        "pot_number": pot_number,
                                        "group": atc_tool.get("group"),
                                        "tool_type": atc_tool.get("tool_type"),
                                        "color": atc_tool.get("color"),
                                    }
                        
                        # Merge ATCTL data into TABLE tools (reverse merge: TOLN -> ATCTL)
                        # This adds: pot_number, group, tool_type, color
                        for tool in tool_table_tools:
                            tool_num = tool.get("tool_number")
                            if tool_num and tool_num in atc_lookup:
                                atc_data = atc_lookup[tool_num]
                                tool["pot_number"] = atc_data["pot_number"]
                                if atc_data.get("group") is not None:
                                    tool["group"] = atc_data["group"]
                                if atc_data.get("tool_type") is not None:
                                    tool["tool_type"] = atc_data["tool_type"]
                                if atc_data.get("color") is not None:
                                    tool["color"] = atc_data["color"]
                        
                        # Merge ATC positions with tool details (forward merge: ATCTL -> TOLN)
                        tools = []
                        tool_lookup = {}
                        
                        # Create lookup by tool number from TOLN data
                        for tool in tool_table_tools:
                            tool_num = tool.get("tool_number")
                            if tool_num:
                                tool_lookup[tool_num] = tool
                        
                        # Merge ATC tools with tool details from TOLN
                        # Match by tool_number to correlate pot position with tool data
                        # Only include tools that have valid TOLN data
                        for atc_tool in atc_parsed.get("tools", []):
                            tool_num = atc_tool.get("tool_number")
                            pot_number = atc_tool.get("pot_number")
                            
                            if tool_num and tool_num > 0 and tool_num != 255:  # Skip "not set" and "cap setting"
                                if tool_num in tool_lookup:
                                    tol_tool = tool_lookup[tool_num]
                                    merged_tool = {
                                        "pot_number": pot_number,
                                        "tool_number": tool_num,
                                        "tool_name": tol_tool.get("tool_name"),
                                        "diameter": tol_tool.get("diameter"),
                                        "length": tol_tool.get("length"),
                                        "group": atc_tool.get("group"),
                                        "life": None,  # Not in ATCTL
                                        "tool_type": atc_tool.get("tool_type"),
                                        "color": atc_tool.get("color"),
                                    }
                                    tools.append(merged_tool)
                        
                        status_data["tools"] = tools
                        status_data["tools_timestamp"] = poll_timestamp.isoformat()
                        logger.debug(f"Machine {self.machine.id} - Fetched {len(tools)} ATC tools and {len(tool_table_tools)} table tools via Telnet")
                    else:
                        logger.warning(f"Machine {self.machine.id} - No ATC data available via Telnet")
                    
                    # Store TABLE data with pot numbers merged (if ATC data was available)
                    status_data["tool_table"] = tool_table_tools
                    status_data["tool_table_timestamp"] = poll_timestamp.isoformat()
                    # Connection stays open in pool for next operation
                else:
                    logger.warning(f"Machine {self.machine.id} - No tool table data available via Telnet")
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch tool data via Telnet: {e}")
                # Continue without tool data - don't fail the entire poll
                # Tools will be empty/undefined, which is fine

            # Program name is already set from MONTR data (operation_program_no)
            # No need to fetch from MEM separately - MONTR is more reliable

            # Calculate response time
            response_time_ms = int((time.time() - poll_start_time) * 1000)

            # Add metadata (preserve is_online from status_data if already set)
            status_data.update({
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": poll_timestamp.isoformat(),
                "response_time_ms": response_time_ms,
            })
            # is_online is already set in status_data based on PRD3 availability - don't override it
            
            # Ensure program_name is explicitly included (even if None)
            if "program_name" not in status_data:
                status_data["program_name"] = None

            # Update machine health (use is_online from status_data, not hardcoded True)
            was_offline = not self.is_online or self.logged_offline_status
            self.is_online = status_data.get("is_online", True)  # Use is_online from status_data
            self.consecutive_failures = 0
            self.last_poll_time = poll_timestamp

            logger.debug(f"Successfully polled machine {self.machine.id} ({self.machine.name}) in {response_time_ms}ms")

            # Log events to database (non-blocking, in background)
            # Only log status events if we have a status (machine is online)
            if status_data.get("status"):
                # If we were previously offline and now recovered, ensure we log the transition back online
                if was_offline:
                    self.logged_offline_status = False
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

            # Get cached status from Redis first (persists across workers and restarts)
            # Fall back to WebSocket manager cache if Redis is unavailable or has cache miss
            cached_status = {}
            try:
                from app.utils.redis_client import get_redis
                import json
                redis = get_redis()
                cache_key = f"machine:status:{self.machine.id}"
                cached_data = redis.get(cache_key)
                if cached_data:
                    cached_status = json.loads(cached_data.decode('utf-8'))
                else:
                    # Main status cache miss - try extended caches for older data
                    # Try tool_table cache (5min TTL)
                    tool_table_key = f"machine:tool_table:{self.machine.id}"
                    tool_table_data = redis.get(tool_table_key)
                    if tool_table_data:
                        cached_status["tool_table"] = json.loads(tool_table_data.decode('utf-8'))
                    
                    # Try panel cache (2min TTL)
                    panel_key = f"machine:panel:{self.machine.id}"
                    panel_data = redis.get(panel_key)
                    if panel_data:
                        cached_status["panel"] = json.loads(panel_data.decode('utf-8'))
                    
                    # Try program_name cache (5min TTL)
                    program_name_key = f"machine:program_name:{self.machine.id}"
                    program_name_data = redis.get(program_name_key)
                    if program_name_data:
                        cached_status["program_name"] = program_name_data.decode('utf-8')
                    
                    # Still fall back to websocket_manager for any missing data
                    ws_status = self.websocket_manager.get_machine_status(self.machine.id) if self.websocket_manager else {}
                    if not cached_status:
                        cached_status = ws_status
                    else:
                        # Merge with websocket_manager data (prefer cached_status, fill gaps from ws_status)
                        for key, value in ws_status.items():
                            if key not in cached_status or cached_status[key] is None:
                                cached_status[key] = value
            except Exception as e:
                # Redis unavailable - fall back to websocket_manager
                logger.debug(f"Failed to read from Redis cache for machine {self.machine.id}, falling back to websocket_manager: {e}")
                cached_status = self.websocket_manager.get_machine_status(self.machine.id) if self.websocket_manager else {}
            
            # Create offline status data for logging, preserving cached data
            offline_status_data = {
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": poll_timestamp.isoformat(),
                "is_online": False,
                "status": "off",  # Set status to "off" when machine is not responding
                "error": str(e),
                "consecutive_failures": self.consecutive_failures,
                "response_time_ms": response_time_ms,
                "program_name": self.cached_program_name,  # Preserve cached program_name even when offline
                # Preserve cached data that doesn't change frequently when offline
                "panel": cached_status.get("panel"),  # Preserve panel data
                "alarms": cached_status.get("alarms", []),  # Preserve alarms
                "tool_table": cached_status.get("tool_table"),  # Preserve tool table
                "current_tool": cached_status.get("current_tool"),  # Preserve current tool
            }

            # Only log offline transition if we've exceeded the threshold AND haven't already logged it
            should_log_offline = (
                self.consecutive_failures >= self.offline_threshold and 
                not self.logged_offline_status
            )
            
            if should_log_offline:
                # Store previous status before updating (needed for event logging)
                previous_status = self.last_status
                # Update last_status to "off" immediately so transition back online will be detected
                self.last_status = "off"
                # Update offline_status_data with correct previous_status for logging
                offline_status_data["previous_status"] = previous_status
                # Log status event for offline transition (non-blocking)
                asyncio.create_task(self._log_events_async(offline_status_data, poll_timestamp, response_time_ms, success=False))
                self.logged_offline_status = True
                logger.info(
                    f"Machine {self.machine.id} ({self.machine.name}) marked offline "
                    f"after {self.consecutive_failures} consecutive failures "
                    f"(previous status: {previous_status})"
                )

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
                # Reset heartbeat timer on status change
                self.last_heartbeat_time = poll_timestamp
            # Log heartbeat if exactly 5 minutes have passed (even if status hasn't changed)
            elif current_status and success:
                # Only log heartbeat if we have a previous heartbeat time to compare against
                # This prevents logging heartbeats on first poll or after poller recreation
                if self.last_heartbeat_time is not None:
                    # Check if heartbeat interval has passed
                    time_since_heartbeat = poll_timestamp - self.last_heartbeat_time
                    if time_since_heartbeat >= timedelta(minutes=self.heartbeat_interval_minutes):
                        # For heartbeats, previous_status should equal current_status (no change)
                        status_data_with_heartbeat = {**status_data, "previous_status": current_status}
                        await self._log_status_event(db, status_data_with_heartbeat, current_status)
                        self.last_heartbeat_time = poll_timestamp
                else:
                    # Initialize heartbeat timer on first successful poll (don't log yet)
                    self.last_heartbeat_time = poll_timestamp

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
            # Use previous_status from status_data if provided (for offline transitions),
            # otherwise use self.last_status
            previous_status = status_data.get("previous_status", self.last_status)
            event = MachineStatusEvent(
                time=datetime.utcnow(),
                machine_id=self.machine.id,
                status=current_status,
                previous_status=previous_status,
                program_name=status_data.get("program_name"),
                o_number=status_data.get("o_number"),
                metrics={
                    "cycle_time_seconds": status_data.get("cycle_time_seconds"),
                    "cutting_time_seconds": status_data.get("cutting_time_seconds"),
                    "power_on_hours": status_data.get("power_on_hours"),
                }
            )
            db.add(event)
            logger.debug(f"Logged status event for machine {self.machine.id}: {previous_status} → {current_status}")
        except Exception as e:
            logger.error(f"Failed to log status event: {e}")
            raise

    async def _log_alarms(self, db: Session, status_data: Dict[str, Any]):
        """
        Log alarm events.

        Uses alarms from status_data (already fetched via Telnet in poll()).
        """
        try:
            # Get alarms from status_data (already fetched via Telnet)
            alarms = status_data.get("alarms", [])

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
        
        # Close all Telnet connections for machines we were polling
        try:
            from app.clients.telnet_client import close_all_connections
            await close_all_connections()
        except Exception as e:
            logger.warning(f"Error closing Telnet connections during polling service stop: {e}")
        
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
