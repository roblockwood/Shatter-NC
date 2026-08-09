"""Extract program title and file label from NC file header comments."""
import re
from typing import Optional


def extract_nc_program_header(content: str) -> dict:
    """Extract program title and file label from an NC file's header comments."""
    title: Optional[str] = None
    file_label: Optional[str] = None
    comment_re = re.compile(r"^\(([^)]*)\)\s*$")

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "%" or re.match(r"^O\d+\b", stripped, re.IGNORECASE):
            continue
        m = comment_re.match(stripped)
        if not m:
            break
        text = m.group(1).strip()
        if not text:
            continue
        if title is None:
            title = text
        if file_label is None and text.upper().startswith("FILE:"):
            file_label = text[5:].strip()
        if title is not None and file_label is not None:
            break

    return {"title": title, "file_label": file_label}


def format_program_note(title: Optional[str], filename: str) -> Optional[str]:
    """Return descriptive note text, stripping redundant O#### prefix when it matches filename."""
    if not title:
        return None

    onumber_match = re.match(r"^O(\d+)", filename, re.IGNORECASE)
    if onumber_match:
        onumber = onumber_match.group(1)
        prefix_pattern = re.compile(
            rf"^O{onumber}\s*[-—:]\s*",
            re.IGNORECASE,
        )
        if prefix_pattern.match(title):
            stripped = prefix_pattern.sub("", title).strip()
            return stripped or None

    return title.strip() or None
