# Manual PDF extraction

Scripts here turn operator / technical PDFs into **JSON + Markdown** for search, docs, and LLM context.

```bash
python3 -m pip install -r docs/scrape/requirements-scrape.txt
```

## Aircenter SX operator manual (Kaeser compressor)

```bash
python3 docs/scrape/extract_pdf_manual.py
```

Defaults read  
`docs/scrape/901837_46 USE Aircenter SX Operator Manual (1).pdf`  
and write:

- `901837_46_USE_Aircenter_SX_Operator_Manual_1.json` — structured pages, TOC, `keyword_index`
- `901837_46_USE_Aircenter_SX_Operator_Manual_1.md` — same content as Markdown

Uses `--preset default` (network / connectivity-oriented keyword index).

## SIGMA CONTROL 2 user manual (controller)

```bash
python3 docs/scrape/extract_pdf_manual.py \
  --pdf docs/scrape/user-manual_controller_sigma-control-2-_9_9450_11use.pdf \
  --stem Sigma_Control_2_User_Manual_9_9450 \
  --preset sc2
```

Writes `Sigma_Control_2_User_Manual_9_9450.json` / `.md`. The **`sc2`** preset fills `keyword_index` with Ethernet, **Kaeser Connect**, IP configuration, Modbus, e-mail, time server, etc.

## Options

| Flag | Purpose |
|------|--------|
| `--pdf PATH` | Input PDF |
| `--out-dir DIR` | Output directory (default: `docs/scrape`) |
| `--stem NAME` | Output basename (default: from PDF filename) |
| `--preset default\|modbus\|sc2` | Keyword set for `keyword_index`: **default** = Aircenter/connectivity; **modbus** = register-manual terms; **sc2** = SIGMA CONTROL 2 (Ethernet, Kaeser Connect, IP, Modbus, …) |
| `--no-keywords` | Omit `keyword_index` in JSON |
| `--keywords a,b` | Extra strings to match for `keyword_index` |
| `--keywords-only` | Only use `--keywords` (or the current preset list if `--keywords` is empty), not merged with the other preset |

For a **dedicated Modbus register map** PDF (when available), use `--preset modbus` or add register-specific terms via `--keywords`.
