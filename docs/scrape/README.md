# Documentation scrape artifacts

This directory holds scripts and extracted reference material used when building Shatter's CNC and compressor documentation.

**Alarm code JSON:** Canonical runtime copies live in [`backend/app/data/alarm_codes/`](../backend/app/data/alarm_codes/). Do not duplicate large JSON files here.

**Source manuals:** Kaeser and Brother operator manuals are not redistributed in this repository. Use vendor documentation or run [`extract_pdf_manual.py`](extract_pdf_manual.py) locally if you need to regenerate extracts.
