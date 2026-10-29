# R22K: R21K without the wall at the end of an open_near strip

**Agent:** `a43` (`3d499552d09d`) · **Prompt:** `p17` (`cb3578251cfe`) · **Memory:** `a17b` ·
**Status:** pre-registered 2026-10-29, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Flies beside R22 (`a42`); the change, the
replay and the smoke are in [R22's README](../R22_open_near_unwalled/README.md).

## Change

`a41` (R21K) on memory `a17b`.

## Hypothesis

R22K scores above R21K.

## Predictions

| Arm | Baseline (R21K, `a41`) | Predicted |
|---|---|---|
| initial | R21K's | + 1 (s03) |
| final | R21K's | same or + 1 |
| dynamic | R21K's | same or + 1 |

## Manipulation check

As R22.

## Drop criterion

Not carried forward if the total does not beat R21K.

## Probe gate

R22's (passed).

## Builds on

R21K (`a41`).

## Outcome

Flown 2026-10-29, lanes 5–8 beside R22: 18/18 valid. **12/18** (initial 6, final 3, dynamic 3)
against R21K's 10/18: **hypothesis held** (+ 2); level with R20K (12/18), the best so far.

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | 1 | . |
| s02c | 1 | . | 1 |
| s02va | 1 | . | 1 |
| s02vc | 1 | 1 | . |
| s03 | 1 | . | . |

- Turn-arounds against a forward "toward" 9 (R21K 22). s03 crossbar first reached at step 8 in all
  three arms (R21K 8, 8, 11; R20K 14, 12, 8). s03 `final` and `dynamic` still unsolved, ending
  9.4 m and 8.0 m away: reaching the crossbar early is not enough, the tines are not searched.
- s02vc `final` solved for the first time with a goal confirmer.
- [manipulation.txt](manipulation.txt).
