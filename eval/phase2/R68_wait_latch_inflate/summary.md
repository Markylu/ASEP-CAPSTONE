# R68 a103 (a102 with a stop wall one cell wide either side) on the ten contested cells, seeds 1-3: summary

**a103 20/30 against the reference lane's 21/30 (R70, `a102`, same batch, same renderer): one below, a draw, not
carried. s02 15/24 against 18/24; s03 5/6 against 3/6. The hypothesis (at least as many runs as the reference)
did not hold on the total; the mechanism was again not exercised (no lobby stall for any agent this batch, every
s03 run in the stem by step 4), and over three flights on three parents (R62, R65, R68: 20, 22, 20 against 16, 18,
21) the one-cell stop wall has shown no sign either way at the divider. The s03 5/6 is the best s03 of the night
and is the latch's work and the flight's luck, not the wall's.**

| cell | `a102` (R70, reference) | `a102` (R66) | `a103` (R68), steps to the goal |
|---|---|---|---|
| s02a `final` | 1/3 | 3/3 | 0/3 |
| s02a `dynamic` | 2/3 | 2/3 | 2/3 (—, 47, 50) |
| s02c `final` | 1/3 | 3/3 | **2/3** (—, 27, 29) |
| s02c `dynamic` | 3/3 | 3/3 | 2/3 (—, 23, 48) |
| s02va `final` | 3/3 | 3/3 | 2/3 (—, 42, 23) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (28, 23, 23) |
| s02vc `final` | 3/3 | 3/3 | 1/3 (—, —, 31) |
| s02vc `dynamic` | 2/3 | 0/3 | **3/3** (26, 29, 35) |
| s03 `final` | 2/3 | 2/3 | **3/3** (48, 25, 48) |
| s03 `dynamic` | 1/3 | 1/3 | **2/3** (57, 45, —) |
| **total** | **21/30** | **23/30** | **20/30** |
| s02 | 18/24 | 20/24 | 15/24 |
| s03 | 3/6 | 3/6 | 5/6 |

Against the predictions (README): reference +0 to +2 predicted, −1 landed; s02 within 2 (−3); s03 within 1 (+2); no
run with min x above 14 (held).

What the runs say (scratch `batch_check.py` and the lobby check, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R68_wait_latch_inflate`):
- **s03 5/6.** The latch fired in every run that read the shut door (gaps 0, 4, 5, 6, 6): `dynamic` 1 read 29,
  latched 29, across 54, goal 57; `dynamic` 2 read 14, latched 20, goal 45; `final` 1 read 14, latched 19, goal 48;
  `final` 3 read 20, latched 26, goal 48; `dynamic` 3 read 31, latched 35, not through. `final` 2 by the open tine
  (25). Every s03 run in the stem by step 4; none stalled in the lobby (nor did any of `a102`'s or `a104`'s).
- **s02 15/24.** Surveys in 23 of 24 by step 8; one station given up in transit (at its 18th step). Losses: s02a
  `final` 1, 2 and 3 (0/3: through-phase and second-station failures, done at 18, 40 and 42; seed 2 crossed at 58),
  s02a `dynamic` 1 (second station, done 40, tagged `failed_goal_identification`), s02c `dynamic` 1 (first station
  given up at 22, second done 44), s02c `final` 1 (second station, done 29), s02va `final` 1 (no survey, latch 21),
  s02vc `final` 1 (through from 2, done 18, latch 20) and 2 (through from 2, done 5). One won run latched before
  crossing (s02va `final` 2).
- **Walls in flight:** missed 17.1% (100/584), phantom 10.6% (631/5951), s03 phantom 13.8% (R70: 17.8 / 11.2 /
  16.1): within 2.3 points. Longest turn-around streak 3.
- **Goal reports:** 226 in 30 runs; 30 with no line of sight (1.0 a run), 10 dropped; the 20 kept were taken.
- **Labels** (`labels.csv`, Claude review): 20 success, 6 replan_failure, 4 timeout; tag failed_goal_identification on
  s02a `dynamic` 1.

**Manipulation check.** Identity and renderer (`a103`, `e53c86de68a7`, `:8006`, H100 in 30 of 30): held. No s03 run
with min x above 14; every s03 run in the stem by step 8: held. No station given up before its tenth step: held. The
latch within 9 steps of a square read: held (0–6). The survey in at least 19 of 24 by step 8 (23): held. A route on at
least 95% of steps: held. Walls within 4 points of R70's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 5–8 of twelve (`~/asep-r68-l5..8`) on a copy of
`:8004` on GPU 3 (`:8006`), beside R70 on `:8004` and R69 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `bbb511b` on 2026-11-07, 07:40–08:24 UTC, by Claude alone
overnight. Shakedown 4/4 won at `bbb511b`. **30/30 valid.** Labels: Claude review, not yet confirmed by the operator.
Frames stay on the host.

**Reading.** Three flights, three parents, no lobby stall to fix and no cost or gain to see: the one-cell stop wall is
a change without a case on this renderer's record. Not carried. If the lobby stall of R58 and R59 recurs, this is
still the first thing to try against it.
