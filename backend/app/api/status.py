"""API endpoints for real-time machine status."""
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.machine import Machine
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient
from app.parsers.gcode_parser import parse_gcode
import logging
import io

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{machine_id}/status")
async def get_machine_status(machine_id: int, db: Session = Depends(get_db)):
    """
    Get comprehensive real-time status for a machine.

    Fetches data from Telnet including:
    - MONTR: Running log (program, cycle time, etc.) and work counters
    - PRD3: Machine operating status
    - ALARM: Current alarms
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        # Phase 5: Migrate to Telnet for MONTR and PRD3 data (replaces HTTP get_status_overview)
        from app.clients.telnet_client import get_or_create_connection
        from app.parsers.montr_parser_v2 import parse_montr_v2
        from app.parsers.alarm_parser_v2 import parse_alarm_v2
        from app.parsers.prd3_parser_v2 import parse_prd3_v2
        from app.utils.alarm_code_lookup import enrich_alarm_with_lookup
        from datetime import datetime
        
        # Use pooled connection
        telnet_client = await get_or_create_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )
        
        # Detect control version
        control_version = await telnet_client.detect_control_type()
        
        # Get MONTR data
        montr_data = await telnet_client.get_monitor_data(verbose=False)
        if not montr_data:
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch MONTR data - machine may be unreachable",
            )
        
        parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=control_version)
        
        # Get PRD3 data (contains current status)
        prd3_data = await telnet_client.get_prd3_data(control_version=control_version, verbose=False)
        prd3_parsed = None
        if prd3_data:
            prd3_parsed = parse_prd3_v2(prd3_data.encode('utf-8'), control_version=control_version)
        
        # Format response
        program_info = parsed.get("program_info", {})
        time_info = parsed.get("time_info", {})
        counters = parsed.get("counters", [])
        
        # Get status from PRD3
        if prd3_parsed and prd3_parsed.get("current_status"):
            current_status_data = prd3_parsed["current_status"]
            status_code = current_status_data.get("current_status")
            machine_status = current_status_data.get("status")
            
            # Override "off" to "standby" if machine is responding and has activity
            if machine_status == "off":
                has_power_on_time = time_info.get("power_on_time", "000000000") != "000000000"
                has_program = bool(program_info.get("operation_program_no"))
                if has_power_on_time or has_program:
                    machine_status = "standby"
        else:
            machine_status = "operating" if program_info.get("operation_program_no") else "standby"
        
        # Format time strings
        def format_time(time_str: str) -> str:
            if not time_str or len(time_str) != 9:
                return time_str
            try:
                return f"{time_str[0:2]}{time_str[2:4]}:{time_str[4:6]}.{time_str[6:9]}"
            except (ValueError, IndexError):
                return time_str
        
        status_data = {
            "ip_address": db_machine.ip_address,
            "timestamp": datetime.now().isoformat(),
            "units": db_machine.units,
            "program_name": program_info.get("operation_program_no", "----"),
            "cycle_time": format_time(time_info.get("total_operation_time", "000000000")),
            "cutting_time": format_time(time_info.get("operation_time", "000000000")),
            "non_cutting_time": "000000:00.0",
            "power_on_hours": format_time(time_info.get("power_on_time", "000000000")),
            "operation_time": format_time(time_info.get("operation_time", "000000000")),
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
        
        # Get alarms from Telnet
        try:
            alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
            if alarm_data_raw:
                alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=None)
                all_alarms = alarm_parsed.get("alarms", []) + alarm_parsed.get("loading_alarms", [])
                # Enrich with lookup data
                enriched_alarms = [enrich_alarm_with_lookup(alarm) for alarm in all_alarms]
                status_data["alarms"] = enriched_alarms
            else:
                status_data["alarms"] = []
        except Exception as e:
            logger.warning(f"Failed to fetch alarms for machine {machine_id}: {e}")
            status_data["alarms"] = []
        
        # Override status to 'error' if there are active alarms (unless machine is off)
        if status_data.get("alarms") and machine_status != "off":
            machine_status = "error"
            status_data["status"] = "error"
        
        status_data["machine_id"] = machine_id
        status_data["machine_name"] = db_machine.name
        
        return status_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch machine status: {str(e)}",
        )


@router.get("/{machine_id}/running-log")
async def get_running_log(machine_id: int, db: Session = Depends(get_db)):
    """Get running log data (time display) from MONTR via Telnet."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        from app.clients.telnet_client import get_or_create_connection
        from app.parsers.montr_parser_v2 import parse_montr_v2
        from datetime import datetime
        
        telnet_client = await get_or_create_connection(
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
        
        def format_time(time_str: str) -> str:
            if not time_str or len(time_str) != 9:
                return time_str
            try:
                return f"{time_str[0:2]}{time_str[2:4]}:{time_str[4:6]}.{time_str[6:9]}"
            except (ValueError, IndexError):
                return time_str
        
        data = {
            "machine_id": machine_id,
            "cycle_time": format_time(time_info.get("total_operation_time", "000000000")),
            "cutting_time": format_time(time_info.get("operation_time", "000000000")),
            "non_cutting_time": "000000:00.0",
            "power_on_hours": format_time(time_info.get("power_on_time", "000000000")),
            "operation_time": format_time(time_info.get("operation_time", "000000000")),
            "timestamp": datetime.now().isoformat(),
        }
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching running log for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/counters")
async def get_work_counters(machine_id: int, db: Session = Depends(get_db)):
    """Get workpiece counter data from MONTR via Telnet."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        from app.clients.telnet_client import get_or_create_connection
        from app.parsers.montr_parser_v2 import parse_montr_v2
        from datetime import datetime
        
        telnet_client = await get_or_create_connection(
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
        
        data = {
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
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching counters for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/alarms")
async def get_alarms(machine_id: int, db: Session = Depends(get_db)):
    """Get alarm log data from ALARM via Telnet."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        from app.clients.telnet_client import get_or_create_connection
        from app.parsers.alarm_parser_v2 import parse_alarm_v2
        from app.utils.alarm_code_lookup import enrich_alarm_with_lookup
        from datetime import datetime
        
        telnet_client = await get_or_create_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )
        
        alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
        
        if alarm_data_raw is None:
            # No alarms or failed to fetch
            data = {
                "machine_id": machine_id,
                "alarms": [],
                "loading_alarms": [],
                "timestamp": datetime.now().isoformat(),
            }
            return data
        
        alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=None)
        
        # Enrich alarms with lookup data
        alarms = [enrich_alarm_with_lookup(alarm) for alarm in alarm_parsed.get("alarms", [])]
        loading_alarms = [enrich_alarm_with_lookup(alarm) for alarm in alarm_parsed.get("loading_alarms", [])]
        
        data = {
            "machine_id": machine_id,
            "alarms": alarms,
            "loading_alarms": loading_alarms,
            "timestamp": datetime.now().isoformat(),
        }
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alarms for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


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

    try:
        if source == "table":
            # Fetch tool table from TOLNI1 (inches) or TOLNM1 (millimeters) via Telnet
            # Phase 5: Using Telnet for data reads (FTP deprecated for data, kept only for file transfers)
            from app.clients.telnet_client import get_or_create_connection
            from app.parsers.tolni_parser_v2 import parse_tolni_v2
            
            # Use pooled connection (reused across operations)
            telnet_client = await get_or_create_connection(
                ip_address=db_machine.ip_address,
                port=10000,  # Telnet port
                timeout=10
            )
            
            # Use machine.units to select correct data name (TOLNI1 vs TOLNM1)
            data_name = "TOLNI1" if db_machine.units == 'in' else "TOLNM1"
            tool_table_content = await telnet_client.get_tool_table_data(units=db_machine.units, verbose=False)
            if tool_table_content is None:
                # Connection stays in pool - don't disconnect
                # Check if we have a more specific error from the Telnet client
                # CM7500 error (status code 40) means "editing communication data" - data is open on machine
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to load {data_name} via Telnet. The machine may be busy (CM7500: editing communication data) or Telnet port 10000 may be blocked. Close any open data files on the machine and try again.",
                )
            
            # Validate that we got TOLN data, not ATCTL data
            # TOLN data should start with T## lines, ATCTL starts with M## lines
            if tool_table_content.strip().startswith('M'):
                logger.error(f"Received ATCTL data instead of TOLN data for {data_name} - possible connection/data mix-up")
                # Connection stays in pool - don't disconnect
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Data type mismatch: received ATCTL data instead of {data_name}. Please try again.",
                )
            
            # Parse the tool table using schema-based parser
            parsed = parse_tolni_v2(
                tool_table_content.encode('utf-8'),
                units=db_machine.units,
                control_version=None  # Auto-detect control version
            )
            
            # Merge pot numbers from ATCTL into TABLE data (reverse merge: TOLN -> ATCTL)
            # This allows TABLE view to show which pot each tool is in
            try:
                from app.parsers.atctl_parser_v2 import parse_atctl_v2
                
                # Fetch ATC data to get pot mappings (reuse same pooled connection)
                atc_data = await telnet_client.get_atc_magazine_data(control_version=None)
                
                if atc_data:
                    atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=None)
                    
                    # Create reverse lookup: tool_number -> ATCTL data
                    # This includes: pot_number, group, tool_type, color
                    atc_lookup = {}
                    for atc_tool in atc_parsed.get("tools", []):
                        tool_num = atc_tool.get("tool_number")
                        pot_number = atc_tool.get("pot_number")
                        
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
                    for tool in parsed.get("tools", []):
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
                # Connection stays in pool - don't disconnect
            except Exception as e:
                logger.warning(f"Failed to merge pot numbers into TABLE data: {e}")
                # Continue without pot numbers - TABLE data is still valid
            
            # Connection stays in pool for reuse - don't disconnect
            parsed["machine_id"] = machine_id
            parsed["source"] = "tool_table"
            parsed["protocol"] = "telnet"  # Track which protocol was used
            
            # Also fetch program_name from MEM while we have Telnet connection open
            try:
                from app.parsers.mem_parser import parse_mem
                mem_data = await telnet_client.get_memory_data()
                if mem_data:
                    logger.debug(f"Raw MEM content: {repr(mem_data)}")
                    parsed_mem = parse_mem(mem_data.encode('utf-8'))
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
            # Default: ATC tool data from Telnet (Phase 5: Replace HTTP/FTP reads)
            from app.clients.telnet_client import get_or_create_connection
            from app.parsers.atctl_parser_v2 import parse_atctl_v2
            from app.parsers.tolni_parser_v2 import parse_tolni_v2
            
            # If raw_html requested, still use HTTP for now (for debugging)
            if raw_html:
                http_client = CNCHttpClient(db_machine.ip_address, port=db_machine.http_port)
                html = http_client._send_request("/tool")
                return {
                    "machine_id": machine_id,
                    "source": "atc",
                    "raw_html": html
                }
            
            # Use pooled connection (reused across operations)
            telnet_client = await get_or_create_connection(
                ip_address=db_machine.ip_address,
                port=10000,  # Telnet port
                timeout=10
            )
            
            # Get ATC magazine data (pot/tool mappings)
            # Retry logic is handled in telnet_client.load_data()
            atc_data = await telnet_client.get_atc_magazine_data(control_version=None, verbose=False)
            if atc_data is None:
                # Connection stays in pool - don't disconnect
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to load ATCTL/ATCTLD via Telnet. The machine may be busy (CM7500: editing communication data) or Telnet port 10000 may be blocked. Close any open data files on the machine and try again.",
                )
            
            # Validate that we got ATCTL data, not TOLN data
            # ATCTL data should start with M## lines, TOLN starts with T## lines
            if atc_data.strip().startswith('T'):
                logger.error(f"Received TOLN data instead of ATCTL data - possible connection/data mix-up")
                # Connection stays in pool - don't disconnect
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Data type mismatch: received TOLN data instead of ATCTL. Please try again.",
                )
            
            # Parse ATC data
            atc_parsed = parse_atctl_v2(atc_data.encode('utf-8'), control_version=None)
            
            # Get tool table data to merge tool details (diameter, length, name)
            # Use the SAME pooled connection (semaphore ensures serialization)
            # Note: If TOLN fails, we still return ATC data (just without tool details)
            data_name = "TOLNI1" if db_machine.units == 'in' else "TOLNM1"
            tool_table_content = None
            try:
                # Reuse same pooled connection (semaphore ensures operations are serialized)
                tool_table_content = await telnet_client.get_tool_table_data(units=db_machine.units, verbose=False)
                
                # Validate TOLN data - should start with T## lines, not M## (ATCTL)
                if tool_table_content:
                    first_line = tool_table_content.strip().split('\n')[0].strip() if tool_table_content.strip() else ""
                    if first_line.startswith('M'):
                        logger.error(f"Received ATCTL data instead of TOLN data ({data_name}) - possible connection/data mix-up. First line: {first_line[:50]}")
                        tool_table_content = None  # Don't use wrong data
                    elif not first_line.startswith('T') and first_line:
                        logger.warning(f"TOLN data ({data_name}) doesn't start with T## - unexpected format. First line: {first_line[:50]}")
                # Connection stays in pool - don't disconnect
            except Exception as e:
                logger.warning(f"Failed to load {data_name} for ATC merge (will continue without tool details): {e}")
                # Connection stays in pool - don't disconnect
            
            if tool_table_content is None:
                logger.warning(f"TOLN data ({data_name}) not available for ATC merge - ATC tools will have pot/tool mappings but no diameter/length/name")
            
            # Merge ATC positions with tool details
            tools = []
            tool_lookup = {}
            
            if tool_table_content:
                tool_table_parsed = parse_tolni_v2(
                    tool_table_content.encode('utf-8'),
                    units=db_machine.units,
                    control_version=atc_parsed.get("control_version")
                )
                logger.debug(f"Loaded {len(tool_table_parsed.get('tools', []))} tools from {data_name} for ATC merge (units={db_machine.units})")
                
                # Create lookup by tool number
                for tool in tool_table_parsed.get("tools", []):
                    tool_num = tool.get("tool_number")
                    if tool_num:
                        tool_lookup[tool_num] = tool
                        logger.debug(f"Added tool {tool_num} to lookup: name={tool.get('tool_name')}, diameter={tool.get('diameter')}, length={tool.get('length')}")
            else:
                logger.warning(f"No TOLN data available for ATC merge - ATC tools will have no diameter/length/name")
            
            # Merge ATC tools with tool details from TOLN
            # Match by tool_number to correlate pot position with tool data
            # Only include tools that have valid TOLN data to ensure we're using the active TOLN file
            for atc_tool in atc_parsed.get("tools", []):
                tool_num = atc_tool.get("tool_number")
                if tool_num and tool_num > 0 and tool_num != 255:  # Skip "not set" and "cap setting"
                    # Only include tools that exist in TOLN data
                    # This ensures we're using the active TOLN file (TOLNI1 or TOLNM1 based on machine.units)
                    if tool_num in tool_lookup:
                        tol_tool = tool_lookup[tool_num]
                        merged_tool = {
                            "pot_number": atc_tool.get("pot_number"),
                            "tool_number": tool_num,
                            "tool_name": tol_tool.get("tool_name"),
                            "diameter": tol_tool.get("diameter"),
                            "length": tol_tool.get("length"),
                            "group": atc_tool.get("group"),
                            "life": None,  # Not in ATCTL
                            "tool_type": atc_tool.get("tool_type"),
                            "color": atc_tool.get("color"),
                        }
                        logger.debug(f"Merged ATC pot {merged_tool.get('pot_number')} tool {tool_num}: diameter={merged_tool['diameter']}, length={merged_tool['length']}, units={db_machine.units}, toln_source={data_name}")
                        tools.append(merged_tool)
                    else:
                        logger.debug(f"Tool {tool_num} in ATC pot {atc_tool.get('pot_number')} not found in TOLN data ({data_name}) - skipping")
            
            data = {
                "tools": tools,
                "machine_id": machine_id,
                "source": "atc",
                "protocol": "telnet",
                "units": db_machine.units,  # Ensure units are included in response
                "control_version": atc_parsed.get("control_version"),
                "toln_source": data_name  # Track which TOLN file was used
            }
            
            logger.info(f"ATC data merged: {len(tools)} tools, TOLN source={data_name}, units={db_machine.units}")
            
            # Also fetch program_name from MEM using same pooled connection
            try:
                from app.parsers.mem_parser import parse_mem
                # Reuse same pooled connection (semaphore ensures serialization)
                mem_data = await telnet_client.get_memory_data()
                if mem_data:
                    logger.debug(f"Raw MEM content: {repr(mem_data)}")
                    parsed_mem = parse_mem(mem_data.encode('utf-8'))
                    program_name = parsed_mem.get("program_name")
                    if program_name:
                        data["program_name"] = program_name
                        logger.debug(f"Extracted program_name from MEM: {program_name}")
                # Connection stays in pool - don't disconnect
            except Exception as e:
                logger.debug(f"Failed to fetch program_name from MEM: {e}")
                # Connection stays in pool - don't disconnect
            
            return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tools for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{machine_id}/tools/atc/pot/{pot_number}/color")
async def change_tool_color(
    machine_id: int,
    pot_number: int,
    tool_number: int = Query(..., description="Tool number in the pot"),
    color: int = Query(..., description="Color value (0-7)"),
    db: Session = Depends(get_db)
):
    """
    Change tool color in ATC magazine.
    
    Args:
        machine_id: Machine ID
        pot_number: Pot number (1-99)
        tool_number: Tool number in the pot (for verification)
        color: Color value (0=None, 1=Blue, 2=Red, 3=Purple, 4=Green, 5=Light Blue, 6=Yellow, 7=White)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    # Validate inputs
    if not 1 <= pot_number <= 99:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pot number: {pot_number} (must be 1-99)",
        )
    
    if not 0 <= color <= 7:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid color value: {color} (must be 0-7)",
        )

    try:
        from app.clients.telnet_client import CNCTelnetClient
        
        # Use pooled connection (reused across operations)
        from app.clients.telnet_client import get_or_create_connection
        telnet_client = await get_or_create_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )
        
        success, status_code = await telnet_client.change_atc_tool_color(
            pot_number=pot_number,
            tool_number=tool_number,
            color=color,
            verbose=True
        )
        
        # Connection stays in pool for reuse - don't disconnect
        
        logger.info(f"Color change result: success={success}, status_code={status_code}")
        
        if not success:
            status_desc = CNCTelnetClient.get_status_description(status_code or "00")
            logger.error(f"Failed to change tool color for pot {pot_number}, tool {tool_number}, color {color}: {status_desc} (status={status_code})")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to change tool color: {status_desc}",
            )
        
        color_names = {0: "None", 1: "Blue", 2: "Red", 3: "Purple", 4: "Green", 5: "Light Blue", 6: "Yellow", 7: "White"}
        return {
            "success": True,
            "pot_number": pot_number,
            "tool_number": tool_number,
            "color": color,
            "color_name": color_names.get(color, "Unknown"),
            "message": f"Tool color changed to {color_names.get(color, 'Unknown')}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing tool color for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/programs")
async def list_programs(
    machine_id: int,
    path: str = "/",
    db: Session = Depends(get_db)
):
    """
    List files and directories on machine via FTP with navigation support.

    Args:
        machine_id: Machine ID
        path: Directory path to list (default: /)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            ip_address=db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        programs = await ftp_client.get_programs(path)
        return {
            "machine_id": machine_id,
            "machine_name": db_machine.name,
            "current_path": path,
            "programs": programs,
            "total_count": len(programs),
        }

    except Exception as e:
        logger.error(f"Error listing programs for machine {machine_id} at path {path}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/position")
async def get_position(machine_id: int, db: Session = Depends(get_db)):
    """
    Get current machine work offsets from POSNI1.NC file via Telnet.

    Returns parsed work offsets (G54-G59) and extended offsets (X01-X48).
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        # Phase 5: Migrate to Telnet for position data (replaces FTP)
        from app.clients.telnet_client import get_or_create_connection
        from app.parsers.posni_parser_v2 import parse_posni_v2
        
        # Use pooled connection
        telnet_client = await get_or_create_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10
        )
        
        # Get position data via Telnet
        position_data = await telnet_client.get_position_data(units=db_machine.units, verbose=False)
        
        if not position_data:
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch POSNI1 data via Telnet",
            )
        
        # Parse using schema-based parser
        parsed = parse_posni_v2(
            position_data.encode('utf-8'),
            units=db_machine.units,
            control_version=None  # Auto-detect
        )
        
        return {
            "machine_id": machine_id,
            "machine_name": db_machine.name,
            "work_offsets": parsed.get("work_offsets", {}),
            "extended_offsets": parsed.get("extended_offsets", {}),
            "fixture_offsets": parsed.get("fixture_offsets", {}),
            "rotary_offsets": parsed.get("rotary_offsets", {}),
            "units": parsed.get("units", db_machine.units),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/download")
async def download_file(
    machine_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    """
    Download a file from the machine via FTP.

    Args:
        machine_id: Machine ID
        file_path: Path to file on machine (e.g., /O2000.NC)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            ip_address=db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        file_content = await ftp_client.download_file(file_path)

        if file_content is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Failed to download file: {file_path}",
            )

        filename = file_path.split('/')[-1]

        return StreamingResponse(
            iter([file_content]),
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file from machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/metadata")
async def get_file_metadata(
    machine_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    """
    Get file metadata including tools and runtime estimates.

    Args:
        machine_id: Machine ID
        file_path: Path to file on machine
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            ip_address=db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        file_content = await ftp_client.download_file(file_path)

        if file_content is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Failed to read file: {file_path}",
            )

        try:
            text_content = file_content.decode('utf-8', errors='replace')
        except Exception:
            text_content = str(file_content)

        # Parse using the comprehensive G-code parser
        parsed = parse_gcode(text_content)

        # Extract tool numbers from parsed tool data
        tools = [tool["tool_number"] for tool in parsed.get("tools", [])]

        return {
            "file_path": file_path,
            "tools": tools,
            "runtime_seconds": int(parsed.get("estimated_runtime_seconds", 0)),
            "has_errors": False,  # G-code parser doesn't detect errors, but that's OK for display
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file metadata from machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/view")
async def view_file(
    machine_id: int,
    file_path: str,
    max_size: int = 8388608,
    db: Session = Depends(get_db)
):
    """
    View file content as text (up to 8MB by default).

    Args:
        machine_id: Machine ID
        file_path: Path to file on machine
        max_size: Maximum file size in bytes (default 8MB)
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            ip_address=db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        file_content = await ftp_client.download_file(file_path)

        if file_content is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Failed to read file: {file_path}",
            )

        if len(file_content) > max_size:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_size} bytes",
            )

        try:
            text_content = file_content.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Error decoding file {file_path}: {e}")
            text_content = str(file_content)

        return {
            "file_path": file_path,
            "content": text_content,
            "size": len(file_content),
            "lines": len(text_content.split('\n')),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing file from machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{machine_id}/upload")
async def upload_file(
    machine_id: int,
    file_path: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a file to the machine via FTP.

    Args:
        machine_id: Machine ID
        file_path: Destination path on machine (e.g., /O2000.NC)
        file: File to upload
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        # Read file content
        file_content = await file.read()

        ftp_client = CNCFtpClient(
            ip_address=db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )

        result = await ftp_client.upload_file(file_content, file_path)

        if not result.get("success"):
            raise Exception(result.get("error", "Upload failed"))

        return {
            "success": True,
            "file_path": file_path,
            "size": len(file_content),
            "message": f"File uploaded successfully to {file_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


