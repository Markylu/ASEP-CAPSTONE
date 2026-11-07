# R64 a93, batch 3's reference lane on H100 frames, on the ten contested cells, seeds 1-3: summary

**a93 16/30 (s02 13/24, s03 3/6) on H100 frames, flown beside R62 (`a99`) and R63 (`a100`) at the same
commit in the same minutes: its lowest flight on this renderer (R54 19, R58 20, R61 21, R64 16; 76/120,
s02 63/96, s03 13/24). The hypothesis held on the lower edge (17–23 predicted, 16 landed). s02c `final`
0/3 and s02vc `dynamic` 0/3 (the latter 0/3 for the third flight running), s02a `final` 1/3.**

| cell | `a93` (R61) | `a93` (R58) | `a93` (R54) | `a93` (R64), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 2/3 | 1/3 (—, —, 21) |
| s02a `dynamic` | 2/3 | 2/3 | 2/3 | 2/3 (—, 41, 42) |
| s02c `final` | 2/3 | 2/3 | 1/3 | 0/3 |
| s02c `dynamic` | 2/3 | 1/3 | 3/3 | 3/3 (25, 38, 29) |
| s02va `final` | 3/3 | 2/3 | 3/3 | 3/3 (22, 29, 29) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 | 3/3 (30, 28, 42) |
| s02vc `final` | 2/3 | 3/3 | 1/3 | 1/3 (—, 26, —) |
| s02vc `dynamic` | 0/3 | 2/3 | 2/3 | 0/3 |
| s03 `final` | 3/3 | 3/3 | 1/3 | 1/3 (38, —, —) |
| s03 `dynamic` | 2/3 | 0/3 | 1/3 | 2/3 (—, 43, 59) |
| **total** | **21/30** | **20/30** | **19/30** | **16/30** |
| s02 | 16/24 | 17/24 | 17/24 | 13/24 |
| s03 | 5/6 | 3/6 | 2/6 | 3/6 |

What the runs say (scratch `batch_check.py`, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R64_ref_a93`):
- **Renderer and identity:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30); every `run.json` carries
  `a93`, `8cc0bfc63d4e`, git `62bee17`, `:8007`.
- **s02 13/24.** The survey started in 22 of 24 runs by step 8. **Stations given up in transit: 5, in 4 runs,
  each at the sixth step** (s02a `final` 2 both stations, no look at all, lost; s02c `final` 1 and 3 the first
  station, lost; s02vc `dynamic` 2 the first, lost): the pattern R63 was built against. The other losses: s02a
  `dynamic` 1 (second station through at 33, done 44), s02a `final` 1 (through from 2, look, done 18), s02c
  `final` 2 (two stations looked, through at 40, done 47), s02vc `dynamic` 1 and 3 (through, check, second
  station, done at 23 and 38), s02vc `final` 1 (two stations, done at 41) and 3 (no survey, latch at 30). No
  won run latched before crossing.
- **s03 3/6.** `dynamic` 2 and 3 won through the latch (read 18, latch 23, goal 43; read 17, latch 22, goal
  59); `dynamic` 1 read at 29, never latched, 9 turn-arounds in a row (tagged `spin_failure`); `final` 1 by the
  open tine (38); `final` 2 read 28, latched 36, not through; `final` 3 crossed at 48 by the open tine and
  wandered the chamber (min x −22, tagged `failed_goal_identification`). Every s03 run was in the stem by
  step 4 (no lobby stall).
- **Walls in flight:** missed 19.9% (174/873), phantom 12.6% (760/6037), s03 phantom 14.9% (R61: 21.0 /
  10.4 / 12.4): within 2.5 points. Longest turn-around streak 9.
- **Goal reports:** 197 in 30 runs; 38 with no line of sight (1.3 a run), 19 dropped; the 21 kept were taken.
- **Labels** (`labels.csv`, Claude review): 16 success, 13 replan_failure, 1 timeout; tags spin_failure (s03
  `dynamic` 1), failed_goal_identification (s03 `final` 3).

**Manipulation check.** Renderer and identity: held. Walls within 4 points of R61: held. The survey in at least
19 of 24 s02 runs by step 8 (22): held. A route on at least 95% of steps (30 of 30): held.

**Not citable.** Host round, three seeds per cell. Host: sctsvr6, lanes 9–12 of twelve (`~/asep-r62-l9..12`) on
a copy of `:8004` on GPU 4 (`:8007`), beside R62 on `:8004` and R63 on `:8006`; Godot on GPU 5
(`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `62bee17` on 2026-11-07,
05:17–06:09 UTC, by Claude alone overnight (OVERNIGHT_PROMPT.md). **30/30 valid.** Labels: Claude review, not
yet confirmed by the operator. Frames stay on the host.

**Reading.** Four flights of one agent on one renderer: 19, 20, 21, 16. The low one is made of the same
pieces as the others (stations given up at the sixth step, surveys that end without crossing), only more of
them; nothing in the host or the renderer differs (walls, reports, renderer lines all as before). It is the
bar for R62 and R63, as the rule says; the reading of those two notes that this bar is the low end of
`a93`'s range.
