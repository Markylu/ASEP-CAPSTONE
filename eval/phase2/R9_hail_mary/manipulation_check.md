# R9 manipulation check

From `python eval/spatial_replay.py manip eval/phase2/R9_hail_mary/runs` (pre-registered list,
README "Manipulation check"). Goal-strip accuracy, phantoms and goal-estimate error use the
manifest's ground truth, evaluation only.

## Round totals

| Measure | R9 | Pre-registered |
|---|---|---|
| decisions with notes | 871 / 871 | every decided step |
| picks carrying "blocked here before" | 0 (0%) | < 5% |
| critic objections / picks changed | 19 / 0 | reported |
| strategist calls | 321 (37% of steps) | reported |
| perceiver failures | 0 | reported |
| goal strip within one, goal in view | 112/113 | reported |
| phantom goal reports, goal not in view | 22/758 (2.9%) | reported |
| revisit rate (mean of runs) | 0.15 | below R7's ~0.19 |
| mean step latency | 3.2 s | reported |
| collisions | 34 | below R7's 60 |

Strategist triggers: your target was reached or is no longer open 115, a new doorway is in view 98, the goal has been out of view for three steps 24, it is time for a regular check 23, the goal just came into view 21, the run is starting 18, you keep coming back to the same ground 11, your last move was blocked 11.

Modes over decided steps: explore 639, approach 182, backtrack 50.

## Per run

| Run | steps | reached | collisions | critic (changed) | strategist | goal strip | phantom | goal estimate error (m) | revisit |
|---|---|---|---|---|---|---|---|---|---|
| s01/dynamic/seed1 | 60 | ✗ | 1 | 1 (0) | 15 | 3/3 | 2/57 | 18.9 | 0.22 |
| s01/final/seed1 | 60 | ✗ | 1 | 5 (0) | 12 | 0/0 | 1/60 | 30.1 | 0.13 |
| s01/initial/seed1 | 14 | ✓ | 0 | 0 (0) | 6 | 14/14 | 0/0 | 2.2 | 0.0 |
| s02a/dynamic/seed1 | 60 | ✗ | 1 | 0 (0) | 22 | 3/3 | 1/57 | 14.9 | 0.15 |
| s02a/final/seed1 | 60 | ✗ | 1 | 0 (0) | 21 | 4/4 | 0/56 | 9.1 | 0.13 |
| s02a/initial/seed1 | 14 | ✓ | 0 | 0 (0) | 10 | 14/14 | 0/0 | 2.2 | 0.0 |
| s02c/dynamic/seed1 | 60 | ✗ | 1 | 1 (0) | 21 | 3/3 | 2/57 | 48.3 | 0.18 |
| s02c/final/seed1 | 60 | ✗ | 4 | 0 (0) | 28 | 0/0 | 4/60 | 25.6 | 0.17 |
| s02c/initial/seed1 | 56 | ✓ | 4 | 0 (0) | 27 | 20/21 | 0/35 | 1.0 | 0.12 |
| s02va/dynamic/seed1 | 29 | ✓ | 3 | 0 (0) | 14 | 10/10 | 1/19 | 1.1 | 0.0 |
| s02va/final/seed1 | 60 | ✗ | 5 | 4 (0) | 20 | 0/0 | 1/60 | 11.1 | 0.23 |
| s02va/initial/seed1 | 19 | ✓ | 0 | 0 (0) | 12 | 19/19 | 0/0 | 0.9 | 0.0 |
| s02vc/dynamic/seed1 | 60 | ✗ | 3 | 4 (0) | 23 | 3/3 | 1/57 | 22.9 | 0.13 |
| s02vc/final/seed1 | 60 | ✗ | 0 | 1 (0) | 20 | 0/0 | 1/60 | 11.7 | 0.27 |
| s02vc/initial/seed1 | 19 | ✓ | 0 | 0 (0) | 5 | 19/19 | 0/0 | 0.9 | 0.0 |
| s03/dynamic/seed1 | 60 | ✗ | 4 | 3 (0) | 22 | 0/0 | 1/60 | 17.1 | 0.22 |
| s03/final/seed1 | 60 | ✗ | 4 | 0 (0) | 22 | 0/0 | 3/60 | 28.4 | 0.42 |
| s03/initial/seed1 | 60 | ✗ | 2 | 0 (0) | 21 | 0/0 | 4/60 | 13.2 | 0.27 |
