#!/usr/bin/env python3
"""
Extract text and structure from a PDF manual (e.g. Kaeser Aircenter SX operator manual)
into JSON and Markdown for downstream use (LLM context, search, Modbus work later).

Requires: pip install -r docs/scrape/requirements-scrape.txt

Example:
  python3 docs/scrape/extract_pdf_manual.py
  python3 docs/scrape/extract_pdf_manual.py --pdf "docs/scrape/manual.pdf" --out-dir docs/scrape
  python3 docs/scrape/extract_pdf_manual.py --pdf docs/scrape/user-manual_controller_sigma-control-2-_9_9450_11use.pdf \\
      --stem Sigma_Control_2_User_Manual_9_9450 --preset sc2
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise SystemExit(
        "PyMuPDF (fitz) is required. Install with:\n"
        "  python3 -m pip install -r docs/scrape/requirements-scrape.txt"
    ) from e


def _sanitize_stem(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE)
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem or "manual"


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    # Collapse excessive blank lines but keep paragraph breaks
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: List[str] = []
    prev_empty = False
    for ln in lines:
        empty = len(ln.strip()) == 0
        if empty and prev_empty:
            continue
        out.append(ln)
        prev_empty = empty
    return "\n".join(out).strip()


def extract_pdf(
    pdf_path: Path,
    keyword_patterns: Optional[Sequence[str]] = None,
    source_label: Optional[str] = None,
) -> Dict[str, Any]:
    doc = fitz.open(pdf_path)
    try:
        meta = doc.metadata or {}
        toc_raw = doc.get_toc()
        # TOC: [level, title, page] — page is 1-based in PDF convention
        toc: List[Dict[str, Any]] = []
        for level, title, page in toc_raw:
            toc.append({"level": level, "title": title.strip(), "pdf_page": page})

        pages: List[Dict[str, Any]] = []
        for i in range(doc.page_count):
            raw = doc[i].get_text()
            pages.append(
                {
                    "page_index": i,  # 0-based for API use
                    "pdf_page": i + 1,  # 1-based, matches printed page numbers when consistent
                    "text": _normalize_text(raw),
                }
            )

        full_text = "\n\n".join(p["text"] for p in pages if p["text"])

        keyword_hits: List[Dict[str, Any]] = []
        if keyword_patterns:
            lowered_pages = [p["text"].lower() for p in pages]
            for pat in keyword_patterns:
                pl = pat.lower()
                for p in pages:
                    if pl in lowered_pages[p["page_index"]]:
                        snippet = p["text"].replace("\n", " ")
                        if len(snippet) > 240:
                            snippet = snippet[:237] + "..."
                        keyword_hits.append(
                            {
                                "keyword": pat,
                                "pdf_page": p["pdf_page"],
                                "page_index": p["page_index"],
                                "snippet": snippet,
                            }
                        )

        return {
            "source_pdf": source_label or str(pdf_path.as_posix()),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "page_count": doc.page_count,
            "metadata": {
                "format": meta.get("format"),
                "title": meta.get("title"),
                "author": meta.get("author"),
                "subject": meta.get("subject"),
                "keywords": meta.get("keywords"),
                "creator": meta.get("creator"),
                "producer": meta.get("producer"),
                "creation_date": meta.get("creationDate"),
                "mod_date": meta.get("modDate"),
            },
            "table_of_contents": toc,
            "pages": pages,
            "full_text": full_text,
            "keyword_index": keyword_hits,
        }
    finally:
        doc.close()


def write_markdown(data: Dict[str, Any], md_path: Path) -> None:
    lines: List[str] = []
    lines.append(f"# Extracted manual\n")
    lines.append(f"- **Source:** `{data['source_pdf']}`\n")
    lines.append(f"- **Extracted:** {data['extracted_at']}\n")
    lines.append(f"- **Pages:** {data['page_count']}\n")
    lines.append("\n## Table of contents\n\n")
    for entry in data["table_of_contents"]:
        indent = "  " * max(0, entry["level"] - 1)
        lines.append(
            f"{indent}- {entry['title']} (PDF p.{entry['pdf_page']})\n"
        )

    hits = data.get("keyword_index") or []
    if hits:
        lines.append("\n## Keyword index\n\n")
        current_kw = None
        for h in sorted(hits, key=lambda x: (x["keyword"], x["pdf_page"])):
            if h["keyword"] != current_kw:
                current_kw = h["keyword"]
                lines.append(f"\n### {current_kw}\n\n")
            lines.append(
                f"- PDF page **{h['pdf_page']}** — _{h['snippet']}_\n"
            )

    lines.append("\n## Full text by page\n\n")
    for p in data["pages"]:
        body = p["text"] or "_(empty)_"
        lines.append(f"### Page {p['pdf_page']}\n\n{body}\n\n")

    md_path.write_text("".join(lines), encoding="utf-8")


DEFAULT_KEYWORDS = (
    "ethernet",
    "ip address",
    "network",
    "lan",
    "sigma control",
    "modbus",
    "tcp",
    "web server",
    "communication",
    "rj45",
    "subnet",
    "gateway",
    "dns",
)

# Sigma 2 Modbus / register manuals (holding registers, function codes, load bank blocks)
MODBUS_PRESET_KEYWORDS = (
    "modbus",
    "register",
    "holding",
    "function code",
    "coil",
    "discrete input",
    "load bank",
    "41001",
    "41101",
    "41201",
    "error response",
    "address",
    "tcp",
    "instrumentation",
)

# SIGMA CONTROL 2 user manual: Ethernet, Kaeser Connect, IP, Modbus, e-mail, etc.
SIGMA_CONTROL_2_PRESET_KEYWORDS = (
    "kaeser connect",
    "ethernet",
    "ip configuration",
    "ip address",
    "subnet mask",
    "gateway",
    "dns",
    "dhcp",
    "modbus",
    "tcp",
    "web server",
    "network",
    "e-mail",
    "time server",
    "ntp",
    "remote control",
    "communication",
    "profinet",
    "fieldbus",
    "lan",
    "rj45",
    "snmp",
    "http",
    "https",
    "vpn",
    "sigma air",
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    default_pdf = (
        repo_root
        / "docs"
        / "scrape"
        / "901837_46 USE Aircenter SX Operator Manual (1).pdf"
    )

    parser = argparse.ArgumentParser(
        description="Extract PDF manual text to JSON and Markdown."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=default_pdf,
        help="Path to PDF file",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=repo_root / "docs" / "scrape",
        help="Directory for output files",
    )
    parser.add_argument(
        "--stem",
        type=str,
        default="",
        help="Output filename stem (default: derived from PDF name)",
    )
    parser.add_argument(
        "--no-keywords",
        action="store_true",
        help="Skip building keyword_index (smaller JSON)",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="",
        help="Comma-separated extra keywords for keyword_index (in addition to defaults unless --keywords-only)",
    )
    parser.add_argument(
        "--keywords-only",
        action="store_true",
        help="Use only --keywords list, not the default connectivity list",
    )
    parser.add_argument(
        "--preset",
        choices=("default", "modbus", "sc2"),
        default="default",
        help=(
            "Keyword set for keyword_index: default=Aircenter/connectivity; "
            "modbus=register manual; sc2=SIGMA CONTROL 2 (Ethernet, Kaeser Connect, IP, Modbus, …)"
        ),
    )
    args = parser.parse_args()

    pdf_path: Path = args.pdf.resolve()
    if not pdf_path.is_file():
        raise SystemExit(f"PDF not found: {pdf_path}")

    if args.preset == "modbus":
        base_keywords = MODBUS_PRESET_KEYWORDS
    elif args.preset == "sc2":
        base_keywords = SIGMA_CONTROL_2_PRESET_KEYWORDS
    else:
        base_keywords = DEFAULT_KEYWORDS

    extra = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if args.keywords_only:
        kws = tuple(extra) if extra else tuple(base_keywords)
    elif extra:
        kws = tuple(dict.fromkeys(list(base_keywords) + extra))
    else:
        kws = tuple(base_keywords)

    if args.no_keywords:
        kws = None

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _sanitize_stem(args.stem) if args.stem else _sanitize_stem(pdf_path.name)

    try:
        source_label = str(pdf_path.relative_to(repo_root))
    except ValueError:
        source_label = str(pdf_path)

    data = extract_pdf(pdf_path, keyword_patterns=kws, source_label=source_label)
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"

    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(data, md_path)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Pages: {data['page_count']}, TOC entries: {len(data['table_of_contents'])}")
    if data.get("keyword_index"):
        print(f"Keyword hits: {len(data['keyword_index'])}")


if __name__ == "__main__":
    main()
