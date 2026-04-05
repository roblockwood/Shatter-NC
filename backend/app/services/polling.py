"""Background polling service for CNC machines."""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from app.models.machine import Machine
from app.models.event import (
    MachineStatusEvent, 
    AlarmEvent, 
    ProductionRun, 
    PollingEvent,
    MacroHistory,
    ToolTableHistory,
    PanelHistory,
    CounterHistory,
    PRD3StatusHistory,
)
from app.clients.http_client import CNCHttpClient
from app.core.config import settings
from app.db.base import SessionLocal
from app.utils.machine_endpoints import get_telnet_endpoint

logger = logging.getLogger(__name__)


class MachinePoller:
    """Handles polling for a single machine."""

    def __init__(self, machine: Machine, websocket_manager):
        self.machine = machine
        self.websocket_manager = websocket_manager
        self.last_poll_time: Optional[datetime] = None
        self.last_fast_poll_time: Optional[datetime] = None  # Track last fast poll for per-machine intervals
        self.last_successful_fast_poll_at: Optional[datetime] = None  # Only advances on successful fast poll (UI freshness)
        self.last_tool_poll_time: Optional[datetime] = None  # Track last tool data poll for slow polling
        self.consecutive_failures = 0
        self.is_online = False
        self.last_status: Optional[str] = None  # Track status transitions in-memory (only updated in _log_events_async)
        self.last_known_prd3_status: Optional[str] = None  # Last status from PRD3; used when PRD3 is missing on a later poll
        self.last_heartbeat_time: Optional[datetime] = None  # Track last heartbeat event
        self.heartbeat_interval_minutes = settings.HEARTBEAT_INTERVAL_MINUTES
        self.offline_threshold = 3  # Require 3 consecutive failures before logging offline
        self.logged_offline_status = False  # Track if we've already logged the offline transition
        self._log_events_lock = asyncio.Lock()  # Serialize per-machine event logging to prevent race-induced duplicate/stale transitions
        
        # Cache for program_name from mem.nc (fetched on-demand, not during regular polling)
        self.cached_program_name: Optional[str] = None
        self.program_name_fetched = False  # Track if we've fetched program_name at least once

        # Extended history state tracking (Log-on-Change + Heartbeat)
        self.last_macros: Optional[Dict[str, Any]] = None
        self.last_tool_table: Optional[List[Dict[str, Any]]] = None
        self.last_panel: Optional[Dict[str, Any]] = None
        self.last_counters: Optional[List[Dict[str, Any]]] = None

        # Tracking last log times for heartbeat (interval from settings)
        self.last_macro_log_time: Optional[datetime] = None
        self.last_tool_table_log_time: Optional[datetime] = None
        self.last_panel_log_time: Optional[datetime] = None
        self.last_counter_log_time: Optional[datetime] = None

    def display_online(self) -> bool:
        """
        Debounced online flag for UI / websocket (matches offline_threshold semantics).

        True only after at least one successful fast poll and while consecutive_failures
        is below offline_threshold.
        """
        if self.last_successful_fast_poll_at is None:
            return False
        return self.consecutive_failures < self.offline_threshold

    def _finalize_poll_failure(
        self,
        exc: BaseException,
        poll_timestamp: datetime,
        poll_start_time: float,
    ) -> Dict[str, Any]:
        """
        Increment failure count, log, build websocket payload, update self.is_online,
        and run offline-transition / heartbeat logging when threshold is met.
        """
        self.consecutive_failures += 1
        response_time_ms = int((time.time() - poll_start_time) * 1000)

        logger.error(
            f"Error polling machine {self.machine.id} ({self.machine.name}): {exc} "
            f"(failures: {self.consecutive_failures})"
        )

        asyncio.create_task(
            self._log_polling_event(
                poll_timestamp,
                success=False,
                response_time_ms=response_time_ms,
                error_message=str(exc),
            )
        )

        cached_status = (
            self.websocket_manager.get_machine_status(self.machine.id) if self.websocket_manager else {}
        )

        last_ok = self.last_successful_fast_poll_at
        last_ok_iso = last_ok.isoformat() if last_ok else cached_status.get("last_successful_poll_at")

        display = self.display_online()
        if display:
            status_for_ui = (
                cached_status.get("status")
                or self.last_known_prd3_status
                or "standby"
            )
        else:
            status_for_ui = "off"

        offline_status_data: Dict[str, Any] = {
            "machine_id": self.machine.id,
            "machine_name": self.machine.name,
            "poll_timestamp": poll_timestamp.isoformat(),
            "last_successful_poll_at": last_ok_iso,
            "is_online": display,
            "status": status_for_ui,
            "consecutive_failures": self.consecutive_failures,
            "response_time_ms": response_time_ms,
            "program_name": self.cached_program_name,
            "part_display_mode": getattr(self.machine, "part_display_mode", "parts"),
            "panel": cached_status.get("panel"),
            "alarms": cached_status.get("alarms", []),
            "tools": cached_status.get("tools"),
            "tools_timestamp": cached_status.get("tools_timestamp"),
            "tool_table": cached_status.get("tool_table"),
            "tool_table_timestamp": cached_status.get("tool_table_timestamp"),
            "current_tool": cached_status.get("current_tool"),
            "macros": cached_status.get("macros", {}),
            "macros_timestamp": cached_status.get("macros_timestamp"),
            "tool_response_time_ms": cached_status.get("tool_response_time_ms"),
        }
        if not display:
            offline_status_data["error"] = str(exc)

        self.is_online = display

        should_log_offline = (
            self.consecutive_failures >= self.offline_threshold and not self.logged_offline_status
        )

        if should_log_offline:
            previous_status = self.last_status
            self.last_status = "off"
            offline_status_data["previous_status"] = previous_status
            asyncio.create_task(
                self._log_events_async(offline_status_data, poll_timestamp, response_time_ms, success=False)
            )
            self.logged_offline_status = True
            self.last_heartbeat_time = poll_timestamp
            logger.info(
                f"Machine {self.machine.id} ({self.machine.name}) marked offline "
                f"after {self.consecutive_failures} consecutive failures "
                f"(previous status: {previous_status})"
            )

        if self.logged_offline_status and self.last_heartbeat_time is not None:
            time_since_heartbeat = poll_timestamp - self.last_heartbeat_time
            if time_since_heartbeat >= timedelta(minutes=self.heartbeat_interval_minutes):
                asyncio.create_task(self._log_offline_heartbeat(offline_status_data, poll_timestamp))
                self.last_heartbeat_time = poll_timestamp

        return offline_status_data

    async def fetch_program_name(self) -> Optional[str]:
        """
        Fetch program_name from MEM via Telnet (on-demand).

        Returns:
            program_name if successfully fetched, None otherwise
        """
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.mem_parser_v2 import parse_mem_v2

        telnet_client = None
        try:
            # Create fresh connection
            telnet_client = await create_fresh_connection(
                ip_address=get_telnet_endpoint(self.machine)[0],
                port=get_telnet_endpoint(self.machine)[1],
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
        finally:
            if telnet_client:
                await telnet_client.disconnect()

        return None

    async def poll_tool_data(self) -> Dict[str, Any]:
        """
        Poll tool table and ATC magazine data (slow polling operation).
        
        Returns:
            Dictionary containing tool data:
            - tools: List of merged ATC tools
            - tool_table: List of tool table entries
            - current_tool: Current tool in spindle
            - tools_timestamp: ISO timestamp of when data was fetched
            - tool_table_timestamp: ISO timestamp of when data was fetched
        """
        poll_start_time = time.time()
        poll_timestamp = datetime.utcnow()
        tool_data = {}
        step_times = {}
        
        telnet_client = None
        try:
            logger.debug(f"[TOOL_POLL] Machine {self.machine.id} ({self.machine.name}) - Starting tool data poll")

            from app.clients.telnet_client import create_fresh_connection
            from app.parsers.atctl_parser_v2 import parse_atctl_v2
            from app.parsers.tolni_parser_v2 import parse_tolni_v2

            # Create fresh connection
            step_start = time.time()
            telnet_client = await create_fresh_connection(
                ip_address=get_telnet_endpoint(self.machine)[0],
                port=get_telnet_endpoint(self.machine)[1],
                timeout=10
            )
            step_times['get_connection'] = time.time() - step_start
            
            # Detect control version (uses Redis cache)
            step_start = time.time()
            control_version = await telnet_client.detect_control_type()
            step_times['detect_control'] = time.time() - step_start
            
            # Get tool table data first (needed for both ATC merge and TABLE display)
            step_start = time.time()
            tool_table_content = await telnet_client.get_tool_table_data(units=self.machine.units, verbose=False)
            step_times['get_tool_table'] = time.time() - step_start
            
            if tool_table_content:
                step_start = time.time()
                tool_table_parsed = parse_tolni_v2(
                    tool_table_content.encode('utf-8'),
                    units=self.machine.units,
                    control_version=None  # Auto-detect
                )
                step_times['parse_tool_table'] = time.time() - step_start
                
                # Get ATC magazine data (pot/tool mappings) for merging
                step_start = time.time()
                atc_data = await telnet_client.get_atc_magazine_data(control_version=None, verbose=False)
                step_times['get_atc'] = time.time() - step_start
                
                # Start with pure TOLN (table) data
                tool_table_tools = tool_table_parsed.get("tools", [])
                
                if atc_data:
                    step_start = time.time()
                    atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=None)
                    step_times['parse_atc'] = time.time() - step_start
                    
                    step_start = time.time()
                    # Create reverse lookup: tool_number -> ATCTL data (for TABLE view)
                    # This includes: pot_number, group, tool_type, color
                    atc_lookup = {}
                    current_tool = None
                    
                    for atc_tool in atc_parsed.get("tools", []):
                        tool_num = atc_tool.get("tool_number")
                        pot_number = atc_tool.get("pot_number")
                        
                        # Extract current_tool from spindle
                        if pot_number and (str(pot_number).upper() == "SPINDLE" or pot_number == 0):
                            if tool_num and tool_num > 0 and tool_num != 255:
                                current_tool = tool_num
                        
                        # Build lookup for ATCTL data (skip spindle and invalid tools)
                        if tool_num and tool_num > 0 and tool_num != 255:
                            if pot_number and str(pot_number).upper() != "SPINDLE":
                                atc_lookup[tool_num] = {
                                    "pot_number": pot_number,
                                    "group": atc_tool.get("group"),
                                    "tool_type": atc_tool.get("tool_type"),
                                    "color": atc_tool.get("color"),
                                }
                    
                    if current_tool:
                        tool_data["current_tool"] = current_tool
                    
                    # Merge ATCTL data into TABLE tools (reverse merge: TOLN -> ATCTL)
                    # This adds: pot_number, group, tool_type, color
                    for tool in tool_table_tools:
                        tool_num = tool.get("tool_number")
                        if tool_num and tool_num in atc_lookup:
                            atc_info = atc_lookup[tool_num]
                            tool["pot_number"] = atc_info["pot_number"]
                            if atc_info.get("group") is not None:
                                tool["group"] = atc_info["group"]
                            if atc_info.get("tool_type") is not None:
                                tool["tool_type"] = atc_info["tool_type"]
                            if atc_info.get("color") is not None:
                                tool["color"] = atc_info["color"]
                    
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
                    
                    tool_data["tools"] = tools
                    tool_data["tools_timestamp"] = poll_timestamp.isoformat()
                    step_times['merge_tools'] = time.time() - step_start
                    logger.debug(f"Machine {self.machine.id} - Fetched {len(tools)} ATC tools and {len(tool_table_tools)} table tools via Telnet (slow poll)")
                else:
                    logger.warning(f"Machine {self.machine.id} - No ATC data available via Telnet")
                
                # Store TABLE data with pot numbers merged (if ATC data was available)
                tool_data["tool_table"] = tool_table_tools
                tool_data["tool_table_timestamp"] = poll_timestamp.isoformat()
                
                # Update websocket manager cache with tool data so fast poll can use it
                step_start = time.time()
                if self.websocket_manager:
                    current = self.websocket_manager.get_machine_status(self.machine.id) or {}
                    merged = {**current, **tool_data, "machine_id": self.machine.id}
                    merged["is_online"] = self.display_online()
                    await self.websocket_manager.broadcast_status(merged)
                step_times['update_cache'] = time.time() - step_start
                
                # Log timing summary
                total_time = time.time() - poll_start_time
                total_time_ms = int(total_time * 1000)
                tool_data["tool_response_time_ms"] = total_time_ms
                step_summary = ", ".join([f"{step}: {time_ms * 1000:.1f}ms" for step, time_ms in 
                                         sorted(step_times.items(), key=lambda x: x[1], reverse=True) 
                                         if time_ms > 0.001])  # Only show steps > 1ms
                logger.debug(f"[TOOL_POLL] Machine {self.machine.id} ({self.machine.name}) - Tool poll completed in {total_time_ms}ms | Steps: {step_summary}")
            else:
                logger.warning(f"Machine {self.machine.id} - No tool table data available via Telnet")
        except Exception as e:
            logger.warning(f"Machine {self.machine.id} - Failed to fetch tool data via Telnet: {e}")
            # Return empty dict on failure
        finally:
            if telnet_client:
                await telnet_client.disconnect()

        return tool_data

    async def poll(self) -> Dict[str, Any]:
        """Poll machine status and return data."""
        poll_start_time = time.time()
        poll_timestamp = datetime.utcnow()
        step_times = {}

        telnet_client = None
        try:
            logger.debug(f"[POLL] Machine {self.machine.id} ({self.machine.name}) - Starting fast poll")

            # Phase 5: Migrate to Telnet for MONTR and PRD3 data (replaces HTTP get_status_overview)
            from app.clients.telnet_client import create_fresh_connection
            from app.parsers.montr_parser_v2 import parse_montr_v2
            from app.parsers.alarm_parser_v2 import parse_alarm_v2
            from app.parsers.prd3_parser_v2 import parse_prd3_v2

            # Create fresh connection
            step_start = time.time()
            telnet_client = await create_fresh_connection(
                ip_address=get_telnet_endpoint(self.machine)[0],
                port=get_telnet_endpoint(self.machine)[1],
                timeout=10
            )
            step_times['get_connection'] = time.time() - step_start
            
            # Detect control version once (cached in telnet_client)
            step_start = time.time()
            control_version = await telnet_client.detect_control_type()
            step_times['detect_control'] = time.time() - step_start
            
            # Get MONTR data (replaces HTTP /running_log and /work_counter)
            step_start = time.time()
            montr_data = await telnet_client.get_monitor_data(verbose=False)
            step_times['get_montr'] = time.time() - step_start
            if not montr_data:
                raise ConnectionError("Failed to fetch MONTR data - machine may be unreachable")
            
            step_start = time.time()
            parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=control_version)
            step_times['parse_montr'] = time.time() - step_start
            
            # Get PRD3 data (contains current status and status history)
            step_start = time.time()
            prd3_data = await telnet_client.get_prd3_data(control_version=control_version, verbose=False)
            step_times['get_prd3'] = time.time() - step_start
            prd3_parsed = None
            if prd3_data:
                step_start = time.time()
                prd3_parsed = parse_prd3_v2(prd3_data.encode('utf-8'), control_version=control_version)
                step_times['parse_prd3'] = time.time() - step_start
                # Ingest PRD3 history asynchronously (non-blocking)
                try:
                    asyncio.create_task(self._log_prd3_history(prd3_parsed))
                except Exception as e:
                    logger.warning(f"Machine {self.machine.id} - Failed to schedule PRD3 history logging: {e}")
            
            # Get MEM data to check mode and operation_status (needed for frontend validation)
            mem_parsed = None
            try:
                step_start = time.time()
                from app.parsers.mem_parser_v2 import parse_mem_v2
                mem_data = await telnet_client.get_memory_data(verbose=False)
                step_times['get_mem'] = time.time() - step_start
                if mem_data:
                    step_start = time.time()
                    mem_parsed = parse_mem_v2(mem_data.encode('utf-8'), control_version=control_version)
                    step_times['parse_mem'] = time.time() - step_start
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
                
                # Update last known PRD3 status (used when PRD3 is missing on a later poll); do not set last_status here
                self.last_known_prd3_status = machine_status
            else:
                # PRD3 data not available - use last known PRD3 status instead of defaulting to "operating"
                if self.last_known_prd3_status:
                    machine_status = self.last_known_prd3_status
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
            
            # is_online for clients is set after last_successful_fast_poll_at (debounced display_online)
            
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
                step_start = time.time()
                from app.utils.alarm_code_lookup import enrich_alarm_with_lookup
                
                alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
                step_times['get_alarms'] = time.time() - step_start
                if alarm_data_raw:
                    step_start = time.time()
                    alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=control_version)
                    # Convert to format expected by frontend (combine alarms and loading_alarms)
                    all_alarms = alarm_parsed.get("alarms", []) + alarm_parsed.get("loading_alarms", [])
                    # Enrich with lookup data (description, cause, solution, stop_level, reset_level)
                    enriched_alarms = [enrich_alarm_with_lookup(alarm, control_version) for alarm in all_alarms]
                    step_times['parse_enrich_alarms'] = time.time() - step_start
                    status_data["alarms"] = enriched_alarms
                else:
                    status_data["alarms"] = []
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch alarms: {e}")
                status_data["alarms"] = []
            
            # Get panel data from Telnet
            try:
                step_start = time.time()
                from app.parsers.panel_parser_v2 import parse_panel_v2
                
                panel_data_raw = await telnet_client.get_panel_data(verbose=False)
                step_times['get_panel'] = time.time() - step_start
                if panel_data_raw:
                    step_start = time.time()
                    panel_parsed = parse_panel_v2(panel_data_raw.encode('utf-8'), control_version=control_version)
                    step_times['parse_panel'] = time.time() - step_start
                    status_data["panel"] = panel_parsed
                else:
                    status_data["panel"] = None
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch panel data: {e}")
                status_data["panel"] = None
            
            # Get macro variables from Telnet (macros #500-999)
            try:
                step_start = time.time()
                macro_values = await telnet_client.get_macro_variable_range(500, 500, verbose=False)
                step_times['get_macros'] = time.time() - step_start
                if macro_values:
                    # Convert list to dictionary mapping macro number to value
                    macros_dict = {}
                    for i, value in enumerate(macro_values):
                        macro_num = 500 + i
                        macros_dict[str(macro_num)] = value

                    status_data["macros"] = macros_dict
                    status_data["macros_timestamp"] = poll_timestamp.isoformat()
                    logger.debug(f"Machine {self.machine.id} - Fetched {len(macro_values)} macro variables (#500-999) via Telnet")
                else:
                    status_data["macros"] = {}
                    status_data["macros_timestamp"] = None
            except Exception as e:
                logger.warning(f"Machine {self.machine.id} - Failed to fetch macro variables: {e}")
                status_data["macros"] = {}
                status_data["macros_timestamp"] = None
            
            # Override status to 'error' only when there are hard alarms (type == "alarm"); ignore operator_message and loading_system
            hard_alarms = [a for a in status_data.get("alarms", []) if a.get("type") == "alarm"]
            if hard_alarms and machine_status != "off":
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

            # Load tool data from websocket manager cache (fetched by slow polling or immediate refresh)
            step_start = time.time()
            ws_status = self.websocket_manager.get_machine_status(self.machine.id) if self.websocket_manager else {}
            step_times['load_tool_cache'] = time.time() - step_start
            if ws_status:
                if "tools" in ws_status:
                    status_data["tools"] = ws_status["tools"]
                if "tool_table" in ws_status:
                    status_data["tool_table"] = ws_status["tool_table"]
                if "current_tool" in ws_status:
                    status_data["current_tool"] = ws_status["current_tool"]
                if "tools_timestamp" in ws_status:
                    status_data["tools_timestamp"] = ws_status["tools_timestamp"]
                    status_data["tool_data_timestamp"] = ws_status["tools_timestamp"]
                if "tool_table_timestamp" in ws_status:
                    status_data["tool_table_timestamp"] = ws_status["tool_table_timestamp"]
                if "tool_response_time_ms" in ws_status:
                    status_data["tool_response_time_ms"] = ws_status["tool_response_time_ms"]

            # Program name is already set from MONTR data (operation_program_no)
            # No need to fetch from MEM separately - MONTR is more reliable

            # Calculate response time
            total_time = time.time() - poll_start_time
            response_time_ms = int(total_time * 1000)

            # Log step timing summary
            step_summary = ", ".join([f"{step}: {time_ms * 1000:.1f}ms" for step, time_ms in 
                                     sorted(step_times.items(), key=lambda x: x[1], reverse=True) 
                                     if time_ms > 0.001])  # Only show steps > 1ms
            logger.debug(f"[POLL] Machine {self.machine.id} ({self.machine.name}) - Fast poll completed in {response_time_ms}ms | Steps: {step_summary}")

            # Add metadata
            status_data.update({
                "machine_id": self.machine.id,
                "machine_name": self.machine.name,
                "poll_timestamp": poll_timestamp.isoformat(),
                "response_time_ms": response_time_ms,
                "part_display_mode": getattr(self.machine, "part_display_mode", "parts"),
            })
            
            # Ensure program_name is explicitly included (even if None)
            if "program_name" not in status_data:
                status_data["program_name"] = None

            was_offline = not self.is_online or self.logged_offline_status
            self.consecutive_failures = 0
            self.last_poll_time = poll_timestamp
            self.last_fast_poll_time = poll_timestamp  # Track fast poll time for per-machine intervals
            self.last_successful_fast_poll_at = poll_timestamp
            status_data["last_successful_poll_at"] = self.last_successful_fast_poll_at.isoformat()
            self.is_online = self.display_online()
            status_data["is_online"] = self.is_online

            # Log events to database (non-blocking, in background)
            # Only log status events if we have a status (machine is online)
            if status_data.get("status"):
                # If we were previously offline and now recovered, ensure we log the transition back online
                if was_offline:
                    self.logged_offline_status = False
                asyncio.create_task(self._log_events_async(status_data, poll_timestamp, response_time_ms, success=True))

            return status_data

        except Exception as e:
            return self._finalize_poll_failure(e, poll_timestamp, poll_start_time)
        finally:
            if telnet_client:
                await telnet_client.disconnect()

    async def _log_prd3_history(self, prd3_parsed: Dict[str, Any]):
        """
        Ingest PRD3/PRDD3 status history into PRD3StatusHistory hypertable.

        This method is designed to be called asynchronously from poll()
        and should not block the main polling loop.
        """
        try:
            history = prd3_parsed.get("history") or []
            if not history:
                return

            db = SessionLocal()
            try:
                # Determine the latest stored timestamp for this machine to avoid duplicates
                latest = (
                    db.query(PRD3StatusHistory.time)
                    .filter(PRD3StatusHistory.machine_id == self.machine.id)
                    .order_by(PRD3StatusHistory.time.desc())
                    .limit(1)
                    .one_or_none()
                )
                latest_time = latest[0] if latest else None

                # Collapse history entries by start time to avoid duplicate
                # primary key violations when PRD3 contains multiple records
                # with the same start_date_time (e.g., standby + operating
                # at the same timestamp). For a given timestamp we keep the
                # last entry seen, which is typically the most specific
                # status (e.g., operating).
                history_by_time: Dict[datetime, Dict[str, Any]] = {}
                for entry in history:
                    start_str = entry.get("start_date_time")
                    if not start_str or len(start_str) != 14:
                        continue
                    try:
                        # PRD3 format: YYYYMMDDhhmmss
                        start_dt = datetime.strptime(start_str, "%Y%m%d%H%M%S")
                    except Exception:
                        continue

                    # Interpret PRD3 timestamps as local machine time in configured timezone.
                    # They are stored in the database as timestamptz (Postgres will keep them in UTC),
                    # but semantic "wall time" comes from LOCAL_TIMEZONE.
                    if start_dt.tzinfo is None:
                        try:
                            start_dt = start_dt.replace(tzinfo=ZoneInfo(settings.LOCAL_TIMEZONE))
                        except Exception:
                            start_dt = start_dt.replace(tzinfo=timezone.utc)

                    # Skip if we've already ingested this or a later entry
                    if latest_time is not None and start_dt <= latest_time:
                        continue

                    # For now, let later entries for the same timestamp win
                    history_by_time[start_dt] = entry

                total_candidates = len(history_by_time)
                if total_candidates == 0:
                    logger.info(
                        f"Machine {self.machine.id} - PRD3 history ingest: no new entries after {latest_time!s}"
                    )
                    return

                logger.info(
                    f"Machine {self.machine.id} - PRD3 history ingest starting, "
                    f"{total_candidates} candidate entries after de-duplication since {latest_time!s}"
                )

                BATCH_SIZE = 1000
                processed = 0
                committed = 0
                batch: list[PRD3StatusHistory] = []

                # Iterate in chronological order so we always insert old→new
                for start_dt in sorted(history_by_time.keys()):
                    entry = history_by_time[start_dt]
                    status_code = entry.get("current_status")
                    status = entry.get("status")
                    if status_code is None or status is None:
                        continue

                    program_or_error = (entry.get("program_or_error_no") or "").strip()
                    program_no = None
                    error_no = None
                    if status == "operating" and program_or_error:
                        program_no = program_or_error
                    elif status == "error" and program_or_error:
                        error_no = program_or_error

                    row = PRD3StatusHistory(
                        time=start_dt,
                        machine_id=self.machine.id,
                        status=status,
                        status_code=status_code,
                        program_no=program_no,
                        error_no=error_no,
                        folder_name=entry.get("folder_name"),
                        memory_operation_type=entry.get("memory_operation_type"),
                        raw=entry,
                    )
                    batch.append(row)
                    processed += 1

                    if len(batch) >= BATCH_SIZE:
                        db.add_all(batch)
                        db.commit()
                        committed += len(batch)
                        logger.info(
                            f"Machine {self.machine.id} - PRD3 ingest committed "
                            f"{len(batch)} entries (total committed: {committed}/{total_candidates})"
                        )
                        batch.clear()

                    if processed % BATCH_SIZE == 0:
                        logger.info(
                            f"Machine {self.machine.id} - PRD3 ingest progress: "
                            f"{processed}/{total_candidates} entries prepared"
                        )

                # Final partial batch
                if batch:
                    db.add_all(batch)
                    db.commit()
                    committed += len(batch)
                    logger.info(
                        f"Machine {self.machine.id} - PRD3 ingest committed final "
                        f"{len(batch)} entries (total committed: {committed}/{total_candidates})"
                    )

                logger.info(
                    f"Machine {self.machine.id} - PRD3 history ingest finished, "
                    f"{committed} new entries logged"
                )
            except Exception as e:
                logger.error(f"Failed to log PRD3 history for machine {self.machine.id}: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Unexpected error in _log_prd3_history for machine {self.machine.id}: {e}")

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
        async with self._log_events_lock:
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
                    # First event after poller creation (last_status is None): pass previous_status=current_status
                    # so the event is stored as a heartbeat and the UI shows [HEARTBEAT] not [STATUS EVENT]
                    if self.last_status is None:
                        status_data = {**status_data, "previous_status": current_status}
                    await self._log_status_event(db, status_data, current_status)
                    self.last_status = current_status
                    # Reset heartbeat timer on status change
                    self.last_heartbeat_time = poll_timestamp
                # Log heartbeat if heartbeat interval has passed (even if status hasn't changed)
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

                # Log extended history (macros, tool table, panel, counters)
                if success:
                    await self._log_extended_history(db, status_data, poll_timestamp)

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

    async def _log_extended_history(self, db: Session, status_data: Dict[str, Any], poll_timestamp: datetime):
        """
        Log extended history data (macros, tool table, panel, counters)
        using a hybrid Log-on-Change + Heartbeat approach.
        """
        try:
            # 1. Macro History
            macros = status_data.get("macros")
            if macros:
                should_log, change_type = self._should_log_history(
                    macros, self.last_macros, self.last_macro_log_time, poll_timestamp
                )
                if should_log:
                    event = MacroHistory(
                        time=poll_timestamp,
                        machine_id=self.machine.id,
                        data=macros,
                        change_type=change_type
                    )
                    db.add(event)
                    self.last_macros = macros
                    self.last_macro_log_time = poll_timestamp
                    logger.debug(f"Logged macro history ({change_type}) for machine {self.machine.id}")

            # 2. Tool Table History
            tool_table = status_data.get("tool_table")
            if tool_table:
                should_log, change_type = self._should_log_history(
                    tool_table, self.last_tool_table, self.last_tool_table_log_time, poll_timestamp
                )
                if should_log:
                    event = ToolTableHistory(
                        time=poll_timestamp,
                        machine_id=self.machine.id,
                        data=tool_table,
                        change_type=change_type
                    )
                    db.add(event)
                    self.last_tool_table = tool_table
                    self.last_tool_table_log_time = poll_timestamp
                    logger.debug(f"Logged tool table history ({change_type}) for machine {self.machine.id}")

            # 3. Panel History
            panel = status_data.get("panel")
            if panel:
                should_log, change_type = self._should_log_history(
                    panel, self.last_panel, self.last_panel_log_time, poll_timestamp
                )
                if should_log:
                    event = PanelHistory(
                        time=poll_timestamp,
                        machine_id=self.machine.id,
                        data=panel,
                        change_type=change_type
                    )
                    db.add(event)
                    self.last_panel = panel
                    self.last_panel_log_time = poll_timestamp
                    logger.debug(f"Logged panel history ({change_type}) for machine {self.machine.id}")

            # 4. Counter History
            counters = status_data.get("counters")
            if counters:
                should_log, change_type = self._should_log_history(
                    counters, self.last_counters, self.last_counter_log_time, poll_timestamp
                )
                if should_log:
                    event = CounterHistory(
                        time=poll_timestamp,
                        machine_id=self.machine.id,
                        data=counters,
                        change_type=change_type
                    )
                    db.add(event)
                    self.last_counters = counters
                    self.last_counter_log_time = poll_timestamp
                    logger.debug(f"Logged counter history ({change_type}) for machine {self.machine.id}")

        except Exception as e:
            logger.error(f"Failed to log extended history for machine {self.machine.id}: {e}")

    def _should_log_history(self, current_data: Any, last_data: Any, last_log_time: Optional[datetime], current_time: datetime) -> Tuple[bool, str]:
        """
        Determine if history data should be logged based on change detection or heartbeat.
        Returns (should_log, change_type)
        """
        # 1. Log immediately if data has changed
        if current_data != last_data:
            return True, "change"

        # 2. Log heartbeat if interval has passed
        if last_log_time is not None:
            time_since_last_log = current_time - last_log_time
            if time_since_last_log >= timedelta(minutes=self.heartbeat_interval_minutes):
                return True, "heartbeat"
        else:
            # First time seeing this data, log it as heartbeat
            return True, "heartbeat"

        return False, ""

    async def _log_offline_heartbeat(self, status_data: Dict[str, Any], poll_timestamp: datetime):
        """Log offline heartbeat status event (status="off", previous_status="off")."""
        db = SessionLocal()
        try:
            # Log offline heartbeat with status="off" and previous_status="off"
            heartbeat_status_data = {
                **status_data,
                "previous_status": "off",  # Explicitly set to "off" for heartbeat
                "status": "off",
            }
            await self._log_status_event(db, heartbeat_status_data, "off")
            db.commit()
            logger.debug(f"Logged offline heartbeat for machine {self.machine.id}")
        except Exception as e:
            logger.error(f"Failed to log offline heartbeat for machine {self.machine.id}: {e}")
            db.rollback()
        finally:
            db.close()

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

    def __init__(self, websocket_manager, mqtt_publisher=None):
        self.websocket_manager = websocket_manager
        self.mqtt_publisher = mqtt_publisher
        self.pollers: Dict[int, MachinePoller] = {}
        self.polling_task: Optional[asyncio.Task] = None
        self.tool_polling_task: Optional[asyncio.Task] = None  # Separate task for slow tool polling
        self.is_running = False

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
                    self.pollers[machine.id] = MachinePoller(machine, self.websocket_manager)
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
                    self.pollers[machine.id] = MachinePoller(machine, self.websocket_manager)
                else:
                    # Always update machine reference with fresh DB data to catch config changes
                    self.pollers[machine.id].machine = machine

            # Poll machines whose tool poll interval has elapsed
            now = datetime.utcnow()
            machines_to_poll = []
            for machine in machines:
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
                        ip_address=get_telnet_endpoint(m)[0],
                        port=get_telnet_endpoint(m)[1],
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
