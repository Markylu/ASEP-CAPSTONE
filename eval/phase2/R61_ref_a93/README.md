# R61: a93 again, batch 2's reference lane on H100 frames (host round), contested cells

**Agent:** `a93` (`8cc0bfc63d4e`), as R53, R54 and R58 flew it, unchanged · **Prompt:** `p17`
(`cb3578251cfe`) · **Perceiver:** `g05` · **Door confirmer:** `d01` · **Memory:** `a17f` ·
**Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) · **Status:** laid out 2026-11-07 (Claude, overnight),
not flown

Written before flying. A host round under the operator's rule of 2026-11-06 ("3+1 with reference lane"):
the reference agent flies beside the candidates on the same renderer in every batch, and the candidates
are read against that flight. Design: the ten contested cells, seeds 1–3, 30 runs.

## Change

**No agent change.** `a93` flown on H100 frames beside R59 (`a98`) and R60 (`a96`), same commit, same
minutes. Its third H100 flight (R54 19, R58 20).

## Hypothesis

`a93` on H100 frames reads as in R54 and R58: 16–24 of 30, s02 13–21, s03 1–5.

## Predictions

| | R54 | R58 | R53 (lavapipe) | Predicted R61 |
|---|---|---|---|---|
| total | 19/30 | 20/30 | 24/30 | 16–24 |
| s02 | 17/24 | 17/24 | 20/24 | 13–21 |
| s03 | 2/6 | 3/6 | 4/6 | 1–5 |

## What it decides

Nothing on its own: the comparison for R59 and R60. With R54 and R58 it is `a93`'s 90 runs on this renderer.

## Manipulation check

- Every `run.json` carries `a93`, `8cc0bfc63d4e`, `:8007`; every `godot.log` names `NVIDIA H100 PCIe`.
- Walls in flight within 4 points of R58's (20.2 / 10.5 / 12.7).
- The survey starts in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps.
- Blind goal reports a run within a third of R58's 1.1.

## Drop criterion

Not applicable (a reference).

## Probe gate

Not needed (no change).

## Shakedown

None (120 valid runs of this agent, 60 on this path).

## Host

Lanes 9–12 of `~/asep-r59-l1..12` on `:8007` (a copy of `:8004` on GPU 4), beside R59 (`:8004`) and R60
(`:8006`); Godot on GPU 5. `~/r59_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R58 (the same agent, renderer and role). Branch `phase2/r59-latch-survey` (shared with R59 and R60).

## Outcome

Not flown yet.
