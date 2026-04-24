#!/usr/bin/env python3
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

PDF_PATH = Path('docs/brother-manuals/CNC-D00_Data bank & Alarm manual.pdf')
JSON_PATH = Path('backend/app/data/alarm_codes/section_2_13_alarm_code_list_d00.json')
OUT_PATH = Path('docs/D00_PREFIX_COVERAGE_REPORT.md')


def expand_code(code_str: str):
    s = code_str.replace('\n', '').strip()
    if ':' in s:
        a, b = [x.strip() for x in s.split(':', 1)]
        ma = re.match(r'([A-Z]+)(\d+)$', a)
        mb = re.match(r'([A-Z]+)(\d+)$', b)
        if ma and mb and ma.group(1) == mb.group(1):
            prefix = ma.group(1)
            width = len(ma.group(2))
            for i in range(int(ma.group(2)), int(mb.group(2)) + 1):
                yield f'{prefix}{i:0{width}d}'
            return
    yield s


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    json_codes = set()
    for table in data.get('tables', []):
        for row in table.get('rows', []):
            if row and isinstance(row[0], str) and row[0].strip():
                json_codes.update(expand_code(row[0]))
    json_codes = {c for c in json_codes if re.match(r'^[A-Z]{2}\d{4}$', c)}

    text = subprocess.check_output(['pdftotext', '-layout', str(PDF_PATH), '-'], text=True, errors='ignore')
    lines = text.splitlines()
    start = max(i for i, line in enumerate(lines) if '2.13' in line and 'Alarm Code List' in line)
    end = next(
        i
        for i, line in enumerate(lines[start + 1:], start=start + 1)
        if re.match(r'^\s*2\.14\s+List of servo errors', line)
    )

    block = lines[start:end]
    row_start_re = re.compile(r'^\s*([A-Z]{2}\d{4})\s+([1-5])\s+([1-3])\b')
    manual_codes = sorted({m.group(1) for line in block for m in [row_start_re.match(line)] if m})
    manual_set = set(manual_codes)

    by_prefix_manual = defaultdict(set)
    by_prefix_present = defaultdict(set)
    by_prefix_missing = defaultdict(set)

    for code in manual_set:
        prefix = code[:2]
        by_prefix_manual[prefix].add(code)
        if code in json_codes:
            by_prefix_present[prefix].add(code)
        else:
            by_prefix_missing[prefix].add(code)

    prefixes = sorted(by_prefix_manual.keys())

    report = []
    report.append('# D00 Prefix Coverage Report')
    report.append('')
    report.append('Source comparison: section 2.13 row-start codes in manual vs current D00 JSON.')
    report.append('')
    report.append('| Prefix | Manual Codes | Present in JSON | Missing | Coverage |')
    report.append('|---|---:|---:|---:|---:|')

    for prefix in prefixes:
        manual_count = len(by_prefix_manual[prefix])
        present_count = len(by_prefix_present[prefix])
        missing_count = len(by_prefix_missing[prefix])
        coverage = (present_count / manual_count * 100.0) if manual_count else 100.0
        report.append(f'| {prefix} | {manual_count} | {present_count} | {missing_count} | {coverage:.1f}% |')

    report.append('')
    report.append('## Missing Samples By Prefix')
    report.append('')
    for prefix in prefixes:
        missing_sorted = sorted(by_prefix_missing[prefix])
        if not missing_sorted:
            continue
        report.append(f'- {prefix}: {", ".join(missing_sorted[:20])}')

    extra = sorted(json_codes - manual_set)
    report.append('')
    report.append(f'JSON-only codes not present as manual row-starts: {len(extra)}')
    if extra:
        report.append('')
        report.append('Sample JSON-only codes: ' + ', '.join(extra[:30]))

    OUT_PATH.write_text('\n'.join(report) + '\n', encoding='utf-8')

    print('manual_unique_codes', len(manual_set))
    print('json_expanded_codes', len(json_codes))
    print('manual_present_in_json', len(manual_set & json_codes))
    print('manual_missing_in_json', len(manual_set - json_codes))
    print('report_path', OUT_PATH)
    for prefix in prefixes:
        manual_count = len(by_prefix_manual[prefix])
        present_count = len(by_prefix_present[prefix])
        missing_count = len(by_prefix_missing[prefix])
        coverage = (present_count / manual_count * 100.0) if manual_count else 100.0
        print(f'{prefix}: manual={manual_count} present={present_count} missing={missing_count} cov={coverage:.1f}%')


if __name__ == '__main__':
    main()
