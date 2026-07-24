# NC Parser Guide (CAM Authors)

Shatter validates Brother Speedio programs by reading **metadata embedded in G-code comments**. Standard posts without these comments will upload but **cannot** run tool/WCS validation.

Post processor: **Autodesk Fusion Brother Speedio** (`brother speedio.cps`). A reference copy lives in [`Samples/brother speedio.cps`](../Samples/brother%20speedio.cps) in this repo.

Operator validation flow: [USER_GUIDE.md](USER_GUIDE.md#validation-algorithm).

---

## Required Post Setup

In Fusion, select the **Brother Speedio** post. Ensure User Parameter **0053** (multiple M codes in one block) is enabled — required for G100 tool changes.

Fork lineage (for attribution):

- WCS verification patterns — inspired by [VerifyWCS](https://github.com/toolpath/VerifyWCS)
- Tool length checks — inspired by [fusion-360-post-processors](https://github.com/ewildgoose/fusion-360-post-processors)

---

## Tool Metadata Comments

Shatter parses tool header lines like:

```
(T01 D=0.25 CR=0 - ZMIN=1.7674 - FLAT END MILL - L=0.65/3.609)
(T02 D=0.25 CR=0.125 - ZMIN=-1.9677 - BALL END MILL - L=1.25/2.3917)
```

Extracted fields:

| Field | Used for |
|-------|----------|
| T number | Match to machine ATC |
| D | Diameter vs tool table |
| CR | Corner radius |
| L | Length (stickout) vs tool table |
| Description text | Mismatch detection |

Tool calls in the program (`T01 M06`, etc.) link operations to these definitions.

---

## WCS Verification Block

Work offset validation uses a macro-style block emitted by the post (O8901-style). Parameters:

| Macro | Meaning |
|-------|---------|
| #23 | WCS number (G54=54 …) |
| #24–#26 | Expected X/Y/Z |
| #8 | Allowable error (E) when not using machine tolerances |

Example shape (abbreviated):

```
(WCS VERIFICATION)
(X - EXPECTED X OFFSET #24)
...
N3 (WCS CHECK)
#104 = ABS[#100 - #24]
...
```

If WCS metadata is absent, validation shows machine G54 values with **XYZ NOT PARSED** status.

---

## Operation Metadata

Operation names from comments `(OPERATION_NAME)` and per-tool feed/speed data enable tool analytics on the Tools page. Missing operation metadata does not block validation — it limits speed/feed reporting.

---

## What Validation Expects

**Tools:** Each T-number in the program exists on the machine with matching diameter/length within tolerance.

**WCS:** Each referenced offset (G54–G59) matches machine POSNI within tolerance.

**Tolerances:**

- Machine settings (`use_machine_tool_tolerances`, `use_machine_wcs_tolerances`) **or**
- G-code defaults (exact diameter; length ≥ required; E parameter for WCS)

Configure per machine in the dashboard edit form.

---

## Sample Files

| File | Purpose |
|------|---------|
| [`Samples/brother speedio.cps`](../Samples/brother%20speedio.cps) | Post processor source |
| [`Samples/parametric_feed.NC`](../Samples/parametric_feed.NC) | Example parsed program |
| [`Samples/O8901.NC`](../Samples/O8901.NC) | WCS verification macro example |

---

## Parser Implementation

[`backend/app/parsers/gcode_parser.py`](../backend/app/parsers/gcode_parser.py) — `GCodeParser.parse()` returns `tools`, `wcs_offset`, `posted_date`, `estimated_runtime_seconds`, and operation lists merged into tool metadata.

If you change comment formats in a custom post fork, update the parser regexes and add tests under `backend/tests/`.

---

## Related

- [USER_GUIDE.md](USER_GUIDE.md) — validate/deploy in the UI
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) — change parser code
