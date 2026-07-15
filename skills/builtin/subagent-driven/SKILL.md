# Subagent-Driven Development Skill

## When to Use
When a task can be broken into independent pieces that can run in parallel.

## Process

### 1. Identify Parallelizable Work
- Look for tasks that DON'T depend on each other
- Examples: searching multiple sources, processing multiple files
- Group related tasks for one subagent each

### 2. Dispatch Subagents
For each independent piece:
- Use `task_queue add` with clear task name and details
- Assign priority based on importance
- Set task type: research, file_op, analysis, system

### 3. Execute in Parallel
- Run multiple tasks simultaneously when possible
- Use `task_queue run_next` to process the queue
- Monitor progress with `task_queue list`

### 4. Collect and Synthesize
- Gather results from all subagents
- Combine into unified response
- Use `obsidian_note write` to save the synthesis

## Two-Stage Review
1. **Spec Compliance**: Did each subagent do what was asked?
2. **Quality Check**: Was the work done correctly?

## Rules
- Max 5 subagents at a time to avoid overload
- Each subagent gets ONE clear task
- Always verify subagent results before presenting to user
