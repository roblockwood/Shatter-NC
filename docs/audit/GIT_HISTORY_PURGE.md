# Git History Purge Runbook

> **Temporary audit artifact** — plan for removing OEM manuals, scraped documentation, and other non-redistributable blobs from **all** Git history on `roblockwood/Shatter-NC`.  
> Deleting files in a normal commit is **not sufficient**; clones and tags can still reach old objects until history is rewritten.

**Related:** [DOCUMENTATION_AUDIT_LOG.md](./DOCUMENTATION_AUDIT_LOG.md), [CODEBASE_GROUND_TRUTH.md](./CODEBASE_GROUND_TRUTH.md)

---

## Why this is needed

The repository historically contained:

- **Operator manuals** (Kaeser SIGMA CONTROL 2, Kaeser Aircenter SX) — PDF and extracted markdown/JSON
- **Brother control documentation** — section JSON scraped from manuals, macro chapter notes
- **CAM / shop artifacts** — Fusion post processor (`.cps`), example `.NC` programs
- **Legacy export trees** — `brother_cnc_export/`, `vendor/kaeser-sc2-api/`
- **Connectivity research dumps** — `manual_connectivity_context.json`

Much of this was removed from the **tip** on branch `chore/docs-consolidation-and-api-cleanup`, but **`origin/main` (v1.0.0) still contains `docs/scrape/` and `Samples/`**, and **every past commit remains recoverable** via `git show <old-sha>:path`.

Open-sourcing under AGPL does **not** grant rights to redistribute OEM manual text embedded in the repo.

---

## Scope tiers

### Tier A — Purge from entire history (high confidence)

Remove these paths from **every commit** on **every ref** (branches and tags).

| Path / pattern | Contents | ~size in history |
|----------------|----------|------------------|
| `docs/scrape/` | Entire scrape tree (PDFs, MD, JSON, scripts) | ~15 MB+ |
| `docs/scrape/user-manual_controller_sigma-control-2-_9_9450_11use.pdf` | Kaeser SC2 PDF | ~5.8 MB |
| `docs/scrape/901837_46 USE Aircenter SX Operator Manual (1).pdf` | Aircenter PDF | ~7.6 MB |
| `docs/scrape/7_7601_PA_27 E Sigma Control 2 Process Map 6.4.1.pdf` | Kaeser process map PDF | ~3.4 MB |
| `Samples/` | G-code, `.cps`, shop programs | ~1–5 MB |
| `brother_cnc_export/` | Legacy Brother protocol export + docs | varies |
| `vendor/kaeser-sc2-api/` | Vendored NestJS sidecar (removed from tip) | varies |
| `manual_connectivity_context.json` | Root-level connectivity research JSON | ~1.2 MB |
| `docs/Chapter 6 Macro.md` | Brother macro documentation excerpt | varies |

**Also purge duplicate alarm extracts under scrape** (runtime copies are kept — see Tier B):

- `docs/scrape/section_11_7_alarm_code_list_c00.json`
- `docs/scrape/section_2_13_alarm_code_list_d00.json`

### Tier B — Keep in history (decision recorded)

**Status:** Maintainer confirmed **2026-07-23** — alarm tables stay at repo tip and in rewritten history.

| Path | Used by | Notes |
|------|---------|-------|
| `backend/app/data/alarm_codes/section_11_7_alarm_code_list_c00.json` | [`alarm_code_lookup.py`](../../backend/app/utils/alarm_code_lookup.py) | C00 alarm table (~1.8 MB) |
| `backend/app/data/alarm_codes/section_2_13_alarm_code_list_d00.json` | same | D00 variant (~1.7 MB) |

**Filter pass:** Do **not** add these paths to `--invert-paths`. Tier A still removes the duplicate scrape-tree copies under `docs/scrape/`.

### Tier C — Do **not** purge

These are large but legitimate project artifacts:

- `backend/app/data/alarm_codes/*.json` (runtime alarm lookup — Tier B decision)
- `frontend/package-lock.json`, fonts under `frontend/public/fonts/`
- Application source, migrations, Docker configs, consolidated docs

---

## Preconditions

1. **Merge** `chore/docs-consolidation-and-api-cleanup` (or equivalent) so `main` tip matches the intended public tree.
2. ~~**Resolve Tier B** alarm-code policy~~ — **done:** keep `backend/app/data/alarm_codes/`; purge scrape duplicates only.
3. **Coordinate** — no one should push to `main` during the rewrite window.
4. **Back up** the repo (bare mirror) in case you need to retry:

   ```bash
   git clone --mirror git@github.com:roblockwood/Shatter-NC.git shatter-nc-backup.git
   ```

5. **Install** [`git-filter-repo`](https://github.com/newren/git-filter-repo) (recommended over BFG for path-based deletes):

   ```bash
   brew install git-filter-repo   # macOS
   pip install git-filter-repo      # alternative
   ```

---

## Recommended tool: `git filter-repo`

Use **`--invert-paths`** to drop paths from all commits. Run from a **fresh clone** (filter-repo refuses the default remote name unless `--force`).

### Step 1 — Fresh clone

```bash
git clone git@github.com:roblockwood/Shatter-NC.git shatter-nc-scrub
cd shatter-nc-scrub
git fetch --all --tags
```

Check out the branch you will rewrite (usually `main` after merge):

```bash
git checkout main
git pull origin main
```

### Step 2 — Dry-run inventory (optional)

Confirm blobs exist before filtering:

```bash
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '/^blob/ && $4 ~ /^docs\/scrape\// {print $3, $4}' \
  | sort -rn | head
```

### Step 3 — Filter pass (Tier A)

```bash
git filter-repo --force --invert-paths \
  --path docs/scrape/ \
  --path Samples/ \
  --path brother_cnc_export/ \
  --path vendor/kaeser-sc2-api/ \
  --path manual_connectivity_context.json \
  --path 'docs/Chapter 6 Macro.md'
```

**Do not** add `backend/app/data/alarm_codes/` to this command — alarm tables are retained per Tier B decision.

**Note:** `git filter-repo` removes the `origin` remote by design. Re-add it after filtering:

```bash
git remote add origin git@github.com:roblockwood/Shatter-NC.git
```

### Step 4 — Verify locally

```bash
# Should print nothing (or only unrelated hits):
git log --all --oneline -- docs/scrape/
git log --all --oneline -- Samples/
git log --all --oneline -- manual_connectivity_context.json

# Spot-check that tip still builds/tests:
PYTHONPATH=backend pytest backend/tests/ -q

# Confirm large PDF blobs are gone from object database:
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '/^blob/ && $4 ~ /\.pdf$/ {print $3, $4}'
```

Run `git gc --prune=now --aggressive` after verification to drop unreachable objects locally.

---

## Publishing the rewritten history

### Step 5 — Force-push branches

```bash
git push --force --all origin
```

Delete stale remote branches that should not be preserved (optional, after review):

```bash
# Example — only if branch is obsolete and contained leaked content:
# git push origin --delete feature/status-timeline-pie-view
```

### Step 6 — Rewrite tags

All existing tags (`v0.2.0` … `v1.0.0`) point at commits that **contained** Tier A material. Either:

**Option A — Force-push rewritten tags** (simplest if semantic-release will recreate going forward):

```bash
git push --force --tags origin
```

**Option B — Delete all tags on GitHub and re-tag** only the new `main` tip as `v1.0.0` (or next version) after CI passes.

Document the break for anyone pinning old tag SHAs.

### Step 7 — GitHub follow-up

1. **Branch protection on `main`**
   - Require pull request
   - **Block force pushes** (except during admin rewrite — re-enable after)
   - Require review before merge

2. **Collaborator reset** — ask anyone with a clone to re-clone or:

   ```bash
   git fetch origin
   git checkout main
   git reset --hard origin/main
   ```

   Warn: **`git push --force` from an old clone can restore dirty history** if branch protection allows it. Keep force-push blocked on `main` for non-admins.

3. **GitHub sensitive data** — for PDFs that were public, open a ticket using  
   [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)  
   so GitHub purges cached blobs (filter + force-push may not be instant on their CDN).

4. **Forks** — existing forks retain old history; you cannot rewrite them. Note in release/README if needed.

---

## What a PR cannot silently undo (if `main` is protected)

After rewrite + protection:

- A developer **cannot** force-push old history to `main` (blocked).
- Reintroduction would require a **PR** adding files back — visible in the diff.
- Admins with bypass **can** still force-push; restrict bypass to maintainers only.

---

## Suggested execution order

| Phase | Action |
|-------|--------|
| 1 | Merge cleanup PR → `main` tip without `docs/scrape/`, `Samples/`, etc. |
| 2 | ~~Decide Tier B alarm JSON~~ — **keep** `backend/app/data/alarm_codes/` |
| 3 | Announce maintenance window; enable admin-only force push temporarily |
| 4 | Bare backup → fresh clone → `git filter-repo` (Tier A only) |
| 5 | Verify tests + blob inventory |
| 6 | `git push --force --all` + `git push --force --tags` |
| 7 | Re-enable branch protection; notify collaborators to re-clone |
| 8 | GitHub sensitive-data request for PDFs |
| 9 | Delete or archive this runbook section from public docs if desired (keep internal copy) |

---

## Quick reference — paths to pass to `--invert-paths`

```
docs/scrape/
Samples/
brother_cnc_export/
vendor/kaeser-sc2-api/
manual_connectivity_context.json
docs/Chapter 6 Macro.md
```

**Explicitly excluded** from `--invert-paths` (keep in history):

```
backend/app/data/alarm_codes/section_11_7_alarm_code_list_c00.json
backend/app/data/alarm_codes/section_2_13_alarm_code_list_d00.json
```

---

## Limitations

- Rewriting **does not** erase copies on machines that already cloned the old repo.
- **GitHub forks** and external mirrors are out of your control.
- **Wayback / search engines** may have indexed raw file URLs; rewriting does not retract those.
- When in doubt about redistribution rights, **remove first**, replace with user-supplied or machine-derived data later.
