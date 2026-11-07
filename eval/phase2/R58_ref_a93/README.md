# R58: a93 again, the batch's reference lane on H100 frames (host round), contested cells

**Agent:** `a93` (`8cc0bfc63d4e`), as R53 and R54 flew it, unchanged · **Prompt:** `p17`
(`cb3578251cfe`) · **Perceiver:** `g05` · **Door confirmer:** `d01` · **Memory:** `a17f` ·
**Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) · **Status:** laid out 2026-11-07 (Claude, overnight); **flown 2026-11-07**,
not flown

Written before flying. A host round under the operator's rule of 2026-11-06 ("3+1 with reference
lane", `eval/docker/README.md`, `docs/phase2-test-plan.md` changelog): **one instance always flies
the reference agent beside the candidates on the same renderer, and the candidates are read against
that flight.** Design: the ten contested cells, seeds 1–3, 30 runs.

## Change

**No agent change.** `a93`, the agent R56 (`a94`) and R57 (`a95`) build on, flown on H100 frames
in the same batch, same commit, same minutes.

## Why

H100 frames cost about 5 runs in 30 against lavapipe for `a93` (R54: 19 against 24) and `a89`
(R55: 18 against 23), cause not found; the flight-to-flight spread of near-identical agents is
about 4. A candidate read against a lavapipe number or an earlier H100 flight could not be told
from either. The reference lane gives the batch its own bar.

## Hypothesis

`a93` on H100 frames reads as it did in R54: 15–23 of 30, s02 13–21, s03 1–4.

## Predictions

| | R54 (`a93`, H100) | R53 (`a93`, lavapipe) | Predicted R58 |
|---|---|---|---|
| total | 19/30 | 24/30 | 15–23 |
| s02 | 17/24 | 20/24 | 13–21 |
| s03 | 2/6 | 4/6 | 1–4 |

## What it decides

Nothing on its own: it is the comparison for R56 and R57 (their READMEs' drop criteria). With R54
it is `a93`'s second H100 flight, 60 runs on this renderer.

## Manipulation check

- Every `run.json` carries `a93`, `8cc0bfc63d4e`, and `:8007`; every `godot.log` names
  `NVIDIA H100 PCIe`.
- Walls in flight (`eval/r28_flight.py`) within 4 points of R54's (19.2 / 11.5 / 15.5).
- The survey starts in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps.
- Goal reports with no line of sight per run within a third of R54's 0.9
  (`eval/probes/a93_goal_check.py --folders R58_ref_a93`).

## Drop criterion

Not applicable (a reference).

## Probe gate

Not needed (no change).

## Shakedown

None: the agent has flown 60 valid runs (R53, R54), the lane path on H100 frames flew R54 and R55.

## Host

Lanes 9–12 of `~/asep-r56-l1..12` on `:8007` (a copy of `:8004` on GPU 4), beside R56 (`:8004`)
and R57 (`:8006`); Godot on GPU 5. `~/r56_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R54 (the same agent and renderer). Branch `phase2/r56-latch-line` (shared with R56 and R57).

## Outcome

**Flown 2026-11-07, 20/30** (s02 17/24, s03 3/6): within the 15–23 predicted, one above R54's 19 on the same renderer;
the hypothesis held. s03 `dynamic` 0/3 (one run never left the lobby: a stop wall at step 4, 56 steps in the lobby; one
latched 33 steps after the read). The bar for R56 and R57. [summary.md](summary.md).
