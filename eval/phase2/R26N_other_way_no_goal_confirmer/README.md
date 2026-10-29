# R26N: R22 with the other way at the fork

**Agent:** `a59` (`8b190373a9f0`) · **Prompt:** `p17` (`cb3578251cfe`) · **Strategist:** `q13` ·
**Memory:** `a17b` · **Status:** pre-registered 2026-10-29, not flown

Written before flying. Flies beside R26 (`a58`); the change, its probes and the gate are in
[R26's README](../R26_other_way/README.md).

## Change

`a42` (R22, 10/18) with `a58`'s "other way at the fork" (listed only in a dead end), the
closed-door line beside it, and strategist `q13`.

## Hypothesis

R26N scores above R22, through s03 `final`/`dynamic`.

## Predictions

| Arm | Baseline (R22, `a42`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 2 | 2 or 3 |
| dynamic | 2 | 2 or 3 |

## Drop criterion

Not carried forward if the total does not beat R22's 10/18.

## Builds on

R22 (`a42`).

## Outcome

Flown 2026-10-29, lanes 5–8 beside R26: 18/18 valid. **11/18** (initial 5, final 3, dynamic 3)
against R22's 10/18: **hypothesis held by one, but not through s03** (0/3, R22 1/3). Below the best
(R25D, 14/18): **not carried forward**.

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | . | . |
| s02c | 1 | 1 | 1 |
| s02va | 1 | . | 1 |
| s02vc | 1 | 1 | . |
| s03 | . | . | . |

- In s03 `final`/`dynamic` the other way was listed and chosen in every run (R26 1 and 1;
  R26N 1 and 2 picks). It did not get the drone back to the fork. The target lies behind, about
  11 m back; the navigator went back and forth (R26 `final`: x −5.3 → −3.6 → −5.3), and the
  stalled-detour hand-back (4 moves gaining under 0.5 m, `a33`) ended the detour after 4 steps. The
  strategist then returned to the along-the-wall items. R26 `dynamic` held it 14 steps and reached
  x = 2.5, then turned back. The probe tested only the strategist's choice, not whether the drone
  could fly 11 m back to the target.
- The next step, if this line is kept: exempt the "other way" from the stall hand-back, or hand
  it to the planner as waypoints back along the trail, rather than as one target 11 m behind.
- Gained against R22: s02c `final` and `dynamic`, s02va `dynamic`, s02vc `final`. Lost: s02va `final`, s02vc
  `dynamic`, s03 `initial` (6.7 m away; the item was never listed there).
- [manipulation.txt](manipulation.txt).
