# R60 a96 (a93 with the spawn's waypoint never behind the drone) on the ten contested cells, seeds 1-3: summary

**a96 19/30 against the reference lane's 21/30 (R61, `a93`, same batch, same renderer): two below, a draw
by the rule, not carried. s02 15/24 against 16/24, s03 4/6 against 5/6. The mechanism held: no run's step-0
waypoint lay behind the drone and no run turned around at step 0 (`a93` R61: 3 waypoints behind, 1
turn-around taken, that run won). The hypothesis (at least as many runs as the reference) did not hold, and
the losses have nothing to do with step 0: s02a `dynamic` 0/3 and s02vc `dynamic` 0/3, lost at the survey's
stations and through phase from step 10 on.**

| cell | `a93` (R61, reference) | `a93` (R58) | `a96` (R60), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | **3/3** (25, 20, 35) |
| s02a `dynamic` | 2/3 | 2/3 | 0/3 |
| s02c `final` | 2/3 | 2/3 | 1/3 (—, 47, —) |
| s02c `dynamic` | 2/3 | 1/3 | **3/3** (26, 23, 25) |
| s02va `final` | 3/3 | 2/3 | 3/3 (27, 29, 30) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (28, 28, 37) |
| s02vc `final` | 2/3 | 3/3 | 2/3 (29, —, 35) |
| s02vc `dynamic` | 0/3 | 2/3 | 0/3 |
| s03 `final` | 3/3 | 3/3 | 2/3 (—, 26, 43) |
| s03 `dynamic` | 2/3 | 0/3 | 2/3 (55, 57, —) |
| **total** | **21/30** | **20/30** | **19/30** |
| s02 | 16/24 | 17/24 | 15/24 |
| s03 | 5/6 | 3/6 | 4/6 |

Against the predictions (README): reference +0 to +2 predicted, −2 landed; s02 +0 to +2 (−1); s03 within 1 (−1).

What the runs say (scratch `batch_check.py` and the step-0 check, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R60_spawn_ahead`):
- **Step 0:** in all 30 runs the first waypoint lay within 90 degrees of the heading (17 degrees at most) and the
  turn-around carried only "behind you is new ground"; no run turned around at step 0. In R61's `a93`, 3 of 30
  step-0 waypoints lay behind (s02a `final` 3, s02va `dynamic` 1 and 2, each with "toward your target" on the
  turn-around) and s02a `final` 3 took it (won at 23 all the same).
- **s02 15/24.** Surveys in 21 of 24 runs by step 8. Losses: s02a `dynamic` 1 (first station, through from 15, look
  again 26, done 30), 2 (second station given up at 31 with no look) and 3 (second station, through 25, look
  34, done 38); s02c `final` 1 (second station done 31) and 3 (no survey, latch at 29); s02vc `dynamic` 1 (through
  from 5, done at 10 as through, was not), 2 (done at 14, latch at 20, crossed at 56) and 3 (second station done
  at 32); s02vc `final` 2 (done at 5, latch 36, crossed 52). One won run latched before crossing (s02c `final` 2,
  latch 14, crossed 39).
- **s03 4/6.** `dynamic` 1 read the shut door at 20, latched at 25 (the `a93` latch with reads 2: the second read
  came at once), across at 51, goal 55; `dynamic` 2 read at 28, latched at 30, across at 54, goal 57; `dynamic` 3
  read at 41, latched at 46, not through in time. `final` 1 lost: crossed at 18 by the open tine, then 42 steps in
  the chamber without reaching the goal (tagged `failed_goal_identification`); `final` 2 and 3 won (26, 43).
- **Walls in flight:** missed 25.3% (197/779), phantom 9.9% (558/5646), s03 phantom 9.7% (R61: 21.0 / 10.4 /
  12.4): missed 4.3 points above the reference (outside the 4 allowed), the others within 3. Longest streak 4.
- **Goal reports:** 211 in 30 runs; 34 with no line of sight (1.1 a run), 16 dropped; the 22 kept were taken.
- **Labels** (`labels.csv`, Claude review): 19 success, 8 replan_failure, 3 timeout; tag failed_goal_identification on
  s03 `final` 1.

**Manipulation check.** Identity and renderer (`a96`, `8bc44fc02535`, H100 in 30 of 30): held. No step-0 waypoint
behind, no "toward your target" on the step-0 turn-around, no step-0 turn-around: held (0, 0, 0). The survey in at
least 19 of 24 s02 runs by step 8 (21): held. A route on at least 95% of steps (30 of 30): held. Walls within 4 points
of R61's: not held on missed (25.3 against 21.0), held on the two phantom rates. The latch in s03 as `a93`'s: held
(gaps 5, 2, 5).

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 5–8 of twelve (`~/asep-r59-l5..8`) on a copy of
`:8004` on GPU 3 (`:8006`), beside R59 on `:8004` and R61 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `13456b0` on 2026-11-07, 04:03–04:52 UTC, by Claude
alone overnight. Shakedown 3/4 won at `13456b0`, every step-0 waypoint ahead. **30/30 valid**, no attempt beyond the
first. Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** The artefact is gone and nothing came of it: the step-0 turn-around cost `a93` a run in 3 of 4 lavapipe
flights of s02vc `final` 3, but on H100 frames the drone has gone straight at step 0 in that cell three times in a
row with or without the fix, and the run is decided later, at the survey's stations. Two below the reference is the
spread. Not carried; harmless to keep in a later parent.
