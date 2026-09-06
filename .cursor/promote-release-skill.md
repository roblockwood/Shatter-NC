---
name: promote-release
description: Promote beta to main with a stable release PR. Use when the user asks to cut a release, promote beta to main, merge beta into main, open a release PR, or ship stable.
allowed-tools: Read, Write, Terminal, Codebase Search
---

# Promote Beta to Main (Stable Release)

Use this skill when the maintainer wants to **cut a stable release** by opening and optionally merging a PR **`beta` → `main`**.

Canonical policy: [docs/RELEASE_PROCESS.md](../docs/RELEASE_PROCESS.md). Commit/version rules: [.cursor/commit-message-skill.md](commit-message-skill.md).

## When to Use

- User says: "promote beta to main", "cut a stable release", "release PR", "ship to main", "merge beta into main"
- User wants Cursor to gather commits, predict semver, write release PR notes, and run `gh pr create`

## What Happens Automatically (you do NOT duplicate)

Stable versioning uses **release-please** (not semantic-release). After the promote PR **merges to `main`**:

1. `release.yml` runs **release-please**, which opens or updates a **Release Please PR** (VERSION, CHANGELOG, package.json, `APP_VERSION`)
2. A maintainer **merges that Release Please PR**
3. release-please creates the GitHub Release + `vX.Y.Z` tag
4. `release.yml` then builds stable Docker images: `:latest`, `:vX.Y.Z`, commit SHA

Do **not** manually edit `VERSION` or CHANGELOG, or create git tags.

---

## Workflow

### 1. Preflight

Run in parallel where possible:

```bash
git fetch origin
git status
git log origin/main..origin/beta --oneline
git log origin/beta..origin/main --oneline   # commits on main NOT in beta — warn if non-empty
cat VERSION
```

**Stop and warn the user if:**

- `beta` is not ahead of `main` (nothing to promote)
- `main` has commits not in `beta` (promote may not include them; sync strategy needed)
- Working tree is dirty (stash/commit first)

Optional: check CI on `beta`:

```bash
gh run list --branch beta --limit 3
```

### 2. Analyze commits for release notes and expected semver

Collect full messages:

```bash
git log origin/main..origin/beta --no-merges --format='-%s (%h)%n%b'
```

Classify each commit by conventional type (`feat:`, `fix:`, `feat!:`, `BREAKING CHANGE:`, etc.).

**Expected bump** (highest wins):

| Types in range | Bump |
|----------------|------|
| `feat!:` or `BREAKING CHANGE:` | **Major** |
| `feat:` | **Minor** |
| `fix:` | **Patch** |
| `chore:`, `docs:`, `refactor:`, `style:`, `test:` only | **None** (promote may still merge; release-please may not open a Release PR) |

Read current version from `VERSION` and state predicted next version (e.g. `1.1.1` + feats → `1.2.0`).

Note: release-please considers commits **since the last release tag on `main`**, which should match `origin/main..origin/beta` after a clean promote (plus any commits already on `main` since the last tag).

### 3. Draft the promote PR

**Base:** `main`  
**Head:** `beta`

**Title examples:**

- `chore: promote beta to main`
- `chore: promote beta to main (expected v1.2.0)`

Use a conventional title — CI lint applies to PRs into `main`.

**Body template:**

```markdown
## Summary
- Promote integration branch `beta` to stable `main`
- Expected semver after Release Please PR: **vX.Y.Z** (<major|minor|patch|none> — from conventional commits since last release)

## Changes included
<!-- Group bullets: ### Features, ### Fixes, ### Other -->
- feat: …
- fix: …

## Release impact
- [ ] After merge: release-please opens/updates a **Release Please PR** on `main`
- [ ] Maintainer merges that Release Please PR to cut `vX.Y.Z` and publish images
- [ ] Stable images: `ghcr.io/.../backend:latest` and `:vX.Y.Z`
- [ ] Maintainer server stays on `IMAGE_TAG=beta`; public shops should pin `vX.Y.Z`

## Test plan
- [ ] CI passed on `beta` before promote
- [ ] Reviewed commit list above
- [ ] After promote merge: confirm Release Please PR appears
- [ ] After Release Please merge: confirm `release.yml` built Docker images

## Post-merge (maintainer)
- [ ] Merge Release Please PR
- [ ] Merge `main` back into `beta` to keep branches aligned
```

Fill in concrete bullets from the git log — do not leave placeholders.

### 4. Create the PR

Follow the user's PR creation rule (`gh pr create`, HEREDOC body). Example:

```bash
gh pr create --base main --head beta --title "chore: promote beta to main" --body "$(cat <<'EOF'
…
EOF
)"
```

Return the PR URL to the user.

**Do not push or merge** unless the user explicitly asks.

### 5. Merge promote (only when user asks)

If user wants merge after CI passes:

```bash
gh pr checks <number> --watch --interval 10
gh pr merge <number> --merge   # or --squash if user prefers; default merge preserves history
```

Then:

```bash
gh pr list --base main --search "release" --state open
gh run list --branch main --limit 5
```

Remind the user to **merge the Release Please PR** to finish the release (tag + Docker).

### 6. Post-release sync

After the Release Please PR has merged and images published:

```bash
git checkout beta
git pull origin beta
git merge origin/main -m "chore: sync beta with main after stable release"
git push origin beta
```

This keeps `beta` aligned with release commits (VERSION / CHANGELOG bumps).

---

## Checklist (agent)

Before opening the promote PR:

- [ ] `origin/beta` is ahead of `origin/main`
- [ ] Warned if `origin/main` has commits missing from `beta`
- [ ] Commits summarized and grouped in PR body
- [ ] Expected semver bump stated
- [ ] PR targets **`base: main`**, **`head: beta`**
- [ ] Title is conventional (`chore: …`)

After promote merge (if requested):

- [ ] Release Please PR exists or was updated
- [ ] User reminded to merge Release Please PR (do not skip)
- [ ] After release: remind to sync `main` → `beta`
- [ ] User reminded public upgrades use `IMAGE_TAG=vX.Y.Z` from GitHub Releases

---

## Related

- Feature PRs target **`beta`**, not `main` — see [CONTRIBUTING.md](../CONTRIBUTING.md)
- Agents must not commit on `main`/`beta`; direct feature → `main` needs user confirmation — [branch-commit-policy](rules/branch-commit-policy.mdc)
- PR template checkbox: `.github/pull_request_template.md`
- Docker channels: [.github/workflows/README.md](../.github/workflows/README.md)
- Config: [`release-please-config.json`](../release-please-config.json)
