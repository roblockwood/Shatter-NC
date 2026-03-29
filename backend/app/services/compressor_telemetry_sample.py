"""Numeric pressure / outlet temperature from SC2 operational payloads for timeline samples."""
from __future__ import annotations

import math
from typing import Any, Dict, Optional


def _as_float(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return None if math.isnan(x) else x
    if isinstance(v, str):
        try:
            x = float(v.strip())
            return None if math.isnan(x) else x
        except ValueError:
            return None
    return None


def telemetry_fields_from_operational(operational: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return flat keys stored on compressor_status_samples.metrics for charting."""
    out: Dict[str, Any] = {}
    if not operational or not isinstance(operational, dict):
        return out
    p = operational.get("pressure")
    if isinstance(p, dict):
        pv = _as_float(p.get("value"))
        if pv is not None:
            out["psi"] = pv
        u = p.get("unit")
        if isinstance(u, str) and u.strip():
            out["psi_unit"] = u.strip()
    t = operational.get("outletTemp")
    if isinstance(t, dict):
        tv = _as_float(t.get("value"))
        if tv is not None:
            out["outlet_temp"] = tv
        u = t.get("unit")
        if isinstance(u, str) and u.strip():
            out["temp_unit"] = u.strip()
    return out
