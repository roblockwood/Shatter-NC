"""Tool-centric unified view: TOLN is primary; ATC fields are assignment edges."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.atc_tool_merge import _is_spindle_pot


def _normalize_pot_number(pot_number: Any) -> Optional[int]:
    if pot_number is None:
        return None
    if _is_spindle_pot(pot_number):
        return None
    if isinstance(pot_number, int):
        return pot_number
    try:
        return int(pot_number)
    except (TypeError, ValueError):
        return None


def expand_atc_parsed_to_pocket_count(atc_parsed: dict, num_pockets: int) -> dict:
    """Ensure ATCTL rows include every pocket 1..num_pockets (synthetic empty when absent)."""
    if num_pockets < 1:
        return atc_parsed

    tools = list(atc_parsed.get("tools") or [])
    by_pot: Dict[int, dict] = {}
    passthrough: List[dict] = []

    for row in tools:
        pot = _normalize_pot_number(row.get("pot_number"))
        if pot is None:
            passthrough.append(row)
            continue
        by_pot[pot] = row

    expanded = list(passthrough)
    for pot in range(1, num_pockets + 1):
        if pot in by_pot:
            expanded.append(by_pot[pot])
        else:
            expanded.append(
                {
                    "pot_number": pot,
                    "tool_number": 0,
                    "tool_type": 1,
                    "color": 0,
                }
            )

    return {**atc_parsed, "tools": expanded}


def _build_atc_lookups(
    atc_parsed: dict,
) -> tuple[Dict[int, dict], List[dict], Optional[dict]]:
    """Return tool_number→ATC info, empty pocket stubs, and spindle assignment."""
    by_tool: Dict[int, dict] = {}
    empty_pockets: List[dict] = []
    spindle: Optional[dict] = None

    for atc_tool in atc_parsed.get("tools", []):
        pot_number = atc_tool.get("pot_number")
        tool_num = atc_tool.get("tool_number") or 0

        if _is_spindle_pot(pot_number):
            if tool_num > 0 and tool_num not in (255, 999):
                spindle = {
                    "pot_number": "SPINDLE",
                    "tool_number": int(tool_num),
                    "tool_type": atc_tool.get("tool_type"),
                    "color": atc_tool.get("color"),
                    "group": atc_tool.get("group"),
                }
            continue

        if pot_number is None:
            continue

        if tool_num in (0, 255, 999):
            empty_pockets.append(
                {
                    "pot_number": pot_number,
                    "tool_type": atc_tool.get("tool_type"),
                    "color": atc_tool.get("color"),
                }
            )
        elif tool_num > 0:
            by_tool[int(tool_num)] = {
                "pot_number": pot_number,
                "group": atc_tool.get("group"),
                "tool_type": atc_tool.get("tool_type"),
                "color": atc_tool.get("color"),
            }

    empty_pockets.sort(
        key=lambda row: (
            row["pot_number"]
            if isinstance(row["pot_number"], (int, float))
            else str(row["pot_number"])
        )
    )
    return by_tool, empty_pockets, spindle


def build_unified_tool_view(
    toln_tools: Optional[List[dict]] = None,
    atc_parsed: Optional[dict] = None,
    atc_pockets: Optional[int] = None,
) -> dict:
    """
    Build tool-centric rows with optional ATC assignment overlay.

    TOLN tools are always the primary rows. ATC metadata appears only when a tool
    is assigned to a magazine pocket. Empty pockets are returned separately for a
    subordinate assign-to-pocket UI (not peer rows in the tool table).
    """
    toln_tools = toln_tools or []
    by_tool: Dict[int, dict] = {}
    empty_pockets: List[dict] = []
    spindle: Optional[dict] = None

    if atc_parsed:
        if atc_pockets and atc_pockets > 0:
            atc_parsed = expand_atc_parsed_to_pocket_count(atc_parsed, atc_pockets)
        by_tool, empty_pockets, spindle = _build_atc_lookups(atc_parsed)

    tool_rows: List[dict] = []
    for tol_tool in toln_tools:
        tool_num = tol_tool.get("tool_number")
        if not tool_num:
            continue
        tn = int(tool_num)
        atc = by_tool.get(tn)

        row: dict[str, Any] = {
            "row_kind": "tool",
            "tool_number": tn,
            "tool_name": tol_tool.get("tool_name"),
            "diameter": tol_tool.get("diameter"),
            "length": tol_tool.get("length"),
            "life": tol_tool.get("life"),
            "in_atc": atc is not None,
        }
        if atc:
            row["pot_number"] = atc["pot_number"]
            row["group"] = atc.get("group")
            row["tool_type"] = atc.get("tool_type")
            row["color"] = atc.get("color")
        tool_rows.append(row)

    return {
        "tools": tool_rows,
        "empty_pockets": empty_pockets,
        "spindle": spindle,
        "atc_available": atc_parsed is not None,
    }


def merge_toln_fields_into_tool_table(
    tool_table_tools: List[dict],
    prior_tool_table: Optional[List[dict]] = None,
) -> List[dict]:
    """When ATCTL is temporarily unavailable, keep prior pot/ATC fields on TOLN rows."""
    if not prior_tool_table:
        return tool_table_tools

    prior_by_num: Dict[int, dict] = {}
    for tool in prior_tool_table:
        tool_num = tool.get("tool_number")
        if tool_num is not None:
            prior_by_num[int(tool_num)] = tool

    merged: List[dict] = []
    for tool in tool_table_tools:
        row = dict(tool)
        tool_num = tool.get("tool_number")
        if tool_num is not None:
            prior = prior_by_num.get(int(tool_num))
            if prior:
                for key in ("pot_number", "group", "tool_type", "color"):
                    if prior.get(key) is not None:
                        row[key] = prior[key]
        merged.append(row)
    return merged


def refresh_unified_toln_fields(
    unified: dict,
    toln_tools: List[dict],
) -> dict:
    """Refresh TOLN-sourced columns in cached unified view; preserve ATC assignment edges."""
    if not unified:
        return unified

    by_num: Dict[int, dict] = {}
    for tool in toln_tools:
        tool_num = tool.get("tool_number")
        if tool_num is not None:
            by_num[int(tool_num)] = tool

    refreshed_tools: List[dict] = []
    for row in unified.get("tools") or []:
        updated = dict(row)
        tool_num = row.get("tool_number")
        if tool_num is not None:
            tol = by_num.get(int(tool_num))
            if tol:
                for key in ("tool_name", "diameter", "length", "life"):
                    if key in tol:
                        updated[key] = tol.get(key)
        refreshed_tools.append(updated)

    return {**unified, "tools": refreshed_tools}
