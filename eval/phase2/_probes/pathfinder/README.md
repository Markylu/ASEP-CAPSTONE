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

All runs on the tuning set R20–R26 (7,048 recorded steps). Readouts added after a run are
marked; the registered five keep their numbers in every table.

**Run 1** (`50cc0db`, parameters as registered): shut tine leads out 54.2% (gate 80), lobby
76.0% (pass), s02 gap 42.2% (gate 60), sealing harm 47.8% (gate 5), initial safety 56.5% against
a49's 83.9% (fail). Fallbacks: none 7,026, soft 15, frontier 7.
- Maps (R25D s03 `final` s45, s50): the exit wall is sealed, but the divider between the tines
  is unknown. a49's looks read the oblique side wall as `lower`/`middle` (floor running on), so
  nothing hard is ever written there, and 7 m of unknown at cost 2 beats a 40 m known detour.
  No cost can change that order; only walls can.
- The registered "sealing harm" counts any impassable cell on the true shortest route, which
  hugs corners: a corner cell beside a seen wall is "sealed" while the route a cell over is
  open. Two readouts added: **4b** "no true route left on a63's map" (A* over the cells both
  maps allow), gate ≤ 5%; **4c** "route relies on unknown that is wall", reported.

**Run 2** (near walls at `bottom` floor ends on a planner-only layer at 2.5 m; stop-wall
inflation 2 cells, never over seen floor; wall extension never over seen floor; readout **1b**
"waypoint never toward the sealed exit" added, gate ≥ 80%): leads out 45.3%, 1b 65.0%, lobby
56.2%, s02 gap 34.8%, sealing harm 62.5%, 4b 11.2%, 4c 78.1%, initial safety 49.3%. Worse on
every row: `bottom` is read on 31–50% of truly open strips (W01), so the near walls were
phantoms, and the divider still read `lower`/`middle`. Near walls dropped (table left empty).

**Run 3** (near walls off; a `d01`-confirmed open doorway's strip writes free cells 6 m along
its rays and no suspect: in run 2's s02 maps the gap's cells were unknown beside the seen
jambs, so the sealing rule closed the door the drone had been shown): leads out 41.1%, 1b
60.3%, lobby 74.1%, s02 gap 45.5%, sealing harm 41.4%, 4b 1.4%, 4c 74.3%, initial safety
60.8%. Costs were swept on R25D's steps alone (unknown 1.2–2, suspects off / 2 / 4, lookahead
4–6): no row moved by more than 5 points, so the failures are not cost choices.

**Runs 4–6** (R25D's steps only, between full runs; initial safety 60.8 → 67.5 → 68.5%, 4b
0.3 → 0.2%). Each is a map bug found by reading the disagreeing steps, not a tuning:
- The door-wall rule wrote a wall at 1 m across a strip *and its neighbour* for a flanking
  closed door read `no_floor` at spawn (12 m away), and at 0.85 m cells the neighbour's ray
  end lands in the cell straight ahead; a `bottom` closed door 14 m away (R25D s02vc `dynamic`
  s3) wrote a wall band at 2.5 m. Now: door walls only for `no_floor` (a door under 1 m),
  `bottom` closed doors are soft suspects, and floor seen in any look erases a door wall.
- a17b's own ray ends: a side strip's end at 0.9 m shares the centre ray's cell, and the last
  strip written popped the floor the centre strip saw (R25D s02a `initial` s0: a `wall` cell
  straight ahead of the spawn). Only tags read that cell in a49; a route search cannot cross
  it. a17d `free_wins`: within one look, floor seen by *another* strip wins over a ray end in
  the same cell; a `no_floor` strip's own half-metre of "floor" (a17 bookkeeping, the camera
  sees no floor under 1.5 m) never counts as evidence.

**Frozen** after run 6: `PATHFINDER_A63` unknown 2.0, suspect 4.0, lookahead 4.0, stall 5 steps /
1.0 m, stop-wall inflation 2; `PARAMS_A17D` door walls `no_floor` 1.0 m, suspects lower 4.5 /
middle 8.0, closed-door suspects bottom 2.5 / lower 4.5 / middle 8.0, open-door reach 6.0,
nose-on run 3 strips + 1 cell, near walls off, `free_wins` on. a63 sha `7e6b2f2a6d8c`.

What the open loop cannot show: in flight a63 bumps the unknown divider or door wall, each bump
writes a stop wall two cells wide each side, and the route moves on. The recorded steps never
bumped where a63 would, so readouts 1, 1b and 3 say where the route points *before* any bump:
into the unknown wall, which is where a frontier search goes. Readout 4c says the same: 73% of
routes rely on unknown ground that is in truth wall, because the map knows walls only where
the drone nearly touched them (a17b writes a wall only for `no_floor`, under 1 m). That is
what the on-policy shakedown (plan §5 step 4) is for.

## Result

Frozen parameters, 2026-11-02. Tuning set R20–R26, 7,048 steps; held-out set R27, 632 steps
(R29 not flown yet). Full tables: [score_tune.txt](score_tune.txt), [score_held.txt](score_held.txt).

| | Readout | Gate | Tuning | Held out (R27) |
|---|---|---|---|---|
| 1 | s03 shut tine: leads out | ≥ 80% | 28.0% (60/214) **fail** | 100% (2/2) pass |
| 1b | s03 shut tine: never toward the sealed exit | ≥ 80% | 46.7% **fail** | 100% (2/2) pass |
| 2 | s03 lobby: through the stem mouth | ≥ 70% | 75.4% (236/313) pass | 100% (12/12) pass |
| 3 | s02 near the open door: crosses in the gap | ≥ 60% | 44.9% (178/396) **fail** | 46.9% (15/32) **fail** |
| 4 | sealing harm, as registered | ≤ 5% | 28.5% **fail** | 25.0% **fail** |
| 4b | no true route left on a63's map | ≤ 5% | 0.8% (59/7048) pass | 0.0% pass |
| 4c | route relies on unknown that is wall | report | 73.4% | 73.7% |
| 5 | initial safety: a63's toward = a49's pick (a49's tag: 83.9%) | ≥ 78.9% | 68.5% (252/368) **fail** | n/a |

**The gate as registered failed**, on the tuning set and on the held-out set. What passed: the
lobby readout (the route points at the stem mouth), and 4b (a63's map almost never seals every
true route: 0.8%, 0.0%). What failed, and why, as far as the record shows:
- **Shut tine (1, 1b) and door gap (3).** From where a49 stood, the divider and the door wall
  are unknown to the map (4c), so the cheapest route is through them. The route points out of
  the tine or through the gap only once bumps have written stop walls; the record has none
  there. The held-out 2/2 and the tuning 28% are the same planner on different recorded maps.
- **Sealing harm (4).** The readout counts corner cells; 4b is the readout that answers the
  question, and it passes. Recorded as registered.
- **Initial safety (5).** 68.5% against a49's 83.9%. On the 14-step straight runs the two agree
  except at the last three steps, where both tags say slight-left and the navigator went
  straight (counted against both). The rest are steps where a49 wandered (s02vc `dynamic`
  s12–24) and a63's route from there differs from the goal bearing by design.

**Reading.** By the rule set above, the planner is not carried to a round on this probe. The
probe also cannot certify it: three of the four failing rows measure a closed-loop behaviour
(bumping, then rerouting) on open-loop data. Whether the on-policy shakedown (six unscored
`dynamic` runs, s03 first, a63 and a64) may stand in for this gate is the operator's decision,
not the probe's. The planner's own invariants hold on every step: a route on 7,043 of 7,048
steps (`soft` 5, `frontier` 0), 0 failed steps in the smoke, every earlier agent's sha
unchanged.
