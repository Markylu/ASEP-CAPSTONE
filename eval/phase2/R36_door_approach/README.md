# R36: a66 with the door approach pose, contested cells

**Agent:** `a76` (`32498e44d94d`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A76` · **Status:**
laid out 2026-11-05 on the operator's instruction ("Build it"); offline readouts measured
(below); **not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Analysis:
[docs/research/round-f-analysis.md](../../../docs/research/round-f-analysis.md) §5 (proposal 3)
and §8. Design: the ten contested cells, seeds 1–3, 30 runs, read against R32P (`a66`, 15/30)
and R35 (`a75`, 13/30).

## Change

One change against `a66`, code only, in the route planner (`planner.door_approach`,
`agent.PATHFINDER_A76`):

- **Door approach pose.** A remembered open doorway (not passed, not read closed) seen at least
  twice, within 8 m of the drone and 2.5 m of the route, takes the waypoint. The doorway's line
  is the route's own direction where it passes the doorway (two cells either side). Off that
  line the waypoint is 2.5 m out on it, on the drone's side; within one cell (0.85 m) of the
  line, or within 1 m of the line-up point, it is 1.7 m beyond the doorway. The nearest
  qualifying doorway is taken.
- **Budget.** Six steps per doorway over the run, counted from the planner records
  (`planner.door`), so a doorway that never closes cannot hold the drone.

The line is taken from the route because the map has no wall to fit one to: around the true
door in lost runs, 9 of 128 remembered-doorway steps had a wall line within 3 m, and its axis
was right on 1. Memory, cost map, tags, turn rule, `g05`, `d01` and `p17` are `a66`'s. `a75`'s
wall-turn rule is not carried (R35: a draw).

## Evidence

s02 change arms of Round F, R32P and R35 (88 runs, 3546 near-side steps after the switch),
memory rebuilt from the records:

- Every won run (43) came within 4 m of the true open door on the near side; 26 of 45 lost
  runs did, 19 never did.
- Within 4 m of it (381 steps): the drone stood more than 30° off the door's line on 309, the
  door was within 45° of its heading on 162, and the waypoint pointed within 30° of the door on
  102 (lost runs 30 of 175, won runs 72 of 206).

## Hypothesis

Squared up 2.5 m out, `g05` and `d01` read the true door open and the route goes through it:
`a76` crosses in the s02 runs that reach the door, and scores at least 15/30.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a76` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 4–7 |
| s02 `dynamic` ×4 | 6/12 | 4–7 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 0–1 |
| **total** | **15/30** | **10–18** |

Centred below `a66` on purpose: the probe gate below says the rule spends most of its steps on
doorways that are not the door. **Noise:** a gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

Code only, from `decisions.jsonl`:
- `planner.door` is set on at least 5% of s02 near-side steps, and no doorway label on more
  than six steps of a run.
- Of s02 steps with `planner.door` set, the doorway is within 2 m of the true open door on at
  least 40% (open loop: 64 of 408, 16%).
- Within 4 m of the true open door on the near side, the door is within 45° of the heading on
  at least 60% of steps (as flown by `a66` and `a75`: 162 of 381, 43%).
- A doorway the drone lined up on and that is not the door is closed (`Opening.closed`) within
  three steps of the first `through` step, on at least 70% of such doorways.

## Drop criterion

Not carried forward below 15/30; or if the shakedown's s02a `final` (R35: 6/6 across both
arms) is lost with more than 12 steps on doorways that are not the door.

## Probe gate

Offline, no model (`eval/probes/a76_replay.py`,
[_probes/a76/replay.txt](../_probes/a76/replay.txt)), on the 110 change-arm runs of Round F,
R32P and R35 (88 s02, 22 s03). **Measured while the agent was being built, before this section was written: a
record, not a pre-registration.** Open loop: the drone flew `a66`'s or `a75`'s route.

| Readout | Lost runs | Won runs |
|---|---|---|
| s02 near-side steps | 2480 (45 runs) | 1066 (43 runs) |
| Rule fires on the true open door | 15 steps, 4 runs | 49 steps, 16 runs |
| Rule fires on another doorway on the divider | 69 steps, 21 runs | 20 steps, 5 runs |
| Rule fires on a doorway off the divider | 121 steps, 33 runs | 134 steps, 35 runs |
| Within 4 m of the door: waypoint toward it, as recorded | 30 of 175 | 72 of 206 |
| The same under `a76` | 30 of 175 | 63 of 206 |
| s03: fires on the open exit door / the shut one / neither | 0 / 0 / 44 (13 runs) | 6 / 6 / 47 (9 runs) |

Gate set in the analysis doc for proposal 3: the losses that stood at the door. **Failed.** In
the 26 lost runs that stood at the door the waypoint points at it no more often (30 of 175
either way), and the rule fires on the door in 4 lost runs. It fires on other doorways twelve
times as often as on the door in lost runs (190 steps against 15) and three times as often in
won runs (154 against 49).

Why: the rule needs the door in the memory, and it is not there. Near side of lost runs, a
live remembered doorway within 2 m of the true door exists on 192 of 2480 steps (8%; won runs
148 of 1066, 14%), against 0.6 live doorways elsewhere per step. Within 4 m of the door (381
steps) the memory's doorway there was live on 130, read closed on 90, struck as passed on 36
and never recorded on 125. On the 162 of those steps with the door within 45° of the heading,
`g05` and `d01` reported an open doorway on 53 (33%; lost runs 19 of 59, won runs 34 of 103).
Remembered doorways off the divider sit mostly on the near-side floor, 1.5–9 m from the
divider (989 of 1205 doorway-steps within 8 m of the drone).

What open loop cannot say: whether a square look from 2.5 m reads the true door open more
often than 33%, and how fast a doorway that is not the door closes once the drone lines up on
it. Those are the two things the rule lives on, and only a flight shows them.

By the test plan's rule this probe does not carry `a76` to a round. If flown against it, as
R30 and R35 were: shakedown first, alone on `:8004`, s02a `final`, s02c `dynamic`, s03 `final`,
s03 `dynamic` (R35's four), scored by the manipulation check; a 30-run round only if the
second and fourth checks pass.

## Builds on

`a66` (R30, Round F). Branch `phase2/r33-deadlock-costmap`.

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (29 pass);
  `VLM_AGENT=a76 python eval/probes/a63_smoke.py`.
- **Replay:** `python eval/probes/a76_replay.py` (about 4 min).
- **Preflight, if flown:** `python -m server.decider --profile remote --agent a76`; `/health`
  should report `32498e44d94d`. `a66` `de7f23d07186`, `a75` `81d682c1424b` unchanged.

## Outcome

Not flown.
