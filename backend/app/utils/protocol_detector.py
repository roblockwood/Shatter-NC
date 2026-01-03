"""Protocol detection utility for Brother CNC machines.

Detects available communication protocols including FOCAS and other
control protocols that may be available on the machine.
"""
import socket
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProtocolDetector:
    """Detect available communication protocols on CNC machines."""

    # Common FOCAS ports (Fanuc Open CNC API Specification)
    FOCAS_PORTS = [
        8193,  # FOCAS1/Ethernet (most common)
        8192,  # Alternative FOCAS port
        8194,  # FOCAS2
        8195,  # FOCAS3
    ]

    # Other common CNC control ports
    OTHER_PORTS = [
        23,    # Telnet
        502,   # Modbus TCP
        102,   # ISO-TSAP (Siemens)
        18245, # OPC UA (common)
        4840,  # OPC UA alternative
        1883,  # MQTT
        9999,  # Custom CNC protocols
    ]

    def __init__(self, ip_address: str, timeout: float = 2.0):
        """
        Initialize protocol detector.

        Args:
            ip_address: Machine IP address
            timeout: Connection timeout in seconds
        """
        self.ip_address = ip_address
        self.timeout = timeout

    def _check_port(self, port: int) -> Tuple[bool, Optional[str]]:
        """
        Check if a port is open and responsive.

        Args:
            port: Port number to check

        Returns:
            Tuple of (is_open, banner_or_error)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.ip_address, port))
            sock.close()

            if result == 0:
                # Port is open, try to get a banner
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.timeout)
                    sock.connect((self.ip_address, port))
                    # Try to receive any initial data
                    sock.settimeout(0.5)
                    try:
                        banner = sock.recv(1024)
                        if banner:
                            return True, banner.decode('utf-8', errors='ignore')[:100]
                    except socket.timeout:
                        pass
                    sock.close()
                    return True, "Port open (no banner)"
                except Exception as e:
                    return True, f"Port open (error reading banner: {str(e)})"
            else:
                return False, None
        except Exception as e:
            return False, str(e)

    def _check_focas_port(self, port: int) -> Dict[str, any]:
        """
        Check if a port appears to be FOCAS.

        Args:
            port: Port number to check

        Returns:
            Dict with detection results
        """
        is_open, banner = self._check_port(port)
        result = {
            "port": port,
            "open": is_open,
            "banner": banner,
            "likely_focas": False,
        }

        if is_open:
            # FOCAS typically responds with specific patterns
            # Port 8193 is the standard FOCAS1/Ethernet port
            if port == 8193:
                result["likely_focas"] = True
                result["protocol"] = "FOCAS1/Ethernet (likely)"
            elif port in [8192, 8194, 8195]:
                result["likely_focas"] = True
                result["protocol"] = f"FOCAS variant (port {port})"

        return result

    def scan_ports(self, port_list: List[int]) -> List[Dict[str, any]]:
        """
        Scan a list of ports.

        Args:
            port_list: List of port numbers to scan

        Returns:
            List of port scan results
        """
        results = []
        for port in port_list:
            is_open, banner = self._check_port(port)
            results.append({
                "port": port,
                "open": is_open,
                "banner": banner,
            })
        return results

    def detect_all(self) -> Dict[str, any]:
        """
        Detect all available protocols.

        Returns:
            Dict with detection results for all protocols
        """
        results = {
            "ip_address": self.ip_address,
            "scan_timestamp": datetime.now().isoformat(),
            "focas": {},
            "other_ports": [],
            "summary": {
                "focas_available": False,
                "other_protocols": [],
            }
        }

        # Check FOCAS ports
        logger.info(f"Scanning FOCAS ports on {self.ip_address}...")
        focas_results = []
        for port in self.FOCAS_PORTS:
            result = self._check_focas_port(port)
            focas_results.append(result)
            if result["open"]:
                results["summary"]["focas_available"] = True
        results["focas"] = {
            "ports_checked": self.FOCAS_PORTS,
            "results": focas_results,
        }

        # Check other common ports
        logger.info(f"Scanning other common ports on {self.ip_address}...")
        other_results = self.scan_ports(self.OTHER_PORTS)
        results["other_ports"] = other_results
        for result in other_results:
            if result["open"]:
                port_name = self._get_port_name(result["port"])
                results["summary"]["other_protocols"].append({
                    "port": result["port"],
                    "name": port_name,
                    "banner": result["banner"],
                })

        return results

    def _get_port_name(self, port: int) -> str:
        """Get common name for a port number."""
        port_names = {
            23: "Telnet",
            502: "Modbus TCP",
            102: "ISO-TSAP (Siemens)",
            18245: "OPC UA",
            4840: "OPC UA",
            1883: "MQTT",
            9999: "Custom/Unknown",
        }
        return port_names.get(port, f"Port {port}")

    async def check_system_files(self, ftp_client) -> Dict[str, any]:
        """
        Check system files for protocol configuration hints.

        Args:
            ftp_client: CNCFtpClient instance

        Returns:
            Dict with system file analysis
        """
        results = {
            "ver_nc": None,
            "io_nc": None,
            "hints": [],
        }

        try:
            # Check VER.NC for version/protocol info
            ver_data = await ftp_client.get_system_file("VER.NC")
            if ver_data:
                results["ver_nc"] = {
                    "available": True,
                    "size": len(ver_data),
                    "preview": ver_data[:200] if len(ver_data) > 200 else ver_data,
                }
                # Look for protocol keywords
                ver_lower = ver_data.lower()
                if "focas" in ver_lower:
                    results["hints"].append("VER.NC mentions FOCAS")
        except Exception as e:
            logger.warning(f"Could not read VER.NC: {e}")

        try:
            # Check IO.NC for protocol configuration
            io_data = await ftp_client.get_system_file("IO.NC")
            if io_data:
                results["io_nc"] = {
                    "available": True,
                    "size": len(io_data),
                }
        except Exception as e:
            logger.warning(f"Could not read IO.NC: {e}")

        return results

    def check_http_endpoints(self, http_client) -> Dict[str, any]:
        """
        Check HTTP endpoints for protocol information.

        Args:
            http_client: CNCHttpClient instance

        Returns:
            Dict with HTTP endpoint analysis
        """
        results = {
            "endpoints_checked": [],
            "protocol_hints": [],
        }

        # Check if there's a protocol info endpoint
        potential_endpoints = [
            "/protocol",
            "/protocols",
            "/api",
            "/focas",
            "/status",
            "/info",
        ]

        for endpoint in potential_endpoints:
            try:
                response = http_client._send_request(endpoint)
                if response and len(response) > 0:
                    results["endpoints_checked"].append({
                        "endpoint": endpoint,
                        "available": True,
                        "response_size": len(response),
                    })
                    # Check for protocol keywords
                    response_lower = response.lower()
                    if "focas" in response_lower:
                        results["protocol_hints"].append(f"{endpoint} mentions FOCAS")
            except Exception:
                pass

        return results


async def detect_protocols(
    ip_address: str,
    http_port: int = 80,
    ftp_client=None,
    http_client=None,
) -> Dict[str, any]:
    """
    Comprehensive protocol detection for a CNC machine.

    Args:
        ip_address: Machine IP address
        http_port: HTTP port (default 80)
        ftp_client: Optional CNCFtpClient instance for system file checks
        http_client: Optional CNCHttpClient instance for HTTP endpoint checks

    Returns:
        Dict with complete protocol detection results
    """
    detector = ProtocolDetector(ip_address)
    results = detector.detect_all()

    # Add system file analysis if FTP client available
    if ftp_client:
        try:
            system_files = await detector.check_system_files(ftp_client)
            results["system_files"] = system_files
        except Exception as e:
            logger.warning(f"Could not check system files: {e}")
            results["system_files"] = {"error": str(e)}

    # Add HTTP endpoint analysis if HTTP client available
    if http_client:
        try:
            http_endpoints = detector.check_http_endpoints(http_client)
            results["http_endpoints"] = http_endpoints
        except Exception as e:
            logger.warning(f"Could not check HTTP endpoints: {e}")
            results["http_endpoints"] = {"error": str(e)}

    return results

