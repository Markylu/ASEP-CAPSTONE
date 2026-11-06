# R42: a66 with the wall survey homing on the door's bearing, contested cells

**Agent:** `a82` (`43255087a08a`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A82` ·
**Status:** laid out 2026-11-05 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R40's shakedown; shakedown and flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30), no control lane. The survey is R40's
([README](../R40_wall_survey/README.md)); its through phase is R41's
([README](../R41_survey_check/README.md)) with one more setting. **This is the round of the
three that flies**: R40 (`a80`) was shaken down and R41 (`a81`) laid out, and each showed the
next fix before 30 runs were spent.

## Change

Against `a81` (R41, laid out, never run): one setting, `home_ray` (`agent.SURVEY_A82`, read in
`planner.wall_survey`). While the wall's range is unknown and the kept rays do not yet cross,
the waypoint is 3 m ahead of the drone **along the newest open-doorway ray** (the door's
bearing from where it was read), not on a line through a point a guessed range out. Once the
rays cross, or the drone has met the wall, the door's line is used as in `a81`. Against `a66`
it is still one change, the wall survey.

## Evidence

- **R40 shakedown, s02vc `final` seed 1** (`a80`): solved at 49 where the survey should have
  had it by 30. The open door was read at step 2 from 16 m, in the left strip; with no range
  the ray was taken 5 m out, which put the door's line at y = −1.4 against a door centred at
  −9; later reads moved the line to −5.3; the drone flew down it and met the wall at (0.7, −4.7)
  at step 16, 4 m beside the door. The survey then sent it to the other station, 16 m back
  (steps 17–25), where it read the door again and, the bug still in place, flew a line that
  drifted from −6.7 to −11.8.
- A bearing needs no range. A drone that flies at where it reads the door, and reads it again
  on the way, arrives at the door whatever the range; the five strips give the bearing to about
  9°, which is 2.4 m at 16 m and 0.6 m at 4 m.
- **R40 shakedown, the other two s02 runs**: s02c `dynamic` seed 1 solved at 25 (through the
  door at 16; `a66` lost it in R32P), s02a `final` seed 1 solved at 22 with no survey (the
  route knew the open door from step 0). R41's README has the first run's faults.

## Hypothesis

R40's: with a square look at the wall 7 m either side of the shut door, the agent finds the
open s02 door that `a66` flies past, and crosses; s03 and the cells `a66` wins are untouched.
It scores at least 18/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a82` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 7–10 |
| s02 `dynamic` ×4 | 6/12 | 7–10 |
| s03 `final` | 3/3 | 2–3 (untouched; `a66`'s draw) |
| s03 `dynamic` | 0/3 | 0 |
| **total** | **15/30** | **16–23** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

R40's and R41's (`eval/probes/a80_check.py`): the survey starts in at least 18 of the 24 s02
runs and in no s03 run; a square look or an open-doorway read in at least 80% of the runs it
starts in; no step after the drone has crossed on which the survey holds the waypoint; of the
s02 wins, at least half cross during or within 3 steps of the survey; a route on at least 95%
of steps; walls in flight within 4 points of Round F's.

## Drop criterion

Not carried forward below 15/30, or with fewer s02 wins than R32P's 12. Carried as the base of
the next round at 18/30 or more.

## Probe gate

**No model probe** (as R40: no call added, nothing the model perceives or reports changes).

- **Closed loop, no model** (`eval/probes/a80_sim.py --agent a82`, `eval/phase2/_probes/a82/`):
  truthful perceiver 96/96 on the change arms, median 30.5 steps, `initial` 48/48 with no
  survey; misread doorways and walls with 20% random moves 61/96 (`a81` 64, `a80` 54, `a66`
  43). Gate: all 96 on the first row, and no worse than `a80` on the second. Passed. The
  simulated perceiver reads no door beyond 12 m, so it cannot show the fault this round fixes;
  that is the shakedown's s02vc run.
- `python -m pytest server/decider/tests -q`: 62 pass. `VLM_AGENT=a82 python
  eval/probes/a63_smoke.py`: 627/627. Earlier agents keep their shas (`a66` `de7f23d07186`,
  `a79` `4ef945298c6d`, `a80` `1c1790de9767`, `a81` `61e8e685422a`).

**Shakedown gate** (on-policy, seed 1, a fifth client beside R39's four lanes): s02vc `final`
(the run above), s02c `dynamic`, s02va `dynamic`, s03 `final`. Passes if the survey starts in
the s02 runs where a closed door is read dead ahead on the way in, never holds the waypoint
after the drone has crossed, the s02vc run crosses by step 30 or its survey's waypoint is
within 2 m of the open door's centre when the drone reaches the wall, the survey does not
start in the s03 run, and a route is on at least 95% of steps in every run.

## Builds on

`a81` (R41, laid out, never run) and `a80` (R40, shaken down, not flown), on `a66` (F 64/90,
R32P 15/30). Branch `phase2/r42-survey-homing` from `phase2/r41-survey-check` (`76bd737`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a82`; `/health` should
  report `43255087a08a`.
- `a83` is defined beside `a82` in `agent.py` and not used by this round: `a82`'s survey with
  `a79`'s latch, for the round after (it is in the code now so this round's lanes need no
  second checkout).

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
