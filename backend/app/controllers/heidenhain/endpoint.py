"""Heidenhain OPC UA endpoint URL construction and discovery."""
from __future__ import annotations

import logging
import re
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Default NC server path per Heidenhain Connection Assistant / Core Information Model.
DEFAULT_HEIDENHAIN_ENDPOINT_PATH = "/HEIDENHAIN/NC"

# Match NC server endpoints regardless of hostname casing.
_NC_ENDPOINT_MARKER = "/HEIDENHAIN/NC"


def build_endpoint_url(host: str, port: int, path: Optional[str] = None) -> str:
    """Build opc.tcp URL with optional path suffix."""
    base = f"opc.tcp://{host}:{port}"
    if not path:
        return base
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{base}{normalized}"


def apply_connect_host(endpoint_url: str, connect_host: str) -> str:
    """Replace the host in an EndpointUrl with the address we actually dial."""
    return re.sub(r"^opc\.tcp://[^:/]+", f"opc.tcp://{connect_host}", endpoint_url, count=1)


def pick_nc_endpoint_url(endpoints: List[Any], connect_host: str) -> Optional[str]:
    """
    Select the Heidenhain NC endpoint from GetEndpoints results.

    Prefers URLs containing /HEIDENHAIN/NC (case-insensitive).
    """
    if not endpoints:
        return None

    available = [getattr(ep, "EndpointUrl", str(ep)) for ep in endpoints]
    logger.debug("OPC UA GetEndpoints returned: %s", available)

    nc_urls: List[str] = []
    for ep in endpoints:
        url = getattr(ep, "EndpointUrl", None)
        if not url:
            continue
        if _NC_ENDPOINT_MARKER in url.upper():
            nc_urls.append(apply_connect_host(url, connect_host))

    if nc_urls:
        chosen = nc_urls[0]
        logger.info("Selected Heidenhain NC endpoint: %s", chosen)
        return chosen

    logger.warning(
        "No %s endpoint in GetEndpoints response; available: %s",
        _NC_ENDPOINT_MARKER,
        available,
    )
    return None


async def discover_nc_endpoint_url(
    host: str,
    port: int,
    *,
    timeout: float = 10.0,
) -> Optional[str]:
    """Query the server for endpoints and return the NC server URL if found."""
    from asyncua import Client

    discovery_url = build_endpoint_url(host, port)
    client = Client(url=discovery_url, timeout=timeout)
    try:
        endpoints = await client.connect_and_get_server_endpoints()
        return pick_nc_endpoint_url(endpoints, host)
    except Exception as exc:
        logger.warning(
            "OPC UA GetEndpoints failed for %s: %s: %s",
            discovery_url,
            type(exc).__name__,
            exc or "(no message)",
        )
        return None
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def resolve_endpoint_url(
    host: str,
    port: int,
    *,
    endpoint_url: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    auto_discover: bool = True,
    timeout: float = 10.0,
) -> str:
    """
    Resolve the OPC UA URL to connect to.

    Priority:
    1. Explicit full endpoint_url from machine config
    2. GetEndpoints discovery (when auto_discover)
    3. Built URL from host:port + endpoint_path (default /HEIDENHAIN/NC)
    """
    if endpoint_url and endpoint_url.strip():
        resolved = endpoint_url.strip()
        logger.info("Using configured OPC UA endpoint URL: %s", resolved)
        return resolved

    if auto_discover:
        discovered = await discover_nc_endpoint_url(host, port, timeout=timeout)
        if discovered:
            return discovered

    path = endpoint_path if endpoint_path is not None else DEFAULT_HEIDENHAIN_ENDPOINT_PATH
    resolved = build_endpoint_url(host, port, path)
    logger.info("Using constructed OPC UA endpoint URL: %s", resolved)
    return resolved
