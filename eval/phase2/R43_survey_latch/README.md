# R43: a66 with the wall survey and the dead-end latch, contested cells

**Agent:** `a83` (`db5b837c8d43`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A83` ·
**Status:** laid out 2026-11-05/06 (overnight run, Claude alone, operator asleep; every
decision here is Claude's, with its reason) from R39's flight and the shakedowns of R40 and
R42; shakedown and flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30) and R39 (`a79`), no control lane.

**A bundle round** (spec §1), by Claude's decision for the night: two parts that act on
different sites, each already run on its own (the latch flew as R39; the survey was shaken
down three times as `a80` and `a82`). The result is credited to the bundle. R39 is the
latch's own round; the survey has none, because each of its shakedowns showed the next fault
before a round was worth 30 runs. If the bundle wins, the round after can fly the survey
alone.

## Change

Against `a66`, two parts (`agent.PATHFINDER_A83`):

**1. The wall survey** (`planner.wall_survey`, `agent.SURVEY_A83`; s02). R40's survey
([README](../R40_wall_survey/README.md)) with R41's and R42's settings and four more, from
`a82`'s shakedown:

| Setting | `a82` | `a83` | Why |
|---|---|---|---|
| `side_only` | an open doorway read on the way to a station is flown at | it only picks the side: the station on that side goes first | five strips give a bearing to about 9°, 2.4 m at 16 m; a door read from 15 m was flown at down lines 4 and 5 m beside it (R40 and R42 shakedowns, s02vc `final`) |
| `no_cross` | rays that differ by 18° are crossed for the door's line | never crossed; the newest ray is flown at, from the look phase | three bearings 15° apart, one of them a blank wall read open, crossed 5 m beside the door |
| `goal_ends` | — | the goal in view ends the survey | on the near side the goal shows only through a doorway; `a80` held the waypoint for nine steps after the drone was through |
| `relook` | five steps with no doorway read: the survey is done | back to the look (fly at the wall from here) unless the goal is in view | `a82` ended its survey 5 m short of the door with 49 steps left |

**2. The dead-end latch** (`planner.dead_end_latch`, `confined_run`; s03). R39's
([README](../R39_confined_latch/README.md)) with two settings:

| Setting | `a79` | `a83` | Why |
|---|---|---|---|
| `confined.dwell_steps` | 5 | 3 | R39 s03 `dynamic` seed 1 was 2.8 m from the goal at step 60; on Round F, R32P and R35 the rule then fires 6 steps after the door shuts instead of 8 |
| `exit.carrot_m` | the route's next point | latched and inside, the waypoint is 4 m back down the middle of the corridor | R39's shakedown made 0.8 m a step on the way out, the route's point 90° off beside a wall and the tag on the turn-around |

The navigator's sentence is `a78`'s, said only while latched. The two parts do not meet: the
survey starts only on the drone's first way in along the direct line, the latch only in a
lane the drone turned into; a latched corridor has no survey.

## Evidence

- **R39 in flight (`a79`)**: s03 `dynamic` seed 1, the latch at step 35 (door shut at 25,
  first closed read at 26), out of the tine at 40, through the other tine's open door at 57,
  2.8 m from the goal at 60: the first run of the cell in Phase 2 to reach the goal chamber.
  The latch also fired in the s02 hall in runs that then crossed (s02vc `final` seeds 2 and 3,
  latched at 24 and 22, won at 52 and 44). R39's summary has the round.
- **R40 shakedown (`a80`)**: s02c `dynamic` seed 1 solved at 25 through the survey (the cell
  is 0/3 for `a66` in R32P); s02vc `final` seed 1 solved at 49 after the drone flew a line 4 m
  beside a door it had read from 16 m ([R40 Outcome](../R40_wall_survey/README.md#outcome)).
- **R42 shakedown (`a82`)**, s02vc `final` seed 1: the door read at steps 3–7 from 15–9 m in
  three different strips, one read a blank wall; the crossing of those rays put the door's
  line at y = −3.3 to −4.6 against a door centred at −9; the survey ended at step 11 beside
  the wall ([R42 Outcome](../R42_survey_homing/README.md#outcome)).
- **The latch's trigger at `dwell_steps` 3** (`eval/probes/confined_trigger.py`, no model):
  Round F, R32P and R35: fires in the shut tine in 9 of 11 s03 `dynamic` runs (8 with 25 or
  more steps left, median 32 left; `a79`: 30), in both s03 `final` losses, in 3 of 53 won s02
  runs before the crossing (`a79`: 0) and 16 of 45 lost ones, in 0 of 30 `initial` runs. R30
  and R32: 2 of 4, 2 of 17, 6 of 17, 0 of 6.

## Hypothesis

The survey finds the open s02 door `a66` flies past and the latch takes the drone out of the
shut s03 tine in time, each where the other is silent; `a83` scores at least 18/30, with s03
`dynamic` above 0/3.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a83` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 7–10 |
| s02 `dynamic` ×4 | 6/12 | 7–10 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 1–2 |
| **total** | **15/30** | **17–24** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule). s03 `dynamic` is also read as a
cell (0/55 before tonight).

## Manipulation check

Code only (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- Survey: starts in at least 18 of the 24 s02 runs and in no s03 run; no through phase begun
  from a transit; no step after the drone has crossed on which it holds the waypoint; of the
  s02 wins, at least half cross during or within 3 steps of the survey.
- Latch: in every s03 run that spends 8 or more steps in the shut tine after the door shut, a
  latch within 9 steps of the door shutting, its axis within 20° of the tine's; the drone out
  past the mouth within 8 steps of it.
- A route on at least 95% of steps; walls in flight within 4 points of Round F's.

## Drop criterion

Not carried forward below 15/30, or with fewer s02 wins than R32P's 12. Carried as the base of
the next round at 18/30 or more.

## Probe gate

**No model probe** (no call added, nothing the model perceives or reports changes; the
sentence is `a78`'s).

- **Survey, closed loop, no model** (`eval/probes/a80_sim.py --far 20`, doors read from up to
  20 m as in the shakedowns, the goal reported when in view; `eval/phase2/_probes/a83/`):
  truthful perceiver 32/32 on the change arms at a median of 25 steps; misread doorways and
  walls with 20% random moves: `a83` 65/96, `a82` 64, `a80` 48, `a66` 48. Gate: all on the
  first row, no worse than `a82` on the second. Passed.
- **Latch, open loop** (`eval/probes/a78_replay.py --agent a83 --answers none`,
  `eval/phase2/_probes/a83/replay_none.txt`): from the latch on, at least 80% of shut-tine
  steps with a route out by the crossbar. **Read: 304 of 328 (93%); the latch in 9 of 11 s03
  `dynamic` runs, 8 with 25 or more steps left (median 32); no route on 65 of 5653 steps
  (1.1%). Passed.**
- `python -m pytest server/decider/tests -q`: 64 pass. `VLM_AGENT=a83 python
  eval/probes/a63_smoke.py`: 627/627. Earlier agents keep their shas (`a66` `de7f23d07186`,
  `a79` `4ef945298c6d`, `a80` `1c1790de9767`, `a81` `61e8e685422a`, `a82` `43255087a08a`).

**Shakedown gate** (on-policy, seed 1 and one seed 2, the four lanes together once R39 has
landed, two runs each): s02vc `final`, s02c `dynamic`, s02a `dynamic`, s02va `final`, s02c
`final`, s03 `final`, s03 `dynamic` seeds 1 and 2. Passes if: no survey step in an s03 run and
no through phase begun from a transit; no step with the survey holding the waypoint after the
drone has crossed; at least 2 of the 5 s02 runs solved (`a66` in R32P at these seeds: 1); a
latch in each s03 run that spends 8 or more steps in the shut tine after the door shut; a
route on at least 95% of steps in every run.

## Builds on

`a82` (R42, shaken down, not flown), `a79` (R39), on `a66` (F 64/90, R32P 15/30). Branch
`phase2/r43-survey-latch` from `phase2/r42-survey-homing` (`bceddac`).

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a83`; `/health` should
  report `db5b837c8d43`.
- **Readouts (no model):** `python eval/probes/a80_sim.py --agent a83 --far 20 [--noise --slip
  0.2]`; `python eval/probes/confined_trigger.py --agent a83 --runs`;
  `python eval/probes/a80_check.py <runs dir>`; `python eval/probes/a79_check.py <runs dir>`.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
