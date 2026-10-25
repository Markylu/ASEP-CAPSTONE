# R10 manipulation check

From `python eval/spatial_replay.py manip eval/phase2/R10_goal_planner/runs` and the same for
R10C (pre-registered list, README "Manipulation check"). Goal-strip accuracy, phantoms and
goal-ward targets use the manifest's ground truth, evaluation only.

## Round totals

| Measure | R10 `a14` | R10C `a13` | R9 `a13` | Pre-registered |
|---|---|---|---|---|
| decisions | 755 | 899 | 871 | |
| [0] left off by the turn rule | 65 | 0 | 0 | on every step where it applies |
| picks naming a hidden index | 0 | – | – | 0 (schema) |
| navigator texts with a goal distance or direction | 0 | – | – | 0 |
| turn-arounds | 65 (8.6%) | 126 (14.0%) | 105 (12.1%) | < 8% |
| longest run of turn-arounds | 1 | 12 | 7 | |
| `spin_failure` runs | 0 | 4 | 4 | 0 |
| steps with no target | 123 (16.3%) | 143 (15.9%) | 194 (22.3%) | < 10% |
| strategist calls | 229 (30% of steps) | 359 (40%) | 321 (37%) | reported |
| strategist goal-ward (target ≥ 3 m nearer the goal than the drone) | 134/229 (58.5%) | 114/359 (31.8%) | 113/321 (35.2%) | ≥ 60% |
| median target changes per run | 8 | 13 | | reported |
| steps with the goal as target | 232 | 206 | 157 | reported |
| picks carrying "blocked here before" | 0 | 2 | 0 | reported |
| critic objections / picks changed | off | 43 / 2 | 19 / 0 | off |
| goal strip within one, goal in view | 143/144 | 123/125 | 112/113 | reported |
| phantom goal reports, goal not in view | 23/611 (3.8%) | 26/774 (3.4%) | 22/758 (2.9%) | reported |
| collisions | 36 | 57 | 34 | at most R10C's |
| revisit rate (mean of runs) | 0.10 | 0.16 | 0.15 | reported |
| mean step latency | 3.1 s | 3.4 s | 3.2 s | reported |

Strategist triggers, R10: a new doorway is in view 81, the doorway you chose is closed or already
passed 30, it is time for a regular check 25, the goal just came into view 22, the goal has been
out of view for three steps 21, the run is starting 18, the drone has reached the target you chose
16, your last move was blocked 13, you keep coming back to the same ground 3. R10C: your target
was reached or is no longer open 142, a new doorway is in view 85, then 27 or fewer each.

Target kinds over decided steps, R10: goal 232, frontier 208, doorway 171, none 123, backtrack 21.
R10C: frontier 320, goal 206, doorway 176, none 143, backtrack 54.

Every turn-around in R10 was followed by a step with [0] left off (65 and 65): no step after a
turn-around had all five forward moves blocked or walled.

## Per run (R10)

| Run | steps | reached | collisions | turn-arounds | [0] left off | no target | strategist (goal-ward) | goal strip | phantom | revisit |
|---|---|---|---|---|---|---|---|---|---|---|
| s01/dynamic/seed1 | 60 | ✗ | 1 | 5 | 5 | 22 | 9 (5/9) | 8/8 | 1/52 | 0.08 |
| s01/final/seed1 | 60 | ✗ | 1 | 9 | 9 | 24 | 10 (5/10) | 0/0 | 0/60 | 0.18 |
| s01/initial/seed1 | 14 | ✓ | 0 | 0 | 0 | 0 | 2 (2/2) | 14/14 | 0/0 | 0.0 |
| s02a/dynamic/seed1 | 50 | ✓ | 6 | 4 | 4 | 11 | 20 (8/20) | 14/14 | 2/36 | 0.14 |
| s02a/final/seed1 | 32 | ✓ | 1 | 2 | 2 | 9 | 12 (8/12) | 6/6 | 1/26 | 0.03 |
| s02a/initial/seed1 | 14 | ✓ | 0 | 0 | 0 | 0 | 4 (4/4) | 14/14 | 0/0 | 0.0 |
| s02c/dynamic/seed1 | 60 | ✗ | 1 | 6 | 6 | 8 | 17 (11/17) | 3/3 | 1/57 | 0.1 |
| s02c/final/seed1 | 47 | ✓ | 1 | 2 | 2 | 0 | 14 (7/14) | 8/8 | 2/39 | 0.17 |
| s02c/initial/seed1 | 19 | ✓ | 0 | 1 | 1 | 0 | 7 (5/7) | 14/15 | 1/4 | 0.0 |
| s02va/dynamic/seed1 | 48 | ✓ | 0 | 2 | 2 | 19 | 16 (7/16) | 8/8 | 1/40 | 0.08 |
| s02va/final/seed1 | 60 | ✗ | 3 | 5 | 5 | 6 | 21 (10/21) | 0/0 | 1/60 | 0.28 |
| s02va/initial/seed1 | 19 | ✓ | 0 | 0 | 0 | 0 | 6 (5/6) | 19/19 | 0/0 | 0.0 |
| s02vc/dynamic/seed1 | 38 | ✓ | 1 | 2 | 2 | 0 | 15 (10/15) | 12/12 | 3/26 | 0.05 |
| s02vc/final/seed1 | 60 | ✗ | 5 | 5 | 5 | 2 | 24 (10/24) | 0/0 | 1/60 | 0.17 |
| s02vc/initial/seed1 | 19 | ✓ | 0 | 0 | 0 | 0 | 7 (7/7) | 19/19 | 0/0 | 0.0 |
| s03/dynamic/seed1 | 60 | ✗ | 6 | 9 | 9 | 10 | 16 (9/16) | 0/0 | 3/60 | 0.25 |
| s03/final/seed1 | 35 | ✓ | 4 | 4 | 4 | 2 | 13 (12/13) | 4/4 | 3/31 | 0.0 |
| s03/initial/seed1 | 60 | ✗ | 6 | 9 | 9 | 10 | 16 (9/16) | 0/0 | 3/60 | 0.25 |

s03 `dynamic` and s03 `initial` are the same run (the switch never fired; summary, "Result").
