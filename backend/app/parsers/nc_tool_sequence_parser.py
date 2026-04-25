"""Extract ordered tool-change sequence from a Brother NC program.

Supports both G100 and M6 tool-change syntax:
  - N30 G100 T02 X... S5000 M3   (Brother-native, T and G100 on same line)
  - T03                           (pre-select, followed by M6 on next line)
  - M6 T04                        (Fanuc-style, T and M6 on same line)
  - T05 M6                        (T before M6, same line)

Block-skip (/) and inline comments (parentheses, semicolons) are stripped
before pattern matching so commented-out tool calls are ignored.
"""
import re
from typing import List, Tuple

# T word: 1-4 digits, word-boundary anchored so H02/D02 are not matched
_T_WORD = re.compile(r'\bT(\d{1,4})\b')
_M6 = re.compile(r'\bM0?6\b')
_G100 = re.compile(r'\bG100\b')


def _clean_line(line: str) -> str:
    """Strip comments from a single NC line.

    Returns an empty string for block-skip lines (starting with /)
    so they are completely ignored by the tool sequence extractor.
    """
    stripped = line.lstrip()
    # Block-skip lines are ignored entirely — they run only when block-skip
    # is OFF (tool measurement/setup pass) and are not part of the program
    if stripped.startswith('/'):
        return ''
    # Remove parenthesised comments
    stripped = re.sub(r'\([^)]*\)', '', stripped)
    # Remove semicolon-style comments
    stripped = re.sub(r';.*$', '', stripped)
    return stripped.strip()


def extract_tool_sequence(nc_content: str) -> List[int]:
    """Return the ordered list of tool numbers called in *nc_content*.

    Each M6 or G100 event contributes exactly one entry.  Repeated calls to
    the same tool on consecutive lines produce one entry each (the controller
    would execute each change).

    Args:
        nc_content: Full text of an NC program.

    Returns:
        List of integer tool numbers in the order they are called.
    """
    cleaned: List[str] = [_clean_line(ln) for ln in nc_content.splitlines()]
    sequence: List[int] = []

    for i, line in enumerate(cleaned):
        if not line:
            continue

        has_g100 = bool(_G100.search(line))
        has_m6 = bool(_M6.search(line))

        if not (has_g100 or has_m6):
            continue

        t_match = _T_WORD.search(line)
        if t_match:
            # T appears on the same line as G100 / M6 — most common pattern
            sequence.append(int(t_match.group(1)))
        elif has_m6:
            # T may be pre-selected on the line immediately before M6
            prev = cleaned[i - 1] if i > 0 else ''
            prev_t = _T_WORD.search(prev)
            if prev_t:
                sequence.append(int(prev_t.group(1)))

    return sequence


def build_transition_counts(tool_sequence: List[int]) -> dict:
    """Return directed transition counts from a tool sequence.

    Args:
        tool_sequence: Ordered list of tool numbers.

    Returns:
        Dict of ``(from_tool, to_tool) -> count`` for every consecutive
        dissimilar pair in *tool_sequence*.
    """
    counts: dict = {}
    for a, b in zip(tool_sequence, tool_sequence[1:]):
        if a != b:
            counts[(a, b)] = counts.get((a, b), 0) + 1
    return counts
