"""Read-only machine status routes.

Routes:
    GET /{machine_id}/status          — comprehensive real-time status (deprecated; use WebSocket)
    GET /{machine_id}/running-log     — MONTR time display data
    GET /{machine_id}/counters        — workpiece counter data
    GET /{machine_id}/alarms/live     — current alarms from ALARM telnet command
    GET /{machine_id}/tools           — tool data (ATC or table source)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.base import get_db
from app.models.machine import Machine
from app.clients.http_client import CNCHttpClient
from app.utils.time_utils import format_cnc_time
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{machine_id}/status", deprecated=True)
async def get_machine_status(
    machine_id: int,
    include_mem: bool = Query(False, description="Include MEM data (mode, operation_status)"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive real-time status for a machine.

    .. deprecated::
        Prefer WebSocket ``status_update`` messages from the polling service.
        This endpoint opens a telnet connection per request.

    Fetches data from Telnet including:
    - MONTR: Running log (program, cycle time, etc.) and work counters
    - PRD3: Machine operating status
    - ALARM: Current alarms
    - MEM: Mode and operation status (if include_mem=True)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    telnet_client = None
    try:
        import time
        start_time = time.time()
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.montr_parser_v2 import parse_montr_v2
        from app.parsers.alarm_parser_v2 import parse_alarm_v2
        from app.parsers.prd3_parser_v2 import parse_prd3_v2
        from app.parsers.mem_parser_v2 import parse_mem_v2
        from app.utils.alarm_code_lookup import enrich_alarm_with_lookup

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        control_version = await telnet_client.detect_control_type()
        is_online = True

        montr_data = await telnet_client.get_monitor_data(verbose=False)
        if not montr_data:
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch MONTR data - machine may be unreachable",
            )

        parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=control_version)

        prd3_data = await telnet_client.get_prd3_data(control_version=control_version, verbose=False)
        prd3_parsed = None
        if prd3_data:
            prd3_parsed = parse_prd3_v2(prd3_data.encode('utf-8'), control_version=control_version)

        mem_parsed = None
        if include_mem:
            mem_data = await telnet_client.get_memory_data(verbose=False)
            if mem_data:
                mem_parsed = parse_mem_v2(mem_data.encode('utf-8'), control_version=control_version)

        program_info = parsed.get("program_info", {})
        time_info = parsed.get("time_info", {})
        counters = parsed.get("counters", [])

        if prd3_parsed and prd3_parsed.get("current_status"):
            current_status_data = prd3_parsed["current_status"]
            status_code = current_status_data.get("current_status")
            machine_status = current_status_data.get("status")

            if machine_status == "off":
                has_power_on_time = time_info.get("power_on_time", "000000000") != "000000000"
                has_program = bool(program_info.get("operation_program_no"))
                if has_power_on_time or has_program:
                    machine_status = "standby"
        else:
            machine_status = "standby"
            logger.warning(f"PRD3 data not available for machine {machine_id}, defaulting to 'standby'")

        status_data = {
            "ip_address": db_machine.ip_address,
            "timestamp": datetime.now().isoformat(),
            "units": db_machine.units,
            "program_name": program_info.get("operation_program_no", "----"),
            "cycle_time": format_cnc_time(time_info.get("total_operation_time", "000000000")),
            "cutting_time": format_cnc_time(time_info.get("operation_time", "000000000")),
            "non_cutting_time": "000000:00.0",
            "power_on_hours": format_cnc_time(time_info.get("power_on_time", "000000000")),
            "operation_time": format_cnc_time(time_info.get("operation_time", "000000000")),
            "status": machine_status,
            "is_online": is_online,
            "response_time_ms": int((time.time() - start_time) * 1000),
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
            alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
            if alarm_data_raw:
                alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=None)
                all_alarms = alarm_parsed.get("alarms", []) + alarm_parsed.get("loading_alarms", [])
                enriched_alarms = [enrich_alarm_with_lookup(alarm) for alarm in all_alarms]
                status_data["alarms"] = enriched_alarms
            else:
                status_data["alarms"] = []
        except Exception as e:
            logger.warning(f"Failed to fetch alarms for machine {machine_id}: {e}")
            status_data["alarms"] = []

        if status_data.get("alarms") and machine_status != "off":
            machine_status = "error"
            status_data["status"] = "error"

        status_data["machine_id"] = machine_id
        status_data["machine_name"] = db_machine.name

        if include_mem and mem_parsed:
            status_data["mode"] = mem_parsed.get("mode")
            status_data["operation_status"] = mem_parsed.get("operation_status")
            status_data["operation_folder_name"] = mem_parsed.get("operation_folder_name")

        return status_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch machine status: {str(e)}",
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()


@router.get("/{machine_id}/running-log")
async def get_running_log(machine_id: int, db: Session = Depends(get_db)):
    """Get running log data (time display) from MONTR via Telnet."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    telnet_client = None
    try:
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.montr_parser_v2 import parse_montr_v2

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        control_version = await telnet_client.detect_control_type()
        montr_data = await telnet_client.get_monitor_data(verbose=False)

        if not montr_data:
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch MONTR data",
            )

        parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=control_version)
        time_info = parsed.get("time_info", {})

        return {
            "machine_id": machine_id,
            "cycle_time": format_cnc_time(time_info.get("total_operation_time", "000000000")),
            "cutting_time": format_cnc_time(time_info.get("operation_time", "000000000")),
            "non_cutting_time": "000000:00.0",
            "power_on_hours": format_cnc_time(time_info.get("power_on_time", "000000000")),
            "operation_time": format_cnc_time(time_info.get("operation_time", "000000000")),
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching running log for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()


@router.get("/{machine_id}/counters")
async def get_work_counters(machine_id: int, db: Session = Depends(get_db)):
    """Get workpiece counter data from MONTR via Telnet."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    telnet_client = None
    try:
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.montr_parser_v2 import parse_montr_v2

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        control_version = await telnet_client.detect_control_type()
        montr_data = await telnet_client.get_monitor_data(verbose=False)

        if not montr_data:
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch MONTR data",
            )

        parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=control_version)
        counters = parsed.get("counters", [])

        return {
            "machine_id": machine_id,
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
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching counters for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()


@router.get("/{machine_id}/alarms/live")
async def get_alarms_live(machine_id: int, db: Session = Depends(get_db)):
    """Get current alarm data from the machine via ALARM telnet command.

    For stored alarm events (timelines, analytics), use
    ``GET /api/machines/{machine_id}/alarms`` (database history).
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    telnet_client = None
    try:
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.alarm_parser_v2 import parse_alarm_v2
        from app.utils.alarm_code_lookup import enrich_alarm_with_lookup

        telnet_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )

        alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)

        if alarm_data_raw is None:
            return {
                "machine_id": machine_id,
                "alarms": [],
                "loading_alarms": [],
                "timestamp": datetime.now().isoformat(),
            }

        alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=None)

        alarms = [enrich_alarm_with_lookup(alarm) for alarm in alarm_parsed.get("alarms", [])]
        loading_alarms = [enrich_alarm_with_lookup(alarm) for alarm in alarm_parsed.get("loading_alarms", [])]

        return {
            "machine_id": machine_id,
            "alarms": alarms,
            "loading_alarms": loading_alarms,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alarms for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()


@router.get("/{machine_id}/tools")
async def get_tools(
    machine_id: int,
    source: str = Query("atc", description="Tool data source: 'atc' for ATC table, 'table' for tool table file"),
    raw_html: bool = Query(False, description="Return raw HTML for debugging"),
    db: Session = Depends(get_db)
):
    """
    Get tool data from machine.

    Args:
        machine_id: Machine ID
        source: 'atc' for ATC (Automatic Tool Changer) table, 'table' for TOLNI1.NC tool table file
        raw_html: If True, return raw HTML for debugging (ATC source only)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    telnet_client = None
    try:
        import time
        start_time = time.time()
        if source == "table":
            from app.clients.telnet_client import create_fresh_connection
            from app.parsers.tolni_parser_v2 import parse_tolni_v2

            telnet_client = await create_fresh_connection(
                ip_address=db_machine.ip_address,
                port=10000,
                timeout=10
            )

            data_name = "TOLNI1" if db_machine.units == 'in' else "TOLNM1"
            tool_table_content = await telnet_client.get_tool_table_data(units=db_machine.units, verbose=False)
            if tool_table_content is None:
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to load {data_name} via Telnet. The machine may be busy (CM7500: editing communication data) or Telnet port 10000 may be blocked. Close any open data files on the machine and try again.",
                )

            if tool_table_content.strip().startswith('M'):
                logger.error(f"Received ATCTL data instead of TOLN data for {data_name} - possible connection/data mix-up")
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Data type mismatch: received ATCTL data instead of {data_name}. Please try again.",
                )

            parsed = parse_tolni_v2(
                tool_table_content.encode('utf-8'),
                units=db_machine.units,
                control_version=None
            )

            try:
                from app.parsers.atctl_parser_v2 import parse_atctl_v2

                atc_data = await telnet_client.get_atc_magazine_data(control_version=None)

                if atc_data:
                    atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=None)

                    atc_lookup = {}
                    for atc_tool in atc_parsed.get("tools", []):
                        tool_num = atc_tool.get("tool_number")
                        pot_number = atc_tool.get("pot_number")

                        if tool_num and tool_num > 0 and tool_num != 255:
                            if pot_number and str(pot_number).upper() != "SPINDLE":
                                atc_lookup[tool_num] = {
                                    "pot_number": pot_number,
                                    "group": atc_tool.get("group"),
                                    "tool_type": atc_tool.get("tool_type"),
                                    "color": atc_tool.get("color"),
                                }

                    for tool in parsed.get("tools", []):
                        tool_num = tool.get("tool_number")
                        if tool_num and tool_num in atc_lookup:
                            atc_entry = atc_lookup[tool_num]
                            tool["pot_number"] = atc_entry["pot_number"]
                            if atc_entry.get("group") is not None:
                                tool["group"] = atc_entry["group"]
                            if atc_entry.get("tool_type") is not None:
                                tool["tool_type"] = atc_entry["tool_type"]
                            if atc_entry.get("color") is not None:
                                tool["color"] = atc_entry["color"]
            except Exception as e:
                logger.warning(f"Failed to merge pot numbers into TABLE data: {e}")

            parsed["machine_id"] = machine_id
            parsed["source"] = "tool_table"
            parsed["protocol"] = "telnet"
            parsed["tool_response_time_ms"] = int((time.time() - start_time) * 1000)

            try:
                from app.parsers.mem_parser_v2 import parse_mem_v2
                mem_data = await telnet_client.get_memory_data()
                if mem_data:
                    logger.debug(f"Raw MEM content: {repr(mem_data)}")
                    parsed_mem = parse_mem_v2(mem_data.encode('utf-8'), control_version=None)
                    program_name = parsed_mem.get("program_name")
                    if program_name:
                        parsed["program_name"] = program_name
                        logger.debug(f"Extracted program_name from MEM: {program_name}")
                    else:
                        logger.debug(f"MEM parsed but no program_name found. Content: {repr(mem_data)}")
            except Exception as e:
                logger.debug(f"Failed to fetch program_name from MEM: {e}")

            return parsed
        else:
            from app.clients.telnet_client import create_fresh_connection
            from app.parsers.atctl_parser_v2 import parse_atctl_v2
            from app.parsers.tolni_parser_v2 import parse_tolni_v2
            from app.services.atc_tool_merge import merge_atc_tools_for_display
            from app.services.unified_tool_view import build_unified_tool_view

            if raw_html:
                http_client = CNCHttpClient(db_machine.ip_address, port=db_machine.http_port)
                html = http_client._send_request("/tool")
                return {
                    "machine_id": machine_id,
                    "source": "atc",
                    "raw_html": html
                }

            telnet_client = await create_fresh_connection(
                ip_address=db_machine.ip_address,
                port=10000,
                timeout=10
            )

            atc_data = await telnet_client.get_atc_magazine_data(control_version=None, verbose=False)
            if atc_data is None:
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to load ATCTL/ATCTLD via Telnet. The machine may be busy (CM7500: editing communication data) or Telnet port 10000 may be blocked. Close any open data files on the machine and try again.",
                )

            if atc_data.strip().startswith('T'):
                logger.error(f"Received TOLN data instead of ATCTL data - possible connection/data mix-up")
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Data type mismatch: received TOLN data instead of ATCTL. Please try again.",
                )

            atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=None)

            data_name = "TOLNI1" if db_machine.units == 'in' else "TOLNM1"
            tool_table_content = None
            try:
                tool_table_content = await telnet_client.get_tool_table_data(units=db_machine.units, verbose=False)

                if tool_table_content:
                    first_line = tool_table_content.strip().split('\n')[0].strip() if tool_table_content.strip() else ""
                    if first_line.startswith('M'):
                        logger.error(f"Received ATCTL data instead of TOLN data ({data_name}) - possible connection/data mix-up. First line: {first_line[:50]}")
                        tool_table_content = None
                    elif not first_line.startswith('T') and first_line:
                        logger.warning(f"TOLN data ({data_name}) doesn't start with T## - unexpected format. First line: {first_line[:50]}")
            except Exception as e:
                logger.warning(f"Failed to load {data_name} for ATC merge (will continue without tool details): {e}")

            if tool_table_content is None:
                logger.warning(f"TOLN data ({data_name}) not available for ATC merge - ATC tools will have pot/tool mappings but no diameter/length/name")

            tool_table_tools: list = []
            if tool_table_content:
                tool_table_parsed = parse_tolni_v2(
                    tool_table_content.encode('utf-8'),
                    units=db_machine.units,
                    control_version=atc_parsed.get("control_version")
                )
                tool_table_tools = tool_table_parsed.get("tools", [])
                logger.debug(
                    f"Loaded {len(tool_table_tools)} tools from {data_name} for ATC merge "
                    f"(units={db_machine.units})"
                )
            else:
                logger.warning(
                    f"No TOLN data available for ATC merge - ATC tools will have no diameter/length/name"
                )

            tools = merge_atc_tools_for_display(atc_parsed, tool_table_tools)
            tools_unified = build_unified_tool_view(tool_table_tools, atc_parsed)

            data = {
                "tools": tools,
                "tools_unified": tools_unified,
                "machine_id": machine_id,
                "source": "atc",
                "protocol": "telnet",
                "units": db_machine.units,
                "control_version": atc_parsed.get("control_version"),
                "toln_source": data_name,
                "tool_response_time_ms": int((time.time() - start_time) * 1000)
            }

            logger.info(f"ATC data merged: {len(tools)} tools, TOLN source={data_name}, units={db_machine.units}")

            try:
                from app.parsers.mem_parser_v2 import parse_mem_v2
                mem_data = await telnet_client.get_memory_data()
                if mem_data:
                    logger.debug(f"Raw MEM content: {repr(mem_data)}")
                    parsed_mem = parse_mem_v2(mem_data.encode('utf-8'), control_version=None)
                    program_name = parsed_mem.get("program_name")
                    if program_name:
                        data["program_name"] = program_name
                        logger.debug(f"Extracted program_name from MEM: {program_name}")
            except Exception as e:
                logger.debug(f"Failed to fetch program_name from MEM: {e}")

            return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tools for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()
