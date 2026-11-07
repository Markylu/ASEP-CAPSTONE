# R65 a101 (a100 with a stop wall one cell wide either side) on the ten contested cells, seeds 1-3: summary

**a101 22/30 against the reference lane's 18/30 (R67, `a100`, same batch, same renderer): four above, a carry
by the rule, but not the parent (`a102`, R66, 23/30 in the same batch). s02 20/24 against 15/24; s03 2/6
against 3/6. The hypothesis (at least as many runs as the reference; no lobby stall) held: no run of either
agent stalled in the lobby, so the mechanism was again not exercised, and the s02 gain is in cells the change
does not touch. Read with the instance caveat below.**

| cell | `a100` (R67, reference) | `a100` (R63) | `a101` (R65), steps to the goal |
|---|---|---|---|
| s02a `final` | 1/3 | 3/3 | **2/3** (—, 42, 23) |
| s02a `dynamic` | 2/3 | 3/3 | **3/3** (47, 40, 51) |
| s02c `final` | 1/3 | 0/3 | **3/3** (23, 18, 30) |
| s02c `dynamic` | 3/3 | 2/3 | 2/3 (28, —, 44) |
| s02va `final` | 3/3 | 3/3 | 3/3 (38, 47, 44) |
| s02va `dynamic` | 2/3 | 3/3 | **3/3** (31, 59, 37) |
| s02vc `final` | 2/3 | 2/3 | 2/3 (30, —, 45) |
| s02vc `dynamic` | 1/3 | 2/3 | **2/3** (—, 45, 38) |
| s03 `final` | 2/3 | 3/3 | 1/3 (—, 58, —) |
| s03 `dynamic` | 1/3 | 1/3 | 1/3 (—, —, 58) |
| **total** | **18/30** | **22/30** | **22/30** |
| s02 | 15/24 | 18/24 | 20/24 |
| s03 | 3/6 | 4/6 | 2/6 |

Against the predictions (README): reference +0 to +2 predicted, +4 landed; s02 within 2 (+5); s03 +0 to +1 (−1); no
run with min x above 14 (held, highest −5.8).

What the runs say (scratch `batch_check.py` and the lobby check, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R65_wait_inflate`):
- **The lobby:** every s03 run in the stem by step 5 (five by 4); so was every one of `a100`'s. At the divider the
  survey started in 22 of 24 runs and 20 crossed: the narrower stop wall cost nothing visible on s02 in 60 runs
  now (R62 and R65).
- **s03 2/6.** The latch fired in all six (gaps 5, 5, 6, 9, 10, 16; `a93`'s two-read trigger) and four runs were
  still lost: `dynamic` 1 and `final` 1 crossed at 58 and 59, too late; `dynamic` 2 and `final` 3 out of the tine
  and not through. `dynamic` 3 won at 58, `final` 2 at 58.
- **s02 20/24.** Surveys in 22 of 24 by step 8; stations given up in transit: 2 (at the 17th and 10th step). Losses:
  s02a `final` 1 (through, check, second station done 30), s02c `dynamic` 2 (first station given up at 21,
  second done 34, crossed at 14 by the survey's reckoning but never the divider), s02vc `dynamic` 1 (through from
  5, two stations, done 28), s02vc `final` 2 (no survey). No won run latched before crossing.
- **Walls in flight:** missed 22.6% (153/676), phantom 10.2% (622/6104), s03 phantom 14.7% (R67: 16.3 / 11.8 /
  18.4): missed 6.3 above the reference (outside the 4), the others within 3.7. Longest turn-around streak 3.
- **Goal reports:** 246 in 30 runs; 37 with no line of sight (1.2 a run), 19 dropped; the 22 kept were taken.
- **Labels** (`labels.csv`, Claude review): 22 success, 3 replan_failure, 5 timeout. No tags.

**Manipulation check.** Identity and renderer (`a101`, `42ae7616cca1`, H100 in 30 of 30): held. No s03 run with min
x above 14; every s03 run in the stem by step 8: held. No station given up before its tenth step (17, 10): held.
The survey in at least 19 of 24 by step 8 (22): held. A route on at least 95% of steps (30 of 30): held. Walls
within 4 points of R67's: not held on missed (22.6 against 16.3), held otherwise.

**Instance caveat (all of the night's batches).** Every reference lane flew on `:8007` (the copy on GPU 4) and every candidate on `:8004` or `:8006`; the four reference flights landed below their batch's candidates every time (20/20–22, 21/20–19, 16/20–22, 18/22–23). The one flight of a single agent spread over the three instances, R55 (`a89`, 2026-11-06), won 9 of 12 on `:8004`, 4 of 10 on `:8006` and 5 of 8 on `:8007`; R53 on lavapipe won 14 of 16 on `:8004` and 10 of 14 on `:8006`. Small counts, but an instance effect of a run or two is possible and untested; batch 5 (R68–R70) puts the reference on `:8004`. Read every carry of the night with this in mind.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 1–4 of twelve (`~/asep-r65-l1..4`) on
`:8004`, beside R66 on `:8006` and R67 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote
profile, temperature 0. Flown at `364b3c8` on 2026-11-07, 06:32–07:17 UTC, by Claude alone overnight. Shakedown
2/4 at `364b3c8` (both s02 won; both s03 lost with latches 5 and 10 steps after the read). **30/30 valid.**
Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** Twice now the one-cell stop wall has flown 30 runs without a lobby stall to fix and without a visible
cost at the divider; twice it has landed above a reference that flew low on `:8007`. Harmless as far as 60 runs
can tell, unproven as a gain. It rides into batch 5 on `a102` (R68, `a103`).
