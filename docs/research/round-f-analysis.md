# Round F: what the 90 runs say, and a73

Written 2026-11-04 by Claude for the operator, from `phase2/final` (`c0af776`): `final/README.md`,
`final/summary.md`, `final/labels.csv`, `results/results.md`, every `decisions.jsonl` of the 90
runs, the R30, R31 and R32 write-ups, `docs/research/r30-analysis-and-proposals.md`, and the
a17d–a17h memory, `planner.pathfind` and `spatial.project` code. No model calls. Counts below are
code over the records (the scripts are quoted where they are in the repo; the rest were one-off
and are reproduced by `eval/probes/a73_replay.py`).

## 1. Result

Round F: `a66`, 90 runs, **64/90** (`initial` 30/30, `final` 17/30, `dynamic` 17/30). Phase 1
25/90. Predicted 59–68. Stretch goal (≥ 50% per layout) met on all six layouts. The operator
said after the flight that `a66` was not meant as the final agent; the round is a citable
measurement of `a66`, not Phase 2's close.

| cell group | lost | what the records show |
|---|---|---|
| s03 `dynamic` | 5/5 (0/52 in Phase 2) | wrong tine, closed read, 30–40 steps at the exit wall and the divider |
| s02 out of view (s02a, s02c) `final` + `dynamic` | 13/20 | never crossed the divider |
| s02 in view (s02va, s02vc) `final` + `dynamic` | 7/20 | the same, less often |
| s03 `final` seed 1 | 1 | `a66`'s first s03 `final` loss (R30 1/1, R32P 3/3) |

## 2. Process

- The final flew an agent whose s03 `dynamic` was 0/47 and whose two gates (offline probe,
  shakedown) had failed; R32's decision rule (gap ≥ 3 on 30 runs, Fisher p = 0.44) chose it.
  The operator then said it was not the intended final. A citable round needs the operator's
  sign-off recorded in the round README before "Fly", not a rule inference.
- The manipulation check "toward your target on ≥ 70% of forward offers" flagged 15 of 90
  runs, all short solved runs: a rate on a small denominator. Use counts, or a minimum number
  of offers (R33 uses ≥ 20).
- Labels on F, R30, R32 and R32P are "Claude review, not yet confirmed by the operator";
  `results.md` says 414 screening runs have no manual label.
- Open-loop gates on recorded frames did not predict closed-loop flight three times (R27, R30,
  R31). The one screen that gave a usable number was on-policy (R32, 30 runs on the contested
  cells).
- R18, R18K, R23, R23K, R28, R29N, R29S and R31 are still `planned` in the index.

## 3. Mechanisms in the traces

**3.1 Turn-around deadlock at nose-on walls.** 373 of 3304 frames (11%) read every strip
`blocked_near`; the navigator turned around after 332 of them. The next step the route lies
behind, so marker 0 gets "toward your target"; `hide_turn_around` exempts a turn-around that
alone carries it (a17); the navigator turns back, faces the wall again, and nothing on the map
has changed. s03 `dynamic` seed 3 s35–s47: 13 turn-arounds in place, `planner.path_cells`
identical on every step, `costs` 49–50 hard. 61 back-to-back turn-around pairs over the round;
the five s03 `dynamic` losses spent 13–21 steps each on nose-on frames (22–35% of the budget).
The a17 side rule (sharpest open move on the target's side) misses the case because the
target-side moves carry stopped-short or wall notes (`PARAMS_A15` marks a block across ±45°,
the whole fan).

**3.2 The route crosses the divider beside the door.** The planner beelines to the goal over
unknown cells (cost 2) and over floor the perceiver painted; the waypoint lands 1–2 m off the
door's centre; the drone meets the wall obliquely, ends at x ≈ 0.7 inside the door's span but
facing along the wall, the frame is wall, it turns away. 10 of 20 s02 change-arm losses came
within 2 m of the open door's centre and left (s02a `final` seed 2 s28–s33, seed 4 s13–s19;
s02c `final` seed 5 s29–s31; s02va `final` seed 2 s16–s23; s02va `dynamic` seed 2 s27–s32;
s02vc `dynamic` seed 3 s15–s17). Of the 20 s02 losses, 18 never passed x = 0.45 and 2 passed
late (steps 56 and 46).

**3.3 What the route crosses on.** Replayed on a73's map (`a73_replay.py`), 1634 s02 near-side
route crossings of x = 0: strong floor → strong floor 766, unknown → unknown 397, visited →
strong floor 340; 1192 cross six metres or more from the open door (along the goal line through
shut door B). s03: 205 of 223 shut-tine routes leave the tine through strong-floor cells of the
divider (141), outer wall (37) or exit wall (27). The floor is painted by `g05`'s `open_far`
rays through walls at 2–4 m, which the memory holds as known ground. R31's finding, confirmed
on 90 runs: no cost or sealing rule moves this much (variants in R33's README: 5% → 8%).

**3.4 `d01` reads walls as doors.** s02 change arms, each verdict's strip ray cast to x = 0: 253
"open" verdicts on the real open door, 297 on blank wall, 39 on a closed door (57% phantom);
at 3–6 m, 40 real against 72 phantom. 16 "closed" verdicts on the real open door within 6 m,
mostly oblique looks along the wall (s02c `final` seed 5 s29: the open door's far jamb read as
a closed door at 3.3 m).

**3.5 Minor.** Nose-on wall cells written 1 m out fall in a cell the drone had visited (so never
hard) on 21 of 325 nose-on frames; stop walls on 6 of 103 blocked moves. Blocked moves (moved
< 1.2 m on a forward pick): 103 in the 50 change-arm runs. A* allowed a diagonal move past one
impassable cell (s02c `final` seed 5 s30: `(0,-9) → (-1,-8)` between wall cells).

## 4. a73 (R33)

Built on the operator's instruction. Two code-only changes on `a66`, defined in
`server/decider/agent.py` (`PATHFINDER_A73`) and `spatial.py` (`A17I`, `wall_turn`,
`after_wall_turn`), with 23 unit tests (`server/decider/tests/test_pathfinder.py`):

1. **Wall-turn rule** (3.1). The step after a turn-around taken facing a wall, "toward your
   target" goes to the open move nearest the target instead of the turn-around, so the turn
   rule hides it; on that step a move onto ground the drone has stood on carries no wall or
   block note (a visit beats one look). Open loop on Round F: of the 41 steps where `a66` turned
   around again after a wall turn, `a73` hides the turn-around on 30; of the 33 where the
   turn-around carried "toward", 24 move it to an open move.
2. **Cost map** (3.2, 3.3, 3.5): unknown 4, far floor 3 (`a17g`), suspects 6, walls seal eight
   neighbours, no diagonal past an impassable cell. Open loop: s02 crossings inside the door's
   gap 5% → 8%, s03 routes out of the shut tine 0% → 2%. The gates written in §5 (≥ 50%, ≥ 80%)
   fail; the cost map is not the lever for the crossings.

Not flown. Write-up and readouts: `eval/phase2/R33_wall_turn_costmap/README.md`,
`eval/phase2/_probes/a73/`.

## 5. Proposals, as written before the replay

1. **Deadlock breaker.** Gate: back-to-back turn-arounds after a wall turn on F's 90 runs 61 → about 0.
2. **Cost map.** Gate: s02 near-side routes through the true gap 10% → ≥ 50%; s03 shut-tine routes pointing out ≥ 80%.
3. **Door approach pose.** A route through a `d01`-confirmed opening gets a pre-waypoint 2.5 m out on
   the opening's centre line, then the centre; within 3 m of a remembered opening the tags name the
   move that faces it. Gate: the 10 losses that stood at the door. Not built.
4. **s03 halo** (R30 analysis P4): unknown cells within 3 m of a confirmed closed door cost 10. Not
   built; §3.3 says the tine's exits are strong floor, not unknown, so a halo on unknown cells would
   not fire either.
5. **Stop spending on `d01` rules**; the phantom floor is `open_far` rays. The lever is the reading at
   2–4 m (R30's verdict), or a memory that does not hold ray floor as known ground.
6. **Protocol.** Contested cells × 3 seeds as the standing screen; operator sign-off before a citable
   round; counts in manipulation checks; confirm labels; close dead rounds.

What §3.3 adds to the R30/R31 verdict: the wall the drone cannot see is not unknown to the
map, it is painted as floor. A memory in which ray floor beyond the near field is never known
ground (only visits and near floor are), with the route paying for every ray cell it crosses,
is the untested map-side idea; `a17g` at 2.5 m moved the readout 3 points, so the near field
would have to be short (1.5 m moved s03 to 5%) and the price high.

## 6. a74 (R34): only visited ground is known

Built on the operator's instruction ("Build a74"), the idea at the end of §5. One change on
`a73`: in the cost map, floor read along a ray, near or far, is a claim (2 per metre, sealed by
a wall beside it); only visits are known ground; a `d01`-confirmed doorway's floor is never
sealed (`PATHFINDER_A74`, `spatial.CostMap`, `SpatialMemory.door_free`; 25 tests).

Round F replayed (`eval/probes/a74_replay.py`), `a66` / `a73` / `a74`:

| Readout | `a66` | `a73` | `a74` |
|---|---|---|---|
| s02 routes through the true gap | 5% | 8% | 9% |
| s03 routes out of the shut tine | 0% | 2% | 10% |
| Failed s02 runs: divider walled on the map at the end | 58% | 65% | 73% |
| s02 steps with the true gap impassable | 3% | 6% | 11% |
| Steps with no route | 0% | 0% | 5% |

The §5 gates fail again. Maps drawn at late steps of failed runs show why the crossing readout
does not move: the divider is on the map as a staggered line of wall cells and the rest of it is
simply unseen; from where `a66` stood the cheapest route is always through the nearest stretch
nothing has looked at. A stricter map makes each probe at a wall stick (73% against 58%), which
is what a closed-loop search needs and what an open-loop replay cannot fly. Closing small holes
in wall lines was tried and changed nothing.

Where this leaves the map side: `a73`'s wall-turn rule is the one change with a clear offline
effect (30 of 41 loops). `a74`'s map is a trade the replay cannot settle; it needs a shakedown.
The crossing itself is still decided by what `g05` reads at 2–4 m (R30's verdict, unchanged by
the 90 runs).
