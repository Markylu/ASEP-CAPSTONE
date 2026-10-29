# R22: R21 without the wall at the end of an open_near strip

**Agent:** `a42` (`264539a2d5b1`) · **Prompt:** `p17` (`cb3578251cfe`) · **Memory:** `a17b` ·
**Status:** pre-registered 2026-10-29, not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Found by a read-only analysis subagent
([../R17_doorway_first/s03_analysis.md](../R17_doorway_first/s03_analysis.md)); built overnight
without the operator.

Second agent at the same SHA: **R22K**, `a43` (`3d499552d09d`) = `a42` + goal confirmer `c01`
([R22K](../R22K_open_near_unwalled_goal_confirmer/README.md)).

## Change

One against `a40` (R21): memory `a17b` instead of `a17`. a17's map writes a wall cell where a
strip's floor ends for `blocked_near`, `open_near` and `wall_far`. `a17b` writes none for
`open_near`, which is what g05's `bottom` maps to (`spatial.A17B`, `floor_ends` blocked_near and
wall_far; appended to the sha). Its floor is still marked free and searched out to 2 m; nothing
else changes.

## Evidence

- s03 analysis (R11, R15–R17K, 15 known-goal s03 runs): 497 of 876 steps in the lobby (R11 12 of
  159); the crossbar reached at median step 37 (R11 step 8). In all 15 runs the first turn-around
  came at steps 0–7 facing the stem, its straight move noted "toward your target; searched already
  this way" with 4–12 m truly free. The note comes from the wall a17 writes 2.5 m out at the end
  of an `open_near` strip, which `_unsearched_ahead` then hits. R14 moved g05's `bottom` from
  `blocked_near` to `open_near` because it is a wall within 1.9 m on 3% of strips, but kept the
  wall. On s03 735 of 1026 lobby `open_near` reads are clear 5 m or more.
- Replay, no model ([probe/notes_replay.txt](probe/notes_replay.txt),
  `eval/r22_floor_ends_probe.py`): every recorded step of R15, R15N, R16K, R17, R17K (4004 steps,
  20020 forward moves) into both memories, notes from `spatial.project`, truth from R11's
  `analysis/geo.py`:

  | | a17 | a17b |
  |---|---|---|
  | forward moves noted "searched already" | 5883 | 1835 |
  | toward moves noted "searched already" (s03) | 1193 (279) | 442 (84) |
  | steps with no forward "new ground" | 39% | 20% (R11 about 15%) |
  | "new ground" on a move truly blocked within 1.9 m | 6.1% | 6.5% |

  With R16 added: s03 353 → 123, all sites 39% → 20%, blocked 5.6% → 5.8%.
- Smoke (`smoke_run`, R15's 827 manifests): `a42`, `a43` 0 failed steps.

## Hypothesis

Without the false "searched already" ahead, the drone flies the lobby and stem instead of turning
around, reaches the s03 crossbar about step 10 and has time for the tines: R22 scores above R21.

## Predictions

| Arm | Baseline (R21, `a40`) | Predicted |
|---|---|---|
| initial | R21's | + 1 (s03) |
| final | R21's | same or + 1 |
| dynamic | R21's | same or + 1 |

Total ≥ R21 + 1. s03: crossbar reached by step 15 in at least 2 of 3 runs.

## Manipulation check

Turn-arounds with a forward "toward" move offered: under half of R21's.

## Drop criterion

Not carried forward if the total does not beat R21.

## Probe gate

Set by the analysis before the replay: s03 toward moves noted "searched" ≤ 100 over R15, R15N,
R16K, R17, R17K, and "new ground" on a truly blocked move ≤ 7%. **Passed** (84; 6.5%).

## Builds on

R21 (`a40`).

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
