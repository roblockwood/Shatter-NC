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

        # Extract alarm entries (simplified - actual parsing will depend on HTML structure)
        # Look for alarm codes and messages
        alarm_pattern = r"(\d{4})\s+([^<]+)"
        matches = re.finditer(alarm_pattern, html)

        for match in matches:
            alarm = {
                "code": match.group(1),
                "message": match.group(2).strip(),
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

        # This will need to be refined based on actual HTML structure
        # For now, return placeholder
        data["timestamp"] = datetime.now().isoformat()
        data["note"] = "Tool parsing not yet implemented - needs actual HTML sample"

        return data

    def get_status_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive machine status overview.

        Combines data from multiple endpoints for a complete picture.

        Returns:
            Combined status data
        """
        overview = {
            "ip_address": self.ip_address,
            "timestamp": datetime.now().isoformat(),
        }

        # Get running log data
        running_data = self.get_running_log()
        if "error" not in running_data:
            overview.update(running_data)

        # Get counter data
        counter_data = self.get_work_counter()
        if "error" not in counter_data:
            overview["counters"] = counter_data.get("counters", [])

        # Get alarm data
        alarm_data = self.get_alarm_log()
        if "error" not in alarm_data:
            overview["alarms"] = alarm_data.get("alarms", [])

        return overview
