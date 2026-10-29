# R20K: R19K with the doorway confirmer

**Agent:** `a38` (`5f54e18d45cb`) · **Prompt:** `p17` (`cb3578251cfe`) · **Goal confirmer:** `c01`
· **Doorway confirmer:** `d01` · **Status:** pre-registered 2026-10-29, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Flies beside R20 (`a37`); the doorway
confirmer, its probe and the smoke are in [R20's README](../R20_door_confirmer/README.md).

## Change

`a36` (R19K: `a35` + `c01`) with `d01`: both second looks, the goal's and the doorway's.

## Evidence

As R20. `c01` alone: R16K (`a28`) 10/18 against R16's 6/18, dynamic 3/6.

## Hypothesis

R20K scores above R19K.

## Predictions

| Arm | Baseline (R19K, `a36`) | Predicted |
|---|---|---|
| initial | R19K's | same (± 1) |
| final | R19K's | + 1 |
| dynamic | R19K's | + 1 |

## Manipulation check

As R20, plus `confirmer` recorded on every goal report.

## Drop criterion

Not carried forward if the total does not beat R19K.

## Probe gate

R20's (passed).

## Builds on

R19K (`a36`).

## Outcome

Flown 2026-10-29, lanes 5–8 beside R20: 18/18 valid. **12/18** (initial 6, final 4, dynamic 2)
against R19K's 11/18: **hypothesis held**. **The best Phase 2 score so far** (R11 11/18).

| site | initial | final | dynamic |
|---|---|---|---|
| s01 | 1 | 1 | 1 |
| s02a | 1 | 1 | 1 |
| s02c | 1 | 1 | . |
| s02va | 1 | . | . |
| s02vc | 1 | . | . |
| s03 | 1 | 1 | . |

- `d01` asked on 262 steps, 0 failed. Menu doorways 18 (R19K 54), 3 within 2.5 m of an open
  door; picked 8 (R19K 16).
- Turn-arounds against a forward "toward" 20 (R19K 18).
- s02va and s02vc `final`/`dynamic` still 0/4: the drone does not find door A or C across the
  divider from B (mode B/K). R21's along-the-wall detours fly next on this agent (`a41`).
- [manipulation.txt](manipulation.txt).
