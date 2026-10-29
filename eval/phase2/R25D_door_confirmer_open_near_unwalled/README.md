# R25D: R20 without the wall at the end of an open_near strip

**Agent:** `a49` (`83f7a6a19b01`) · **Prompt:** `p17` (`cb3578251cfe`) · **Memory:** `a17b` ·
**Status:** pre-registered 2026-10-29, not flown

Written before flying. Flies beside R25 (`a48`); the change and its evidence are in
[R25's README](../R25_best_open_near_unwalled/README.md).

## Change

`a37` (R20, 11/18) on memory `a17b`.

## Hypothesis

R25D scores above R20.

## Predictions

| Arm | Baseline (R20, `a37`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 4 | 4 or 5 |
| dynamic | 1 | 1 or 2 |

## Drop criterion

Not carried forward if the total does not beat R20's 11/18.

## Builds on

R20 (`a37`).

## Outcome

Flown 2026-10-29, lanes 1–4 beside R25: 18/18 valid. **14/18** (initial 6, final 3, dynamic 5)
against R20's 11/18: **hypothesis held** (+ 3). **Best Phase 2 score so far** (R20K, R22K, R25
12/18).

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | 1 | 1 |
| s02c | 1 | . | 1 |
| s02va | 1 | . | 1 |
| s02vc | 1 | 1 | 1 |
| s03 | 1 | . | . |

- `dynamic` 5/6 (R20 1/6), the best arm in any round: every s02 `dynamic` run solved. `final`
  3/6 (R20 4/6): s03 `final` lost (9.2 m away), s02vc `final` gained.
- Turn-arounds against a forward "toward" 4 (R20 14). s03 crossbar first reached at step 8 in
  `initial` and `dynamic`, 31 in `final`. s03 `final`/`dynamic` fail as in the s03 tines analysis
  ([../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md](../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md)):
  8.9–9.2 m from the goal, in the shut tine.
- One seed per run: + 3 is the largest step in Phase 2, and part of it may be seed-1 luck
  (R21's `dynamic` 4/6 did not repeat in R22).
- Why 14: [why_14.md](why_14.md). In short, memory `a17b` helps at the open door (45% → 57% once within
  3 m), on a lucky draw: the same step-0 frame is read differently from round to round at temperature 0, and the
  `a17b` family expects 11.3 ± 1.4.
- [manipulation.txt](manipulation.txt).
