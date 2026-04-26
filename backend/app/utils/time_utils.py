"""Time formatting helpers for CNC time counters.

Some CNC sources encode a time value as a **9-digit** string in the form:

    HHMMSSMMM

Where:
  - HH: hours (00-99+; no range enforcement here)
  - MM: minutes
  - SS: seconds
  - MMM: milliseconds

We render this as:

    HHMM:SS.MMM
"""

from __future__ import annotations


def format_cnc_time(raw: str | None) -> str | None:
    """Format CNC time strings as `HHMM:SS.MMM`.

    Args:
        raw: A 9-digit `HHMMSSMMM` string (e.g. `"123456789"`).

    Returns:
        Formatted time string. If input is `None`, empty, non-numeric, or not exactly
        9 characters, returns the original value unchanged.
    """
    if raw is None:
        return None

    s = str(raw)
    if s == "":
        return ""

    if len(s) != 9:
        return s

    if not s.isdigit():
        return s

    hhmm = s[:4]
    ss = s[4:6]
    mmm = s[6:9]
    return f"{hhmm}:{ss}.{mmm}"

