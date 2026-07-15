# Verification Skill

## When to Use
After completing ANY task. Before telling the user "done".

## Process

### 1. Self-Check
- Did I do exactly what was asked?
- Does the output match the expected format?
- Are there any errors in the console or logs?

### 2. Test the Result
- If I created a file: does it exist in the right location?
- If I opened an app: is it actually running?
- If I searched: are the results relevant?
- If I wrote text: is it correct and complete?

### 3. Edge Cases
- What if the file already exists?
- What if the app is not installed?
- What if there's no internet?
- Handle these gracefully.

### 4. Report
- Tell the user what you did AND what you verified
- "I opened Chrome, verified it's running, and searched for X. The results are on screen."
- If anything failed, say so clearly and suggest next steps.

## Rules
- Never say "Done" without verifying
- If verification fails, use `systematic-debugging` skill
- Log results with `obsidian_note daily`
