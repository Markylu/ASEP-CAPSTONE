# R10C: a13 control on the R10 host

**Agent:** `a13` (`3de550e110e7`) · **Navigator prompt:** `p14` (`31a9f28eaf94`) · **Perceiver:**
`g03` (`3531e4d9ade9`) · **Strategist:** `q01` (`40fb0fbc3285`) · **Spatial memory:**
`eceb875a68a3` · **Status:** flown (18/18 valid)

Written before flying. Spec: `docs/phase2-test-plan.md`.

## Change

None. This is `a13`, the agent R9 flew (dropped), flown again unchanged on sctsvr6 at R10's SHA,
right after R10. It is the control R10 is read against, not a round of its own.

## Evidence

R10 (`a14`) is a bundle of three changes on `a13`, read against a control on the same host at the
same SHA (R10 README, "Attribution rule"). With `a13` as the control, R10 against R10C measures
those three changes and nothing else (operator, 2026-10-24).

## Hypothesis

None to test. This branch's changes leave `a13`'s sha and every one of R9's 871 decisions'
renders unchanged (R10 README, "Change"), so R10C is expected to reproduce R9.

## Predictions

| Arm | R9 `a13` | Predicted R10C |
|---|---|---|
| initial | 5/6 | 5/6 |
| final | 0/6 | 0/6 |
| dynamic | 1/6 | 1/6 |

Any cell that differs from R9 is reported with its first divergent step. R9C reproduced R8 in 16
of 18 pick sequences (both differences on s03), so a few divergent sequences are expected; an
outcome that differs means the host or the decider is less deterministic than that.

## Manipulation check

Not applicable (no change). The renderer line in `godot.log` must read Vulkan, Forward+ and
llvmpipe, and every run's captured frame size must be 768x768 (checked by validation).

## Drop criterion

None. Used only to read R10 against.

## Outcome

Flown 2026-10-25 on sctsvr6 at `76f8a05`, right after R10, 18/18 valid. 7/18 (initial 5/6, final
1/6, dynamic 1/6), against R9's 6/18 with the same agent: 3 outcomes differ (2 gained, 1 lost) and
11 of 18 pick sequences differ. The prediction missed on `final` (1/6, not 0/6).
[summary.md](summary.md).
