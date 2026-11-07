# R67: a100 again, batch 4's reference lane on H100 frames (host round), contested cells

**Agent:** `a100` (`22e2941dc494`), as R63 flew it, unchanged · **Prompt:** `p17` (`cb3578251cfe`) ·
**Perceiver:** `g05` · **Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100
(`GODOT_VK=nvidia`) · **Status:** laid out 2026-11-07 (Claude, overnight), not flown

Written before flying. A host round under the operator's rule of 2026-11-06 ("3+1 with reference lane"): the
candidates' parent flies beside them on the same renderer. `a100` was carried in batch 3 (R63, 22/30 against
`a93`'s 16/30), so it is batch 4's parent and reference. Design: the ten contested cells, seeds 1–3, 30 runs.

## Change

**No agent change.** `a100` on H100 frames beside R65 (`a101`) and R66 (`a102`), same commit, same minutes.
Its second flight.

## Hypothesis

`a100` on H100 frames reads as in R63 within the family's spread: 18–24 of 30, s02 14–21, s03 2–6; at most
two stations given up in transit, none before the tenth step.

## Predictions

| | R63 (`a100`) | `a93` on H100 (4 flights) | Predicted R67 |
|---|---|---|---|
| total | 22/30 | 19, 20, 21, 16 | 18–24 |
| s02 | 18/24 | 17, 17, 16, 13 | 14–21 |
| s03 | 4/6 | 2, 3, 5, 3 | 2–6 |

## What it decides

The comparison for R65 and R66, and `a100`'s second sample: with R63 it is 60 runs against `a93`'s 120 on this
renderer. If it reads 18 or below, R63's +6 was in part `a93`'s low flight; the morning report says so either way.

## Manipulation check

- Every `run.json` carries `a100`, `22e2941dc494`, `:8007`; every `godot.log` names `NVIDIA H100 PCIe`.
- No station given up in transit before its tenth step.
- Walls in flight within 4 points of R63's (17.6 / 12.2 / 16.0).
- The survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps.

## Drop criterion

Not applicable (a reference).

## Probe gate

Not needed (no change).

## Shakedown

None (30 valid runs in R63, 4 in its shakedown).

## Host

Lanes 9–12 of `~/asep-r65-l1..12` on `:8007`, beside R65 (`:8004`) and R66 (`:8006`); Godot on GPU 5.
`~/r65_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R63 (the same agent). Branch `phase2/r65-wait-inflate` (shared with R65 and R66).

## Outcome

Not flown yet.
