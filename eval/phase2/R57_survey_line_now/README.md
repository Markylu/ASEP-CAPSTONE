# R57: a93 with the survey started for a drone on the direct line now, contested cells

**Agent:** `a95` (`f4cb70320370`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Renderer:** NVIDIA H100 (`GODOT_VK=nvidia`) ·
**Status:** laid out 2026-11-07 (Claude, overnight, operator asleep), not flown

Written before flying. Spec: `docs/phase2-test-plan.md` §2–§5; host layout: the operator's rule of
2026-11-06. Design: the ten contested cells, seeds 1–3, 30 runs, **read against R58, the reference
lane (`a93`) flown in the same batch on the same renderer.** Lavapipe numbers for the record only.

## Change

One change to the planner, in the wall survey's start (`planner.survey_start`, `SURVEY` of
`PATHFINDER_A95`, `line_now`): the test that the drone is on its first way in reads **where the
drone is now** (within `line_m`, 2.5 m, of the direct line from the spawn to the goal) instead of
every position of its trail. The other conditions are unchanged: a closed door read in the centre
strip on this step, the heading within 35 degrees of the line, 3 m or more along it, a station
reachable. A drone that left the line and came back can now start a survey; one in a corridor off
the line (the s03 tines, 3.5 to 6.5 m off it) still cannot.

## Evidence

- **s02vc `final` seed 3 is lost in four of four flights** (R49 `a89`, R53, R54 `a93`, R55 `a89`)
  **and never starts a survey** (`eval/phase2/R5[345]_*/summary.md`: "no survey", the latch firing
  instead at 19, 27, 39). On the record (scratch trace, 2026-11-07): at the spawn the route's first
  waypoint lies 0.8 m behind the drone (a grid artefact; "toward your target" sits on the
  turn-around and the navigator takes it, R53 and R54 step 0, R55 step 1 on a "wall close" read),
  the drone wanders to 4–5 m off the direct line in steps 2–4, and the trail test fails for the
  rest of the run: R55 read the shut door square from 2.1, 1.7 and 1.3 m off the line at steps
  12–14, heading 14 degrees off, and no survey started. R55 s02va `dynamic` seed 1 the same (lost,
  no survey; on the line again at step 9).
- **The change on the record** (`python eval/probes/a95_survey_start.py
  R44,R45,R46,R47,R49,R51,R52,R53,R54,R55`, an approximation of `survey_start` without the station
  guard): of 296 runs, 200 start the survey at the same step, 85 start none either way, and **11
  start one that had none**, all in s02: R55 s02vc `final` 3 (step 12), R55 s02va `dynamic` 1 (8),
  R47 s02vc `final` 3 (10), R46 s02vc `final` 1 (2) and 3 (8), R44/R51/R52 s02c `dynamic` 1 (4),
  R47 s02va `dynamic` 1 (15), R51 s02vc `final` 1 (2), plus one s03 step the real start had
  refused for another reason (R52 s03 `dynamic` 3, the lobby, both rules pass the line test there).
  R53 and R54 s02vc `final` 3 are not among them: there the drone stayed 4–5 m off the line to the
  wall (so this change answers R55's loss, not those two; the step-0 waypoint is the next idea).
- `a93` starts no survey in any s03 run (R49, R53, R54, R55: 0 of 24), so s03 has no exposure the
  old rule did not have, except a drone back on the line in the crossbar: covered by the
  shakedown's s03 cell.
- Offline: `python -m pytest server/decider/tests -q` 82 passed; `VLM_AGENT=a95 python
  eval/probes/a63_smoke.py` 627/627 steps planned, 0 failed.

## Hypothesis

A survey started for a drone back on the direct line wins the s02 runs `a93` loses with no survey,
and `a95` scores at least as many runs as the reference lane in the same batch, the gain on s02.

## Predictions

| | R58 (`a93`, reference) | Predicted R57 (`a95`) |
|---|---|---|
| total | its own flight | reference +0 to +2 |
| s02 | | reference +0 to +2; a survey in at least 23 of 24 (`a93`: 21, 23) |
| s03 | | within 1 of the reference (no change there) |

## Manipulation check

- Every `run.json` carries `a95`, `f4cb70320370`; every `godot.log` names `NVIDIA H100 PCIe`.
- **A survey starts in every s02 run whose trail comes back within 2.5 m of the direct line with a
  closed door read in the centre strip** (the new rule's reach), and in at least 23 of 24 s02 runs.
- **No survey starts in any s03 run** (`a93`: 0 of 24).
- Unbroken: a route on at least 95% of steps; walls in flight within 4 points of R58's; the latch
  fires in the shut s03 tine as in R58 (within 5 steps either way per run, same seeds).

## Drop criterion

Three or more runs below R58: dropped. Within 2: a draw, not carried. Three or more above: carried.

## Probe gate

Not needed: nothing the model perceives or is told changes. Offline gate (the position-now rule
starts a survey in no s03 run of R44–R55 where the old rule refused for the line, and in at least
2 of the 4 flown s02 losses with no survey) passed: 0 s03 starts for the line, R55's two losses.

## Shakedown

Four seed-1 runs in `~/asep-r56-shake-b` on `:8006`, H100 frames: s02vc `final`, s02va `dynamic`
(the cells the losses were in), s02a `final` (a survey that must still start as before) and s03
`dynamic` (no survey must start). Scored by the manipulation check; wins not required.

## Host

Lanes 5–8 of `~/asep-r56-l1..12` on `:8006` (a copy of `:8004` on GPU 3), beside R56 (`:8004`) and
R58 (`:8007`); Godot on GPU 5. `~/r56_fly.sh`. Recorded in `phase.json` "lanes".

## Builds on

R53/R54 (`a93`). Branch `phase2/r56-latch-line` (shared with R56 and R58).

## Outcome

Not flown yet.
