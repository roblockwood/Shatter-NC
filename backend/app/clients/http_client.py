"""HTTP client for communicating with Brother CNC machines.

Brother CNC machines use a custom HTTP server that requires raw socket connections
due to non-standard HTTP/1.1 implementation.
"""
import socket
import re
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CNCHttpClient:
    """HTTP client for Brother CNC machines using raw sockets."""

    def __init__(self, ip_address: str, port: int = 80, timeout: int = 5):
        """
        Initialize HTTP client.

        Args:
            ip_address: CNC machine IP address
            port: HTTP port (default 80)
            timeout: Socket timeout in seconds
        """
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout

    def _send_request(self, endpoint: str) -> str:
        """
        Send raw HTTP request to CNC and return response body.

        Args:
            endpoint: HTTP endpoint (e.g., '/running_log')

        Returns:
            Response body as string

        Raises:
            ConnectionError: If unable to connect
            TimeoutError: If request times out
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

        try:
            # Connect to CNC
            sock.connect((self.ip_address, self.port))

            # Send HTTP/1.0 request (CNC doesn't handle HTTP/1.1 properly)
            request = f"GET {endpoint} HTTP/1.0\r\n\r\n".encode()
            sock.send(request)

            # Receive response with special handling for Brother CNC
            # The machine may close connection abruptly, so we need longer initial timeout
            response = b""
            sock.settimeout(2)  # Give it 2 seconds to start responding
            try:
                # Try to get initial data
                first_chunk = sock.recv(4096)
                if first_chunk:
                    response += first_chunk
                    # Now try to get remaining data with shorter timeout
                    sock.settimeout(0.2)
                    while True:
                        try:
                            chunk = sock.recv(4096)
                            if not chunk:
                                break
                            response += chunk
                        except socket.timeout:
                            break
            except socket.timeout:
                # No response within timeout
                pass

            # Decode response
            response_str = response.decode("utf-8", errors="replace")

            # Split headers and body
            if "\r\n\r\n" in response_str:
                headers, body = response_str.split("\r\n\r\n", 1)
                return body
            else:
                return response_str

        except socket.timeout:
            logger.error(f"Timeout connecting to {self.ip_address}:{self.port}")
            raise TimeoutError(f"Connection to {self.ip_address} timed out")
        except socket.error as e:
            logger.error(f"Socket error: {e}")
            raise ConnectionError(f"Failed to connect to {self.ip_address}: {e}")
        finally:
            sock.close()

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to CNC machine.

        Returns:
            Dict with connection test results
        """
        try:
            start_time = datetime.now()
            response = self._send_request("/")
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds() * 1000  # ms

            # Validate that response looks like it came from a CNC machine
            # (should contain HTML or valid response content)
            if not response or len(response.strip()) == 0:
                return {
                    "success": False,
                    "error": "Empty response from machine",
                    "timestamp": datetime.now().isoformat(),
                }

            return {
                "success": True,
                "latency_ms": round(latency, 2),
                "response_size": len(response),
                "timestamp": datetime.now().isoformat(),
            }
        except (ConnectionError, TimeoutError) as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_running_log(self) -> Dict[str, Any]:
        """
        Fetch running log data (time display).

        Returns:
            Parsed running log data including:
            - program_name: Current program
            - cycle_time: Current cycle time
            - cutting_time: Cutting time
            - non_cutting_time: Non-cutting time
            - power_on_hours: Total power on time
            - operation_time: Operation time
        """
        try:
            html = self._send_request("/running_log")
            return self._parse_running_log(html)
        except Exception as e:
            logger.error(f"Error fetching running log: {e}")
            return {"error": str(e)}

    def _parse_running_log(self, html: str) -> Dict[str, Any]:
        """Parse running log HTML response."""
        data = {}

        # Extract program name (current)
        # Try multiple patterns to handle different HTML formats
        program_match = re.search(
            r"Program.*?Current\s*</td>.*?<td[^>]*>(.*?)</td>", html, re.DOTALL | re.IGNORECASE
        )
        if not program_match:
            # Try alternative pattern
            program_match = re.search(
                r"Program\s+Current[^<]*<td[^>]*>(.*?)</td>", html, re.DOTALL | re.IGNORECASE
            )
        if program_match:
            program_name = program_match.group(1).strip()
            # Only set if not empty and not just whitespace
            if program_name and program_name.strip():
                data["program_name"] = program_name
            else:
                data["program_name"] = None
        else:
            # No program found - set to None explicitly
            data["program_name"] = None

        # Extract cycle time
        cycle_match = re.search(
            r"Cycle time.*?<td[^>]*>([\d:\.]+)</td>", html, re.DOTALL
        )
        if cycle_match:
            data["cycle_time"] = cycle_match.group(1).strip()

        # Extract cutting time
        cutting_match = re.search(
            r"Cutting time.*?<td[^>]*>([\d:\.]+)</td>", html, re.DOTALL
        )
        if cutting_match:
            data["cutting_time"] = cutting_match.group(1).strip()

        # Extract non-cutting time
        non_cutting_match = re.search(
            r"Non cutting time.*?<td[^>]*>([\d:\.]+)</td>", html, re.DOTALL
        )
        if non_cutting_match:
            data["non_cutting_time"] = non_cutting_match.group(1).strip()

        # Extract power on time
        power_match = re.search(
            r"Power on time.*?<td[^>]*>([\d:]+)</td>", html, re.DOTALL
        )
        if power_match:
            data["power_on_hours"] = power_match.group(1).strip()

        # Extract operation time
        operation_match = re.search(
            r"Operation time.*?<td[^>]*>([\d:]+)</td>", html, re.DOTALL
        )
        if operation_match:
            data["operation_time"] = operation_match.group(1).strip()

        # Extract status from page header
        status_match = re.search(r"Status\s*:\s*([\w\s]+)</td>", html)
        if status_match:
            data["status"] = status_match.group(1).strip()

        data["timestamp"] = datetime.now().isoformat()
        return data

    def get_work_counter(self) -> Dict[str, Any]:
        """
        Fetch workpiece counter data.

        Returns:
            Parsed counter data for all 4 counters
        """
        try:
            html = self._send_request("/work_counter")
            return self._parse_work_counter(html)
        except Exception as e:
            logger.error(f"Error fetching work counter: {e}")
            return {"error": str(e)}

    def _parse_work_counter(self, html: str) -> Dict[str, Any]:
        """Parse work counter HTML response."""
        data = {"counters": []}

        # Extract counter data for each of 4 counters
        for i in range(1, 5):
            counter = {"counter_number": i}

            # Find the counter column (they're in order)
            # This is a simplified parser - may need refinement based on actual HTML
            count_pattern = rf"Counter {i}.*?<td[^>]*>(\d+)</td>"
            count_match = re.search(count_pattern, html, re.DOTALL)
            if count_match:
                counter["count"] = int(count_match.group(1))

            data["counters"].append(counter)

        data["timestamp"] = datetime.now().isoformat()
        return data

    def get_alarm_log(self) -> Dict[str, Any]:
        """
        Fetch alarm log data.

        Returns:
            Parsed alarm data
        """
        try:
            html = self._send_request("/alarm_log")
            return self._parse_alarm_log(html)
        except Exception as e:
            logger.error(f"Error fetching alarm log: {e}")
            return {"error": str(e)}

    def _parse_alarm_log(self, html: str) -> Dict[str, Any]:
        """Parse alarm log HTML response."""
        data = {"alarms": []}

        # Map alarm level classes to severity levels
        level_map = {
            "alarm_level_1": "info",
            "alarm_level_2": "warning",
            "alarm_level_3": "error",
            "alarm_level_4": "critical",
        }

        # Extract alarm rows from the table
        # Each alarm is in a <tr> with a class like alarm_level_X
        # Pattern: <tr bgcolor="#000000" class="alarm_level_X">...<td>CODE</td>...<td>MESSAGE</td>...<td>PROGRAM</td>...<td>BLOCK</td>
        row_pattern = r'<tr bgcolor="#000000" class="(alarm_level_\d)">.*?<td[^>]*>\s*([A-Za-z0-9\s]+)</td>.*?<td[^>]*>([^<]+)</td>.*?<td[^>]*>([^<]*)</td>.*?<td[^>]*>([^<]*)</td>.*?</tr>'
        matches = re.finditer(row_pattern, html, re.DOTALL)

        for match in matches:
            level_class = match.group(1)
            code = match.group(2).strip()
            message = match.group(3).strip()
            program = match.group(4).strip()
            block_no = match.group(5).strip()

            # Skip empty rows (those that have &nbsp; or are blank)
            if not code or code == "&nbsp;" or code.isspace():
                continue

            alarm = {
                "code": code,
                "message": message,
                "program": program if program and program != "&nbsp;" else None,
                "block_no": block_no if block_no and block_no != "&nbsp;" else None,
                "severity": level_map.get(level_class, "unknown"),
                "level_class": level_class,
            }
            data["alarms"].append(alarm)

        data["timestamp"] = datetime.now().isoformat()
        return data

    def get_tool_data(self, units: str = 'in') -> Dict[str, Any]:
        """
        Fetch ATC tool data.

        Args:
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.

        Returns:
            Parsed tool table data with units metadata
        """
        try:
            html = self._send_request("/tool")
            return self._parse_tool_data(html, units=units)
        except Exception as e:
            logger.error(f"Error fetching tool data: {e}")
            return {"error": str(e)}

    def _parse_tool_data(self, html: str, units: str = 'in') -> Dict[str, Any]:
        """Parse tool data HTML response.
        
        Parses ATC tool table with the following field mappings:
        - pot_number: Pot/slot number in ATC
        - tool_number: Tool number (integer)
        - tool_name: Tool name/description
        - diameter: Tool diameter (float, from "length x diameter" format)
        - length: Tool length (float, from "length x diameter" format)
        - group: Tool group identifier (string)
        - life: Tool life remaining in minutes (integer)
        - tool_type: Tool type (integer: 1=STD Tool, 2=Large Tool)
        - color: Tool color (integer: 0=no color, 1=blue, 2=red, 3=purple, 4=green, 5=light blue, 6=yellow, 7=white)
        
        Args:
            html: HTML content from /tool endpoint
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
        """
        data = {"tools": []}

        # Parse tool table rows
        # Each row has: pot number, tool number, tool name, tool data (diameter x length), group, life, type, color
        # Extract all <td> elements from each row to get all fields
        
        # Find all tool rows
        row_pattern = r'<tr bgcolor="#[^"]*">.*?</tr>'
        tool_rows = re.findall(row_pattern, html, re.DOTALL)

        for row in tool_rows:
            # Skip header row
            if 'Tool No.' in row or 'Tool name' in row or 'Pot' in row:
                continue

            # Extract all <td> elements from the row
            # Use non-greedy match to handle nested tags and get all TDs
            td_pattern = r'<td[^>]*>(.*?)</td>'
            td_matches = re.findall(td_pattern, row, re.DOTALL)
            
            # Clean HTML tags from each match (in case there are nested tags)
            def clean_td_content(content):
                # Remove any nested HTML tags
                cleaned = re.sub(r'<[^>]+>', '', content)
                # Clean up whitespace and &nbsp;
                cleaned = cleaned.replace('&nbsp;', '').strip()
                return cleaned
            
            td_matches = [clean_td_content(td) for td in td_matches]
            
            if len(td_matches) < 3:  # Need at least pot, tool number, and tool name
                continue
            
            # Parse fields based on position (may vary, but typically: pot, tool#, name, data, group, life, type, color)
            # Clean up &nbsp; and whitespace from all fields
            def clean_field(value):
                if not value:
                    return None
                cleaned = value.replace('&nbsp;', '').strip()
                return cleaned if cleaned else None
            
            pot_number_raw = td_matches[0] if len(td_matches) > 0 else ""
            tool_number_str = td_matches[1] if len(td_matches) > 1 else ""
            tool_name = td_matches[2] if len(td_matches) > 2 else ""
            
            # Clean fields
            pot_number = clean_field(pot_number_raw)
            tool_number_str = clean_field(tool_number_str) or ""
            tool_name = clean_field(tool_name) or ""
            
            # Skip empty tool slots
            if not tool_name or not tool_number_str:
                continue

            try:
                tool_number = int(tool_number_str)
            except (ValueError, TypeError):
                continue

            # Extract tool data (length x diameter format in HTML) - typically 4th column
            length = 0.0
            diameter = 0.0
            if len(td_matches) > 3:
                data_str = td_matches[3].strip()
                data_match = re.search(r'([\d.]+)x\s*([\d.]+)', data_str)
                if data_match:
                    length = float(data_match.group(1))
                    diameter = float(data_match.group(2))

            # Extract additional fields if available (clean &nbsp; from all)
            group = clean_field(td_matches[4]) if len(td_matches) > 4 else None
            
            # Parse life as integer (remove "mi" suffix and extract numeric value)
            life = None
            if len(td_matches) > 5:
                life_str = clean_field(td_matches[5])
                if life_str:
                    # Handle formats like "9952mi  9952" or "9952mi9952" - extract first number before "mi"
                    # Pattern: number followed by "mi" (with optional spaces) then optionally more numbers
                    life_match = re.search(r'(\d+)\s*mi', life_str, re.IGNORECASE)
                    if not life_match:
                        # Fall back to just first number
                        life_match = re.search(r'(\d+)', life_str)
                    if life_match:
                        try:
                            life = int(life_match.group(1))
                        except (ValueError, TypeError):
                            life = None
            
            # Parse tool_type as integer (1=STD Tool, 2=Large Tool)
            tool_type = None
            if len(td_matches) > 6:
                type_str = clean_field(td_matches[6])
                if type_str:
                    # Check for text patterns first, then fall back to numeric
                    type_lower = type_str.lower()
                    if 'std' in type_lower or 'standard' in type_lower:
                        tool_type = 1
                    elif 'large' in type_lower:
                        tool_type = 2
                    else:
                        # Try to extract numeric value
                        type_match = re.search(r'(\d+)', type_str)
                        if type_match:
                            try:
                                tool_type = int(type_match.group(1))
                            except (ValueError, TypeError):
                                tool_type = None
            
            # Parse color as integer (0=no color, 1=blue, 2=red, 3=purple, 4=green, 5=light blue, 6=yellow, 7=white)
            # Color is encoded in the CSS class of the TD element, not in the content
            # Map CSS classes to color values: bg_blue=1, bg_red=2, bg_purple=3, bg_green=4, bg_cyan=5, bg_yellow=6, bg_white=7
            color = None
            
            # Color mapping from CSS class to integer
            color_class_map = {
                'bg_blue': 1,
                'bg_red': 2,
                'bg_purple': 3,
                'bg_green': 4,
                'bg_cyan': 5,  # light blue
                'bg_yellow': 6,
                'bg_white': 7,
            }
            
            # Extract all TD opening tags with their attributes to check CSS classes
            # Find all <td...> tags in order
            td_tag_pattern = r'<td([^>]*)>'
            td_tag_matches = list(re.finditer(td_tag_pattern, row))
            
            # Try column 7 first (expected position), then 8, then 6
            for col_idx in [7, 8, 6]:
                if len(td_tag_matches) > col_idx:
                    # Get the attributes from this TD tag
                    td_attrs = td_tag_matches[col_idx].group(1)
                    # Extract class attribute
                    class_match = re.search(r'class="([^"]*)"', td_attrs)
                    if class_match:
                        classes = class_match.group(1).split()
                        # Check for color class
                        for cls in classes:
                            if cls in color_class_map:
                                color = color_class_map[cls]
                                if col_idx != 7:
                                    logger.debug(f"Tool {tool_number}: Color found in column {col_idx} instead of 7")
                                break
                        if color is not None:
                            break
            
            # Debug logging for tool 1 to inspect color parsing
            if tool_number == 1:
                logger.info(f"Tool 1 DEBUG - Total columns: {len(td_matches)}")
                logger.info(f"Tool 1 DEBUG - All column values: {td_matches}")
                logger.info(f"Tool 1 DEBUG - Extracted values: pot={pot_number}, tool#={tool_number}, name={tool_name}, life={life}, type={tool_type}, color={color}")
                if color is None:
                    logger.info(f"Tool 1 DEBUG - Color is NULL. Column 7 value: '{td_matches[7] if len(td_matches) > 7 else 'N/A'}'")
                    logger.info(f"Tool 1 DEBUG - Column 8 value: '{td_matches[8] if len(td_matches) > 8 else 'N/A'}'")
                    logger.info(f"Tool 1 DEBUG - Raw HTML row (first 1500 chars): {row[:1500]}")

            tool = {
                "pot_number": pot_number,
                "tool_number": tool_number,
                "tool_name": tool_name,
                "diameter": diameter,
                "length": length,
                "group": group,
                "life": life,
                "tool_type": tool_type,
                "color": color,
            }
            data["tools"].append(tool)

        data["timestamp"] = datetime.now().isoformat()
        data["units"] = units
        return data

    def get_status_overview(self, units: str = 'in', include_tools: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive machine status overview.

        Combines data from multiple endpoints for a complete picture.

        Args:
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
            include_tools: If True, include tool data via HTTP (deprecated - use Telnet instead).
                          Defaults to False to avoid stale data.

        Returns:
            Combined status data

        Raises:
            ConnectionError: If unable to retrieve running log (critical data)
        """
        # Get running log data (critical - if this fails, machine is unreachable)
        running_data = self.get_running_log()
        if "error" in running_data:
            raise ConnectionError(f"Failed to get running log: {running_data['error']}")

        overview = {
            "ip_address": self.ip_address,
            "timestamp": datetime.now().isoformat(),
            "units": units,
        }
        overview.update(running_data)

        # Get counter data (optional - don't fail if this fails)
        counter_data = self.get_work_counter()
        if "error" not in counter_data:
            overview["counters"] = counter_data.get("counters", [])

        # Get alarm data (optional - don't fail if this fails)
        alarm_data = self.get_alarm_log()
        if "error" not in alarm_data:
            overview["alarms"] = alarm_data.get("alarms", [])

        # Get tool data (optional - deprecated, use Telnet instead)
        # Only include if explicitly requested (for backward compatibility)
        if include_tools:
            tool_data = self.get_tool_data(units=units)
            if "error" not in tool_data:
                overview["tools"] = tool_data.get("tools", [])
                overview["current_tool"] = tool_data.get("current_tool")

        return overview
    
    def get_status_overview_with_ftp(self, ftp_client, machine, units: str = 'in') -> Dict[str, Any]:
        """
        Get comprehensive machine status overview including FTP data.
        
        This version includes program_name from mem.nc via FTP.
        Use this when FTP client is already available (e.g., when fetching tool table).

        Args:
            ftp_client: CNCFtpClient instance for fetching mem.nc
            units: Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.

        Returns:
            Combined status data with program_name from mem.nc
        """
        # Get base status overview
        overview = self.get_status_overview(units=units)
        
        # Fetch program_name from MEM via Telnet (Phase 5: Replace FTP reads)
        # Note: This is a synchronous method, so we use asyncio.run for async Telnet client
        try:
            import asyncio
            from app.clients.telnet_client import create_fresh_connection
            from app.parsers.mem_parser_v2 import parse_mem_v2
            from app.utils.machine_endpoints import get_telnet_endpoint

            async def fetch_mem():
                telnet_client = await create_fresh_connection(
                    ip_address=get_telnet_endpoint(machine)[0],
                    port=get_telnet_endpoint(machine)[1],
                    timeout=10
                )
                try:
                    mem_data = await telnet_client.get_memory_data(verbose=False)
                    return mem_data
                finally:
                    await telnet_client.disconnect()
            
            mem_data = asyncio.run(fetch_mem())
            if mem_data:
                logger.debug(f"Raw MEM content: {repr(mem_data)}")
                parsed_mem = parse_mem_v2(mem_data.encode('utf-8'), control_version=None)
                program_name = parsed_mem.get("program_name")
                if program_name:
                    overview["program_name"] = program_name
                    logger.debug(f"Extracted program_name from MEM: {program_name}")
                else:
                    logger.debug(f"MEM parsed but no program_name found. Content: {repr(mem_data)}")
            else:
                logger.debug(f"MEM file not found or empty")
        except Exception as e:
            logger.debug(f"Failed to fetch program_name from MEM via Telnet: {e}")
            # Continue without program_name - not critical
        
        return overview
