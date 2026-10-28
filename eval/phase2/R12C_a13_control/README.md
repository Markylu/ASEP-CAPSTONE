# R12C: a13 control on the R12 host

**Agent:** `a13` (`3de550e110e7`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) · **Perceiver:**
`g03` (`3531e4d9ade9`) · **Strategist:** `q01` (`40fb0fbc3285`) · **Spatial memory:**
`eceb875a68a3` · **Status:** draft, not flown

Draft written 2026-10-28 with [R12's draft](../R12_staged_search/README.md). Spec:
`docs/phase2-test-plan.md`.

## Change

None. This is `a13`, the agent R9 flew (dropped) and R10C re-flew, flown again unchanged on the R12
host at R12's SHA, right after R12. It is the control R12 is read against, not a round of its own.

## Evidence

R12 (`a17`) drops goal truth, so its control must not have it either.
- `a14` (R10) and `a16` (R11) read the goal's true position in code.
- `a13` is the last agent with none: the goal reaches it only through the perceiver.

R12 against R12C then measures the bundle (coverage map, stages, evaluator, reachable targets,
`g04`, `q04`) with the information each agent has held equal.

`a13` re-flown moved 3 of 18 outcomes (R10C against R9) and repeated 7 of 18 pick sequences. R12C
against R10C measures that floor again.

## Hypothesis

None to test. R12's changes must leave:
- `a13`'s sha unchanged;
- every one of R10C's 899 decision renders unchanged in words. Checked 2026-10-28 with
  `spatial_replay.py rerender`: 0 differ in words. 12 differ in the strategist field only, because
  replaying the strategist cannot reproduce its live call.

R12C is therefore expected to reproduce R10C up to `a13`'s own run-to-run variation.

## Predictions

| Arm | R10C `a13` | Predicted R12C |
|---|---|---|
| initial | 5/6 | 5/6 |
| final | 1/6 | 1/6 |
| dynamic | 1/6 | 1/6 |

Every cell that differs from R10C is reported with its first divergent step. The number of outcomes
R12C changes against R10C enters R12's attribution floor (R12 README, "Attribution rule").

## Manipulation check

Not applicable (no change). The renderer line in `godot.log` must read Vulkan, Forward+ and
llvmpipe, and every run's captured frame size must be 768x768 (checked by validation). R12C's
records are also replayed through `a17`'s memory to give the `view_revisit` baseline for R12's
predictions.

## Outcome

Not flown.
