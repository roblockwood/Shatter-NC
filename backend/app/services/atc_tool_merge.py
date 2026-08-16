"""Merge ATCTL magazine rows with TOLN tool table for ATC display."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _is_spindle_pot(pot_number: Any) -> bool:
    return pot_number is not None and str(pot_number).upper() == "SPINDLE"


def _build_tool_lookup(tool_table_tools: List[dict]) -> Dict[int, dict]:
    lookup: Dict[int, dict] = {}
    for tool in tool_table_tools:
        tool_num = tool.get("tool_number")
        if tool_num:
            lookup[int(tool_num)] = tool
    return lookup


def _merge_atc_row(atc_tool: dict, tool_lookup: Dict[int, dict], tool_num: int) -> dict:
    tol_tool = tool_lookup.get(tool_num, {})
    return {
        "pot_number": atc_tool.get("pot_number"),
        "tool_number": tool_num,
        "tool_name": tol_tool.get("tool_name"),
        "diameter": tol_tool.get("diameter"),
        "length": tol_tool.get("length"),
        "group": atc_tool.get("group"),
        "life": tol_tool.get("life"),
        "tool_type": atc_tool.get("tool_type"),
        "color": atc_tool.get("color"),
    }


def _empty_atc_row(atc_tool: dict) -> dict:
    return {
        "pot_number": atc_tool.get("pot_number"),
        "tool_number": 0,
        "tool_name": None,
        "diameter": None,
        "length": None,
        "group": atc_tool.get("group"),
        "life": None,
        "tool_type": atc_tool.get("tool_type"),
        "color": atc_tool.get("color"),
    }


def merge_atc_tools_for_display(
    atc_parsed: dict,
    tool_table_tools: Optional[List[dict]] = None,
) -> List[dict]:
    """
    Build ATC view rows: one entry per magazine pocket from ATCTL, including empty
    and cap (255) pockets as assignable rows with tool_number 0.
    """
    tool_lookup = _build_tool_lookup(tool_table_tools or [])
    tools: List[dict] = []
    spindle_tool: Optional[dict] = None

    for atc_tool in atc_parsed.get("tools", []):
        pot_number = atc_tool.get("pot_number")
        if _is_spindle_pot(pot_number):
            tool_num = atc_tool.get("tool_number") or 0
            if tool_num > 0 and tool_num != 255:
                spindle_tool = _merge_atc_row(atc_tool, tool_lookup, int(tool_num))
            continue

        if pot_number is None:
            continue

        tool_num = atc_tool.get("tool_number") or 0
        if tool_num in (0, 255):
            tools.append(_empty_atc_row(atc_tool))
        elif tool_num > 0:
            tools.append(_merge_atc_row(atc_tool, tool_lookup, int(tool_num)))

    if spindle_tool:
        tools.insert(0, spindle_tool)

    return tools
