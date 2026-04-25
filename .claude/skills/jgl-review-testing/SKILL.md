---
name: jgl-review-testing
description: Audit the test suite for substantive quality using LLM analysis, coverage data, and CI inspection. Produces a plan to improve testing if warranted. Use when the user says "review tests", "/jgl-review-testing", "audit tests", "how are my tests?", "improve test quality", or before a refactor.
allowed-tools: Bash, Read, Grep, Glob
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
2. **Weak assertions** — tests that use existence checks (`assert result is not None`, `assert len(result) > 0`) when they should assert specific computed values. These pass even when the code is wrong.
3. **Missing edge cases** — functions that take collections but are only tested with one size. Look for missing tests at sizes 0, 1, 2, and N. Especially relevant for: NC file parsing, FTP sync rule filtering, ATC magazine tool lists.
4. **Missing round-trip tests** — any encode/decode, serialize/parse pair that isn't tested in both directions. NC program parsing is a prime candidate.
5. **Tests that mirror implementation** — tests where the assertion is just the function's logic copied into the test. These can't catch bugs.
6. **Over-mocking** — tests that mock so many dependencies that they only verify the mocks. Mocks should be at architectural seams: FTP connections, telnet sessions, database, time.
7. **Coverage gaps on critical paths** — NC parsing, FTP sync rules, ATC validation, machine status mapping should be near 100%.
8. **CI pipeline gaps** — see next section.

## CI Pipeline Check

Open `.github/workflows/` and verify all of the following for the test workflow specifically (note: the project's current CI focuses on Docker builds and releases, not test runs):

1. **A workflow exists that runs tests.** If none exists, that's the first finding — the test infrastructure exists but it's not automated.
2. **It runs on the right triggers.** At minimum: every PR and every push to `main`.
3. **It runs the entire suite.** Compare the test command in CI against what you run locally. Watch for patterns that only run a subset.
4. **The test step can actually fail the build.** Check for `|| true`, `continue-on-error: true`, or `exit 0` patterns.
5. **Required status checks are enforced.** The test workflow must be a required check in branch protection, or it can't block broken PRs from merging.

Red flags to grep for explicitly:
```bash
grep -r "continue-on-error\||| true\|exit 0" .github/workflows/
grep -r "skip\|xfail" backend/tests/
```

**Report CI gaps as first-class findings**, on equal footing with missing tests.

## What NOT to Do

- Don't write tests. Just report and plan.
- Don't suggest testing: bootstrap files, type-only files (`models.py` with only Pydantic schemas), pure FastAPI routing boilerplate with no logic.
- Don't chase coverage percentage as a goal. Focus on whether the important code is meaningfully tested.

## Testing Threshold

- **No action needed** if: all files with business logic have test files, assertions check real values, edge cases are covered for critical paths, coverage on core logic is 80%+, **and the full test suite runs in CI on every PR and push to main with no silent skips**. Say so and stop.
- **Improvement recommended** if any of these are true:
  - Backend source files with real logic have zero test coverage
  - Core business logic (NC parsing, FTP rules, ATC validation) is below 80% coverage
  - Existing tests rely primarily on weak assertions
  - No round-trip tests for NC parsing (parse → validate → expected structure)
  - **No CI workflow runs tests** (this project's current state)
  - Frontend has no test framework at all

## Testing Plan

If the threshold is met, produce a prioritized plan:

1. **Do first** — **fix CI gaps first** (add a test workflow that runs pytest on every PR), then add tests for untested business logic files. CI fixes make every subsequent improvement trustworthy.
2. **Do second** — round-trip tests for NC parsing, contract tests for telnet/FTP seams, edge cases for sync rules.
3. **Skip for now** — things that look like gaps but aren't worth the effort, with a one-line explanation. Examples: FastAPI route boilerplate, Pydantic schema-only files, Docker entrypoint scripts.

For each item, list the file that needs testing, what behavior should be tested, and what kind of test (unit or integration). For CI items, list the specific workflow file and the specific change to make.

**Important**: this skill pairs with `/jgl-review-code`. Run `/jgl-review-testing` first to build a safety net, then use `/jgl-review-code` to plan structural refactors with confidence.
