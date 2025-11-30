#!/usr/bin/env python3
"""
Scrape connectivity information from CNC machine operation manual (data) PDF.
Extracts text and structures it into JSON format for context reference.
"""

import json
import sys
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
    import PyPDF2


def extract_pdf_content(pdf_path):
    """Extract text content from PDF file."""
    content = {
        "source": str(pdf_path),
        "pages": [],
        "sections": {}
    }

    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        total_pages = len(pdf_reader.pages)

        print(f"Processing {total_pages} pages...")

        for page_num in range(total_pages):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()

            content["pages"].append({
                "page_number": page_num + 1,
                "text": text
            })

            # Progress indicator
            if (page_num + 1) % 10 == 0:
                print(f"Processed {page_num + 1}/{total_pages} pages")

    # Extract sections based on common patterns
    full_text = "\n".join([p["text"] for p in content["pages"]])

    # Look for connectivity-related keywords
    keywords = [
        "ethernet", "network", "tcp/ip", "communication", "protocol",
        "connection", "port", "interface", "rs232", "serial", "usb",
        "ftp", "http", "modbus", "profinet", "opcua", "mtconnect",
        "socket", "server", "client", "address", "configuration"
    ]

    # Create keyword index
    content["keyword_index"] = {}
    for keyword in keywords:
        pages_with_keyword = []
        for page in content["pages"]:
            if keyword.lower() in page["text"].lower():
                pages_with_keyword.append(page["page_number"])
        if pages_with_keyword:
            content["keyword_index"][keyword] = pages_with_keyword

    return content


def main():
    manual_path = Path(__file__).parent / "Manuals" / "Operation manual(data).pdf"

    if not manual_path.exists():
        print(f"Error: Manual not found at {manual_path}")
        sys.exit(1)

    print(f"Extracting content from: {manual_path}")
    content = extract_pdf_content(manual_path)

    # Save to JSON
    output_path = Path(__file__).parent / "manual_connectivity_context.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Extraction complete!")
    print(f"✓ Saved to: {output_path}")
    print(f"✓ Total pages: {len(content['pages'])}")
    print(f"✓ Keywords found: {len(content['keyword_index'])}")

    if content["keyword_index"]:
        print("\nConnectivity-related keywords found:")
        for keyword, pages in sorted(content["keyword_index"].items()):
            print(f"  - {keyword}: pages {pages}")


if __name__ == "__main__":
    main()
