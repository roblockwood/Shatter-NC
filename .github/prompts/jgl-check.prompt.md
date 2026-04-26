---
name: jgl-check
description: Run the full verification suite — backend tests, frontend type check and lint, dependency audits, and build. Use when the user says "check", "/jgl-check", "verify", "is everything passing", or after any significant change.
---

# Check

Run the full verification suite for this Python + React/TypeScript project and report results. Do all steps in order. Do not stop at the first failure — run all steps so the user sees the full picture.

## Backend (run from workspace root with venv active)

1. **Dependency audit**: Run `pip-audit` if available, else skip and note it.
   ```bash
   pip-audit 2>/dev/null || echo "pip-audit not installed — skipping"
   ```
2. **Lint / static analysis**: Run `ruff check backend/app` if ruff is available.
   ```bash
   ruff check backend/app 2>/dev/null || echo "ruff not installed — skipping"
   ```
3. **Unit tests**: Run pytest with quiet output and short tracebacks.
   ```bash
   pytest backend/tests/ -q --tb=short
   ```

## Frontend (run from `frontend/` directory)

4. **Dependency audit**: Run `npm audit`.
   ```bash
   cd frontend && npm audit
   ```
5. **Type check**: Run `npx tsc -b`.
   ```bash
   cd frontend && npx tsc -b
   ```
6. **Lint**: Run `npm run lint`.
   ```bash
   cd frontend && npm run lint
   ```
7. **Build**: Run `npm run build`.
   ```bash
   cd frontend && npm run build
   ```

## Reporting

After all steps complete, provide a short summary:

- ✓ or ✗ for each step
- If anything failed, show the relevant error output
- If everything passed, say so clearly and concisely

**Note on frontend tests**: The project currently has no frontend unit test framework configured. Note it as a gap rather than a failure.
