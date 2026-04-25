"""
Time string utilities for CNC telnet data.

Brother CNC machines return time values in HHMMSSMMM format (9-char string).
This module provides a single canonical conversion to HHMM:SS.MMM display format.
"""


def format_cnc_time(time_str: str) -> str:
    """Convert a 9-character HHMMSSMMM string to HHMM:SS.MMM display format.

    Returns the original string unchanged if it is empty, None, or not 9 chars.
    """
    if not time_str or len(time_str) != 9:
        return time_str
    try:
        hours = time_str[0:2]
        minutes = time_str[2:4]
        seconds = time_str[4:6]
        milliseconds = time_str[6:9]
        return f"{hours}{minutes}:{seconds}.{milliseconds}"
    except (ValueError, IndexError):
        return time_str
