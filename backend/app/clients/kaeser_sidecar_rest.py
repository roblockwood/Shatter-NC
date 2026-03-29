"""HTTP client for Brown-Industries kaeser-sc2-api (NestJS) maintenance endpoints."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Nest IsEnumKey validates query values against CompressorData *keys*, not enum string values.
MAINTENANCE_QUERY = [
    ("data", "Operational"),
    ("data", "IO_Module"),
    ("data", "Messages"),
    ("data", "Maintenance"),
    ("data", "OperatingHours"),
]


async def fetch_maintenance_bundle(
    base_url: str,
    client: httpx.AsyncClient,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    GET /api/v1/maintenance?data=... — returns operational, iom, messages, maintence, operatingHours.
    """
    url = f"{base_url.rstrip('/')}/api/v1/maintenance"
    try:
        r = await client.get(url, params=MAINTENANCE_QUERY, timeout=45.0)
        if r.status_code != 200:
            return None, f"sidecar HTTP {r.status_code}: {r.text[:200]}"
        data = r.json()
        if not isinstance(data, dict):
            return None, "sidecar returned non-object JSON"
        led_url = f"{base_url.rstrip('/')}/api/v1/maintenance/led-data"
        try:
            lr = await client.get(led_url, timeout=20.0)
            if lr.status_code == 200:
                lj = lr.json()
                if isinstance(lj, dict):
                    data["led_data"] = lj
        except Exception:
            logger.debug("Optional led-data fetch failed for %s", base_url, exc_info=True)
        return data, None
    except httpx.TimeoutException:
        return None, "sidecar request timeout"
    except httpx.RequestError as e:
        return None, f"sidecar request failed: {e}"
    except Exception as e:
        logger.exception("sidecar REST error")
        return None, str(e)
