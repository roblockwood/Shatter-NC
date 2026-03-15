---
name: bug-reporting-github
description: Report and action bugs using GitHub Issues. Use when the user wants to report a bug, log an issue, create a GitHub issue, or work on fixing a bug tracked in Issues.
allowed-tools: Read, Write, Terminal, Codebase Search, Web Search
---

# Bug Reporting and Actioning (GitHub Issues)

Bugs and improvements are tracked in **GitHub Issues**. Use this skill when reporting new bugs or when working on an existing issue.

## When to Use

- User asks to "report a bug", "log a bug", "create an issue", or "add something to issues"
- User refers to a bug by number (e.g. "fix #12", "address issue 5") or wants to work on an open issue
- User wants to document a defect or improvement for the repo

## Reporting a Bug

**Prefer creating the issue directly** when the user has authenticated with GitHub (e.g. `gh auth login`). Use `gh issue create` from the repo root so the issue is created in one step. Otherwise, provide a draft they can paste or link to the New Issue page.

### Option A: Create issue directly (when `gh` is authenticated)

From the repo root, run:

```bash
gh issue create --title "Brief title" --label "bug" --body "## Summary
...
## Steps to reproduce
...
## Expected / Actual
..."
```

- Use `--label "bug"` for defects; add `--label "good first issue"` or `"help wanted"` if appropriate.
- If `gh issue create` fails (e.g. TLS or auth), fall back to Option B.

### Option B: Draft or link (when not using `gh`)

- **New issue in browser:** [GitHub Issues – New](https://github.com/roblockwood/Shatter-NC/issues/new). Use the **Bug report** template from the dropdown if available.
- **Draft for paste:** Write the title and body in markdown (or a short file) so the user can paste it into the web form.

### What to include (align with [.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md))

- **Summary** – One-line description
- **Area** – Where it occurs (e.g. File browser, FTP, Dashboard)
- **Steps to reproduce** – Numbered list
- **Expected vs actual behavior** – Clear difference
- **Environment** – OS, browser, how Shatter is run (Docker Desktop, script, etc.)
- **Relevant code** – File paths or endpoints when known

## Actioning a Bug (Fixing an Issue)

1. **Locate the issue**  
   - Ask for the issue number or open [GitHub Issues](https://github.com/roblockwood/Shatter-NC/issues) and find the bug.  
   - Read the issue for repro steps, expected/actual, and any code references.

2. **Reproduce**  
   - Follow the steps in the issue.  
   - Identify the relevant code from the issue or by searching the repo (area, error message, file paths).

3. **Implement the fix**  
   - Make minimal, focused changes.  
   - Match existing patterns (see CONTRIBUTING.md and .cursorrules).

4. **Link the PR to the issue**  
   - In the PR description or in a commit footer, add: `Fixes #<number>` (e.g. `Fixes #3`).  
   - GitHub will auto-close the issue when the PR is merged.

5. **Optional**  
   - Add a short comment on the issue when you start work (e.g. "Working on this in PR #X").  
   - If the fix is only partial, say so and leave the issue open or add a follow-up issue.

## Quick Reference

| Action              | Link / command |
|---------------------|----------------|
| Create issue (CLI)  | `gh issue create --title "..." --label "bug" --body "..."` (from repo root; requires `gh auth login`) |
| List issues         | https://github.com/roblockwood/Shatter-NC/issues |
| New issue (browser) | https://github.com/roblockwood/Shatter-NC/issues/new |
| Bug template        | `.github/ISSUE_TEMPLATE/bug_report.md` |
| Close issue from PR | Put `Fixes #N` in PR description or commit message |

## Docs

- [docs/README.md](docs/README.md) – Links to GitHub Issues under "Bugs & issues".  
- [CONTRIBUTING.md](CONTRIBUTING.md) – Branch naming (`fix/` for bug fixes), PR expectations, and issue references.
