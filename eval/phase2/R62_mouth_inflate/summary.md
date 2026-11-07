# R62 a99 (a93 with a stop wall one cell wide either side, not two) on the ten contested cells, seeds 1-3: summary

**a99 20/30 against the reference lane's 16/30 (R64, `a93`, same batch, same renderer): four above, which
the rule calls a carry; not taken as the parent because `a100` (R63, 22/30) stands above it in the same
batch, and its own mechanism was not exercised: no run of either agent stalled in the lobby this flight
(every s03 run of `a99` and of `a93` was in the stem by step 4). The hypothesis (no lobby stall, at least as
many runs as the reference) held on its face; the gain over the reference is the reference's low flight
(19, 20, 21, 16), and against `a93`'s four H100 flights `a99`'s 20 is level.**

| cell | `a93` (R64, reference) | `a93` (R61) | `a99` (R62), steps to the goal |
|---|---|---|---|
| s02a `final` | 1/3 | 2/3 | **3/3** (22, 43, 21) |
| s02a `dynamic` | 2/3 | 2/3 | 0/3 |
| s02c `final` | 0/3 | 2/3 | 0/3 |
| s02c `dynamic` | 3/3 | 2/3 | 3/3 (25, 39, 29) |
| s02va `final` | 3/3 | 3/3 | 3/3 (22, 25, 29) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (29, 38, 35) |
| s02vc `final` | 1/3 | 2/3 | **2/3** (29, —, 28) |
| s02vc `dynamic` | 0/3 | 0/3 | **2/3** (31, —, 30) |
| s03 `final` | 1/3 | 3/3 | **2/3** (28, 24, —) |
| s03 `dynamic` | 2/3 | 2/3 | 2/3 (60, 59, —) |
| **total** | **16/30** | **21/30** | **20/30** |
| s02 | 13/24 | 16/24 | 16/24 |
| s03 | 3/6 | 5/6 | 4/6 |

Against the predictions (README): reference +0 to +2 predicted, +4 landed; s02 within 2 (+3); s03 +0 to +1 (+1),
no run with min x above 14 (held: the highest 4.3).

What the runs say (scratch `batch_check.py` and the lobby check, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R62_mouth_inflate`):
- **The lobby:** every s03 run was in the stem (x < 15) by step 4; so was every one of `a93`'s this flight. The
  stall the change was built against (seed 2 in R58 and R59) did not recur for either agent, so the flight says
  nothing about the mechanism. At the s02 divider, where the inflation matters, the survey started in 22 of 24
  runs and the drone crossed in 16: no sign the narrower stop wall let the route through a wall.
- **s03 4/6.** `dynamic` 1 and 2 won at the last step through the latch (read 19, latch 24, goal 60; read 25,
  latch 30, goal 59); `dynamic` 3 read 21, latched 27, across at 59, one step short. `final` 1 and 2 by the open
  tine (28, 24); `final` 3 spent the run in the crossbar (min x 4.3), never in a tine.
- **s02 16/24.** Losses: s02a `dynamic` 1 and 2 (through from 12 and 13, look again, done 24), s02a `dynamic` 3
  (second station, through 22, done 34), s02c `final` 1 (first station given up at 8, second looked, done 27,
  crossed at 57), s02c `final` 2 and 3 (no survey, lost), s02vc `dynamic` 2 (first station given up at 10,
  second done 28, latch 31), s02vc `final` 2 (through from 2, look, second station given up at 34). Stations
  given up in transit: 5 in 5 runs (`a93`: 5 in 4). No won run latched before crossing.
- **Walls in flight:** missed 23.7% (188/792), phantom 10.5% (571/5438), s03 phantom 15.1% (R64: 19.9 / 12.6 /
  14.9): missed 3.8 points above, within the 4. Longest turn-around streak 5.
- **Goal reports:** 202 in 30 runs; 32 with no line of sight (1.1 a run), 19 dropped; the 19 kept were taken.
- **Labels** (`labels.csv`, Claude review): 20 success, 8 replan_failure, 2 timeout. No tags.

**Manipulation check.** Identity and renderer (`a99`, `03c0c43ab9b3`, H100 in 30 of 30): held. No s03 run with
min x above 14: held (and in R64). Every s03 run in the stem by step 8: held (by 4). The survey in at least 19 of
24 s02 runs by step 8 (22): held. A route on at least 95% of steps (30 of 30): held. Walls within 4 points of
R64's: held (missed at 3.8). The latch within 9 steps of a square read: held (5, 5, 6).

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 1–4 of twelve (`~/asep-r62-l1..4`) on
`:8004`, beside R63 on `:8006` and R64 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote
profile, temperature 0. Flown at `62bee17` on 2026-11-07, 05:17–06:09 UTC, by Claude alone overnight. Shakedown
3/4 won at `62bee17`. **30/30 valid.** Labels: Claude review, not yet confirmed by the operator. Frames stay on the
host.

**Reading.** Four above a reference that flew its low flight, with the mechanism untested by the run. Cheap and,
on this flight, harmless at the divider; it rides into the next batch on `a100` (R65, `a101`) where the
question is whether it costs anything over 30 more runs, and the lobby stall gets another chance to show.
