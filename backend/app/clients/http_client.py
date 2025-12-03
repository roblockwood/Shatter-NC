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

            # Receive response
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

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
        program_match = re.search(
            r"Program.*?Current\s*</td>.*?<td[^>]*>(.*?)</td>", html, re.DOTALL
        )
        if program_match:
            data["program_name"] = program_match.group(1).strip()

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

    def get_tool_data(self) -> Dict[str, Any]:
        """
        Fetch ATC tool data.

        Returns:
            Parsed tool table data
        """
        try:
            html = self._send_request("/tool")
            return self._parse_tool_data(html)
        except Exception as e:
            logger.error(f"Error fetching tool data: {e}")
            return {"error": str(e)}

    def _parse_tool_data(self, html: str) -> Dict[str, Any]:
        """Parse tool data HTML response."""
        data = {"tools": []}

        # Parse tool table rows
        # Each row has: pot number, tool number, tool name, tool data (diameter x length), group, life, type, color
        # Example: <td width="80" align="right" class="border_line2 lang_same">01</td>
        #          <td width="190" align="center" class="border_line2 lang_same">.250 3FL      </td>
        #          <td width="150" align="right" class="border_line2 lang_same">  3.4494x  0.0000</td>

        # Find all tool rows (they start with pot number)
        row_pattern = r'<tr bgcolor="#[^"]*">.*?</tr>'
        tool_rows = re.findall(row_pattern, html, re.DOTALL)

        for row in tool_rows:
            # Skip header row
            if 'Tool No.' in row or 'Tool name' in row:
                continue

            # Extract tool number
            tool_num_match = re.search(r'<td width="80"[^>]*>(\d+)</td>', row)
            if not tool_num_match:
                continue

            tool_number = int(tool_num_match.group(1))

            # Extract tool name
            name_match = re.search(r'<td width="190"[^>]*>([^<]+)</td>', row)
            tool_name = name_match.group(1).strip() if name_match else ""

            # Skip empty tool slots (those with &nbsp; or empty names)
            if tool_name == "&nbsp;" or tool_name == "" or tool_name.isspace():
                continue

            # Extract tool data (length x diameter format in HTML)
            data_match = re.search(r'<td width="150"[^>]*>\s*([\d.]+)x\s*([\d.]+)</td>', row)
            length = float(data_match.group(1)) if data_match else 0.0
            diameter = float(data_match.group(2)) if data_match else 0.0

            tool = {
                "tool_number": tool_number,
                "tool_name": tool_name,
                "diameter": diameter,
                "length": length,
            }
            data["tools"].append(tool)

        data["timestamp"] = datetime.now().isoformat()
        return data

    def get_status_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive machine status overview.

        Combines data from multiple endpoints for a complete picture.

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

        # Get tool data (optional - don't fail if this fails)
        tool_data = self.get_tool_data()
        if "error" not in tool_data:
            overview["tools"] = tool_data.get("tools", [])
            overview["current_tool"] = tool_data.get("current_tool")

        return overview
