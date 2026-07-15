---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

You write test cases (pressure scenarios), watch them fail (baseline behavior without the skill), write the skill, watch tests pass (agents comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools. Skills help future agents find and apply effective approaches.

**Skills are:** Reusable techniques, patterns, tools, reference guides

**Skills are NOT:** Narratives about how you solved a problem once

## When to Create a Skill

**Create when:**
- Technique wasn't intuitively obvious
- You'd reference this again across projects
- Pattern applies broadly (not project-specific)
- Others would benefit

**Don't create for:**
- One-off solutions
- Standard practices well-documented elsewhere
- Project-specific conventions (put in AGENTS.md)

## SKILL.md Structure

**Frontmatter (YAML):**
- Required fields: `name` and `description`
- `name`: Use letters, numbers, and hyphens only
- `description`: Start with "Use when..." to focus on triggering conditions
  - Describe ONLY when to use, NOT what the skill does
  - Use concrete triggers, symptoms, and situations

```markdown
---
name: skill-name-here
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
What is this? Core principle in 1-2 sentences.

## When to Use
Bullet list with SYMPTOMS and use cases. When NOT to use.

## Core Pattern
Before/after code comparison

## Quick Reference
Table or bullets for scanning common operations

## Implementation
Inline code or link to separate file

## Common Mistakes
What goes wrong + fixes
```

## Skill Discovery Optimization (SDO)

### Description Field

**CRITICAL: Description = When to Use, NOT What the Skill Does**

The description should ONLY describe triggering conditions. Do NOT summarize the skill's process.

```yaml
# BAD: Summarizes workflow
description: Use when executing plans - dispatches subagent with code review

# GOOD: Just triggering conditions
description: Use when executing implementation plans with independent tasks
```

### Token Efficiency

Target word counts:
- Frequently-loaded skills: under 200 words total
- Other skills: under 500 words

## Testing Skills

Follow RED-GREEN-REFACTOR:

### RED: Baseline
Run scenario WITHOUT the skill. Document exact behavior, rationalizations, failures.

### GREEN: Write Skill
Write skill addressing specific baseline failures. Run scenario WITH skill. Verify compliance.

### REFACTOR: Close Loopholes
Find new rationalizations, add counters, re-test until bulletproof.

## Common Rationalizations for Skipping Testing

| Excuse | Reality |
|--------|---------|
| "Skill is obviously clear" | Clear to you is not clear to other agents. Test it. |
| "Testing is overkill" | Untested skills have issues. Always. |
| "No time to test" | Deploying untested skill wastes more time later. |

## The Iron Law

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

Write skill before testing? Delete it. Start over.

## Skill Creation Checklist

- [ ] Name uses only letters, numbers, hyphens
- [ ] Description starts with "Use when..." and includes triggers
- [ ] Description written in third person
- [ ] Keywords throughout for search
- [ ] Clear overview with core principle
- [ ] One excellent example (not multi-language)
- [ ] Common mistakes section
- [ ] Tested with pressure scenarios
- [ ] Rationalization table if discipline skill
