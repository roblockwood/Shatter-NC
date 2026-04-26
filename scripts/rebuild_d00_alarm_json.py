#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path


PDF_PATH = Path("docs/brother-manuals/CNC-D00_Data bank & Alarm manual.pdf")
JSON_PATH = Path("backend/app/data/alarm_codes/section_2_13_alarm_code_list_d00.json")


def clean_text(value: str) -> str:
    value = re.sub(r"\s+$", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def expand_code(code_str: str) -> list[str]:
    s = code_str.replace("\n", "").strip()
    if ":" in s:
        a, b = [x.strip() for x in s.split(":", 1)]
        ma = re.match(r"([A-Z]+)(\d+)$", a)
        mb = re.match(r"([A-Z]+)(\d+)$", b)
        if ma and mb and ma.group(1) == mb.group(1):
            prefix = ma.group(1)
            width = len(ma.group(2))
            return [f"{prefix}{i:0{width}d}" for i in range(int(ma.group(2)), int(mb.group(2)) + 1)]
    return [s]


def main() -> None:
    output = subprocess.check_output(
        ["pdftotext", "-layout", str(PDF_PATH), "-"],
        text=True,
        errors="ignore",
    )
    lines = output.splitlines()

    # Prefer body markers over TOC markers.
    start_candidates = [
        i
        for i, line in enumerate(lines)
        if re.match(r"^\s*2\.13\s+Alarm Code List", line)
    ]
    start = start_candidates[-1] if start_candidates else None

    end_candidates = [
        i
        for i, line in enumerate(lines)
        if re.match(r"^\s*2\.14\s+List of servo errors", line)
    ]
    end = next((i for i in end_candidates if start is not None and i > start), None)
    if start is None or end is None:
        raise RuntimeError(f"Could not locate section bounds: start={start}, end={end}")

    block = lines[start:end]
    header_idx = next(
        (
            i
            for i, line in enumerate(block)
            if "No." in line and "Alarm message" in line and "Cause" in line and "Solution" in line
        ),
        None,
    )
    if header_idx is None:
        raise RuntimeError("Could not locate alarm table header")

    header = block[header_idx]
    idx_alarm = header.index("Alarm message")
    idx_cause = header.index("Cause")
    idx_solution = header.index("Solution")

    code_level_re = re.compile(r"^\s*([A-Z]{2}\d{4})\s+([1-5])\s+([1-3])\s+")
    code_only_re = re.compile(r"^\s*([A-Z]{2}\d{4})\s*$")

    rows: list[list[str]] = []
    current = None
    range_pending = False

    def add_segment(line: str) -> None:
        nonlocal current
        if current is None:
            return
        padded = line + (" " * max(0, idx_solution + 40 - len(line)))
        message = padded[idx_alarm:idx_cause].strip()
        cause = padded[idx_cause:idx_solution].strip()
        solution = padded[idx_solution:].strip()
        if message:
            current["message_parts"].append(message)
        if cause:
            current["cause_parts"].append(cause)
        if solution:
            current["solution_parts"].append(solution)

    def finalize_current() -> None:
        nonlocal current
        if current is None:
            return
        code = current["start_code"]
        if current.get("end_code"):
            code = f"{current['start_code']}\n:\n{current['end_code']}"
        rows.append(
            [
                code,
                current["stop_level"],
                current["reset_level"],
                clean_text("\n".join(current["message_parts"])),
                clean_text("\n".join(current["cause_parts"])),
                clean_text("\n".join(current["solution_parts"])),
            ]
        )
        current = None

    for raw in block[header_idx + 1 :]:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped:
            continue
        if "Chapter 2 Alarms" in stripped:
            continue
        if re.match(r"^\d{4}/\d{2}/\d{2}", stripped):
            continue
        if re.match(r"^eCOM\w+", stripped):
            continue
        if re.match(r"^2\s*-\s*\d+", stripped):
            continue

        match = code_level_re.match(line)
        if match:
            finalize_current()
            current = {
                "start_code": match.group(1),
                "end_code": None,
                "stop_level": match.group(2),
                "reset_level": match.group(3),
                "message_parts": [],
                "cause_parts": [],
                "solution_parts": [],
            }
            range_pending = False
            add_segment(line)
            continue

        if stripped == ":":
            range_pending = True
            continue

        code_only = code_only_re.match(line)
        if code_only and current is not None and range_pending:
            current["end_code"] = code_only.group(1)
            range_pending = False
            continue

        if current is not None:
            add_segment(line)

    finalize_current()

    existing = json.loads(JSON_PATH.read_text())
    new_data = {
        "document": existing.get("document", "CNC-D00_Data bank & Alarm manual.pdf"),
        "section": "2.13",
        "section_title": "Alarm Code List",
        "page_range": existing.get("page_range", {"start": 297, "end": 598}),
        "tables": [
            {
                "table_number": "",
                "caption": "",
                "headers": [
                    "No.",
                    "Stop\\nlevel",
                    "Reset\\nlevel",
                    "Alarm message",
                    "Cause",
                    "Solution",
                ],
                "rows": rows,
                "notes": "Regenerated from manual via pdftotext -layout parser.",
                "context_before": "",
                "context_after": "",
            }
        ],
    }

    JSON_PATH.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    all_codes = set()
    for row in rows:
        all_codes.update(expand_code(row[0]))

    print(f"rows_written={len(rows)}")
    print(f"expanded_codes={len(all_codes)}")
    print(f"has_SM7551={'SM7551' in all_codes}")
    print(f"has_SM7571={'SM7571' in all_codes}")


if __name__ == "__main__":
    main()
