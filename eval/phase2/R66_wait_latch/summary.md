# R66 a102 (a100 with a94's latch) on the ten contested cells, seeds 1-3: summary

**a102 23/30 against the reference lane's 18/30 (R67, `a100`, same batch, same renderer): five above,
carried by the rule; the night's highest flight on H100 frames (`a93`'s four: 19, 20, 21, 16). s02 20/24
against 15/24; s03 3/6 against 3/6. The hypothesis held on the total and on s02, not on s03 `dynamic` (1/3
against 1/3): the latch fired 5 to 11 steps after the read in every run that read the door square in the tine
(5 of 5), and two of the three s03 `dynamic` runs still did not get through in time. Read with the instance
caveat below: the gain is on s02, where this change does nothing, and the reference flew on `:8007`.**

| cell | `a100` (R67, reference) | `a100` (R63) | `a102` (R66), steps to the goal |
|---|---|---|---|
| s02a `final` | 1/3 | 3/3 | **3/3** (37, 18, 46) |
| s02a `dynamic` | 2/3 | 3/3 | 2/3 (49, 40, —) |
| s02c `final` | 1/3 | 0/3 | **3/3** (56, 21, 23) |
| s02c `dynamic` | 3/3 | 2/3 | 3/3 (29, 32, 29) |
| s02va `final` | 3/3 | 3/3 | 3/3 (29, 26, 31) |
| s02va `dynamic` | 2/3 | 3/3 | **3/3** (32, 58, 37) |
| s02vc `final` | 2/3 | 2/3 | **3/3** (33, 25, 35) |
| s02vc `dynamic` | 1/3 | 2/3 | 0/3 |
| s03 `final` | 2/3 | 3/3 | 2/3 (—, 53, 29) |
| s03 `dynamic` | 1/3 | 1/3 | 1/3 (—, —, 52) |
| **total** | **18/30** | **22/30** | **23/30** |
| s02 | 15/24 | 18/24 | 20/24 |
| s03 | 3/6 | 4/6 | 3/6 |

Against the predictions (README): reference +0 to +2 predicted, +5 landed; s02 within 2 (+5); s03 `dynamic` 1–2 of
3 (1), every latch within 9 steps of a square read (5, 6, 8; 11 in `final` 1).

What the runs say (scratch `batch_check.py`, the survey timelines, `eval/r28_flight.py`, `eval/probes/a93_goal_check.py
--folders R66_wait_latch`):
- **The latch:** `dynamic` 1 read 15, latched 21, not through; `dynamic` 3 read 20, latched 25, across at 48, goal
  at 52; `dynamic` 2 read at 26 and never latched (zigzag beside the lane); `final` 1 read 13, latched 24, 5
  turn-arounds in a row, not through (tagged `spin_failure`); `final` 2 read 18, latched 26, across at 49, goal
  at 53; `final` 3 by the open tine (29). Gaps 5, 6, 8, 11. No latch in the open tine or the stem.
- **s02 20/24.** Surveys in 23 of 24 runs by step 8; stations given up in transit: 2 (s02c `final` 1 at its
  twelfth step, won at 56; s02vc `dynamic` 2 at its tenth, lost). Losses: s02a `dynamic` 3 (second station, done
  36), s02vc `dynamic` 1 (through from 5, look 17, second station done 35, latch 38), 2 (both stations given up
  or looked, done 38) and 3 (through from 7, look 29, done 33). One won run latched before crossing (s02c `final`
  1, latch 35, crossed 47).
- **Walls in flight:** missed 20.5% (143/697), phantom 9.6% (528/5503), s03 phantom 12.0% (R67: 16.3 / 11.8 /
  18.4): missed 4.2 above the reference (outside the 4), s03 phantom 6.4 below. Longest turn-around streak 5.
- **Goal reports:** 224 in 30 runs; 30 with no line of sight (1.0 a run), 13 dropped; the 23 kept were taken.
- **Labels** (`labels.csv`, Claude review): 23 success, 6 replan_failure, 1 timeout; tag spin_failure on s03
  `final` 1.

**Manipulation check.** Identity and renderer (`a102`, `e405aeb4a004`, H100 in 30 of 30): held. The latch within
9 steps of a square read in the shut tine: held in 3 of 4 (11 in `final` 1). No latch in the open tine or the
stem: held. No station given up before its tenth step (10, 12): held. A latch before crossing in at most 3 won
s02 runs (1): held. The survey in at least 19 of 24 by step 8 (23): held. A route on at least 95% of steps (30 of
30): held. Walls within 4 points of R67's: not held on missed (20.5 against 16.3) and s03 phantom (12.0 against
18.4), held on phantom.

**Instance caveat (all of the night's batches).** Every reference lane flew on `:8007` (the copy on GPU 4) and every candidate on `:8004` or `:8006`; the four reference flights landed below their batch's candidates every time (20/20–22, 21/20–19, 16/20–22, 18/22–23). The one flight of a single agent spread over the three instances, R55 (`a89`, 2026-11-06), won 9 of 12 on `:8004`, 4 of 10 on `:8006` and 5 of 8 on `:8007`; R53 on lavapipe won 14 of 16 on `:8004` and 10 of 14 on `:8006`. Small counts, but an instance effect of a run or two is possible and untested; batch 5 (R68–R70) puts the reference on `:8004`. Read every carry of the night with this in mind.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 5–8 of twelve (`~/asep-r65-l5..8`) on a copy
of `:8004` on GPU 3 (`:8006`), beside R65 on `:8004` and R67 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `364b3c8` on 2026-11-07, 06:32–07:17 UTC, by Claude
alone overnight. Shakedown 4/4 won at `364b3c8` (s03 `dynamic` 1 latched on the read at 25, goal 58). **30/30
valid.** Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** 23 is the best H100 flight of the night and of this family, and by the rule `a102` is carried as
batch 5's parent and reference (R68–R70, where it flies on `:8004`). The honest size: the five-run gain over
`a100` is all on s02, where `a102` and `a100` share every line of code, so it is the flight's spread (and
perhaps the instance), not the latch; the latch did its own job (5 of 5 within 11 steps) and s03 `dynamic` stayed
1/3. Against `a93`'s four H100 flights (mean 19) and `a100`'s two (mean 20), 23 is +3 to +4 on one flight.
