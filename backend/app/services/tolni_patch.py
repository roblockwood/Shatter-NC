"""Patch tool names in TOLNn file content without altering other fields."""
from __future__ import annotations

import re
from typing import Dict, Iterable, Set

TOOL_NAME_CSV_INDEX = 8
TOOL_NAME_PARTS_INDEX = TOOL_NAME_CSV_INDEX + 1  # parts[0] is T## prefix
TOOL_NAME_INNER_MAX = 14
_TOOL_LINE_RE = re.compile(r"^T(\d{1,2}),", re.IGNORECASE)


def normalize_tool_name(name: str) -> str:
    """Strip and truncate to Brother inner field width (14 chars inside quotes)."""
    return name.strip()[:TOOL_NAME_INNER_MAX]


def format_tool_name_field(name: str) -> str:
    """Encode tool name as Brother CSV field: 16 chars including single quotes."""
    inner = normalize_tool_name(name).ljust(TOOL_NAME_INNER_MAX)
    return f"'{inner}'"


def tool_names_match(expected: str, actual: str) -> bool:
    return normalize_tool_name(expected) == normalize_tool_name(actual)


def _tool_number_from_line(line: str) -> int | None:
    match = _TOOL_LINE_RE.match(line.strip())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def patch_tool_name_in_line(line: str, tool_number: int, new_name: str) -> str:
    """Replace only the tool_name CSV field on a single T## line."""
    stripped = line.strip()
    actual = _tool_number_from_line(stripped)
    if actual is None:
        raise ValueError(f"Not a tool line: {line!r}")
    if actual != tool_number:
        raise ValueError(f"Line is T{actual:02d}, expected T{tool_number:02d}")

    parts = stripped.split(",")
    while len(parts) <= TOOL_NAME_PARTS_INDEX:
        parts.append("")
    parts[TOOL_NAME_PARTS_INDEX] = format_tool_name_field(new_name)
    return ",".join(parts)


def patch_tool_names(content: str, updates: Dict[int, str]) -> str:
    """
    Patch one or more tool names in full TOLN file content.

    Preserves non-tool lines and all other CSV columns on each tool row.
    """
    if not updates:
        return content

    remaining: Set[int] = set(updates.keys())
    lines = content.split("\n")
    patched_lines: list[str] = []

    for line in lines:
        tool_num = _tool_number_from_line(line)
        if tool_num is not None and tool_num in updates:
            patched_lines.append(patch_tool_name_in_line(line, tool_num, updates[tool_num]))
            remaining.discard(tool_num)
        else:
            patched_lines.append(line)

    if remaining:
        missing = ", ".join(f"T{n:02d}" for n in sorted(remaining))
        raise ValueError(f"Tool(s) not found in TOLN content: {missing}")

    return "\n".join(patched_lines)


def collect_tool_names(content: str, tool_numbers: Iterable[int]) -> Dict[int, str]:
    """Read current tool_name values (stripped of quotes/padding) from content."""
    wanted = set(tool_numbers)
    found: Dict[int, str] = {}
    for line in content.split("\n"):
        tool_num = _tool_number_from_line(line)
        if tool_num is None or tool_num not in wanted:
            continue
        parts = line.strip().split(",")
        if len(parts) <= TOOL_NAME_PARTS_INDEX:
            found[tool_num] = ""
            continue
        raw = parts[TOOL_NAME_PARTS_INDEX].strip()
        if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
            found[tool_num] = raw[1:-1]
        else:
            found[tool_num] = raw
    return found
