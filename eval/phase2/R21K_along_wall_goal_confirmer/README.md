# R21K: R20K with along-the-wall detours

**Agent:** `a41` (`ca6f816e9c32`) · **Prompt:** `p17` (`cb3578251cfe`) · **Strategist:** `q08` ·
**Goal confirmer:** `c01` · **Doorway confirmer:** `d01` · **Status:** pre-registered 2026-10-29,
not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Flies beside R21 (`a40`); the change, its
probes and the smoke are in [R21's README](../R21_along_wall/README.md).

## Change

`a38` (R20K) with `a40`'s along-the-wall detours and strategist `q08`.

## Evidence

As R21.

## Hypothesis

R21K scores above R20K.

## Predictions

| Arm | Baseline (R20K, `a38`) | Predicted |
|---|---|---|
| initial | R20K's | same (± 1) |
| final | R20K's | + 1 or more |
| dynamic | R20K's | + 1 |

## Manipulation check

As R21.

## Drop criterion

Not carried forward if the total does not beat R20K.

## Probe gate

R21's.

## Builds on

R20K (`a38`).

## Outcome

Flown 2026-10-29, lanes 5–8 beside R21: 18/18 valid. **10/18** (initial 6, final 1, dynamic 3)
against R20K's 12/18: **not carried forward**.

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | . | . |
| s02c | 1 | . | 1 |
| s02va | 1 | . | 1 |
| s02vc | 1 | . | . |
| s03 | 1 | . | . |

Same pattern as R21: `dynamic` up (3, R20K 2; s02va `dynamic` solved), `final` down (1, R20K 4).
Along item picked on 81 of 84 calls; stalled-detour hand-backs 29 (R20K 11); mean span 3.7.
[manipulation.txt](manipulation.txt).
