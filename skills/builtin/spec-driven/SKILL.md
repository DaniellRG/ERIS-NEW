---
name: spec-driven
description: "Specification-Driven Development (SDD). Use when starting new features, refactoring, or when requirements need formal specification before implementation. Inverts the traditional model: specs drive code, not the other way around."
---

# Specification-Driven Development (SDD)

## Core Principle

Specifications don't serve code — code serves specifications. The PRD isn't a guide for implementation; it's the source that generates implementation. Technical plans aren't documents that inform coding; they're precise definitions that produce code.

## The SDD Workflow

### Phase 1: Specify (Intent → PRD)
- Start with an idea (often vague and incomplete)
- Through iterative dialogue, transform into a comprehensive PRD
- AI asks clarifying questions, identifies edge cases, defines acceptance criteria
- Research agents gather: library compatibility, performance benchmarks, security implications
- Organizational constraints discovered and applied automatically

### Phase 2: Plan (PRD → Technical Plan)
- Generate implementation plans that map requirements to technical decisions
- Every technology choice has documented rationale
- Every architectural decision traces back to specific requirements
- Consistency validation: AI analyzes for ambiguity, contradictions, gaps (ongoing, not one-time)

### Phase 3: Tasks (Plan → Task Breakdown)
- Break the plan into concrete, actionable tasks
- Each task maps to specific requirements
- Tasks are ordered by dependency
- Acceptance criteria are explicit per task

### Phase 4: Implement (Tasks → Code)
- Code generation begins as soon as specs and plans are stable enough
- Early generations may be exploratory (testing if spec makes sense in practice)
- Domain concepts → data models, User stories → API endpoints, Acceptance scenarios → tests
- Development and testing merge through specification

### Phase 5: Converge (Code → Validation)
- Run tests, verify acceptance criteria
- Production metrics and incidents feed back into specs
- Performance bottlenecks → new non-functional requirements
- Security vulnerabilities → constraints for future generations

## Core Principles

1. **Specifications as the Lingua Franca** — Specs are the primary artifact; code is their expression
2. **Executable Specifications** — Precise, complete, unambiguous enough to generate working systems
3. **Continuous Refinement** — Consistency validation is ongoing, not a one-time gate
4. **Research-Driven Context** — Research agents gather technical context throughout
5. **Bidirectional Feedback** — Production reality informs spec evolution
6. **Branching for Exploration** — Generate multiple approaches from the same spec

## Key Commands

### /specify
Transform a feature description into a complete, structured specification with automatic repository management.

### /plan
Generate implementation plan from the specification.

### /tasks
Break the plan into concrete tasks.

### /implement
Generate code from the specification and plan.

## Eris-Specific Integration

- Eris's ODD workflow already follows SDD principles (Authorize → Explore → Classify → Track → Implement → Close)
- The feature document (`odd/tasks/<feature>.md`) IS the specification
- Specs (S#) quote the user's exact strings — this IS the PRD
- Tasks (T#) map to specs — this IS the implementation plan
- Work-unit commits are the implementation
- Verification is the convergence step

### Enhancement: Use SDD commands
- Before implementing a large feature, run `/specify` to formalize the PRD
- Use `/plan` to generate the technical plan
- Use `/tasks` to break into concrete tasks
- Use `/implement` to generate code from specs

## Why SDD Matters Now

1. **AI capabilities** — natural language specs can reliably generate working code
2. **Software complexity** — modern systems integrate dozens of services; SDD provides systematic alignment
3. **Pace of change** — requirements change rapidly; SDD transforms pivots into systematic regenerations

## When to Use SDD

- New features with complex requirements
- Refactoring with unclear boundaries
- Multi-component systems
- When multiple implementations might be needed
- When requirements are likely to change

## When NOT to Use SDD

- Simple bug fixes (use TDD instead)
- Single-file changes
- Exploratory spikes
- When the spec is already clear (just implement)
