# R11C: a14 control on the R11 host

**Agent:** `a14` (`63ad006476b6`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) · **Perceiver:**
`g03` (`3531e4d9ade9`) · **Strategist:** `q02` (`f3a866c9d927`) · **Spatial memory:**
`eceb875a68a3` + a14 wording `0075a8a0e5c0` · **Status:** **draft, not flown**

Draft written 2026-10-25 with [R11's draft](../R11_goal_default/README.md). Spec:
`docs/phase2-test-plan.md`.

## Change

None. This is `a14`, the agent R10 flew (not dropped, not credited), flown again unchanged on the
R11 host at R11's SHA, right after R11. It is the control R11 is read against, not a round of its
own.

## Evidence

R11 (`a15`) is a bundle on `a14`, read against a control on the same host at the same SHA. With
`a14` as the control, R11 against R11C measures the bundle and nothing else.

R10C showed that re-flying an unchanged multi-call agent moves outcomes: `a13` repeated R9 in 7 of
18 pick sequences and 15 of 18 outcomes. No such floor has been measured for `a14` (R10 summary,
"For the next round" 1). R11C against R10 is that measurement.

## Hypothesis

None to test. R11's changes must leave `a14`'s sha and every one of R10's 755 decisions' renders
unchanged, so R11C is expected to reproduce R10 up to `a14`'s own run-to-run variation.

## Predictions

| Arm | R10 `a14` | Predicted R11C |
|---|---|---|
| initial | 5/6 | 5/6 |
| final | 3/6 | 3/6 |
| dynamic | 3/6 | 3/6 |

Every cell that differs from R10 is reported with its first divergent step. The number of
outcomes R11C changes against R10 enters R11's attribution floor (R11 README, "Attribution rule").

## Manipulation check

Not applicable (no change). The renderer line in `godot.log` must read Vulkan, Forward+ and
llvmpipe, and every run's captured frame size must be 768x768 (checked by validation).

## Outcome

Not flown.
