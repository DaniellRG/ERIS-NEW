# Systematic Debugging Skill

## When to Use
When ANYTHING fails: tool error, wrong result, crash, unexpected behavior.

## Process - 4 Phases

### Phase 1: DETECT
- Read the FULL error message (don't skip)
- Identify WHICH tool or module failed
- Log the error: `learn_from_mistake` with error details
- "I tried X but got error Y"

### Phase 2: DIAGNOSE
- Is it a code error? → Check syntax, imports, parameters
- Is it a timing issue? → Add wait, retry with delay
- Is it a missing file/app? → Verify path, try alternative
- Is it a permission issue? → Check access rights
- "The error says Z. This usually means..."

### Phase 3: FIX
- Try the SIMPLEST fix first
- Test in sandbox if risky: `sandbox_run`
- If fix A fails, try fix B (different approach)
- NEVER try more than 3 times without asking user
- "Attempting fix: [description]"

### Phase 4: LEARN
- Document what went wrong and how it was fixed
- Save to Obsidian: `obsidian_note write` in folder "Memoria"
- Register the lesson: `learn_from_mistake`
- "I learned that X fails because of Y. Next time I'll do Z."

## Root Cause Tracing
- Ask "why" 5 times to find the real cause
- Why did it fail? → Because X
- Why did X happen? → Because Y
- Why Y? → Because Z (ROOT CAUSE)

## Rules
- Never guess. Test each hypothesis.
- One fix at a time. Verify before next attempt.
- If stuck after 3 tries, EXPLAIN what you tried and ask for help.
