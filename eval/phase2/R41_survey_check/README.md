# R41: a66 with the wall survey, through phase checked, contested cells

**Agent:** `a81` (`61e8e685422a`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A81` ·
**Status:** laid out 2026-11-05 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) while R40's shakedown was in flight; **never run, superseded
by `a82` (R42) before its shakedown** ([Outcome](#outcome))

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30), no control lane. The survey is R40's
([README](../R40_wall_survey/README.md)); this round is what R40's first shakedown run showed
wrong with its last phase, fixed before 30 runs were spent on it.

## Change

Against `a80` (R40, shaken down, not flown): five settings of the survey's through phase
(`agent.SURVEY_A81`, read in `planner.wall_survey` and `survey_door_line`; `a80` keeps its sha
and its behaviour, each change is behind its own setting). Against `a66` it is still one
change, the wall survey.

| Setting | `a80` | `a81` | Why |
|---|---|---|---|
| `check_steps`, `check_m` | a move stopped short with no doorway read: a phantom, on to the next station | the route has the waypoint for 3 steps; 2 m farther toward the wall the drone is through, else a phantom | the drone clipped the jamb of the real door and the survey turned the tags back |
| `ray_mean` | the open strip nearest the heading is the ray | the middle of the open strips | a door read across two strips; the nearer strip pointed 0.9 m off its centre |
| `been_floor`, `reach_ray_m` | wall's range unknown: the ray taken 5 m out | 4 m out, and no nearer than 1 m beyond the farthest the drone has been toward the wall | the door 3.8 m off was placed at 5 |
| `cross_det` | rays crossed when they differ by about 13° | by about 18° | two rays 5° apart crossed 1.7 m beyond the door |
| `look_nose_on` | flying at the wall, it is met when a move is stopped, or every strip is blocked one step after near floor | or every strip is blocked | far floor was read from 3 m and every strip blocked from 1.3 m |

## Evidence

- **R40 shakedown, s02c `dynamic` seed 1** (`a80`, `~/asep-r33-shake` at `5f09d34`, alone on
  slot 5 beside R39's lanes): solved in 25 steps, a cell `a66` lost 3 of 3 in R32P and 4 of 5
  in Round F. The survey started at step 4, reached its station at 11, read the open door at 12
  and 13 while still turning to the wall, and the drone was through the door at 16. What went
  wrong on the way: the two reads, 5° apart, crossed at y = −10.7 against a door centred at −9
  and spanning −7.8 to −10.2; the drone clipped the far jamb at step 14–15 (a 1.4 m move); the
  survey called the door a phantom and from step 15 to 24 its waypoint was the other station,
  back through the wall, 9 steps on which "toward your target" pointed away from the goal. The
  navigator ignored it and flew to the goal, which it could see.
- **The same run's start**: at steps 4 and 5 the navigator flew straight at the shut door with
  the tag on the sharp left; at 6 it stood 1.3 m from the wall, every strip blocked, having read
  far floor from 3 m a step before. Nothing in this round changes that the navigator may
  decline the survey's first move.
- R40's evidence for the survey itself stands (`../R40_wall_survey/README.md`).

## Hypothesis

R40's: with a square look at the wall 7 m either side of the shut door, the agent finds the
open s02 door that `a66` flies past, and crosses; s03 and the cells `a66` wins are untouched.
It scores at least 18/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a81` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 7–9 |
| s02 `dynamic` ×4 | 6/12 | 7–9 |
| s03 `final` | 3/3 | 2–3 (untouched; `a66`'s draw) |
| s03 `dynamic` | 0/3 | 0 |
| **total** | **15/30** | **16–21** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

R40's (`eval/probes/a80_check.py`), and:
- No step after the drone has crossed the wall on which the survey holds the waypoint (a
  `transit` or `look` phase with x < 0): `a80`'s shakedown run had 9.
- Of the through phases that end in a stopped move, the check phase ends "through" at least as
  often as "phantom" in runs that cross.

## Drop criterion

Not carried forward below 15/30, or with fewer s02 wins than R32P's 12. Carried as the base of
the next round at 18/30 or more.

## Probe gate

**No model probe** (as R40: no call added, nothing the model perceives or reports changes).

- **Closed loop, no model** (`eval/probes/a80_sim.py --agent a81`, tables in
  `eval/phase2/_probes/a81/`): truthful perceiver 96/96 on the change arms, median 30.5 steps,
  `initial` 48/48 with no survey (as `a80`); misread doorways and walls with 20% random moves
  64/96 (`a80` 54/96, `a66` 43/96). Gate: no worse than `a80` on either row. Passed.
- `python -m pytest server/decider/tests -q`: 60 pass (4 on `a81`, one of them that `a80`'s
  sha and behaviour are unchanged). `VLM_AGENT=a81 python eval/probes/a63_smoke.py`: 627/627.

**Shakedown gate** (on-policy, seed 1, a fifth client beside R39's four lanes): s02c
`dynamic`, s02a `dynamic`, s02vc `final`, s03 `final`. Passes if the survey starts in the s02
runs where a closed door is read dead ahead on the way in and takes a frame square to the
wall or reads an open doorway in each, never holds the waypoint after the drone has crossed,
does not start in the s03 run, and a route is on at least 95% of steps in every run.

## Builds on

`a80` (R40, laid out and shaken down, not flown), on `a66` (F 64/90, R32P 15/30). Branch
`phase2/r41-survey-check` from `phase2/r40-wall-survey` (`5f09d34`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a81`; `/health` should
  report `61e8e685422a`. Earlier agents keep their shas (`a66` `de7f23d07186`, `a79`
  `4ef945298c6d`, `a80` `1c1790de9767`).
- **Readouts:** as R40, with `--agent a81`.

## Outcome

**Not flown and never run: superseded before its shakedown by `a82` ([R42](../R42_survey_homing/README.md)).**
While this round was being laid out, R40's third shakedown run (s02vc `final`) showed a fault
`a81` does not fix: an open door read from 16 m was placed on a line by a guessed range, and
the drone met the wall 4 m beside it. The fix is one more setting; the tooling does not let a
laid-out agent be edited (`eval/phase2.py init` refuses, by the spec's §2), so it is a new
version and a new round. `a81`'s five settings are all in `a82`, so nothing of this round is
lost; its hypothesis is tested there.
