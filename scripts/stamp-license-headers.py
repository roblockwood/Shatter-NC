#!/usr/bin/env python3
# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Stamp SPDX license headers on Shatter-NC source files.

Every source file carries its license with it, so attribution survives
copy/paste, vendoring, and LLM-assisted reuse.

Idempotent: files already containing an SPDX-License-Identifier are skipped.
Preserves leading shebang / encoding / @charset lines.

Usage:
    python3 scripts/stamp-license-headers.py [--check] [--root PATH]

--check reports what would change without writing anything.
"""
import argparse
import os
import re
import subprocess
import sys

COPYRIGHT = "Copyright (C) 2024 Shatter-NC contributors"
SPDX = "SPDX-License-Identifier: AGPL-3.0-or-later"
# Directories intentionally left unstamped.
SKIP_DIRS = (
    ".github/workflows/",  # GitHub requires a separate Workflows PAT permission
                            # to modify these; owner opted out 2026-09-13.
)
# Matches a real header comment, not a passing mention inside a docstring.
HEADER_RE = re.compile(r"^\s*(#|//|--|\*|/\*)\s*SPDX-License-Identifier")

# extension -> (style, )
STYLES = {
    ".py": "hash",
    ".sh": "hash",
    ".yml": "hash",
    ".yaml": "hash",
    ".ts": "slash",
    ".tsx": "slash",
    ".js": "slash",
    ".mjs": "slash",
    ".cjs": "slash",
    ".sql": "dash",
    ".css": "block",
    ".scss": "block",
}


def header(style):
    if style == "hash":
        return [f"# {COPYRIGHT}", f"# {SPDX}", ""]
    if style == "slash":
        return [f"// {COPYRIGHT}", f"// {SPDX}", ""]
    if style == "dash":
        return [f"-- {COPYRIGHT}", f"-- {SPDX}", ""]
    if style == "block":
        return ["/*", f" * {COPYRIGHT}", f" * {SPDX}", " */", ""]
    raise ValueError(style)


def preserved_prefix(lines, ext):
    """Lines that must stay at the very top (shebang, encoding, @charset)."""
    keep = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#!"):
            keep.append(line)
        elif ext in (".py",) and "coding" in stripped and stripped.startswith("#"):
            keep.append(line)
        elif ext in (".css", ".scss") and stripped.startswith("@charset"):
            keep.append(line)
        else:
            break
    return keep


def source_files(root):
    """Tracked files plus new (untracked, non-ignored) files, by extension."""
    out = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    seen = set()
    for flag in ([], ["--others", "--exclude-standard"]):
        out = subprocess.run(
            ["git", "ls-files"] + flag,
            cwd=root, capture_output=True, text=True, check=True,
        )
        for rel in out.stdout.splitlines():
            if rel in seen:
                continue
            seen.add(rel)
            if rel.startswith(SKIP_DIRS):
                continue
            ext = os.path.splitext(rel)[1].lower()
            if ext in STYLES:
                yield os.path.join(root, rel), ext


def process(path, ext, check):
    with open(path, "r", encoding="utf-8", errors="strict") as f:
        text = f.read()
    if not text.strip():
        return "empty"
    lines = text.split("\n")
    if any(HEADER_RE.match(l) for l in lines[:15]):
        return "skipped-has-header"
    if "\x00" in text:
        return "skipped-binary"
    keep = preserved_prefix(lines, ext)
    rest = lines[len(keep):]
    # avoid double blank line between header and body
    new_lines = keep + header(STYLES[ext]) + rest
    new_text = "\n".join(new_lines)
    if check:
        return "would-stamp"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return "stamped"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    stats = {}
    for path, ext in source_files(root):
        try:
            result = process(path, ext, args.check)
        except (UnicodeDecodeError, OSError) as exc:
            result = f"error:{exc}"
        stats[result] = stats.get(result, 0) + 1
        if result in ("would-stamp", "stamped") or result.startswith("error"):
            print(f"{result:20} {os.path.relpath(path, root)}")
    print("\nsummary:", dict(sorted(stats.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
