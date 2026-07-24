# Tablet overview pane plan (CNC machines + compressors)

**Purpose:** Give kiosk users a single-screen summary that matches the **desktop dashboard compact cards**, with **tap → navigate** to existing tablet panes (no hover previews).

**Workflow:** Implement in **Agent mode** with normal file edits—not shell workarounds. Optional Cursor plan artifact may also exist under `.cursor/plans/`; **this document is the repo-local source of truth.**

---

## Routing (both asset types)

| Decision | Detail |
|----------|--------|
| Nav | **`overview` is leftmost** (before PANEL). |
| Default URL | **`/tablet/:machineId`** and **`/tablet/compressor/:id`** redirect to **`overview`**, not `status`. |
| Swipe order | Follows nav arrays (`useTabletPaneSwipe` / `useTabletCompressorPaneSwipe`). |

---

## Part A — CNC machines

### Config

- [`frontend/src/pages/tablet/tabletPaneConfig.ts`](frontend/src/pages/tablet/tabletPaneConfig.ts): prepend `'overview'` to `TABLET_PANE_SLUGS` and `TABLET_NAV_ITEMS`; set `TABLET_DEFAULT_PANE` to `'overview'`.

### Shell

- [`frontend/src/pages/tablet/TabletMachineShell.tsx`](frontend/src/pages/tablet/TabletMachineShell.tsx): add `case 'overview'` → **`MachineOverviewPane`** with `machine` + poll freshness (`fastPollLastSuccessAt`).
- [`frontend/src/pages/tablet/TabletRedirectToDefaultPane.tsx`](frontend/src/pages/tablet/TabletRedirectToDefaultPane.tsx): update comment to reflect default pane constant (not hardcoded `status`).

### New pane: `MachineOverviewPane`

- Location: [`frontend/src/components/machine-detail/MachineOverviewPane.tsx`](frontend/src/components/machine-detail/MachineOverviewPane.tsx).
- **Visual parity:** import [`frontend/src/components/MachineCard.css`](../frontend/src/components/MachineCard.css); use `machine-card-content`, `machine-row`, production-run mini-bar classes (`production-run-summary`, `production-run-bar-track`, `mini-segment-*`).
- **`useNavigate`** → `/tablet/${machineId}/${slug}` for actionable rows.

**Suggested row → slug mapping**

| Row | Slug |
|-----|------|
| STATUS | `status` |
| PROGRAM | `program` |
| PRODUCTION RUN | `runs` |
| ATC TOOLS / TOOL | `tools` |
| ALARMS/WARN | `alarms` |
| FILES (optional) | `files` |

### Shared logic (machines)

- **`useLatestMachineProductionRun(machineId)`** — extract production-runs-timeline fetch (same query as [`MachineCard.tsx`](../frontend/src/components/MachineCard.tsx) compact card).
- **`machineSummaryStatus.ts`** (or similar) — pure helpers for summary status text/classes (from MachineCard `getStatusDisplay` / value styling).
- **`ProductionRunCompactSummary`** — presentational chunk for the mini-bar + util line (props: `latestRun`, loading, `partDisplayMode`).
- **`alarmStopLevel`** — shared helper matching AlarmPane / compact card severity rules.
- Optionally refactor **`MachineCard`** to import the same helpers/hook to avoid duplication (same PR or follow-up).

### Tablet CSS

- Only if needed: narrow selectors in [`frontend/src/pages/tablet/tablet.css`](frontend/src/pages/tablet/tablet.css) under `.tablet-machine-shell-body` for tap targets / overflow.

---

## Part B — Compressors

### Current gaps

- [`frontend/src/pages/tablet/tabletCompressorPaneConfig.ts`](frontend/src/pages/tablet/tabletCompressorPaneConfig.ts): `overview` exists but **not first**; **`TABLET_DEFAULT_COMPRESSOR_PANE`** is still **`status`**.
- [`frontend/src/components/machine-detail/CompressorOverviewPane.tsx`](frontend/src/components/machine-detail/CompressorOverviewPane.tsx): today is **KV / operational JSON** style—not the [**CompressorCard**](../frontend/src/components/CompressorCard.tsx) compact rows.

### Config (align with CNC)

- Move **`overview` to index 0** in slugs + nav items.
- Set **`TABLET_DEFAULT_COMPRESSOR_PANE`** to **`'overview'`**.
- Update comments on [`TabletCompressorRedirectToDefaultPane`](frontend/src/pages/tablet/TabletCompressorRedirectToDefaultPane.tsx) / [`TabletEntry`](frontend/src/pages/tablet/TabletEntry.tsx) compressor paths if they mention `status` as default.

### Refactor `CompressorOverviewPane`

Replace body with **`machine-card-content` + `machine-row`** matching **CompressorCard** compact card:

| Row | Source (CompressorCard) | Tap → slug |
|-----|---------------------------|------------|
| STATUS | `statusDisplay` / `statusValueClass` | **`panel`** (matches card: first row opens panel preview on desktop) |
| OPERATION | `controllerDetail` (`readCompressorControllerStatus`) | **`status`** |
| PSI | `psiLine` | **`psi`** |
| TEMP | `tempLine` | **`temp`** |

Optional: **alarms** summary → `alarms` if useful.

**Dashboard vs tablet:** `CompressorOverviewPane` is also embedded in **expanded** [`CompressorCard`](frontend/src/components/CompressorCard.tsx) layout. Do **not** navigate to `/tablet/...` from the dashboard. Use an optional prop, e.g. **`tabletRouteBase?: string`** — when set (tablet shell), rows call `navigate`; when unset (dashboard), rows are display-only (same copy as card).

Extract shared text/metrics into e.g. **`frontend/src/utils/compressorCardSummary.ts`** and use from both **`CompressorCard`** and **`CompressorOverviewPane`**.

---

## Verification

- `npm run build` in `frontend/`.
- CNC: `/tablet/:id` → overview tab first; rows navigate.
- Compressor: `/tablet/compressor/:id` → overview first; rows navigate when `tabletRouteBase` is set; dashboard expanded view unchanged.

## Changelog

- One unreleased entry in [`CHANGELOG.md`](../CHANGELOG.md) covering both flows.

---

## Implementation checklist

1. CNC: `tabletPaneConfig`, `TabletMachineShell`, `TabletRedirect` comment, `MachineOverviewPane` + hooks/utils + optional `ProductionRunCompactSummary`.
2. Compressor: reorder config + default pane; refactor `CompressorOverviewPane` + `compressorCardSummary`; wire `tabletRouteBase` from `TabletCompressorShell` only.
3. CHANGELOG + build.
