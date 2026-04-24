#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path


PDF_PATH = Path("docs/brother-manuals/CNC-D00_Data bank & Alarm manual.pdf")
JSON_PATH = Path("backend/app/data/alarm_codes/section_2_13_alarm_code_list_d00.json")


def expand_code(code_str: str) -> list[str]:
    compact = code_str.replace("\n", "").strip()
    if ":" in compact:
        start, end = [p.strip() for p in compact.split(":", 1)]
        m1 = re.match(r"([A-Z]+)(\d+)$", start)
        m2 = re.match(r"([A-Z]+)(\d+)$", end)
        if m1 and m2 and m1.group(1) == m2.group(1):
            prefix = m1.group(1)
            width = len(m1.group(2))
            return [f"{prefix}{i:0{width}d}" for i in range(int(m1.group(2)), int(m2.group(2)) + 1)]
    return [compact]


def extract_manual_section_lines() -> list[str]:
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(PDF_PATH), "-"],
        text=True,
        errors="ignore",
    )
    lines = text.splitlines()

    start = max(i for i, line in enumerate(lines) if "2.13" in line and "Alarm Code List" in line)
    end = next(
        i
        for i, line in enumerate(lines[start + 1 :], start=start + 1)
        if re.match(r"^\s*2\.14\s+List of servo errors", line)
    )
    return lines[start:end]


def parse_manual_rows(section_lines: list[str]) -> dict[str, tuple[str, str, str]]:
    # Capture row starts: CODE STOP RESET ...
    start_re = re.compile(r"^\s*([A-Z]{2}\d{4})\s+([1-5])\s+([1-3])\s+(.*)$")

    rows: dict[str, tuple[str, str, str]] = {}
    for raw in section_lines:
        line = raw.rstrip("\n")
        m = start_re.match(line)
        if not m:
            continue
        code, stop_level, reset_level, tail = m.groups()

        # Best-effort: keep only the first textual segment as message.
        # Columns in pdftotext -layout are separated by multiple spaces.
        parts = [p.strip() for p in re.split(r"\s{2,}", tail) if p.strip()]
        message = parts[0] if parts else "Alarm listed in D00 manual."

        if code not in rows:
            rows[code] = (stop_level, reset_level, message)

    return rows


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    tables = data.get("tables", [])
    if not tables:
        raise RuntimeError("No tables found in D00 JSON")

    existing_codes: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            if not row or not isinstance(row[0], str) or not row[0].strip():
                continue
            existing_codes.update(expand_code(row[0]))

    section_lines = extract_manual_section_lines()
    manual_rows = parse_manual_rows(section_lines)

    missing_rows = []
    for code in sorted(manual_rows.keys()):
        if code in existing_codes:
            continue
        stop_level, reset_level, message = manual_rows[code]
        missing_rows.append([
            code,
            stop_level,
            reset_level,
            message,
            "",
            "",
        ])

    # Append to the first table to keep backward compatibility in lookup logic.
    tables[0].setdefault("rows", [])
    tables[0]["rows"].extend(missing_rows)

    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"manual_row_starts={len(manual_rows)}")
    print(f"existing_expanded_codes={len(existing_codes)}")
    print(f"missing_added={len(missing_rows)}")
    print(f"has_SM7551_after={any(r[0] == 'SM7551' for r in tables[0]['rows'])}")
    print(f"has_SM7571_after={any(r[0] == 'SM7571' for r in tables[0]['rows'])}")


if __name__ == "__main__":
    main()
