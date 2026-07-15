# Writing Plans Skill

## When to Use
After brainstorming is approved. Before any implementation begins.

## Process

### 1. Break It Down
- Divide the work into tasks that take 2-5 minutes each
- Each task must be: specific, testable, independent
- No task should be "implement the whole feature"

### 2. Task Format
For each task:
```
- [ ] Task Name (2 min)
  File: path/to/file.py
  Action: Add/Modify/Delete
  Details: What exactly to do
  Verify: How to confirm it worked
```

### 3. Order Matters
- Dependencies first (setup, configs, base classes)
- Core logic next
- Polish last (styles, messages, edge cases)

### 4. Checkpoints
- After every 3-5 tasks, pause for review
- Verify everything works before continuing
- If something breaks, fix it before moving on

## Rules
- Every task has: exact file path, complete specs, verification step
- No task over 5 minutes. If longer, split it.
- Write the plan to Obsidian: `obsidian_note write` in folder "Reportes"
