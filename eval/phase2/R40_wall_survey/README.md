# R40: a66 with the wall survey, contested cells

**Agent:** `a80` (`1c1790de9767`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A80` ·
**Status:** laid out 2026-11-05 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason); offline gates passed; shakedown and flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30), no control lane. Aimed at the eight s02 cells
(R32P 12/24, Round F 20/40 on the change arms).

## Change

One change against `a66`, code only (`planner.wall_survey`, `agent.SURVEY_A80`): **the drone
takes the square looks at the wall that `a66`'s route never takes.** No new prompt, no extra
call; `g05`, `d01`, `p17`, memory `a17f`, the cost map, the tags and the turn rule are `a66`'s.
While the survey runs it sets the planner's waypoint, so "toward your target" sits on the move
toward its station instead of the route's next point; the navigator is asked what it is always
asked.

- **Start.** A closed door read in the centre strip (after `d01`) while the drone is on its
  first way in: heading within 35° of the bearing from the spawn to the goal (the approach
  axis), 3 m or more along it, never yet more than 2.5 m off that line, and a station it can
  fly to over passable cells. A corridor the drone turned into lies off the direct line, so
  the survey never starts in an s03 tine (that is `a79`'s dead end, R39).
- **Station.** 7 m to the side of the approach (what one square look's 87° frame covers of a
  wall 4 m off): the side of a remembered open doorway at least 2 m off the line first, else
  the left; then the other side. Abreast of where the survey started until the wall has been
  met, then 5 m back from the wall. A station not come half a metre nearer in 6 steps is given
  up.
- **Look.** At the station the waypoint is 6 m ahead along the approach axis: the drone turns
  to the wall and flies at it, and every frame on the way in is a look square to it. It ends
  where the drone meets the wall (a move stopped short, or every strip blocked one step after
  near floor down the centre): **the wall's range is taken only from there**, never from the
  perceiver's floor classes.
- **Through.** An open doorway read on a strip whose ray lies within 40° of the axis is kept as
  a ray (the last six). The doorway's line runs along the axis through the point where the
  rays cross (least squares), or where the newest ray meets a wall whose range is known; the
  waypoint is 3 m ahead of the drone on that line, so a drone knocked off it comes back onto
  it before the wall. Done 5 steps after the last such read, or 3 m beyond a known wall; the
  route then takes over. A move stopped short with no doorway read from where it stopped is a
  phantom: on to the next station.
- **End.** Stations used up, or 44 steps: `a66`'s route as before.

## Evidence

- **The reading is sound square on and breaks along the wall** (probe door_read,
  `docs/research/round-f-analysis.md` §9, 4256 near-side frames): at 2–9 m a look within 20° of
  square read the open door on 157 of 158 looks and a blank wall strip as open on 1 of 366;
  20–40°, 36 of 41 and 17 of 939; beyond 60°, 112 of 231 and 76 of 393.
- **`a66` almost never looks square at the open door**: in view within 20° of square at 2–6 m
  on 58 of 4256 frames. It meets the divider at shut door B and flies along it; 19 of 45 lost
  s02 runs never came within 4 m of the open door, and within 4 m the drone stood more than
  30° off the door's line on 309 of 381 steps (§8).
- **Everything tried at the door itself failed for want of the wall's range and line**
  (`a76`, `a77`: §8–§11; a doorway is written at x = 2.7 against a wall at 0). On Round F a
  closed door "2.5 m ahead" was read from 16 m and every strip blocked from 13 m
  (`eval/probes/a80_start.py`, earlier variants of the start rule). The survey needs neither
  until the drone is stopped by the wall: its stations hang off the drone's own trail.
- **Where it would start** (`eval/probes/a80_start.py`, open loop to the starting step, Round
  F, R32P, R35 and R30, 168 runs, `eval/phase2/_probes/a80/start.txt`): in 83 of 96 s02
  change-arm runs, at steps 2–5 (44 of 48 lost ones, 39 of 48 won ones; most of the 13 it does
  not start in flew straight to an open door they had seen); in 0 of 36 `initial` runs, 0 of
  24 s03 change-arm runs, 0 of 18 s01 runs.

## Hypothesis

With a square look at the wall 7 m either side of the shut door, `a80` finds the open s02
door that `a66` flies past, and crosses; s03 and the cells `a66` wins are untouched. It
scores at least 18/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a80` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 7–9 |
| s02 `dynamic` ×4 | 6/12 | 7–9 |
| s03 `final` | 3/3 | 2–3 (untouched; `a66`'s draw) |
| s03 `dynamic` | 0/3 | 0 |
| **total** | **15/30** | **16–21** |

A survey that takes the right side first should cross by about step 15 and reach the goal by
25; the wrong side first, about 30 and 40 (the simulation below: 22–26 and 35–40 steps).

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

Code only, from `decisions.jsonl` (`planner.survey`, `eval/probes/a80_check.py`):
- The survey starts in at least 18 of the 24 s02 runs, by step 8; in none of the 6 s03 runs.
- In runs it starts in: a frame square to the wall (`looks` ≥ 1) in at least 80%; a through
  phase in at least 50%.
- Of the s02 runs that are won, at least half cross during or within 3 steps of the survey.
- A route on at least 95% of steps; walls in flight within 4 points of Round F's.

## Drop criterion

Not carried forward below 15/30, or with fewer s02 wins than R32P's 12. Carried as the base of
the next round at 18/30 or more.

## Probe gate

**No model probe: the change adds no call and changes nothing the model is asked to perceive
or report.** Three gates without the model, then a shakedown:

**Gate 1, the start on the record** (above): never in an `initial`, s03 or s01 run; in at
least 75% of s02 change-arm runs by step 6. **Read: 0 of 78; 83 of 96 (86%), all by step 5.
Passed.** The start rule was written against these same runs (three earlier variants fired
in `initial` runs or far from the wall and were dropped), so this is a fit, not a test.

**Gate 2, the state machine in closed loop** (`eval/probes/a80_sim.py`, tables in
`eval/phase2/_probes/a80/`). The planner, the memory and the tags are the agent's code; the
drone flies R11's 2D model of the four s02 sites, 12 seeds per cell. It says whether the
machine does what it was written to do when the drone goes where it is sent, and nothing about
what the model reads or picks.

| Simulated world | `a66` | `a80` | Gate |
|---|---|---|---|
| Truthful perceiver, navigator takes the tagged move: change arms won | 56/96 | **96/96** | all |
| the same: median steps of a win | 45 | 30.5 | — |
| the same: `initial` arms | 48/48 | 48/48, no survey | all, none |
| Doorways and walls misread at the measured rates, 20% of moves random: change arms | 43/96 | 54/96 | ≥ `a66` |

Passed. The noisy row uses probe door_read's rates by look angle and Round F's wall rates
(missed 16.7%, phantom 12.4%); how often a shut door is read closed is a guess (70%), and in
that world a quarter of the runs never start the survey (14% on the record). The row is there
to show the machine degrades toward `a66` and not below it.

**Gate 3:** `python -m pytest server/decider/tests -q` (56 pass, 7 on the survey);
`VLM_AGENT=a80 python eval/probes/a63_smoke.py` (627/627). Earlier agents keep their shas
(`a66` `de7f23d07186`, `a75` `81d682c1424b`, `a77` `6744446339b0`, `a78` `d2c5d0f26cf4`,
`a79` `4ef945298c6d`).

**Shakedown gate** (on-policy, seed 1, alone on `:8004`): s02c `dynamic`, s02a `final`, s02vc
`final`, s03 `final`. Passes if the survey starts in the three s02 runs by step 8 and takes a
frame square to the wall in each, does not start in the s03 run, and a route is on at least
95% of steps in every run. Wins are not required; a survey that starts and never looks is a
failure.

## Builds on

`a66` (F 64/90, R32P 15/30). Branch `phase2/r40-wall-survey` from `phase2/r39-confined-latch`
(`095d9c9`, while R39 was in flight; R39's results are merged in before this round's PR).

## Notes for the operator

- **Readouts (no model):** `python eval/probes/a80_start.py` (about a minute);
  `python eval/probes/a80_sim.py --agent a80 [--noise --slip 0.2] [--trace s02c/final]`;
  `python eval/probes/a80_check.py <runs dir>`.
- **Preflight:** `python -m server.decider --profile remote --agent a80`; `/health` should
  report `1c1790de9767`.
- **What the simulation cannot show:** whether the navigator flies sideways off a line it was
  told heads for the goal, and what `g05` reads on the way in. Both are the shakedown's.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
