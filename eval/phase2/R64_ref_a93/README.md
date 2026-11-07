# R64: a93 again, batch 3's reference lane on H100 frames (host round), contested cells

**Agent:** `a93` (`8cc0bfc63d4e`), unchanged · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight); **flown 2026-11-07**

Written before flying. A host round under the operator's rule of 2026-11-06 ("3+1 with reference lane").
Design: the ten contested cells, seeds 1–3, 30 runs.

## Change

**No agent change.** `a93` on H100 frames beside R62 (`a99`) and R63 (`a100`), same commit, same minutes.
Its fourth H100 flight (R54 19, R58 20, R61 21).

## Hypothesis

`a93` on H100 frames reads as before: 17–23 of 30, s02 13–20, s03 2–6.

## Predictions

| | R54 | R58 | R61 | Predicted R64 |
|---|---|---|---|---|
| total | 19/30 | 20/30 | 21/30 | 17–23 |
| s02 | 17/24 | 17/24 | 16/24 | 13–20 |
| s03 | 2/6 | 3/6 | 5/6 | 2–6 |

## What it decides

Nothing on its own: the comparison for R62 and R63. With R54, R58 and R61 it is `a93`'s 120 runs on this
renderer.

## Manipulation check

- Every `run.json` carries `a93`, `8cc0bfc63d4e`, `:8007`; every `godot.log` names `NVIDIA H100 PCIe`.
- Walls in flight within 4 points of R61's (21.0 / 10.4 / 12.4).
- The survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps.

## Drop criterion

Not applicable (a reference).

## Probe gate

Not needed (no change).

## Shakedown

None.

## Host

Lanes 9–12 of `~/asep-r62-l1..12` on `:8007`, beside R62 (`:8004`) and R63 (`:8006`); Godot on GPU 5.
`~/r62_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R61 (the same agent, renderer and role). Branch `phase2/r62-mouth-stall` (shared with R62 and R63).

## Outcome

**Flown 2026-11-07, 16/30** (s02 13/24, s03 3/6): the low edge of the 17–23 predicted, `a93`'s lowest of four H100
flights (19, 20, 21, 16). Five stations given up in transit at the sixth step in four runs, all lost. The bar for
R62 and R63. [summary.md](summary.md).
