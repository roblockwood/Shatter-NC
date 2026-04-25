---
name: jgl-review-testing
description: Audit the test suite for substantive quality using LLM analysis, coverage data, and CI inspection. Produces a plan to improve testing if warranted. Use when the user says "review tests", "/jgl-review-testing", "audit tests", "how are my tests?", "improve test quality", or before a refactor.
---

# Review Testing

Audit the project's test suite for substantive quality — what the tests actually verify about behavior, not just whether coverage numbers look good. Use four sources of information:

1. **Your own analysis** — read the existing tests in `backend/tests/` and evaluate what they actually assert.
2. **Test run** — run the suite and note any failures.
   ```bash
   pytest backend/tests/ -q --tb=short
   ```
3. **Coverage data** — identify files with real logic that have low or no coverage.
   ```bash
   pytest backend/tests/ --cov=backend/app --cov-report=term-missing -q
   ```
4. **CI pipeline inspection** — read `.github/workflows/*.yml` and confirm whether tests run in CI on every PR and push to main.

**Frontend note**: The project currently has no frontend unit test framework configured. Flag this as a first-class finding.

## What to Check

1. **Untested logic files** — backend source files with real business logic that have no corresponding tests. List them.
2. **Weak assertions** — tests that use existence checks when they should assert specific computed values.
3. **Missing edge cases** — functions that take collections but are only tested with one size. Especially relevant for: NC file parsing, FTP sync rule filtering, ATC magazine tool lists.
4. **Missing round-trip tests** — any serialize/parse pair that isn't tested in both directions. NC program parsing is a prime candidate.
5. **Tests that mirror implementation** — tests where the assertion is just the function's logic copied into the test.
6. **Over-mocking** — mocks should be at architectural seams only: FTP connections, telnet sessions, database, time.
7. **Coverage gaps on critical paths** — NC parsing, FTP sync rules, ATC validation, machine status mapping should be near 100%.
8. **CI pipeline gaps** — see next section.

## CI Pipeline Check

Open `.github/workflows/` and verify all of the following (note: the project's current CI focuses on Docker builds and releases, not test runs):

1. **A workflow exists that runs tests.** If none exists, that's the first finding.
2. **It runs on the right triggers.** At minimum: every PR and every push to `main`.
3. **The test step can actually fail the build.** Check for `|| true`, `continue-on-error: true`, or `exit 0` patterns.
4. **Required status checks are enforced.** The test workflow must be a required check in branch protection.

Red flags to grep for explicitly:
```bash
grep -r "continue-on-error\||| true\|exit 0" .github/workflows/
grep -r "skip\|xfail" backend/tests/
```

**Report CI gaps as first-class findings**, on equal footing with missing tests.

## What NOT to Do

- Don't write tests. Just report and plan.
- Don't suggest testing: bootstrap files, type-only files (Pydantic schemas with no logic), pure FastAPI routing boilerplate.
- Don't chase coverage percentage. Focus on whether the important code is meaningfully tested.

## Testing Threshold

- **No action needed** if: all files with business logic have tests, assertions check real values, edge cases covered for critical paths, coverage on core logic 80%+, **and the full suite runs in CI on every PR**. Say so and stop.
- **Improvement recommended** if any of these are true:
  - Backend source files with real logic have zero coverage
  - NC parsing, FTP rules, or ATC validation is below 80%
  - **No CI workflow runs tests** (current state of this project)
  - Frontend has no test framework at all

## Testing Plan

If the threshold is met, produce a prioritized plan:

1. **Do first** — **fix CI gaps first** (add a test workflow that runs pytest on every PR), then add tests for untested business logic files.
2. **Do second** — round-trip tests for NC parsing, edge cases for sync rules, integration tests for telnet/FTP seams.
3. **Skip for now** — things not worth the effort, with a one-line explanation.

For each item, list the file that needs testing, what behavior should be tested, and what kind of test (unit or integration). For CI items, list the specific workflow file and specific change needed.

**Important**: run `/jgl-review-testing` first to build a safety net, then use `/jgl-review-code` to plan structural refactors.
