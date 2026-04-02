"""Map Kaeser SC2/Connect payloads to Shatter compressor_status shape."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    if isinstance(dt, str):
        return dt
    return str(dt)


def messages_to_alarms(messages: Any) -> List[Dict[str, Any]]:
    if not isinstance(messages, list):
        return []
    out: List[Dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        mid = m.get("messageId")
        out.append(
            {
                "code": str(mid) if mid is not None else "",
                "message": m.get("message") or "",
                "message_type": m.get("messageType"),
                "message_date": _iso(m.get("messageDate")),
            }
        )
    return out


def _normalize_led_inner(led_raw: Any) -> Optional[Dict[str, Any]]:
    """Sidecar may publish { "led-data": { load, idle, ... } } or a flat dict."""
    if not isinstance(led_raw, dict):
        return None
    inner = led_raw.get("led-data")
    if isinstance(inner, dict):
        return inner
    return led_raw


def infer_status(
    operational: Optional[Dict[str, Any]],
    led_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Map Kaeser SC2 compressorState (often raw HMI text) to a coarse Shatter status.
    When SC2 load/idle LEDs are present, they take precedence — compressorState
    often lags while the panel LEDs (and UI) reflect load/idle immediately.
    Order matters: avoid treating 'unload', 'no load', 'download' as load.
    """
    if operational is not None:
        ps = str(operational.get("powerState") or "").lower().strip()
        if ps == "off":
            return "stopped"

    led_inner = _normalize_led_inner(led_data)
    if led_inner is not None:
        if led_inner.get("load") is True:
            return "load"
        if led_inner.get("idle") is True:
            return "idle"

    if operational is None:
        return "unknown"
    ps = str(operational.get("powerState") or "").lower().strip()
    cs = str(operational.get("compressorState") or "").lower().strip()
    if not cs:
        if ps in ("on", "yes", "true", "1"):
            return "online"
        return "unknown"

    if "back pressure" in cs:
        return "back_pressure"

    # Not on load (check before generic 'load' substring)
    if (
        "no load" in cs
        or ("unload" in cs and "on load" not in cs)
        or "off load" in cs
        or cs == "idle"
        or " idle" in cs
        or cs.startswith("idle")
        or "standby" in cs
        or cs == "ready"
        or "bereit" in cs
        or "leerlauf" in cs
    ):
        return "idle"

    # On load / producing (strings that often omit the word 'load' entirely)
    if (
        cs == "load"
        or "on load" in cs
        or "full load" in cs
        or "running" in cs
        or "operating" in cs
        or "production" in cs
        or "produktion" in cs
        or "belastung" in cs
        or " unter last" in cs
        or cs.endswith(" last")
    ):
        if "not running" in cs or "not operating" in cs:
            return "idle"
        return "load"

    if "load" in cs and "download" not in cs:
        return "load"

    if cs:
        return cs.replace(" ", "_")
    return "online"


def build_metrics(
    operational: Optional[Dict[str, Any]],
    rest_bundle: Optional[Dict[str, Any]],
    rest_error: Optional[str],
    mqtt_stale: bool,
) -> Dict[str, Any]:
    m: Dict[str, Any] = {}
    if operational:
        m["operational"] = operational
    if rest_bundle:
        for k in ("iom", "maintence", "maintenance", "operatingHours", "led_data"):
            if k in rest_bundle and rest_bundle[k] is not None:
                m[k] = rest_bundle[k]
    if rest_error:
        m["error"] = rest_error
    if mqtt_stale:
        m["mqtt_stale"] = True
    return m


def build_compressor_status_payload(
    *,
    compressor_id: int,
    compressor_name: str,
    ip_address: str,
    enabled: bool,
    poll_interval_seconds: int,
    operational: Optional[Dict[str, Any]],
    rest_bundle: Optional[Dict[str, Any]],
    rest_error: Optional[str],
    last_operational_mqtt_at: Optional[datetime],
    poll_timestamp: datetime,
    response_time_ms: int,
) -> Dict[str, Any]:
    now = poll_timestamp
    stale_s = 15.0
    mqtt_stale = False
    if operational is None and last_operational_mqtt_at:
        age = (now - last_operational_mqtt_at).total_seconds()
        mqtt_stale = age > stale_s

    if operational is None and rest_bundle and isinstance(rest_bundle.get("operational"), dict):
        operational = rest_bundle["operational"]

    # Telemetry drives online; REST errors still surface in metrics / error when we have no data.
    is_online = operational is not None

    led_raw = None
    if rest_bundle and isinstance(rest_bundle.get("led_data"), dict):
        led_raw = rest_bundle["led_data"]

    status = infer_status(operational, led_raw) if is_online else "offline"

    messages = None
    if rest_bundle and isinstance(rest_bundle.get("messages"), list):
        messages = rest_bundle["messages"]
    alarms = messages_to_alarms(messages or [])

    metrics = build_metrics(operational, rest_bundle, rest_error, mqtt_stale)

    err: Optional[str] = None
    if not is_online and rest_error:
        err = rest_error

    out: Dict[str, Any] = {
        "asset_kind": "compressor",
        "compressor_id": compressor_id,
        "compressor_name": compressor_name,
        "ip_address": ip_address,
        "enabled": enabled,
        "poll_interval_seconds": poll_interval_seconds,
        "is_online": is_online,
        "status": status,
        "alarms": alarms,
        "metrics": metrics,
        "poll_timestamp": now.isoformat(),
        "last_successful_poll_at": now.isoformat() if is_online else None,
        "response_time_ms": response_time_ms,
    }
    if err:
        out["error"] = err

    return out
