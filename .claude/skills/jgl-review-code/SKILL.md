---
name: jgl-review-code
description: Review the codebase for structural issues — duplication, large files, dead code, dependency health — using LLM analysis and static analysis. Produces a refactor plan if warranted. Use when the user says "review code", "/jgl-review-code", "code review", "anything need refactoring?", or "look over the code".
allowed-tools: Bash, Read, Grep, Glob
---

# Review Code

Review the codebase for structural quality. Use three sources of information:

1. **Your own analysis** — read the code and identify issues.
2. **Static analysis** — run linters and type checkers for both backend and frontend.
3. **Coverage data** — run `pytest backend/tests/ --cov=backend/app --cov-report=term-missing -q` and review which files have low coverage.

## Static Analysis Commands

**Backend:**
```bash
# Lint
ruff check backend/app 2>/dev/null || echo "ruff not installed"
# Type check (if mypy is available)
mypy backend/app --ignore-missing-imports 2>/dev/null || echo "mypy not installed"
```

**Frontend:**
```bash
cd frontend && npx tsc -b
cd frontend && npm run lint
```

## What to Check

1. **Files over 250 lines** — likely have too many responsibilities. List them with line counts.
   ```bash
   find backend/app frontend/src -name "*.py" -o -name "*.ts" -o -name "*.tsx" | xargs wc -l | sort -rn | head -20
   ```
2. **Duplicated logic** — same block of code in three or more places. Common in this codebase: telnet command formatting, FTP path construction, machine status parsing.
3. **Dead code** — unused functions, commented-out blocks, unreachable branches. Check for unused Python imports and unused TypeScript exports.
4. **Tangled logic** — pure business logic (NC parsing, FTP sync rules, ATC tool validation) embedded in API route handlers or React components that should be extracted into testable modules.
5. **Type safety gaps**:
   - Backend: missing type hints on public functions, use of `Any` in Pydantic models
   - Frontend: `any` types, unsafe type assertions, missing return types on exported functions
6. **Security concerns** — hardcoded machine IPs or credentials, missing input validation on API endpoints that accept machine addresses or file paths, directory traversal risks in file browser endpoints. Flag immediately.
7. **Dependency health**:
   ```bash
   pip-audit 2>/dev/null || echo "pip-audit not installed"
   cd frontend && npm audit
   ```

## What NOT to Do

- Don't fix anything. Just report and plan.
- Don't nitpick formatting or style.
- Don't suggest speculative future improvements.
- Don't propose refactors for code that has no test coverage — flag it as needing tests first (use `/jgl-review-testing` first).

## Refactor Threshold

Not every finding warrants a refactor. Use this threshold:

- **No refactor needed** if: no files over 250 lines, no logic duplication beyond 2x, no tangled business logic, audits are clean, and type coverage is solid. Say so and stop.
- **Refactor recommended** if any of these are true:
  - 3+ files over 250 lines
  - Same logic block duplicated 3+ times
  - Business logic (NC parsing, FTP rules, ATC operations) embedded in route handlers or React components that can't be unit tested
  - `pip-audit` or `npm audit` reports moderate or higher vulnerabilities
  - Multiple missing type hints in core logic files

## Refactor Plan

If the threshold is met, end with a prioritized refactor plan:

1. **Do first** — high-value, low-risk: extracting duplicated logic, splitting oversized files, fixing audit vulnerabilities.
2. **Do second** — medium-value: extracting tangled logic into pure testable modules, adding missing type hints.
3. **Skip for now** — real issues not worth the effort yet, with a one-line explanation.

For each item, list the file path, what's wrong, and what the fix would be. Keep it concrete.

**Important**: if any files in the refactor plan lack test coverage, note that tests should be added *before* refactoring (use `/jgl-review-testing` first).
