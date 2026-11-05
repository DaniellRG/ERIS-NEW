---
name: tdd
description: "Test-Driven Development for any feature or bugfix. Use when implementing new functionality, fixing bugs, or refactoring. Write tests first, then code."
---

# Test-Driven Development

## Core Principle

Write the test first. Watch it fail. Write minimal code to pass. Refactor. Repeat.

## The Red-Green-Refactor Cycle

### 1. Red — Write a failing test
- Write one test that describes the desired behavior
- Run it — it must FAIL (not error, not pass)
- If it passes, the test is wrong or the feature already exists

### 2. Green — Write minimal code
- Write the simplest code that makes the test pass
- Don't add features, don't optimize, don't refactor
- Run the test — it must PASS

### 3. Refactor — Clean up
- Improve code quality without changing behavior
- Run tests after each change — they must stay green
- Remove duplication, improve naming, simplify

## Test Quality Rules

- **One assertion per test** (when possible)
- **Test behavior, not implementation** — tests should survive refactoring
- **Name tests clearly** — `test_user_can_login_with_valid_credentials`
- **Arrange-Act-Assert** pattern
- **No test interdependence** — each test runs in isolation

## For Bug Fixes

1. Write a test that reproduces the bug (red)
2. Fix the bug (green)
3. The test becomes the regression test

## For Refactoring

1. Ensure existing tests pass (green baseline)
2. Refactor in small steps
3. Run tests after each step
4. If a test breaks, the refactor changed behavior — revert or fix

## Eris-Specific

- Python tests: `pytest` with `test_all.py` as the main suite
- Frontend tests: check for existing test files in `tests/`
- Always run `test_all.py` after changes to verify no regression
- Use `--fast` flag for quick iteration during development
