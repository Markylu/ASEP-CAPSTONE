# R69 a104 (a102 with the goal check at 20 degrees, not 26) on the ten contested cells, seeds 1-3: summary

**a104 23/30 against the reference lane's 21/30 (R70, `a102`, same batch, same renderer): two above, a draw by
the rule (under 3), not carried. s02 20/24 against 18/24; s03 3/6 against 3/6. The hypothesis (at least as many
runs as the reference) held; the check did what it was built to do (13 of 30 blind reports dropped, 43%; 9 of 202
true ones, 4.5%; no goal tag on a dropped step) and the cells it moved are s02a's (6/6 against 3/6), where the
blind reports are.**

| cell | `a102` (R70, reference) | `a102` (R66) | `a104` (R69), steps to the goal |
|---|---|---|---|
| s02a `final` | 1/3 | 3/3 | **3/3** (35, 41, 44) |
| s02a `dynamic` | 2/3 | 2/3 | **3/3** (40, 43, 38) |
| s02c `final` | 1/3 | 3/3 | **2/3** (26, —, 28) |
| s02c `dynamic` | 3/3 | 3/3 | 1/3 (—, 24, —) |
| s02va `final` | 3/3 | 3/3 | 3/3 (27, 36, 30) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (30, 23, 23) |
| s02vc `final` | 3/3 | 3/3 | 3/3 (28, 27, 25) |
| s02vc `dynamic` | 2/3 | 0/3 | 2/3 (35, 34, —) |
| s03 `final` | 2/3 | 2/3 | 1/3 (33, —, —) |
| s03 `dynamic` | 1/3 | 1/3 | **2/3** (52, 49, —) |
| **total** | **21/30** | **23/30** | **23/30** |
| s02 | 18/24 | 20/24 | 20/24 |
| s03 | 3/6 | 3/6 | 3/6 |

Against the predictions (README): reference −1 to +2 predicted, +2 landed; s02 within 2 (+2); s03 within 1 (0).

What the runs say (`eval/probes/a93_goal_check.py --agent a104 --folders R69_goal_check_20`, scratch
`batch_check.py`, the survey timelines, `eval/r28_flight.py`):
- **The check:** 232 goal reports in 30 runs; 30 with no line of sight, **13 dropped (43%)** (`a102` in the same
  batch at 26 degrees: 12 of 31, 39%); **9 of 202 made with a line of sight dropped (4.5%)** (`a102`: 2 of 179,
  1.1%). No goal tag stood on a step whose report was dropped (22 dropped steps). The 17 blind reports kept raised a
  tag each and the navigator took all 17.
- **s02 20/24.** Surveys in 22 of 24 by step 8; one station given up in transit, at its tenth step. Losses: s02c
  `dynamic` 1 (second station looked, done 31) and 3 (second station, done 32, latch 35), s02c `final` 2 (no survey,
  latch 22), s02vc `dynamic` 3 (second station, through 23, look 28, done 30). s02a 6/6: the a site's second clean
  sweep of the night (R57's `a95` the first).
- **s03 3/6.** `dynamic` 1 and 2 won through the latch (read 20, latch 24, goal 52; read 17, latch 22, goal 49);
  `dynamic` 3 read 23, latched 35 (a 12-step gap: the drone was still advancing down the tine), not through; `final`
  1 by the open tine (33); `final` 2 read 21, latched 27, not through; `final` 3 crossed at 59 by the open tine, out
  of steps.
- **Walls in flight:** missed 17.6% (98/556), phantom 10.6% (572/5399), s03 phantom 15.2% (R70: 17.8 / 11.2 /
  16.1): within 1 point. Longest turn-around streak 3.
- **Labels** (`labels.csv`, Claude review): 23 success, 5 replan_failure, 2 timeout. No tags.

**Manipulation check.** Identity and renderer (`a104`, `df66b94d8c6a`, `:8007`, H100 in 30 of 30): held. At least
40% of blind reports dropped (43%): held. At most 6% of true reports dropped (4.5%): held. No goal tag on a dropped
step: held. No station given up before its tenth step (one, at 10): held. The latch within 9 steps of a square read:
held in 3 of 4 (12 in `dynamic` 3, still advancing). The survey in at least 19 of 24 by step 8 (22): held. A route on
at least 95% of steps: held. Walls within 4 points of R70's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 9–12 of twelve (`~/asep-r68-l9..12`) on a
copy of `:8004` on GPU 4 (`:8007`), beside R70 on `:8004` and R68 on `:8006`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `bbb511b` on 2026-11-07, 07:40–08:24 UTC, by Claude alone
overnight. Shakedown 4/4 won at `bbb511b`. **30/30 valid.** Labels: Claude review, not yet confirmed by the operator.
Frames stay on the host.

**Reading.** Two above the reference, inside the draw band; level with `a102`'s own best flight. The check is cheap,
did its job exactly and cost 7 more true reports in 30 runs without a visible price; it is a reasonable thing to
keep on the next parent, but this flight does not earn it a carry. Not carried.
