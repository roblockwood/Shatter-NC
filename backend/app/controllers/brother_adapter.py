"""Brother CNC controller adapter (Protocol Type 2 / Telnet)."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from app.clients.telnet_client import CNCTelnetClient
from app.controllers.base import BROTHER_CAPABILITIES
from app.models.machine import Machine
from app.parsers.alarm_parser_v2 import parse_alarm_v2
from app.parsers.atctl_parser_v2 import parse_atctl_v2
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.montr_parser_v2 import parse_montr_v2
from app.parsers.panel_parser_v2 import parse_panel_v2
from app.parsers.prd3_parser_v2 import parse_prd3_v2
from app.parsers.tolni_parser_v2 import parse_tolni_v2
from app.utils.alarm_code_lookup import enrich_alarm_with_lookup
from app.utils.time_utils import format_cnc_time

logger = logging.getLogger(__name__)

# Internal keys stripped before WebSocket broadcast.
INTERNAL_POLL_KEYS = frozenset({"_prd3_parsed", "_last_known_prd3_status"})


def strip_internal_poll_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k not in INTERNAL_POLL_KEYS}


class BrotherAdapter:
    """Collects Brother machine data via Telnet Protocol Type 2."""

    def __init__(
        self,
        machine: Machine,
        last_known_prd3_status: Optional[str] = None,
    ):
        self.machine = machine
        self._last_known_prd3_status = last_known_prd3_status

    def capabilities(self) -> Set[str]:
        return set(BROTHER_CAPABILITIES)

    @property
    def last_known_prd3_status(self) -> Optional[str]:
        return self._last_known_prd3_status

    async def close(self) -> None:
        return None

    async def test_connection(self) -> Dict[str, Any]:
        telnet_client = None
        try:
            start = datetime.now()
            telnet_client = CNCTelnetClient(
                self.machine.ip_address,
                port=10000,
                timeout=5,
            )
            mem_data = await telnet_client.load_data("MEM", verbose=False, max_retries=2)
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            if mem_data:
                return {
                    "success": True,
                    "latency_ms": round(latency_ms, 2),
                    "status_code": "00",
                    "timestamp": datetime.now().isoformat(),
                }
            return {
                "success": False,
                "latency_ms": round(latency_ms, 2),
                "status_code": None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            if telnet_client:
                await telnet_client.disconnect()

    async def poll_slow(self, *, skip_if_operating: bool = False) -> Optional[Dict[str, Any]]:
        if skip_if_operating:
            logger.debug(
                "[TOOL_POLL] Machine %s (%s) - skipping tool poll: machine is operating",
                self.machine.id,
                self.machine.name,
            )
            return {}

        poll_start_time = time.time()
        poll_timestamp = datetime.utcnow()
        tool_data: Dict[str, Any] = {}
        step_times: Dict[str, float] = {}
        telnet_client = None

        try:
            logger.debug(
                "[TOOL_POLL] Machine %s (%s) - Starting tool data poll",
                self.machine.id,
                self.machine.name,
            )
            step_start = time.time()
            telnet_client = CNCTelnetClient(
                ip_address=self.machine.ip_address,
                port=10000,
                timeout=10,
            )
            step_times["get_connection"] = time.time() - step_start

            step_start = time.time()
            tool_table_content = await telnet_client.get_tool_table_data(
                units=self.machine.units, verbose=False
            )
            step_times["get_tool_table"] = time.time() - step_start

            if not tool_table_content:
                logger.warning(
                    "Machine %s - No tool table data available via Telnet",
                    self.machine.id,
                )
                return tool_data

            step_start = time.time()
            tool_table_parsed = parse_tolni_v2(
                tool_table_content.encode("utf-8"),
                units=self.machine.units,
                control_version=self.machine.control_version,
            )
            step_times["parse_tool_table"] = time.time() - step_start

            step_start = time.time()
            atc_data = await telnet_client.get_atc_magazine_data(
                control_version=self.machine.control_version, verbose=False
            )
            step_times["get_atc"] = time.time() - step_start

            tool_table_tools = tool_table_parsed.get("tools", [])

            if atc_data:
                step_start = time.time()
                atc_parsed = parse_atctl_v2(
                    atc_data.encode("utf-8"), control_version=self.machine.control_version
                )
                step_times["parse_atc"] = time.time() - step_start

                step_start = time.time()
                atc_lookup: Dict[int, Dict[str, Any]] = {}
                current_tool = None

                for atc_tool in atc_parsed.get("tools", []):
                    tool_num = atc_tool.get("tool_number")
                    pot_number = atc_tool.get("pot_number")

                    if pot_number and (
                        str(pot_number).upper() == "SPINDLE" or pot_number == 0
                    ):
                        if tool_num and tool_num > 0 and tool_num != 255:
                            current_tool = tool_num

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

                tools: List[Dict[str, Any]] = []
                tool_lookup = {
                    t.get("tool_number"): t
                    for t in tool_table_tools
                    if t.get("tool_number")
                }

                for atc_tool in atc_parsed.get("tools", []):
                    tool_num = atc_tool.get("tool_number")
                    pot_number = atc_tool.get("pot_number")
                    if tool_num and tool_num > 0 and tool_num != 255 and tool_num in tool_lookup:
                        tol_tool = tool_lookup[tool_num]
                        tools.append(
                            {
                                "pot_number": pot_number,
                                "tool_number": tool_num,
                                "tool_name": tol_tool.get("tool_name"),
                                "diameter": tol_tool.get("diameter"),
                                "length": tol_tool.get("length"),
                                "group": atc_tool.get("group"),
                                "life": None,
                                "tool_type": atc_tool.get("tool_type"),
                                "color": atc_tool.get("color"),
                            }
                        )

                tool_data["tools"] = tools
                tool_data["tools_timestamp"] = poll_timestamp.isoformat()
                step_times["merge_tools"] = time.time() - step_start
            else:
                logger.warning(
                    "Machine %s - No ATC data available via Telnet", self.machine.id
                )
                tool_data["tools"] = []
                tool_data["tools_timestamp"] = poll_timestamp.isoformat()

            tool_data["tool_table"] = tool_table_tools
            tool_data["tool_table_timestamp"] = poll_timestamp.isoformat()

            total_time_ms = int((time.time() - poll_start_time) * 1000)
            tool_data["tool_response_time_ms"] = total_time_ms
        except Exception as exc:
            logger.warning(
                "Machine %s - Failed to fetch tool data via Telnet: %s",
                self.machine.id,
                exc,
            )
        finally:
            if telnet_client:
                await telnet_client.disconnect()

        return tool_data

    async def poll_fast(
        self,
        *,
        ws_tool_cache: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        poll_start_time = time.time()
        step_times: Dict[str, float] = {}
        telnet_client = None

        try:
            step_start = time.time()
            telnet_client = CNCTelnetClient(
                ip_address=self.machine.ip_address,
                port=10000,
                timeout=10,
            )
            step_times["get_connection"] = time.time() - step_start

            control_version = self.machine.control_version

            step_start = time.time()
            montr_data = await telnet_client.get_monitor_data(verbose=False)
            step_times["get_montr"] = time.time() - step_start
            if not montr_data:
                raise ConnectionError(
                    "Failed to fetch MONTR data - machine may be unreachable"
                )

            step_start = time.time()
            parsed = parse_montr_v2(montr_data.encode("utf-8"), control_version=control_version)
            step_times["parse_montr"] = time.time() - step_start

            step_start = time.time()
            prd3_data = await telnet_client.get_prd3_data(
                control_version=control_version, verbose=False
            )
            step_times["get_prd3"] = time.time() - step_start
            prd3_parsed = None
            if prd3_data:
                step_start = time.time()
                prd3_parsed = parse_prd3_v2(
                    prd3_data.encode("utf-8"), control_version=control_version
                )
                step_times["parse_prd3"] = time.time() - step_start

            mem_parsed = None
            try:
                step_start = time.time()
                mem_data = await telnet_client.get_memory_data(verbose=False)
                step_times["get_mem"] = time.time() - step_start
                if mem_data:
                    step_start = time.time()
                    mem_parsed = parse_mem_v2(
                        mem_data.encode("utf-8"), control_version=control_version
                    )
                    step_times["parse_mem"] = time.time() - step_start
            except Exception as exc:
                logger.warning(
                    "Machine %s - Failed to fetch MEM data: %s", self.machine.id, exc
                )

            program_info = parsed.get("program_info", {})
            time_info = parsed.get("time_info", {})
            counters = parsed.get("counters", [])

            if prd3_parsed and prd3_parsed.get("current_status"):
                current_status_data = prd3_parsed["current_status"]
                machine_status = current_status_data.get("status")

                if machine_status == "off":
                    has_power_on_time = (
                        time_info.get("power_on_time", "000000000") != "000000000"
                    )
                    has_program = bool(program_info.get("operation_program_no"))
                    if has_power_on_time or has_program:
                        machine_status = "standby"

                self._last_known_prd3_status = machine_status
            elif self._last_known_prd3_status:
                machine_status = self._last_known_prd3_status
            else:
                machine_status = "standby"

            _montr_program = program_info.get("operation_program_no")
            _mem_program = mem_parsed.get("program_name") if mem_parsed else None
            _resolved_program_name = _montr_program or _mem_program or "----"

            status_data: Dict[str, Any] = {
                "ip_address": self.machine.ip_address,
                "timestamp": datetime.now().isoformat(),
                "units": self.machine.units,
                "program_name": _resolved_program_name,
                "cycle_time": format_cnc_time(
                    time_info.get("total_operation_time", "000000000")
                ),
                "cutting_time": format_cnc_time(
                    time_info.get("operation_time", "000000000")
                ),
                "non_cutting_time": "000000:00.0",
                "power_on_hours": format_cnc_time(
                    time_info.get("power_on_time", "000000000")
                ),
                "operation_time": format_cnc_time(
                    time_info.get("operation_time", "000000000")
                ),
                "status": machine_status,
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

            try:
                step_start = time.time()
                alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
                step_times["get_alarms"] = time.time() - step_start
                if alarm_data_raw:
                    step_start = time.time()
                    alarm_parsed = parse_alarm_v2(
                        alarm_data_raw.encode("utf-8"), control_version=control_version
                    )
                    all_alarms = alarm_parsed.get("alarms", []) + alarm_parsed.get(
                        "loading_alarms", []
                    )
                    status_data["alarms"] = [
                        enrich_alarm_with_lookup(alarm, control_version)
                        for alarm in all_alarms
                    ]
                    step_times["parse_enrich_alarms"] = time.time() - step_start
                else:
                    status_data["alarms"] = []
            except Exception as exc:
                logger.warning(
                    "Machine %s - Failed to fetch alarms: %s", self.machine.id, exc
                )
                status_data["alarms"] = []

            try:
                step_start = time.time()
                panel_data_raw = await telnet_client.get_panel_data(verbose=False)
                step_times["get_panel"] = time.time() - step_start
                if panel_data_raw:
                    step_start = time.time()
                    status_data["panel"] = parse_panel_v2(
                        panel_data_raw.encode("utf-8"), control_version=control_version
                    )
                    step_times["parse_panel"] = time.time() - step_start
                else:
                    status_data["panel"] = None
            except Exception as exc:
                logger.warning(
                    "Machine %s - Failed to fetch panel data: %s", self.machine.id, exc
                )
                status_data["panel"] = None

            try:
                step_start = time.time()
                macro_values = await telnet_client.get_macro_variable_range(
                    500, 500, verbose=False
                )
                step_times["get_macros"] = time.time() - step_start
                if macro_values:
                    status_data["macros"] = {
                        str(500 + i): value for i, value in enumerate(macro_values)
                    }
                    status_data["macros_timestamp"] = datetime.utcnow().isoformat()
                else:
                    status_data["macros"] = {}
                    status_data["macros_timestamp"] = None
            except Exception as exc:
                logger.warning(
                    "Machine %s - Failed to fetch macro variables: %s",
                    self.machine.id,
                    exc,
                )
                status_data["macros"] = {}
                status_data["macros_timestamp"] = None

            def _is_halting_alarm(alarm: Dict[str, Any]) -> bool:
                try:
                    return int(alarm.get("stop_level") or 0) >= 4
                except (ValueError, TypeError):
                    return False

            halting_alarms = [
                a for a in status_data.get("alarms", []) if _is_halting_alarm(a)
            ]
            if halting_alarms and machine_status not in ("off", "operating"):
                machine_status = "error"
                status_data["status"] = "error"

            if mem_parsed:
                mode = mem_parsed.get("mode")
                operation_status = mem_parsed.get("operation_status")
                if mode is not None:
                    status_data["mem_mode"] = mode
                if operation_status is not None:
                    status_data["mem_operation_status"] = operation_status

            if ws_tool_cache:
                for key in (
                    "tools",
                    "tool_table",
                    "current_tool",
                    "tools_timestamp",
                    "tool_table_timestamp",
                    "tool_response_time_ms",
                ):
                    if key in ws_tool_cache:
                        status_data[key] = ws_tool_cache[key]
                if "tools_timestamp" in ws_tool_cache:
                    status_data["tool_data_timestamp"] = ws_tool_cache["tools_timestamp"]

            response_time_ms = int((time.time() - poll_start_time) * 1000)
            status_data["response_time_ms"] = response_time_ms

            if prd3_parsed:
                status_data["_prd3_parsed"] = prd3_parsed
            status_data["_last_known_prd3_status"] = self._last_known_prd3_status

            return status_data

        finally:
            if telnet_client:
                await telnet_client.disconnect()
