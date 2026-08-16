# Plan: Remote tool name writes (#137)

**Issue:** [GitHub #137](https://github.com/roblockwood/Shatter-NC/issues/137)  
**Status:** In progress (backend + UI on `feat/tool-name-ftp-writes`)  
**Supersedes:** #138 (closed as duplicate)

## Problem

Tool **names** are readable in Shatter (via `LOD` → `TOLNI1` / `TOLNM1` + `tolni_parser_v2`) but **not writable** through telnet field commands used for offsets/life/ATC.

| Field | Read | Telnet write |
|-------|------|--------------|
| H / D / W offsets | `LOD` TOLN, `REDTOFS` | `WRTTOFS` ✅ |
| Life | `LOD` TOLN, `REDTLLF` | `WRTTLLF` ✅ |
| **Tool name** | `LOD` TOLN only (CSV field 8) | **No `WRT*` command** ❌ |

Name is metadata in the TOLN **file record**, not a standalone RED/WRT register. Remote edits require **FTP whole-file patch**, not telnet `SAV` (out of scope).

## Phased implementation

### Phase 1 — TOLN patch layer (backend, no machine I/O)

**Goal:** Parse → patch one tool's name → serialize → re-parse with no other field drift.

| Task | Detail |
|------|--------|
| Add `patch_tool_name()` | New module e.g. `backend/app/services/tolni_patch.py` |
| Serialize helper | Format field 8 as `'NAME          '` (16 chars, single-quoted, space-padded) per `tolni_schema` |
| Line targeting | Find `T{tool_number:02d},...` line; replace only CSV index 8 |
| Preserve bytes | Prefer raw-line splice over full rebuild where possible |
| Tests | Fixture round-trip — patch T07, assert other tools unchanged |

**Exit criteria:** Unit tests green; no FTP/telnet yet.

### Phase 2 — FTP write service

**Goal:** Safe end-to-end write with verify + audit.

| Task | Detail |
|------|--------|
| `write_tool_names_via_ftp()` | In `tool_write_service.py` or dedicated service |
| Read source | **FTP download of full `TOLNI1.NC` / `TOLNM1.NC`** — telnet LOD is read-only for verify; it often omits M## magazine rows |
| Pre-upload backup | FTP download current file; log diff for target tool only |
| Integrity gate | Refuse upload if patch would drop M/V/Y section rows |
| Upload | `upload_file()` → `TOLNI1.NC` / `TOLNM1.NC` per machine `units` |
| Verify | Telnet `LOD` re-read; assert `tool_name` matches |
| Cache refresh | `refresh_tool_data` / poller invalidation |
| Locking | Hold telnet lock + pause/skip TOLN poll during upload |

**Exit criteria:** Can rename T07 via service call (mock FTP in tests).

### Phase 3 — API + batch orchestration

**Goal:** Expose name writes through unified PUSH without corrupting mixed batches.

| Task | Detail |
|------|--------|
| Extend `ToolChangeOperationType` | Add `"name"` |
| Extend `ToolChangeItem` | Add `name_value: Optional[str]` (max 14 chars inside quotes) |
| Validator | Add `tool_name` to `MachineStateValidator` — same gates as `tool_offset` / `tool_life` |
| Batch rules | **Recommended:** telnet ops first (offset/life/ATC), then one consolidated FTP upload if any name changes. Alternative: reject mixed batches. |
| Audit | `operation_type: "tool_name"` with `{tool_number, old_name, new_name}` |
| Optional route | `PUT /api/machines/{id}/tools/{tool_number}/name` for single-name writes |

**Exit criteria:** API accepts `operation_type: "name"`; mixed batch behavior documented and tested.

### Phase 4 — ToolsPane UI

**Goal:** NAME column editable like D/H/LIFE.

| Task | Detail |
|------|--------|
| Inline editor | Replace read-only name cell with text input (max 14 chars, trim) |
| Pending state | `stagePendingChange(..., 'tool_name', ..., 'name', 'tool')` |
| Batch mapping | Extend `pendingToBatchItem` + `ToolChangeBatchItem` with `name_value` |
| Push / clear | Same PUSH / × flow as offsets; pending row tint |
| Result handling | Map `operation_type: "name"` in batch result handler |

**Exit criteria:** Edit name → PUSH → name persists after poll refresh.

### Phase 5 — Live validation + docs

| Task | Detail |
|------|--------|
| Live script | Extend `test_tool_write_live.py` with `--name "TEST EM"` + optional restore |
| Docs | `docs/TELNET_REFERENCE.md` — "Tool name writes via FTP TOLN upload" |
| Shop test | C00 @ 192.168.86.89 — stop backend dev container first |

**Exit criteria:** All acceptance criteria in #137 checked off.

## Suggested branches

```text
feat/tool-name-ftp-patch     → beta   (Phases 1–3)
feat/tool-name-ui-push       → beta   (Phase 4, can stack on first PR)
```

Or one PR if the diff stays reviewable (~400–600 lines).

## Risks / decisions

1. **Multi-name in one push** — Patch all changed tools in one read → multi-patch → one FTP upload.
2. **Data bank** — Confirm bank 0 only vs multi-bank before shipping.
3. **Name + offset in same PUSH** — Telnet writes first; FTP upload last.

## Key files

| Area | Path |
|------|------|
| TOLN schema | `backend/app/schemas/cnc_data/tolni_schema.py` |
| Parser | `backend/app/parsers/tolni_parser_v2.py` |
| FTP upload | `backend/app/clients/ftp_client.py` |
| Telnet read | `backend/app/clients/_telnet_data_reads.py` |
| Batch orchestrator | `backend/app/services/tool_write_service.py` |
| UI | `frontend/src/components/machine-detail/ToolsPane.tsx` |
| Live test | `backend/scripts/test_tool_write_live.py` |

## Acceptance criteria (from #137)

- [ ] Set T07 name from API/UI; persists after `LOD` re-read
- [ ] Other tools unchanged (diff vs pre-upload snapshot)
- [ ] Fails cleanly when machine busy / edit mode
- [ ] Unit tests: TOLN line patch round-trip
