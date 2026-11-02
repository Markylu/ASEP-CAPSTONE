# Probe: a63's route planner on recorded steps (R30, no model)

**Script:** `eval/probes/pathfinder.py` · **Agent:** `a63` (`planner.pathfind` over
`spatial.CostMap`, memory `a17d`) · **Status:** gate set 2026-11-02 before the first run.

Comes from [docs/research/pathfinder-plan.md](../../../../docs/research/pathfinder-plan.md) §5
step 2. No model calls: every readout is code on recorded `decisions.jsonl` against the site
geometry (`eval/probes/common.py`, R11's `geo.py`) with the door state each run had.

## Belief

The s03 dead end and the s02 door wall are routing failures on a map that was right. A route
search over the same memory steers out of the shut tine, at the stem mouth from the lobby, and
through the open door's gap, without sealing true passages with the perceiver's phantom walls.

## Method

For every recorded step of rounds R20–R26 (tuning set; R27 and R29, when its runs land, are
held out), the memory is rebuilt as a63 builds it (`spatial.rebuild` with `A17D` from that run's
own records and perception), `planner.pathfind` runs on it, and the result is scored. Open loop:
the drone flew a49's route, so this says where a63 would have steered from where a49 stood.

| Readout | Steps counted | Scored |
|---|---|---|
| s03 shut tine | in the tine whose door shut, x < −3, after the first `d01` `closed` of the run | the waypoint lies further +x than the drone (leads out) |
| s03 lobby | x > 15 | the ray from the drone through the waypoint passes within 2 m of the stem mouth (15, 0), or the waypoint is in the stem |
| s02 near the open door | near side (x > 0.5), within 4 m of the open door's centre | the first route cell past x = 0 lies inside the opening (±1.2 m plus half a cell) |
| sealing harm | every step outside the s03 tines | a cell of the true shortest route (8-connected over the geometry, 0.85 m cells) is impassable on a63's cost map |
| initial safety | R25D's solved runs | the action a63 would tag "toward your target" equals the action a49 took, against a49's own tag's rate |

Reported, not gated: fallback counts (`soft`, `frontier`), waypoint bearing within 30° of the
true route's, sealing harm per site, and s02 routes that cross the wall outside the gap.

## Gate (set before the first run)

| | Gate |
|---|---|
| 1 | s03 shut tine: leads out on ≥ 80% |
| 2 | s03 lobby: through the mouth on ≥ 70% |
| 3 | s02 near the open door: crosses in the gap on ≥ 60% (R19: the goal line did on 2% of inner-side steps) |
| 4 | sealing harm outside the s03 tines ≤ 5% |
| 5 | initial safety: a63's toward matches a49's pick at least as often as a49's own tag did, minus 5 points |

All five hold on the tuning set and on the held-out set → the planner is as designed; the
on-policy shakedown (plan §5 step 4) is next. Any fails → `PATHFINDER_A63` and `PARAMS_A17D`
may be tuned on R20–R26 only, each change noted below with the numbers before and after; the
frozen values are then re-scored on the held-out set. A held-out failure after tuning means the
planner is not carried to a round as it stands.

## Tuning log

(none yet)

## Result

Not run.
