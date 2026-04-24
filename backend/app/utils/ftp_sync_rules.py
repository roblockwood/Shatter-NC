"""Brother CNC filename and file-type rules for FTP sync exclusion."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

# System/data files that should never be written by the sync pipeline.
SYSTEM_FILE_PATTERNS = [
    "ALARM*",
    "MONTR*",
    "MEM*",
    "POSN*",
    "TOLN*",
    "TLOAD*",
    "ATCTL*",
    "ATCTLD*",
    "PRDC*",
    "PRDD*",
    "SYSC*",
    "SYSD*",
]

DEFAULT_EXCLUDE_PATTERNS = [
    ".*",
    "~*",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.swp",
    "*.DS_Store",
]

SUPPORTED_EXTENSIONS = {".NC"}
ONUMBER_RE = re.compile(r"^O\d{4}$")
SAFE_NAME_RE = re.compile(r"^[A-Z0-9_]+$")


@dataclass
class RuleDecision:
    """Decision output for one candidate path."""

    allowed: bool
    reason: str | None = None


def should_exclude_by_pattern(name: str, exclude_patterns: list[str]) -> bool:
    """True if filename matches any configured exclude pattern."""
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def validate_brother_filename(
    file_name: str,
    *,
    control_type: str,
    strict_naming: bool,
    require_onumber: bool,
    exclude_patterns: list[str],
) -> RuleDecision:
    """Validate one file against Brother-style upload constraints.

    Manual references used for limits:
    - C00 section 5.6.4: Program No. length 4, program folder 8 half-width chars.
    - D00 section 3.6.5: Program field length 32.
    """
    candidate = Path(file_name).name
    upper_candidate = candidate.upper()

    if should_exclude_by_pattern(candidate, exclude_patterns):
        return RuleDecision(False, "filename_matches_exclude_pattern")

    base, ext = Path(candidate).stem, Path(candidate).suffix.upper()
    if ext not in SUPPORTED_EXTENSIONS:
        return RuleDecision(False, "unsupported_extension")

    if any(not c.isascii() for c in candidate):
        return RuleDecision(False, "non_ascii_filename")

    if upper_candidate != candidate:
        return RuleDecision(False, "filename_must_be_uppercase")

    if any(fnmatch.fnmatch(upper_candidate, p) for p in SYSTEM_FILE_PATTERNS):
        return RuleDecision(False, "reserved_system_filename")

    if require_onumber and not ONUMBER_RE.match(base):
        return RuleDecision(False, "requires_onumber_filename")

    if ONUMBER_RE.match(base):
        return RuleDecision(True)

    if strict_naming and not SAFE_NAME_RE.match(base):
        return RuleDecision(False, "invalid_characters")

    mode = (control_type or "C00").upper()
    max_base_length = 8 if mode == "C00" else 32
    if len(base) > max_base_length:
        return RuleDecision(False, f"filename_too_long_for_{mode}")

    return RuleDecision(True)
