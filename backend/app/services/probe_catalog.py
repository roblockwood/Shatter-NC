"""Blum V4A probe routine catalog (shared with frontend JSON)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "probe_catalog.json"

POISON_WCS = 0.0
POISON_GEOMETRY = 999.0
POISON_TOOL = 0.0


class ProbeCatalogError(ValueError):
    """Invalid probe type, mode, or parameters."""


@lru_cache(maxsize=1)
def load_probe_catalog() -> Dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def get_poison_values() -> Dict[int, float]:
    raw = load_probe_catalog().get("poison") or {}
    return {int(k): float(v) for k, v in raw.items()}


def get_result_macro_numbers() -> List[int]:
    return [int(n) for n in load_probe_catalog().get("result_macros") or []]


def list_routines() -> List[Dict[str, Any]]:
    return list(load_probe_catalog().get("routines") or [])


def list_categories() -> List[Dict[str, Any]]:
    return list(load_probe_catalog().get("categories") or [])


def get_fields() -> Dict[str, Any]:
    return dict(load_probe_catalog().get("fields") or {})


def resolve_routine(routine_id: str, mode: str) -> Dict[str, Any]:
    """Return {routine, mode_key, program, macros} or raise ProbeCatalogError."""
    mode_key = (mode or "").strip().lower()
    if mode_key not in ("probe", "measure"):
        raise ProbeCatalogError(f"Invalid mode {mode!r}; expected probe or measure")

    for routine in list_routines():
        if routine.get("id") != routine_id:
            continue
        modes = routine.get("modes") or {}
        entry = modes.get(mode_key)
        if entry is None:
            raise ProbeCatalogError(
                f"Routine {routine_id!r} does not support mode {mode_key!r}"
            )
        macros = [str(m) for m in entry.get("macros") or []]
        program = int(entry["program"])
        return {
            "routine": routine,
            "mode": mode_key,
            "program": program,
            "macros": macros,
        }
    raise ProbeCatalogError(f"Unknown probe routine {routine_id!r}")


def _is_poison_value(macro: str, value: float, poison: Dict[int, float]) -> bool:
    expected = poison.get(int(macro))
    if expected is None:
        return False
    return abs(float(value) - float(expected)) < 1e-9


def validate_wcs(value: float) -> Optional[str]:
    """Return error message if WCS (#900) is invalid for a run."""
    v = float(value)
    if abs(v - POISON_WCS) < 1e-9:
        return "WCS (#900) is poisoned (0); set G54-G59 or negative G54.1 P"
    if 54.0 <= v <= 59.0:
        return None
    if v <= -1.0:
        return None
    return "WCS (#900) must be 54-59 (G54-G59) or negative (G54.1 P)"


def validate_run_params(
    routine_id: str,
    mode: str,
    params: Dict[str, float],
) -> Tuple[Dict[str, Any], Dict[int, float]]:
    """
    Validate params against catalog.

    params keys may be macro numbers as str/int ("900") or field keys ("wcs").
    Returns (resolved entry, macro_number -> value) ready to write.
    """
    resolved = resolve_routine(routine_id, mode)
    fields = get_fields()
    poison = get_poison_values()

    # Normalize incoming params: accept "900" or field key
    key_to_macro: Dict[str, str] = {}
    for macro, meta in fields.items():
        key_to_macro[str(macro)] = str(macro)
        key = meta.get("key")
        if key:
            key_to_macro[str(key)] = str(macro)

    normalized: Dict[str, float] = {}
    for raw_key, raw_val in (params or {}).items():
        macro = key_to_macro.get(str(raw_key))
        if macro is None:
            raise ProbeCatalogError(f"Unknown parameter {raw_key!r}")
        normalized[macro] = float(raw_val)

    required = resolved["macros"]
    missing = [m for m in required if m not in normalized]
    if missing:
        raise ProbeCatalogError(f"Missing required macros: {', '.join(missing)}")

    extras = [m for m in normalized if m not in required]
    if extras:
        raise ProbeCatalogError(f"Unexpected macros for this routine: {', '.join(extras)}")

    for macro in required:
        value = normalized[macro]
        if _is_poison_value(macro, value, poison):
            raise ProbeCatalogError(
                f"Macro #{macro} still has poison value {poison[int(macro)]}; "
                "set a real job value before run"
            )
        if macro == "900":
            err = validate_wcs(value)
            if err:
                raise ProbeCatalogError(err)

    writes = {int(m): normalized[m] for m in required}
    return resolved, writes


def catalog_for_api() -> Dict[str, Any]:
    """Public catalog payload for GET /probe/catalog."""
    cat = load_probe_catalog()
    return {
        "version": cat.get("version", 1),
        "poison": cat.get("poison"),
        "result_macros": cat.get("result_macros"),
        "fields": cat.get("fields"),
        "categories": cat.get("categories"),
        "routines": cat.get("routines"),
    }
