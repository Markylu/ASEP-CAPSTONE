# R39: a66 with the dead-end latch fired by the trail, contested cells

**Agent:** `a79` (`4ef945298c6d`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A79` ·
**Status:** laid out 2026-11-05 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason); offline gates passed; shakedown flown 2026-11-06 (latch
fired in the shut tine in both s03 `dynamic` runs, too late to judge the way out; s02 untouched);
**round flown 2026-11-06: 15/30, a draw against `a66`'s 15/30, s03 `dynamic` 0/3, not carried**
([summary](summary.md))

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R32P (`a66`, 15/30), no control lane. Aimed at s03 `dynamic` (0/52 in
Phase 2) and the s03 `final` losses that begin in the shut tine.

## Change

One change against `a66`: R38's dead-end latch (`planner.dead_end_latch`, the rectangle, the
lane, the plug, the navigator's sentence: all `a78`'s, unchanged) with **the drone's own trail
as its trigger instead of a model call** (`planner.confined_run`, `agent.PATHFINDER_A79`). No
dead-end confirmer, no new prompt, no extra call. `g05`, `d01`, `p17`, memory `a17f`, the cost
map, the tags and the turn rule are `a66`'s.

The latch fires on the first step where all of these hold:

| Rule | Parameter | Why |
|---|---|---|
| The trail holds a straight run of 5 m or more (`straight_run`, segments within 30° of its axis) | `min_run_m` 5.0 | a lane of two moves is not a corridor (`a78`: 3.0) |
| The drone turned into it: the move before the run is more than 30° off its axis | — | a run that reaches back to the spawn has no mouth to go back through |
| Every position since the run began is within 1.5 m of its axis and no more than 1 m behind its start | `half_m`, `back_m` | a 3 m corridor confines the drone; in a hall it sidesteps |
| In the last 5 steps the drone got no more than 1 m farther down the lane than before them | `dwell_steps`, `advance_m` | it is no longer flying down it |
| A closed door was read in the centre three strips (after `d01`) on 2 steps since the run began, heading within 70° of the axis | `reads`, `facing_deg` | the door is at the lane's end |
| The drone has never stood between 1.5 and 4 m beside the lane, abreast of the part the latch would shut | `beside_m` | a corridor has walls there; ground stood on says it has none |

The corridor is the longest run that qualifies. From there on it is `a78`: shut as one rectangle
(6.8 m either side, from 2 m down the run to 2 m beyond the farthest the drone has been), a
1.5 m lane left open back to the mouth, the lane shut once the drone is out, and, while latched
and inside with "toward your target" on the turn-around, the planner line gets "This corridor
ends at a closed door: it is a dead end. The next point on your route is behind you: the turn
around is the move toward it."

## Evidence

- **s03 `dynamic` is 0/52 in Phase 2**; Round F 0/5 with 30–41 steps in the shut tine after the
  closed read, R35 0/3 (`eval/phase2/final/summary.md`, `eval/phase2/R35_wall_turn_only/summary.md`).
- **The latch is sound on the record, and had no trigger** (`eval/phase2/R38_dead_end_latch/README.md`):
  with a confirmer that is never wrong, 354 of 396 shut-tine routes after the latch leave by the
  crossbar (`a66`: 0 of 444) and no won s02 run is latched. The model could not be that confirmer:
  `e01` said yes on 37% of s02 steps, `e02` on 17% of shut-tine steps.
- **`a69`: nothing in `g05`'s per-strip reads tells a 3 m corridor from a hall**
  (`eval/phase2/R30_pathfinder/README.md`). The trail does: in the shut tine the drone turns
  about for 30–40 steps inside a strip 2.6 m wide (y from 3.7 to 6.3 in every recorded run); at
  the s02 divider it leaves the line of its approach, or has stood beside it.
- **The trigger on the record** (`eval/probes/confined_trigger.py`, no model; tables in
  `eval/phase2/_probes/a79/`). Round F, R32P and R35, 150 runs:

  | Readout | `a79`'s rule |
  |---|---|
  | s03 `dynamic` runs it fires in, in the shut tine | 9 of 11, at steps 26–43 (8 with 25 or more steps left) |
  | s03 `final` losses it fires in (both began in the shut tine) | 2 of 2, at steps 26 and 27 |
  | Fires anywhere else in s03 | 0 |
  | Won s02 change-arm runs it fires in before the crossing | 0 of 53 |
  | Lost s02 change-arm runs it fires in | 13 of 45 |
  | `initial` runs it fires in | 0 of 30 |

  The two s03 `dynamic` runs it misses: R32P seed 3 (door shut at step 32, first closed read
  at 38, the drone never flew a 5 m run in the tine) and R35 seed 1 (the tine was entered on a
  curve).

## Hypothesis

With the corridor it is confined to latched as a dead end by its own trail, `a79` leaves the
shut s03 tine and takes the other one, where `a66` stays; the rule is silent in s02 runs `a66`
wins. It scores at least 15/30, with s03 `dynamic` above 0/3.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a79` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 5–7 (`a66`'s draw; a latch only in runs already stuck) |
| s02 `dynamic` ×4 | 6/12 | 5–7 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 1–2 (the latch at step 26–35, about 23 steps from the shut door to the goal) |
| **total** | **15/30** | **15–18** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule). The best case here is about +3, so
s03 `dynamic` is also read as a cell: at 0/52 before, 2 of 3 or better has probability under 1%
if the cell's rate were still 5% or less.

## Manipulation check

Code only, from `decisions.jsonl` (`planner.latch`, `route_behind`):
- Every s03 run that spends 10 or more steps in the shut tine after the door shut: a latch, by
  step 40; its axis within 20° of the tine's; its mouth at 0 ≤ x ≤ 8.
- After the latch: the drone out past x = 5 within 12 steps, and no later step in the shut tine.
- The sentence on every latched step with "toward your target" on the turn-around; the
  turn-around taken on at least 70% of them.
- s02: no latch before the crossing in a run that is won; a route on at least 95% of steps.
- Walls in flight within 4 points of Round F's (missed 16.7%, phantom 12.4%).

## Drop criterion

Not carried forward below 15/30, or with s03 `dynamic` at 0/3. Carried as the base of the next
round at 18/30 or more, or at 15–17 with s03 `dynamic` at 2/3 or 3/3.

## Probe gate

**No model probe: the change adds no call and changes nothing the model is asked to perceive.**
The sentence is `a78`'s and is said only while latched. Two gates, both without the model:

**Gate 1, held-out trigger check.** The rule's parameters were chosen on Round F, R32P and R35
(the table above is a fit). Before reading any other round, the gate was set in the night log
(`~/asep-overnight/2026-11-05/LOG.md`, 22:34 EST): on R30 and R32 (48 runs, never used for the
fit), (a) no `initial` run fires, (b) at most 1 won s02 change-arm run fires before its
crossing, (c) at least half of the s03 `dynamic` runs fire in the shut tine.

| Readout | Gate | First rule (no "stood beside", lane 3 m, facing 45°) | `a79` |
|---|---|---|---|
| (a) `initial` runs fired | 0 | 0 of 6 | 0 of 6 |
| (b) won s02 runs fired before the crossing | ≤ 1 | **2 of 17: failed** | 1 of 17 |
| (c) s03 `dynamic` runs fired in the shut tine | ≥ half | 3 of 4 | 2 of 4 |

The first rule failed (b) and was dropped. `a79`'s rule adds "never stood beside the lane"
(the same idea: a corridor has walls), a 5 m lane and a 70° facing cone, and passes all three.
**It was read on R30 and R32 after the first rule had been, so for `a79` the held-out set is no
longer untouched**: one look, three rows, the gate unchanged. The one won run it fires in is R32
s02va `dynamic` seed 2 (`a49`, fired at step 21, crossed at 48).

**Gate 2, the latch after the trigger** (`eval/probes/a78_replay.py --agent a79 --answers none`,
open loop on the 120 change-arm runs, `eval/phase2/_probes/a79/replay_none.txt`): from the
latch on, at least 80% of shut-tine steps have a route that leaves by the crossbar (`a78` with
a perfect confirmer: 89%); steps with no route under 1%. **Read: 283 of 304 (93%); no route on
31 of 5653 steps (0.5%); the latch in 9 of 11 s03 `dynamic` runs (8 with 25 or more steps
left), in 0 of 53 won s02 runs and 10 of 45 lost ones; the sentence on 103 latched steps.
Passed.**

**Shakedown gate** (on-policy, seed 1, alone on `:8004`): s03 `dynamic`, s03 `final`, s02c
`dynamic`, s02a `final` (R35's and R37's four cells). Passes if the s03 `dynamic` run latches
in the shut tine and the drone then gets out past x = 5, no s02 run is latched before a
crossing it would otherwise make, and a route is on at least 95% of steps in every run.

## Builds on

`a66` (F 64/90, R32P 15/30), the latch of `a78` (R38, never flown). Branch
`phase2/r39-confined-latch` from `phase2/r38-dead-end-latch` (`dbd6270`).

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (49 pass);
  `VLM_AGENT=a79 python eval/probes/a63_smoke.py` (627/627). Earlier agents keep their shas
  (`a66` `de7f23d07186`, `a75` `81d682c1424b`, `a77` `6744446339b0`, `a78` `d2c5d0f26cf4`).
- **Readouts (no model):** `python eval/probes/confined_trigger.py --runs` (a few seconds;
  `--sweep` for the parameter table); `python eval/probes/a78_replay.py --agent a79 --answers none`.
- **Preflight:** `python -m server.decider --profile remote --agent a79`; `/health` should
  report `4ef945298c6d`.

## Outcome

**Flown 2026-11-06, 04:15–05:09 UTC, 30/30 valid: 15/30 against `a66`'s 15/30 (R32P), a draw,
with s03 `dynamic` at 0/3. The hypothesis did not hold and, by the drop criterion, `a79` is not
carried forward as it is.** The latch worked in one of the three s03 `dynamic` runs: out of the
shut tine five steps after it fired, through the other tine's open door at step 57 (the first
run of the cell to reach the goal chamber in Phase 2), 2.8 m from the goal at 60. In the other
two the trigger was too late (step 45) or silent; a dwell of three steps would have caught
both. The latch also fired in 7 s02 runs, 5 of which then crossed. Details:
[summary.md](summary.md). `a83` (R43) carries the latch on, sooner.

**Shakedown (2026-11-06, 03:42–04:15 UTC): five unscored runs, one lane alone on `:8004`,
sctsvr6 `~/asep-r33-shake` at `1502692`; runs kept on the host as `~/r39_shake_a79_runs` and in
that checkout, logs `~/r39_shake_a79.log`, `~/r39_shake2_a79.log`. All five valid. The gate's
s02 and route rows passed; its s03 row could not be judged (both latches came with too few steps
left). Flown on Claude's decision: nothing was broken, and the 30 runs are the test.**
(`eval/probes/a79_check.py`.)

| Cell | `a79` | Door shut | Latch | After the latch | Route on |
|---|---|---|---|---|---|
| s03 `dynamic` seed 1 | lost | step 49 | step 58, shut tine, axis 184°, mouth x = 3.4 | route points out, the turn-around taken at 59 (1 of 1 sentence) | 60/60 |
| s03 `dynamic` seed 2 | lost | step 37 | step 49, shut tine | 7.6 m back up the tine in 10 steps (x = −5.3 to 2.3), the turn-around taken on both sentences | 60/60 |
| s03 `final` seed 1 | **solved, 25** | — | none (took the open tine) | — | 25/25 |
| s02c `dynamic` seed 1 | lost | step 3 | none | — | 60/60 |
| s02a `final` seed 1 | **solved, 18** | — | none | — | 18/18 |

- **The latch does what it was built to do, late.** In both s03 `dynamic` runs it fired in the
  shut tine with the tine's axis, 9 and 12 steps after the door shut, and the route and the
  drone turned for the mouth. Neither run had the steps left to show the rest: seed 1 spent 36
  steps in the lobby (a sharp right at step 2, then the route's waypoint through the lobby
  wall) and seed 2 spent 26 steps at the crossbar and the tine's mouth before going down it.
  Both delays are before any latch and are `a66`'s own (R32P's door shut at steps 22–32, R35's
  at 22–35).
- **The way out is slow**: 0.8 m a step in seed 2 against 1.7 m for a straight flight. Twice
  the waypoint lay about 90° off the heading beside a wall, no side move read open, and the
  tag went to the turn-around.
- **s02: no latch in either run; a route on every step.** The gate's rows for s02 and the
  route passed.
- **The gate's s03 row ("the drone then gets out past x = 5") was not met in the steps left
  and is not failed either**: 2 and 11 steps after the latch are not the 12 it allows.
