# Shatter Project Guidelines

Shatter is a full-stack CNC machine monitoring and management platform.

- **Backend**: Python 3.x, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery
- **Frontend**: React 19, TypeScript, Vite, Zustand, TanStack Query
- **Infrastructure**: Docker Compose (dev and prod), MQTT, telnet, FTP
- **Testing**: pytest (backend), no frontend test framework currently

---

## Skills Available

Use these prompts by referencing them in the chat:

- `/jgl-check` — run the full verification suite (backend tests, frontend type check/lint/build, dependency audits)
- `/jgl-commit` — stage, commit, and push with a meaningful message
- `/jgl-review-code` — structural code review with refactor plan
- `/jgl-review-testing` — test suite audit with improvement plan

---

## Code Structure

- One concept per file, named after the concept.
- Each file should be understandable without reading more than its direct imports.
- 250–500 lines per file is a soft target — bias toward the low end. A file pushing past 500 is a signal to look for a split, not a hard rule.
- One clear responsibility per function. If you can't name what a function does in one sentence, split it.
- Predictable, named exports. No hidden global state. No clever metaprogramming.
- **Backend**: Explicit return type hints on all public functions. Use Pydantic models for validation at API boundaries.
- **Frontend**: Explicit return types on exported functions. Use discriminated unions over boolean flags when a value can be in one of several states.

## Duplication

- Two identical blocks is usually fine. Three is borderline — extract if non-trivial. Four or more: extract.
- Centralize shared constants, regexes, magic strings, and repeated parsing patterns — especially telnet command strings, FTP path patterns, and NC file parsing logic.
- Three similar lines of code is better than a premature abstraction. Don't extract a helper for one caller.

## Testing

- Testing is critical. High coverage is desirable — but only when the tests are meaningful. Adding tests just to raise a coverage number is not valuable.
- Test behavior, not implementation. Test names should describe what the system does, not what the code calls.
- **Backend**: Use pytest. Both unit tests and integration tests are valuable. Mock at architectural seams: FTP connections, telnet sessions, database, time — not at every function boundary.
- **Frontend**: No test framework is currently configured. Adding Vitest is a recommended next step.
- Cover sizes 0, 1, 2, and N for any function that takes a collection. Especially important for NC file parsing and FTP sync rule filtering.
- Round-trip test any encode/decode, save/load, or serialize/parse pair.
- Use real assertions (`assert result == expected`) not existence checks (`assert result is not None`).
- Some files are correctly untested: FastAPI routing boilerplate with no logic, Pydantic schema-only files, Docker entrypoint scripts.

## Git Hygiene

- Commit early and often. A commit after every meaningful change gives you a rollback point.
- Write short commit messages that say *what changed and why*. Use conventional commit format:
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Push to GitHub regularly — at minimum after every working session.
- Work on `main` for solo projects. Use branches when collaborating.

## Security

- **Never hardcode** machine IP addresses, credentials, or API keys in source code. Use environment variables and `.env` files (which are gitignored).
- **Validate all inputs** at API boundaries — especially machine hostnames/IPs, file paths, and NC program content. Reject unexpected characters before passing to telnet or FTP clients.
- **Directory traversal**: File browser endpoints that accept user-supplied paths must canonicalize and restrict to allowed base directories.
- Run `pip-audit` and `npm audit` after adding or updating packages. Fix vulnerabilities before committing.
- Do not commit `.env` files, `kaeser-sc2-api.env`, or any file containing machine credentials.

## Dependencies

- **Backend**: Add packages to `backend/requirements.txt`. Prefer pinned versions. Check that a package is actively maintained before adding it.
- **Frontend**: Add packages via `npm install` from the `frontend/` directory. Pin major versions in `package.json`.
- Fewer dependencies is better. Don't install a package for something you can write in a few lines.
- Review what a package actually does before installing it.

## Refactoring

- Refactoring untested code is high-risk. Establish reasonable test coverage before significant refactors.
- Refactoring means same behavior, better shape. Existing tests must still pass without modification.
- No speculative future-proofing. Don't build abstractions for requirements that don't exist yet.
- No backwards-compatibility shims. If something is unused, delete it completely.

## UX and Design

- This project uses a terminal/retro aesthetic. All UI must use the design system defined in `docs/UX_DESIGN_GUIDE.md`.
- Box-drawing characters only (┌ ┐ └ ┘ ─ │). Green phosphor (#00ff00) on black (#0a0a0a).
- No emoji in the UI. Use ASCII characters: `/`, `-`, `|`, `*`, `+`.
- Monospace fonts only: IBM Plex Mono, JetBrains Mono, Fira Code.

## CI / Automation

- The project currently has GitHub Actions workflows for Docker image builds and releases, but **no automated test pipeline**.
- The highest-priority CI gap is adding a workflow that runs `pytest backend/tests/` on every PR and push to main.
- Tests that only run locally are tests that get skipped.

## Verification

- After any significant change, run the test suite. Use `/jgl-check` to run all verification steps.
- If tests fail, fix them before moving on to new work.
- Before shipping a new feature, verify the happy path, error cases, and at least one edge case.
