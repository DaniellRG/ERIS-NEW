---
name: code-review
description: "Systematic code review for quality, security, and maintainability. Use when reviewing PRs, code changes, or auditing code."
---

# Code Review

## Review Checklist

### Correctness
- [ ] Does the code do what it's supposed to do?
- [ ] Are edge cases handled?
- [ ] Are error conditions handled gracefully?
- [ ] Are there any off-by-one errors?

### Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user inputs
- [ ] No SQL injection, XSS, or command injection
- [ ] Proper authentication/authorization checks
- [ ] Sensitive data not logged

### Performance
- [ ] No N+1 queries
- [ ] No unnecessary allocations in hot paths
- [ ] Proper use of caching
- [ ] No blocking operations in async code

### Maintainability
- [ ] Clear, descriptive names
- [ ] Functions do one thing
- [ ] No deep nesting (>3 levels)
- [ ] No magic numbers (use constants)
- [ ] Comments explain WHY, not WHAT

### Testing
- [ ] Are there tests for the new code?
- [ ] Do tests cover edge cases?
- [ ] Are tests independent and deterministic?

## Review Process

1. **Read the diff** — understand what changed
2. **Check the tests** — do they exist? Do they pass?
3. **Run the code** — does it work?
4. **Check for security issues** — scan for common vulnerabilities
5. **Suggest improvements** — be specific, not vague
6. **Approve or request changes** — with clear reasoning

## Eris-Specific
- Always run `test_all.py` after changes
- Check that tool declarations match the registry
- Verify config panel reflects new settings
- Test on both local and server mode
