# R63 a100 (a93 with the survey's stations held 10 steps in transit) on the ten contested cells, seeds 1-3: summary

**a100 22/30 against the reference lane's 16/30 (R64, `a93`, same batch, same renderer): six above,
carried by the rule (3 or more). s02 18/24 against 13/24; s03 4/6 against 3/6. The hypothesis held (at
least as many runs as the reference, the gain on the c and vc sites: s02vc `dynamic` 2/3 against 0/3,
s02a 6/6 against 3/6). The mechanism held exactly: one station given up in transit, at its tenth step
(`a93`: five, each at the sixth). Caveat the reading states: R64 is `a93`'s lowest of four H100 flights
(19, 20, 21, 16); against the four together (mean 19), `a100`'s 22 is +3, at the edge of the rule.**

| cell | `a93` (R64, reference) | `a93` (R61) | `a100` (R63), steps to the goal |
|---|---|---|---|
| s02a `final` | 1/3 | 2/3 | **3/3** (35, 57, 34) |
| s02a `dynamic` | 2/3 | 2/3 | **3/3** (42, 39, 39) |
| s02c `final` | 0/3 | 2/3 | 0/3 |
| s02c `dynamic` | 3/3 | 2/3 | 2/3 (25, —, 23) |
| s02va `final` | 3/3 | 3/3 | 3/3 (28, 26, 31) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (22, 28, 42) |
| s02vc `final` | 1/3 | 2/3 | **2/3** (58, 34, —) |
| s02vc `dynamic` | 0/3 | 0/3 | **2/3** (—, 39, 22) |
| s03 `final` | 1/3 | 3/3 | **3/3** (49, 43, 32) |
| s03 `dynamic` | 2/3 | 2/3 | 1/3 (58, —, —) |
| **total** | **16/30** | **21/30** | **22/30** |
| s02 | 13/24 | 16/24 | 18/24 |
| s03 | 3/6 | 5/6 | 4/6 |

Against the predictions (README): reference +0 to +3 predicted, +6 landed; s02 +0 to +3 (+5), stations given up
in transit in at most half as many runs (1 against 4); s03 within 1 (+1).

What the runs say (scratch `batch_check.py` and the give-up count, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R63_station_wait`):
- **The stations:** one given up in transit in 30 runs (s02a `final` 3, the first station at its tenth step;
  the run went on to the second station and won at 34). `a93` in the same batch: five, in four runs, each at the
  sixth step, all four lost. The s02vc `dynamic` seeds `a93` lost 0/3 in three flights running: seed 2 through
  at 39, seed 3 at 22; seed 1 looked, went through, checked, took the second station and ended at 38 without
  crossing.
- **s02 18/24.** Surveys in 21 of 24 runs (the three without: s02a `final` 2 won at 57 by the route with a latch
  at 32; s02c `final` 3 and s02vc `final` 3 lost, latches at 18 and 20). Losses: s02c `dynamic` 2 (second
  station, through from 29, done 48), s02c `final` 1 (through from 2, look 13, done 17), s02c `final` 2 (two
  looks, done 26, 5 turn-arounds in a row, tagged `spin_failure`), s02vc `dynamic` 1 (above), and the two with
  no survey. s02c `final` is 0/3 for `a100` and `a93` alike this batch (2/3 each the batch before).
- **s03 4/6.** `dynamic` 1 read the shut door at 30, latched at 35, across at 55, goal at 58; `dynamic` 2 read a
  closed door at step 1 from the lobby and latched only at 33 (`a93`'s trigger: two reads), not through;
  `dynamic` 3 read 34, latched 39, not through in time. `final` 3/3 (49, 43, 32), two by the open tine, one
  through a read at 26 without a latch. No survey in any s03 run.
- **Walls in flight:** missed 17.6% (132/749), phantom 12.2% (694/5681), s03 phantom 16.0% (R64: 19.9 / 12.6 /
  14.9): within 2.3 points. Longest turn-around streak 5.
- **Goal reports:** 246 in 30 runs; 38 with no line of sight (1.3 a run), 23 dropped; the 21 kept were taken.
- **Labels** (`labels.csv`, Claude review): 22 success, 8 replan_failure; tag spin_failure on s02c `final` 2.

**Manipulation check.** Identity and renderer (`a100`, `22e2941dc494`, H100 in 30 of 30): held. No station given
up in transit before its tenth step: held (one, at 10). Stations given up in at most half as many runs as R64 (1
against 4): held. The survey in at least 19 of 24 s02 runs by step 8 (21): held. No survey in s03: held. A route on
at least 95% of steps (30 of 30): held. Walls within 4 points of R64's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 5–8 of twelve (`~/asep-r62-l5..8`) on a copy
of `:8004` on GPU 3 (`:8006`), beside R62 on `:8004` and R64 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `62bee17` on 2026-11-07, 05:17–06:09 UTC, by Claude alone
overnight. Shakedown 3/4 won at `62bee17`, no station given up before step 10. **30/30 valid.** Labels: Claude
review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** The change did what it was built to do and the runs it was built for were won: the four `a93` losses
that gave a station up at the sixth step have their counterpart in `a100`'s one give-up at the tenth, and s02vc
`dynamic`, 0 of 9 for `a93` in three flights, went 2/3. Six above the same-batch reference is a carry by the rule,
and `a100` is the next batch's parent and reference (R65–R67). The honest size of the gain is smaller: against
`a93`'s four H100 flights it is +3 on the mean and +1 on the best, and `a92` (12 steps, on `a91`) gained one run
in R52. One flight; the next batch's reference lane (`a100` again) is its second.
