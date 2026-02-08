---
name: commit-message
description: Assist with formatting commit messages using conventional commits format for automatic versioning. Validates format and explains version impact.
allowed-tools: Read, Write, Codebase Search
---

# Commit Message Skill

## Purpose

Help format commit messages using conventional commits format to enable automatic versioning via semantic-release. This skill ensures commit messages are properly formatted and explains the version impact of each commit type.

## When to Use

Use this skill whenever:
- User is about to commit changes
- User asks about commit message format
- User wants to know version impact of their changes
- User needs help choosing the right commit type

## Conventional Commit Format

**Required Format:**
```
<type>: <subject>

[optional body]

[optional footer]
```

**Example:**
```
feat: add pane visibility toggle

- Added visibility toggle button in drag handle
- Created pane list panel with checkboxes
- Updated LayoutManager to filter visible panes
- Added CSS styles for toggle button

Closes #123
```

## Commit Types and Version Impact

### Version-Bumping Types

**`feat:` - New Feature**
- **Version Impact**: Minor bump (0.1.0 → 0.2.0)
- **Use When**: Adding new functionality, features, UI components, API endpoints
- **Examples**:
  - `feat: add pane visibility toggle`
  - `feat: implement layout customization`
  - `feat: add machine status timeline`

**`fix:` - Bug Fix**
- **Version Impact**: Patch bump (0.1.0 → 0.1.1)
- **Use When**: Fixing bugs, correcting errors, resolving defects
- **Examples**:
  - `fix: resolve pane visibility toggle issue`
  - `fix: prevent hiding all panes`
  - `fix: correct layout edit mode button behavior`

**`feat!:` - Breaking Change**
- **Version Impact**: Major bump (0.1.0 → 1.0.0)
- **Use When**: Changes that break backward compatibility
- **Examples**:
  - `feat!: redesign machine card layout`
  - `feat!: change API authentication method`
- **Alternative Format**:
  ```
  feat: new authentication system
  
  BREAKING CHANGE: Authentication API has changed
  ```

### Non-Version-Bumping Types

**`chore:` - Maintenance**
- **Version Impact**: No bump
- **Use When**: Dependency updates, build config, tooling changes
- **Examples**:
  - `chore: update dependencies`
  - `chore: configure semantic-release`
  - `chore: update Docker configuration`

**`docs:` - Documentation**
- **Version Impact**: No bump
- **Use When**: Documentation-only changes
- **Examples**:
  - `docs: update README`
  - `docs: add versioning guide`
  - `docs: update API reference`

**`refactor:` - Code Refactoring**
- **Version Impact**: No bump
- **Use When**: Code improvements that don't change behavior
- **Examples**:
  - `refactor: clean up LayoutManager code`
  - `refactor: simplify pane visibility logic`
  - `refactor: extract common utilities`

**`style:` - Formatting**
- **Version Impact**: No bump
- **Use When**: Code style, formatting, whitespace changes
- **Examples**:
  - `style: fix indentation`
  - `style: format code with prettier`
  - `style: remove trailing whitespace`

**`test:` - Tests**
- **Version Impact**: No bump
- **Use When**: Adding or modifying tests
- **Examples**:
  - `test: add tests for pane visibility`
  - `test: update layout manager tests`
  - `test: fix flaky test`

## How to Determine Commit Type

**Ask yourself:**
1. **Does this add new functionality?** → `feat:`
2. **Does this fix a bug?** → `fix:`
3. **Does this break backward compatibility?** → `feat!:` or include `BREAKING CHANGE:`
4. **Is this only documentation?** → `docs:`
5. **Is this only code cleanup without behavior change?** → `refactor:`
6. **Is this only formatting/style?** → `style:`
7. **Is this only tests?** → `test:`
8. **Is this maintenance/tooling?** → `chore:`

## Subject Line Guidelines

- **Use imperative mood**: "add" not "added" or "adds"
- **Lowercase first letter** (unless starting with proper noun)
- **No period at end**
- **Keep it concise** (50-72 characters ideal)
- **Be specific**: "fix pane visibility toggle" not "fix bug"

**Good Examples:**
- `feat: add pane visibility toggle`
- `fix: prevent hiding all panes`
- `docs: update versioning guide`

**Bad Examples:**
- `Added new feature` (missing type, wrong mood)
- `fix: Fixed the bug` (redundant, wrong mood)
- `FEAT: Add Pane Visibility` (wrong case, period)

## Commit Body Guidelines

**When to include a body:**
- Complex features that need explanation
- Multiple related changes
- Breaking changes (must include BREAKING CHANGE note)

**Format:**
- Use bullet points for multiple changes
- Explain the "what" and "why", not the "how"
- Reference issues: `Closes #123` or `Fixes #456`
- Keep lines under 72 characters when possible

**Example:**
```
feat: add pane visibility toggle

- Added visibility toggle button in drag handle when in edit mode
- Created pane list panel with checkboxes for all panes
- Updated LayoutManager to filter visible panes before rendering
- Added CSS styles for toggle button and hidden pane states
- Persists visibility state per machine in layout_config

Closes #123
```

## Breaking Changes

**When to use:**
- API changes that break existing clients
- Database schema changes requiring migration
- Configuration format changes
- Removing deprecated features

**Format Options:**

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

## Version Bump Summary

| Commit Type | Version Bump | Example |
|------------|-------------|---------|
| `feat:` | Minor (0.1.0 → 0.2.0) | New feature |
| `fix:` | Patch (0.1.0 → 0.1.1) | Bug fix |
| `feat!:` | Major (0.1.0 → 1.0.0) | Breaking change |
| `chore:` | None | Maintenance |
| `docs:` | None | Documentation |
| `refactor:` | None | Code cleanup |
| `style:` | None | Formatting |
| `test:` | None | Tests |

## Automatic Versioning

The project uses semantic-release which:
- Analyzes commits since last tag
- Determines highest version bump needed
- Creates git tag automatically
- Updates VERSION file
- Generates CHANGELOG.md
- Creates GitHub release

**You don't need to:**
- Manually update version numbers
- Create git tags
- Write changelog entries
- Think about versioning

**You just need to:**
- Write commits in conventional format
- Merge PRs to main
- Let semantic-release handle the rest

## Examples by Change Type

**Adding a new feature:**
```bash
git commit -m "feat: add pane visibility toggle"
# Triggers: 0.1.0 → 0.2.0
```

**Fixing a bug:**
```bash
git commit -m "fix: resolve pane visibility toggle not working"
# Triggers: 0.1.0 → 0.1.1
```

**Breaking change:**
```bash
git commit -m "feat!: redesign layout system

BREAKING CHANGE: LayoutManager API has changed. 
Component props are now different."
# Triggers: 0.1.0 → 1.0.0
```

**Documentation only:**
```bash
git commit -m "docs: update versioning guide"
# No version bump
```

**Refactoring:**
```bash
git commit -m "refactor: clean up LayoutManager component"
# No version bump
```

## Validation Checklist

Before committing, verify:
- [ ] Commit type is correct (`feat:`, `fix:`, etc.)
- [ ] Subject line is imperative mood
- [ ] Subject line is lowercase (unless proper noun)
- [ ] Subject line has no period
- [ ] Breaking changes use `feat!:` or include `BREAKING CHANGE:`
- [ ] Body explains complex changes (if needed)
- [ ] Issues are referenced (if applicable)

## Common Mistakes to Avoid

❌ **Wrong:**
```bash
git commit -m "Added new feature"
git commit -m "fix bug"
git commit -m "FEAT: Add Pane Visibility."
git commit -m "feat: added pane visibility toggle"
```

✅ **Correct:**
```bash
git commit -m "feat: add pane visibility toggle"
git commit -m "fix: resolve pane visibility issue"
git commit -m "feat: add pane visibility toggle"
git commit -m "feat: add pane visibility toggle"
```

## Integration with Cursor/Claude

When helping with commits:
1. **Analyze the changes** - Review what was modified
2. **Suggest commit type** - Based on change nature
3. **Draft commit message** - In conventional format
4. **Explain version impact** - What version bump will occur
5. **Validate format** - Ensure it follows conventions

## Reference

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- Project docs: `docs/VERSIONING.md`
