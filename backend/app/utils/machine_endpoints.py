"""Helpers for resolving machine protocol endpoints with per-protocol overrides."""

from typing import Any, Dict, Tuple


DEFAULT_TELNET_PORT = 10000


def get_telnet_endpoint(machine: Any) -> Tuple[str, int]:
    """Return the host/port used for Telnet operations."""
    host = getattr(machine, "telnet_host", None) or machine.ip_address
    port = getattr(machine, "telnet_port", None) or DEFAULT_TELNET_PORT
    return host, port


def get_ftp_endpoint(machine: Any) -> Tuple[str, int]:
    """Return the host/port used for FTP operations."""
    host = getattr(machine, "ftp_host", None) or machine.ip_address
    port = machine.ftp_port
    return host, port


def get_http_endpoint(machine: Any) -> Tuple[str, int]:
    """Return the host/port used for HTTP operations."""
    host = getattr(machine, "http_host", None) or machine.ip_address
    port = machine.http_port
    return host, port


def get_endpoint_summary(machine: Any) -> Dict[str, Dict[str, Any]]:
    """Return resolved protocol endpoints for API responses and logging."""
    telnet_host, telnet_port = get_telnet_endpoint(machine)
    ftp_host, ftp_port = get_ftp_endpoint(machine)
    http_host, http_port = get_http_endpoint(machine)

    return {
        "primary": {"host": machine.ip_address},
        "telnet": {"host": telnet_host, "port": telnet_port},
        "ftp": {"host": ftp_host, "port": ftp_port},
        "http": {"host": http_host, "port": http_port},
    }