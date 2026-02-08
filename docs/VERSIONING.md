# Automatic Versioning

Shatter uses **semantic-release** with **conventional commits** for fully automatic version management. You don't need to manually update version numbers, create git tags, or write changelogs - it all happens automatically based on your commit messages.

## How It Works

1. **You write commits** using conventional commit format (`feat:`, `fix:`, etc.)
2. **You merge PRs** to `main` branch
3. **GitHub Action runs** semantic-release automatically
4. **semantic-release analyzes** all commits since the last tag
5. **Version is determined** based on commit types (patch/minor/major)
6. **Git tag is created** (e.g., `v0.2.0`)
7. **Files are updated** (VERSION, package.json, CHANGELOG.md)
8. **GitHub release is created** with release notes

## Commit Message Format

**Required Format:**
```
<type>: <subject>

[optional body]

[optional footer]
```

### Commit Types

| Type | Version Bump | When to Use | Example |
|------|--------------|-------------|---------|
| `feat:` | Minor (0.1.0 → 0.2.0) | New features, functionality | `feat: add pane visibility toggle` |
| `fix:` | Patch (0.1.0 → 0.1.1) | Bug fixes, error corrections | `fix: resolve pane visibility issue` |
| `feat!:` | Major (0.1.0 → 1.0.0) | Breaking changes | `feat!: redesign layout system` |
| `chore:` | None | Maintenance, dependencies | `chore: update dependencies` |
| `docs:` | None | Documentation only | `docs: update README` |
| `refactor:` | None | Code cleanup, no behavior change | `refactor: clean up LayoutManager` |
| `style:` | None | Formatting, whitespace | `style: fix indentation` |
| `test:` | None | Tests only | `test: add pane visibility tests` |

### Breaking Changes

To trigger a major version bump, use one of these formats:

**Option 1: Use `!` after type**
```bash
git commit -m "feat!: redesign layout system"
```

**Option 2: Include BREAKING CHANGE in footer**
```bash
git commit -m "feat: new authentication system

BREAKING CHANGE: Authentication API endpoints have changed.
Old endpoints /api/v1/auth are removed. Use /api/v2/auth instead."
```

## Examples

### Minor Version Bump (0.1.0 → 0.2.0)

```bash
git commit -m "feat: add pane visibility toggle"
git commit -m "feat: implement layout customization"
git commit -m "feat: add machine status timeline"
```

### Patch Version Bump (0.1.0 → 0.1.1)

```bash
git commit -m "fix: resolve pane visibility toggle issue"
git commit -m "fix: prevent hiding all panes"
git commit -m "fix: correct layout edit mode button behavior"
```

### Major Version Bump (0.1.0 → 1.0.0)

```bash
git commit -m "feat!: redesign machine card layout"
git commit -m "feat!: change API authentication method"
```

Or with BREAKING CHANGE:
```bash
git commit -m "feat: new authentication system

BREAKING CHANGE: Authentication API has changed"
```

### No Version Bump

```bash
git commit -m "chore: update dependencies"
git commit -m "docs: update README"
git commit -m "refactor: clean up LayoutManager code"
git commit -m "style: fix code formatting"
git commit -m "test: add tests for pane visibility"
```

## Subject Line Guidelines

- **Use imperative mood**: "add" not "added" or "adds"
- **Lowercase first letter** (unless starting with proper noun)
- **No period at end**
- **Keep it concise** (50-72 characters ideal)
- **Be specific**: "fix pane visibility toggle" not "fix bug"

**Good:**
- `feat: add pane visibility toggle`
- `fix: prevent hiding all panes`
- `docs: update versioning guide`

**Bad:**
- `Added new feature` (missing type, wrong mood)
- `fix: Fixed the bug` (redundant, wrong mood)
- `FEAT: Add Pane Visibility.` (wrong case, period)

## Commit Body

Include a body for complex changes:

```bash
git commit -m "feat: add pane visibility toggle

- Added visibility toggle button in drag handle
- Created pane list panel with checkboxes
- Updated LayoutManager to filter visible panes
- Added CSS styles for toggle button
- Persists visibility state per machine

Closes #123"
```

## Version Bump Rules

semantic-release analyzes all commits since the last tag and determines the highest version bump needed:

- If any commit is `feat!:` or has `BREAKING CHANGE:` → **Major bump**
- If any commit is `feat:` (and no breaking changes) → **Minor bump**
- If any commit is `fix:` (and no features or breaking changes) → **Patch bump**
- If only `chore:`, `docs:`, `refactor:`, `style:`, `test:` → **No release**

**Example:**
```
Commits since last tag (v0.1.0):
- feat: add pane visibility toggle
- fix: resolve pane visibility issue
- docs: update README

Result: Minor bump → v0.2.0 (because of feat:)
```

## What Gets Updated Automatically

When semantic-release runs, it automatically:

1. **Creates git tag** (e.g., `v0.2.0`)
2. **Updates VERSION file** (e.g., `0.2.0`)
3. **Updates frontend/package.json** version field
4. **Generates CHANGELOG.md** with release notes
5. **Creates GitHub release** with changelog
6. **Pushes tag and commits** to repository

## Checking Current Version

**In Development:**
- Version is shown in the app header: "SHATTER v0.2.0"
- Version comes from git tags using `git describe`

**In Production:**
- Version comes from VERSION file (updated by semantic-release)
- Version is baked into Docker image at build time

**Check git version:**
```bash
git describe --tags
# Output: v0.2.0 or v0.2.0-5-gabc1234 (if commits after tag)
```

**Check VERSION file:**
```bash
cat VERSION
# Output: 0.2.0
```

## Skipping a Release

Sometimes you don't want a release (e.g., only documentation changes). Use `[skip release]` or `[no release]` in the commit message:

```bash
git commit -m "docs: update documentation [skip release]"
```

Or configure semantic-release to only release when there are `feat:` or `fix:` commits (default behavior).

## Workflow Example

**Complete workflow:**

```bash
# 1. Work on a feature
git checkout -b feature/pane-visibility
git commit -m "feat: add pane visibility toggle UI"
git commit -m "fix: prevent hiding all panes"
git commit -m "docs: update layout documentation"

# 2. Create PR, get reviewed, merge to main

# 3. GitHub Action automatically:
#    - Analyzes commits: feat: (minor), fix: (patch), docs: (none)
#    - Determines: minor bump needed (highest is minor)
#    - Current: 0.1.0 → New: 0.2.0
#    - Creates tag: v0.2.0
#    - Updates VERSION: 0.2.0
#    - Generates CHANGELOG.md
#    - Creates GitHub release
#    - Pushes everything

# 4. Next build shows: "SHATTER v0.2.0"
```

## Configuration Files

- **`.releaserc.json`** - semantic-release configuration
- **`.github/workflows/release.yml`** - GitHub Action that runs semantic-release
- **`frontend/vite.config.ts`** - Reads version from git tags or VERSION file
- **`VERSION`** - Updated automatically by semantic-release

## Troubleshooting

**Version not updating?**
- Check that commits use conventional format
- Verify PR was merged to `main` branch
- Check GitHub Actions for errors
- Check that semantic-release has `contents: write` permission

**Wrong version bump?**
- Review commit messages - highest bump type wins
- Breaking changes require `feat!:` or `BREAKING CHANGE:`
- Only `feat:` and `fix:` trigger releases

**Want to manually tag?**
```bash
# Not recommended, but possible
git tag -a v1.0.0 -m "Release v1.0.0"
git push --tags
```

## Reference

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [semantic-release Documentation](https://semantic-release.gitbook.io/)

## Getting Help

- See `.cursor/commit-message-skill.md` for commit message assistance
- See `.claude/rules.md` for commit message guidelines
- Check GitHub Actions logs if releases aren't working
