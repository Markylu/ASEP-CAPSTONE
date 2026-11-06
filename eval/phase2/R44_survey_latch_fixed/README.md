# R44: a66 with the wall survey and the dead-end latch, after R43's shakedown, contested cells

**Agent:** `a84` (`58e76b4b2054`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A84` ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R43's shakedown; shakedown flown 2026-11-06 (s02c
`dynamic` and s03 `final` solved; one gate row failed in s02vc `final`, waived with reasons);
round flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30) and R39 (`a79`, 15/30), no control lane. **A
bundle round**, R43's ([README](../R43_survey_latch/README.md): the wall survey for s02, the
dead-end latch for s03, why they are flown together); this round is that bundle with the two
faults its shakedown showed taken out.

## Change

Against `a83` (R43, shaken down, not flown), `agent.PATHFINDER_A84`:

| Part | Setting | `a83` | `a84` | Why (R43's shakedown) |
|---|---|---|---|---|
| Survey | `goal_ends` | the goal reported in view ends the survey | off | `g05` reported the goal where it was not in view: "above the door" at steps 3–4 of s02c `dynamic` (the door shut at 3), through a wall at step 11 of s02vc `final`. The survey ended on its first step in the one run and 3 m from the open door in the other; both were lost |
| Survey | `side_only` | a doorway read on the way to a station only picks the side | only a read in one of the two outer strips does; a doorway read in the centre three strips (within 40° of the approach axis) is flown at from any phase, on the newest ray | in s02vc `final` the navigator flew at the open door it could see from step 4, the door in its centre strips from step 7, while the survey's tag pointed back at the station. In the simulation, with no side-only at all, far reads flown at diagonally cost wins (49/96 against 59 with this rule and 65 with `a83`'s) |
| Latch | `confined.span_m` | the drone within 1.5 m of the run's axis | its positions since the run began spread no more than 2.8 m across the axis, wherever the axis lies | s03 `final` seed 1: 34 steps in the shut tine and no latch. The run down the tine was flown along its inner wall (y = −3.7 to −4.3) and the drone then turned about by the outer one (y = −5.4 to −6.3), 1.5–2.3 m off the axis. R39 seeds 2 and 3 the same. The tine is 3 m wide and the drone's positions in it spread 2.6 m in every recorded run |

Unchanged from `a83`: the survey's start, stations and look, `no_cross`, `relook`, the check
after a stopped move; the latch's dwell of three steps, its way out down the corridor's middle,
`a78`'s sentence. Against `a66` it is the bundle of R43: the wall survey and the dead-end
latch.

## Evidence

R43's shakedown (`a83`, eight unscored runs on the four lanes;
[R43 Outcome](../R43_survey_latch/README.md#outcome)):

- **s03 `dynamic` seed 2 solved at 54 steps: the first solve of the cell in Phase 2** (0/58
  scored runs before it). Door shut at 26, latch at 33, out of the tine at 37, through the
  other tine's door at 51.
- **s02a `dynamic` seed 1 solved at 39 and s02c `final` seed 1 at 23, through the survey**
  (both lost by `a66` in R32P): the first took the wrong side, met the wall, went back and
  across, read the door at step 25 and was through at 30; the second read it at 12 and was
  through at 15.
- **The two faults above** cost s02c `dynamic`, s02vc `final` and s03 `final`.
- s03 `dynamic` seed 1 spent 53 steps before the tine (the lobby and the stem): `a66`'s own
  loss, untouched here.
- **The latch's trigger with the lane by its spread** (`eval/probes/confined_trigger.py
  --agent a84`): Round F, R32P and R35: fires in the shut tine in 10 of 11 s03 `dynamic` runs,
  9 with 25 or more steps left, 6 steps after the door shuts in 8 of them; in 4 of 53 won s02
  runs before the crossing and 25 of 45 lost ones; in 0 of 30 `initial` runs. R30 and R32: 3
  of 4; 4 of 17 and 10 of 17; 0 of 6. R39's own three s03 `dynamic` runs: all three, 6, 6 and
  10 steps after the door shut. It fires more in the s02 hall than `a79`'s did; in R39's
  flight 5 of the 7 runs latched there then crossed.

## Hypothesis

R43's: the survey finds the open s02 door `a66` flies past and the latch takes the drone out
of the shut s03 tine in time, each where the other is silent; the agent scores at least
18/30, with s03 `dynamic` above 0/3.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a84` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 7–10 |
| s02 `dynamic` ×4 | 6/12 | 7–10 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 1–2 |
| **total** | **15/30** | **17–24** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

R43's (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`), with its "no through phase
begun from a transit" row dropped (that is now the design): the survey starts in at least 18
of the 24 s02 runs and in no s03 run, and is still running three steps after it starts in
every run it starts in; no step after the drone has crossed on which it holds the waypoint
for more than five steps; of the s02 wins, at least half cross during or within 3 steps of
the survey; in every s03 run that spends 8 or more steps in the shut tine after the door
shut, a latch within 9 steps of the door shutting (or of the first closed read, in `final`)
and the drone out past the mouth within 8 steps of it; a route on at least 95% of steps;
walls in flight within 4 points of Round F's.

## Drop criterion

Not carried forward below 15/30, or with fewer s02 wins than R32P's 12. Carried as the base of
the next round at 18/30 or more.

## Probe gate

**No model probe** (no call added, nothing the model perceives or reports changes).

- **Survey, closed loop, no model** (`eval/probes/a80_sim.py --agent a84 --far 20`,
  `eval/phase2/_probes/a84/`). Gate: every change-arm run on the truthful row; no worse than
  `a80` (48/96) on the misread row. **Read: 32/32 (and `initial` 16/16); 59/96 with doorways
  and walls misread and 20% random moves (`a83` 65, `a80` 48, `a66` 48). Passed.** The
  simulated perceiver never reports a goal that is not there, so it cannot show the fault
  `goal_ends` had; that is the shakedown's.
- **Latch, open loop** (`eval/probes/a78_replay.py --agent a84 --answers none`, on Round F,
  R32P, R35 and R39, `eval/phase2/_probes/a84/replay_none.txt`): from the latch on, at least
  80% of shut-tine steps with a route out by the crossbar. **Read: 358 of 421 (85%); the latch
  in 13 of 14 s03 `dynamic` runs, 12 with 25 or more steps left; no route on 107 of 7135
  steps (1.5%). Passed.**
- `python -m pytest server/decider/tests -q`: 67 pass. `VLM_AGENT=a84 python
  eval/probes/a63_smoke.py`: 627/627. Earlier agents keep their shas (`a66` `de7f23d07186`,
  `a79` `4ef945298c6d`, `a80` `1c1790de9767`, `a81` `61e8e685422a`, `a82` `43255087a08a`,
  `a83` `db5b837c8d43`).

**Shakedown gate** (on-policy, seed 1, the four lanes together, one run each: the three runs
the two faults cost and the lobby run): s02c `dynamic`, s02vc `final`, s03 `final`, s03
`dynamic`. Passes if the survey is not ended by a goal report in either s02 run and both
come within 2 m of the open door's centre or cross; no survey step in an s03 run; a latch in
any s03 run that spends 8 or more steps in the shut tine; a route on at least 95% of steps.
Wins are not required.

## Builds on

`a83` (R43, shaken down, not flown), on `a66` (F 64/90, R32P 15/30). Branch
`phase2/r44-survey-latch-fixed` from `phase2/r43-survey-latch`, with R39's results merged in.

## Notes for the operator

- **Preflight:** `python -m server.decider --profile remote --agent a84`; `/health` should
  report `58e76b4b2054`.

## Outcome

Not flown yet. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).

**Shakedown (2026-11-06, 05:23–05:30 UTC): four unscored runs, one on each lane slot together
(`~/asep-r42-l1..4` at `ccf3e46`, logs `~/r44_shake_l1..4.log`), alone on `:8004`. All valid.
One row of the gate failed (s02vc `final`); the round is flown all the same, on Claude's
decision, for the reasons under the table.**

| Cell (seed 1) | `a84` | `a83` (R43 shakedown) | R32P `a66` | What happened |
|---|---|---|---|---|
| s02c `dynamic` | **solved, 24** | lost (survey ended by a goal report) | lost | survey from step 4, station at 11, door read at 12, through at 15; goal reports at steps 3–4 no longer end it |
| s02vc `final` | lost | lost | lost | survey from step 6; the door read in the right strip at step 8 (21° off the axis) and flown at; at steps 9–11 it was read in the left strips, 42–58° off the axis, **not counted**, so the aim stayed on the first ray and the drone met the wall at (1.1, −5.8), 3.3 m from the door's centre; then 12 steps along the wall in the look phase |
| s03 `final` | **solved, 55** | lost (no latch) | solved | took the open tine; no latch needed |
| s03 `dynamic` | lost | lost | lost | 38 steps before the tine; door shut at 39, **latch at 45**, out of the tine at 50, ten steps left |

- **Gate.** Not ended by a goal report: held in both s02 runs. No survey step in s03: held. A
  latch in the s03 run that stayed in the shut tine: held (six steps after the door shut). A
  route on every step: held. **"Both s02 runs come within 2 m of the door's centre or cross":
  failed for s02vc `final` (3.3 m).**
- **Why it flies anyway** (Claude's decision; the operator's instruction for the night is that
  rounds fly, and that a gate is there to stop a change that breaks s02). (1) Across the
  shakedowns of `a83` and `a84`, the same survey but for the faults named, five s02 cells were
  flown at seed 1 and four were solved (s02a `dynamic`, s02c `final`, s02c `dynamic`, s02va
  `final`); `a66` solved one of those five in R32P. Nothing is broken; one cell has a known
  fault. (2) That fault is a threshold: doorway reads more than 40° off the approach axis are
  dropped even while the drone is already flying at the door. The fix is a new version
  (`a85`), built while this round is in the air, and it will be read against this round. (3)
  The four lanes were idle, and R40 to R43 had each been stopped before a flight.
- **What is new and held:** the s03 `dynamic` latch came six steps after the door shut (R39:
  ten, 25 and never); s03 `final` seed 1 was solved (lost in R39's flight and in R40's and
  R43's shakedowns).
