# R70 a102, batch 5's reference lane on H100 frames, on `:8004`, on the ten contested cells, seeds 1-3: summary

**a102 21/30 (s02 18/24, s03 3/6) on H100 frames beside R68 (`a103`) and R69 (`a104`), same commit, same
minutes, this time on `:8004` and not `:8007`: two below its first flight (R66, 23/30 on `:8006`). Within the
19–25 predicted. `a102`'s two flights are 44/60 (s02 38/48, s03 6/12), 22 a flight, against `a100`'s 20 (22,
18) and `a93`'s 19 (19, 20, 21, 16) on this renderer. The first reference lane off `:8007` landed one above
one candidate and two below the other: the instance did not make the night's reference lanes low on its own.**

| cell | `a102` (R66, `:8006`) | `a100` (R67) | `a93` (R64) | `a102` (R70, `:8004`), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 3/3 | 1/3 | 1/3 | 1/3 (—, 31, —) |
| s02a `dynamic` | 2/3 | 2/3 | 2/3 | 2/3 (—, 42, 52) |
| s02c `final` | 3/3 | 1/3 | 0/3 | 1/3 (—, —, 29) |
| s02c `dynamic` | 3/3 | 3/3 | 3/3 | 3/3 (24, 24, 32) |
| s02va `final` | 3/3 | 3/3 | 3/3 | 3/3 (29, 29, 29) |
| s02va `dynamic` | 3/3 | 2/3 | 3/3 | 3/3 (30, 27, 29) |
| s02vc `final` | 3/3 | 2/3 | 1/3 | 3/3 (30, 29, 33) |
| s02vc `dynamic` | 0/3 | 1/3 | 0/3 | 2/3 (—, 31, 28) |
| s03 `final` | 2/3 | 2/3 | 1/3 | 2/3 (—, 32, 55) |
| s03 `dynamic` | 1/3 | 1/3 | 2/3 | 1/3 (42, —, —) |
| **total** | **23/30** | **18/30** | **16/30** | **21/30** |
| s02 | 20/24 | 15/24 | 13/24 | 18/24 |
| s03 | 3/6 | 3/6 | 3/6 | 3/6 |

What the runs say (scratch `batch_check.py`, the give-up count, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R70_ref_a102`):
- **Renderer and identity:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30); every `run.json` carries
  `a102`, `e405aeb4a004`, git `bbb511b`, **`:8004`**.
- **s02 18/24.** Surveys in 22 of 24 runs by step 8; stations given up in transit: 3 (at the 10th, 10th and 11th
  step; none before the tenth). Losses: s02a `dynamic` 1 (second station given up at 34, latch 54), s02a `final` 1
  (through from 8, look, done 24, crossed at 14 by the survey's reckoning, never the divider) and 3 (second station,
  through 31, done 46), s02c `final` 1 (both stations, done 30) and 2 (no survey, latch 14), s02vc `dynamic` 1 (both
  stations given up or looked, done 41, latch 44). No won run latched before crossing.
- **s03 3/6.** The latch fired in every run that read the shut door (gaps 0, 4, 6, 9, 9): `dynamic` 1 won at 42
  (read 17, latch 21, across 38), `final` 3 at 55 (read 15, latch 24, across 50); `dynamic` 2 latched on the read
  at 30, `dynamic` 3 at 44 (5 turn-arounds in a row, tagged `spin_failure`), `final` 1 at 27: out, not through.
  `final` 2 by the open tine (32). Every s03 run in the stem by step 4.
- **Walls in flight:** missed 17.8% (116/652), phantom 11.2% (613/5483), s03 phantom 16.1% (R66: 20.5 / 9.6 /
  12.0): within 4.1 on s03 phantom (at the edge), within 2.7 otherwise. Longest turn-around streak 5.
- **Goal reports:** 210 in 30 runs; 31 with no line of sight (1.0 a run), 12 dropped (39%); 2 of 179 with a line
  of sight dropped (1.1%). The 19 kept were taken.
- **Labels** (`labels.csv`, Claude review): 21 success, 8 replan_failure, 1 timeout; tag spin_failure on s03
  `dynamic` 3.

**Manipulation check.** Renderer and identity (on `:8004`): held. No station given up before its tenth step: held.
The latch within 9 steps of a square read in the shut tine: held (0–9). Walls within 4 points of R66: held but for
s03 phantom at 4.1. The survey in at least 19 of 24 by step 8 (22): held. A route on at least 95% of steps: held.

**Not citable.** Host round, three seeds per cell. Host: sctsvr6, lanes 1–4 of twelve (`~/asep-r68-l1..4`) on
`:8004`, beside R68 on `:8006` and R69 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote
profile, temperature 0. Flown at `bbb511b` on 2026-11-07, 07:40–08:24 UTC, by Claude alone overnight
(OVERNIGHT_PROMPT.md). **30/30 valid.** Labels: Claude review, not yet confirmed by the operator. Frames stay on
the host.

**Reading.** 23 then 21: `a102` holds at 22 a flight over 60 runs, three above `a93`'s four-flight mean and two
above `a100`'s. On `:8004` the reference landed where its candidates did, so the instance is at most a run or
two of the night's story; the rest is the flight-to-flight spread of 2 to 4 that every agent of this family
shows. The bar for R68 and R69. The night ends with `a102` as the agent to build on: `a93` plus the survey's
stations held 10 steps plus the latch fired on one square read and for a corridor drifted into.
