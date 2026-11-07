# R67 a100, batch 4's reference lane on H100 frames, on the ten contested cells, seeds 1-3: summary

**a100 18/30 (s02 15/24, s03 3/6) on H100 frames beside R65 (`a101`) and R66 (`a102`), same commit, same
minutes: four below its first flight (R63, 22/30). Within the 18–24 predicted, at the low edge. `a100`'s two
flights are 40/60 (s02 33/48, s03 7/12), level with `a93`'s four (76/120). Stations given up in transit: one,
at its tenth step (the mechanism holds); the s02 losses are elsewhere (second stations looked and done, a
through phase ending without the crossing).**

| cell | `a100` (R63) | `a93` (R64) | `a93` (R61) | `a100` (R67), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 3/3 | 1/3 | 2/3 | 1/3 (—, 18, —) |
| s02a `dynamic` | 3/3 | 2/3 | 2/3 | 2/3 (42, 38, —) |
| s02c `final` | 0/3 | 0/3 | 2/3 | 1/3 (22, —, —) |
| s02c `dynamic` | 2/3 | 3/3 | 2/3 | 3/3 (37, 29, 41) |
| s02va `final` | 3/3 | 3/3 | 3/3 | 3/3 (23, 36, 30) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 | 2/3 (29, 27, —) |
| s02vc `final` | 2/3 | 1/3 | 2/3 | 2/3 (—, 35, 56) |
| s02vc `dynamic` | 2/3 | 0/3 | 0/3 | 1/3 (25, —, —) |
| s03 `final` | 3/3 | 1/3 | 3/3 | 2/3 (29, —, 30) |
| s03 `dynamic` | 1/3 | 2/3 | 2/3 | 1/3 (54, —, —) |
| **total** | **22/30** | **16/30** | **21/30** | **18/30** |
| s02 | 18/24 | 13/24 | 16/24 | 15/24 |
| s03 | 4/6 | 3/6 | 5/6 | 3/6 |

What the runs say (scratch `batch_check.py`, the give-up count, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R67_ref_a100`):
- **Renderer and identity:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30); every `run.json` carries
  `a100`, `22e2941dc494`, git `364b3c8`, `:8007`.
- **s02 15/24.** Surveys in 21 of 24 runs by step 8. One station given up in transit (s02vc `dynamic` 2, at its
  tenth step; lost). Losses: s02a `dynamic` 3 and s02a `final` 1 (second station looked, done at 36 and 33),
  s02a `final` 3 (no survey), s02c `final` 2 and 3 (first station looked to 26 and 23, second looked, done at
  38 and 33), s02va `dynamic` 3 (through from 4, look 21, done 25, latch 32), s02vc `dynamic` 2 (above) and 3
  (through, look, through, look, second station, done at 43), s02vc `final` 1 (through from 2, done 16, latch
  25). One won run latched before crossing (s02vc `final` 3).
- **s03 3/6.** `dynamic` 1 won through the latch (read 20, latch 26, goal 54); `dynamic` 2 and 3 latched 6 steps
  after the read (29, 26), out, not through in time (seed 3 crossed at 59). `final` 1 and 3 by the open tine;
  `final` 2 read a closed door from the lobby at step 1, latched at 19, crossed at 58, out of steps. Every s03
  run in the stem by step 4.
- **Walls in flight:** missed 16.3% (123/756), phantom 11.8% (691/5849), s03 phantom 18.4% (R63: 17.6 / 12.2 /
  16.0): within 2.4 points. Longest turn-around streak 3.
- **Goal reports:** 197 in 30 runs; 32 with no line of sight (1.1 a run), 18 dropped; the 19 kept were taken.
- **Labels** (`labels.csv`, Claude review): 18 success, 9 replan_failure, 3 timeout. No tags.

**Manipulation check.** Renderer and identity: held. No station given up before its tenth step (one, at 10):
held. Walls within 4 points of R63: held. The survey in at least 19 of 24 s02 runs by step 8 (21): held. A route on
at least 95% of steps (30 of 30): held.

**Instance caveat (all of the night's batches).** Every reference lane flew on `:8007` (the copy on GPU 4) and every candidate on `:8004` or `:8006`; the four reference flights landed below their batch's candidates every time (20/20–22, 21/20–19, 16/20–22, 18/22–23). The one flight of a single agent spread over the three instances, R55 (`a89`, 2026-11-06), won 9 of 12 on `:8004`, 4 of 10 on `:8006` and 5 of 8 on `:8007`; R53 on lavapipe won 14 of 16 on `:8004` and 10 of 14 on `:8006`. Small counts, but an instance effect of a run or two is possible and untested; batch 5 (R68–R70) puts the reference on `:8004`. Read every carry of the night with this in mind.

**Not citable.** Host round, three seeds per cell. Host: sctsvr6, lanes 9–12 of twelve (`~/asep-r65-l9..12`) on a
copy of `:8004` on GPU 4 (`:8007`), beside R65 on `:8004` and R66 on `:8006`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `364b3c8` on 2026-11-07, 06:32–07:17 UTC, by Claude
alone overnight (OVERNIGHT_PROMPT.md). **30/30 valid.** Labels: Claude review, not yet confirmed by the operator.
Frames stay on the host.

**Reading.** 22 then 18: `a100`'s carry in batch 3 was in part `a93`'s low flight. Over two flights `a100` is
20 a flight, as `a93` is over four; the station rule still does what it says (one give-up in 60 runs at the
tenth step against `a93`'s five at the sixth in one flight) and the cell it was built for, s02vc `dynamic`, is
3 of 6 for `a100` against 0 of 9 for `a93` on this renderer. The bar for R65 and R66, with the instance caveat.
