# R60: a93 with the spawn's waypoint never behind the drone, contested cells

**Agent:** `a96` (`8bc44fc02535`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep); **flown 2026-11-07**

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R61, the reference lane
(`a93`) flown in the same batch on the same renderer.**

## Change

One change to the planner (`planner.pathfind`, `PATHFINDER_A96`, `spawn_ahead`): on the first step of a
run (no decision recorded yet, no latch, no survey), when the route's waypoint lies more than 90 degrees
off the drone's heading and the goal lies within 90 degrees of it, the waypoint goes to the goal's
bearing, `waypoint_min_m` (1 m) ahead. Every later step is `a93`'s.

## Evidence

- **At the spawn the route's first point lies behind the drone** in 13 of 150 runs of R49–R55 and 6 of 90
  in R56–R58 (scratch `wp_behind.py`, 2026-11-07): every strip reads `blocked_near` from 20 m (the perceiver's
  known quirk on frames 5–17 m from any wall), the memory paints a wall one cell ahead in every strip, and
  A* steps back and round it (path cells `[23,0] → [24,1] → [23,2]`, the waypoint 0.8 m behind, 1.3 m to
  the side). The tag "toward your target" then sits on the turn-around.
- **The navigator takes it**: in 5 of the 13 (R49 s02va `final` 3 won; R49, R51, R53, R54 s02vc `final` 3:
  three of four lost) and 2 of the 6 (R56 and R58 s02vc `final` 3, both won this time). R53 and R54's s02vc
  `final` 3, on lavapipe frames identical step for step, turned around at step 0, wandered 4–5 m off the
  direct line, never started a survey and lost (`eval/phase2/R57_survey_line_now/README.md`, Evidence).
- The fix is at the symptom, not the cause (the perceiver's far-wall read and the memory's wall from it):
  the forward moves keep their "wall close (seen now)" tags, and a drone that turns about on those alone
  (R55 s02vc `final` 3, step 1) is not helped. What it removes is the planner's own tag on the turn-around.
- Offline: 82 tests pass; `VLM_AGENT=a96 python eval/probes/a63_smoke.py` 627/627 planned, 0 failed. By
  construction the step-0 waypoint is ahead in every run.

## Hypothesis

With no "toward your target" on the turn-around at the spawn, `a96` loses no run to a turn-about at step
0 and scores at least as many runs as the reference lane in the same batch.

## Predictions

| | R61 (`a93`, reference) | Predicted R60 (`a96`) |
|---|---|---|
| total | its own flight | reference +0 to +2 |
| s02 | | reference +0 to +2 (the artefact is an s02 one: the spawn 20 m from the door wall) |
| s03 | | within 1 of the reference (no change there: the lobby's first waypoint has been ahead in every s03 run read) |

## Manipulation check

- Every `run.json` carries `a96`, `8bc44fc02535`; every `godot.log` names `NVIDIA H100 PCIe`.
- **No run's step-0 waypoint lies more than 90 degrees off the heading** (`a93` R58: 2 of 30), and **no
  step-0 turn-around carries "toward your target"**.
- No run turns around at step 0 (`a93` R58: 1 of 30; R49–R55: 5 of 150).
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8; a route on at least 95% of steps; walls in
  flight within 4 points of R61's; the latch in s03 as `a93`'s.

## Drop criterion

Three or more below R61: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed: nothing the model perceives or is told changes except the tag's place on one step.

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-b` on `:8006`, H100 frames: s02va `dynamic` (R54's seed-1 case of the
artefact), s02vc `final`, s02a `final`, s03 `dynamic` (must be unchanged). Scored by the manipulation check.

## Host

Lanes 5–8 of `~/asep-r59-l1..12` on `:8006` (a copy of `:8004` on GPU 3), beside R59 (`:8004`) and R61
(`:8007`); Godot on GPU 5. `~/r59_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R53/R54 (`a93`). Branch `phase2/r59-latch-survey` (shared with R59 and R61).

## Outcome

**Flown 2026-11-07, 19/30** (s02 15/24, s03 4/6) against the reference lane's 21/30 (R61): two below, a draw by the
rule, not carried. The mechanism held (no step-0 waypoint behind, no step-0 turn-around, 30 of 30); the losses are at
the survey's stations from step 10 on (s02a `dynamic` 0/3, s02vc `dynamic` 0/3). [summary.md](summary.md).
