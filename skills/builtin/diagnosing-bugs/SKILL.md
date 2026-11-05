---
name: diagnosing-bugs
description: "Diagnosis loop for hard bugs and performance regressions. Use when the user says diagnose/debug, or reports something broken, throwing, failing, or slow."
---

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

## Phase 1: Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug, you will find the cause. If you don't, no amount of staring at code will save you.

### Ways to construct one
1. **Failing test** at whatever seam reaches the bug.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with fixture input, diffing stdout against known-good snapshot.
4. **Headless browser script** (Playwright) driving the UI.
5. **Replay a captured trace** — save a real payload, replay through code path in isolation.
6. **Throwaway harness** — minimal subset exercising the bug code path.
7. **Property / fuzz loop** — 1000 random inputs, look for failure mode.
8. **Bisection harness** — automate "boot at state X, check, repeat".
9. **Differential loop** — run same input through old vs new version, diff outputs.
10. **HITL bash script** — last resort, drive the human with structured script.

### Tighten the loop
- Can I make it faster? (Cache setup, narrow test scope.)
- Can I make the signal sharper? (Assert on specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem.)

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is a debugging superpower.

### Non-deterministic bugs
Raise reproduction rate: loop 100×, parallelise, add stress, narrow timing windows. A 50%-flake bug is debuggable; 1% is not.

### When you genuinely cannot build a loop
Stop and say so explicitly. List what you tried. Ask for: (a) access to reproducing environment, (b) redacted captured artifact, (c) permission for production instrumentation. Do NOT hypothesise without a loop.

### Completion criterion: a tight loop that goes red
- **Red-capable**: drives the actual bug code path, asserts the **user's exact symptom**
- **Deterministic**: same verdict every run
- **Fast**: seconds, not minutes
- **Agent-runnable**: you can run it unattended

No red-capable command = no Phase 2.

## Phase 2: Reproduce + minimise

Run the loop. Watch it go red. Confirm:
- The loop produces the failure the **user** described, not a different failure nearby.
- The failure is reproducible across multiple runs.
- You captured the exact symptom (error message, wrong output, slow timing).

### Minimise
Shrink the repro to the **smallest scenario that still goes red**. Cut inputs, callers, config, data, steps one at a time, re-running after each cut. Keep only what's load-bearing.

Done when **every remaining element is load-bearing**: removing any one makes the loop go green.

## Phase 3: Hypothesise

Generate **3–5 ranked hypotheses** before testing any. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe: discard or sharpen.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly.

## Phase 4: Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:
1. **Debugger / REPL inspection** if env supports it.
2. **Targeted logs** at boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch:** For performance regressions, logs are usually wrong. Establish a baseline measurement (timing harness, profiler, query plan), then bisect. Measure first, fix second.

## Phase 5: Fix + regression test

Write the regression test **before the fix**, but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow, a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for the next phase.

If a correct seam exists:
1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail. If forced red by mutating code/fixture, `diff` against pristine copy to prove the mutation landed.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6: Cleanup

Required before declaring done:
- [ ] Original repro no longer reproduces (re-run Phase 1 loop)
- [ ] Regression test passes (or absence of seam documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to clearly-marked debug location)
- [ ] The hypothesis that turned out correct is stated in the commit/PR message
