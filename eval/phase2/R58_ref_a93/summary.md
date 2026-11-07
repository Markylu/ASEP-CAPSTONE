# R58 a93, the batch's reference lane on H100 frames, on the ten contested cells, seeds 1-3: summary

**a93 20/30 (s02 17/24, s03 3/6) on H100 frames, flown beside R56 (`a94`) and R57 (`a95`) at the
same commit in the same minutes. The hypothesis held: within the 15–23 predicted, one above R54's
19 (the same agent on H100 frames the day before), four below R53's 24 on lavapipe. This is the
bar the batch's candidates are read against. s03 `dynamic` 0/3: one run never left the lobby.**

| cell | `a93` (R54, H100) | `a93` (R53, lavapipe) | `a93` (R58), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 3/3 | 2/3 (24, —, 35) |
| s02a `dynamic` | 2/3 | 1/3 | 2/3 (45, 37, —) |
| s02c `final` | 1/3 | 3/3 | 2/3 (—, 28, 32) |
| s02c `dynamic` | 3/3 | 3/3 | 1/3 (—, 26, —) |
| s02va `final` | 3/3 | 2/3 | 2/3 (—, 23, 29) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (29, 28, 29) |
| s02vc `final` | 1/3 | 2/3 | 3/3 (29, 32, 43) |
| s02vc `dynamic` | 2/3 | 3/3 | 2/3 (26, 30, —) |
| s03 `final` | 1/3 | 3/3 | 3/3 (35, 25, 32) |
| s03 `dynamic` | 1/3 | 1/3 | 0/3 |
| **total** | **19/30** | **24/30** | **20/30** |
| s02 | 17/24 | 20/24 | 17/24 |
| s03 | 2/6 | 4/6 | 3/6 |

What the runs say (scratch `batch_check.py`, `eval/r28_flight.py`, `eval/probes/a93_goal_check.py
--folders R58_ref_a93`, the survey timelines):
- **Renderer and identity:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30); every `run.json`
  carries `a93`, `8cc0bfc63d4e`, git `755a89d`, `:8007`.
- **s03 3/6.** `final` 3/3 by the open tine (35, 25, 32), no latch needed. `dynamic` 0/3: seed 1 read
  the shut door at 25 and latched at 58 (the zigzag, 33 steps in the shut tine: R55 `dynamic` 1 did the
  same at the same steps); seed 3 latched at 33 (read 28), out, not through in time; **seed 2 never left
  the lobby**: stopped by a wall at step 4 at x = 15, the route then wandered the lobby for 56 steps (x
  15–23, y −2 to 12), no goal report made, no latch; labelled `pre_change_failure` (min x 15.2).
- **s02 17/24.** The survey started in 22 of 24 runs, all by step 8; the two without one (s02c `final`
  3, s02vc `final` 3) were won by the route and, in s02vc `final` 3, a latch at 29 in the hall and the
  crossing at 35 (the same cell that lost four of four flights with no survey before). Losses: s02a
  `dynamic` 3 and s02a `final` 2 (second station, through phase lost: `th1` → `lo1` → done; `final` 2
  spun 5 turn-arounds in a row, tagged `spin_failure`), s02c `dynamic` 1 (through at 18 by the survey's
  reckoning, never across; timeout) and 3 (station 1, `check`, done at 25), s02c `final` 1 (first station
  given up at 9, second station looked and done at 25), s02va `final` 1 (first station's look to 23, second
  station done at 39), s02vc `dynamic` 3 (second station, done at 36).
- **Walls in flight:** missed 20.2% (138/683), phantom 10.5% (569/5402), s03 phantom 12.7% (R54: 19.2 /
  11.5 / 15.5): within 4 points. Longest turn-around streak 5 (s02a `final` 2).
- **Goal reports:** 227 in 30 runs; 33 with no line of sight (1.1 a run; R54 0.9), 11 of them dropped
  (33%; R54 30%); 2 of 194 made with a line of sight dropped (1.0%). The 22 blind reports kept raised a tag
  each and the navigator took all 22.
- **Labels** (`labels.csv`, Claude review): 20 success, 7 replan_failure, 2 timeout, 1 pre_change_failure;
  tag spin_failure on s02a `final` 2.

**Manipulation check.** Renderer and identity: held. Walls within 4 points of R54: held. The survey in at
least 19 of 24 s02 runs by step 8 (22): held. A route on at least 95% of steps (30 of 30 at 100%): held.
Blind reports a run within a third of R54's 0.9 (1.1): held.

**Not citable.** Host round, three seeds per cell. Host: sctsvr6, lanes 9–12 of twelve (`~/asep-r56-l9..12`)
on a copy of `:8004` on GPU 4 (`:8007`), four lanes to the instance, beside R56 on `:8004` and R57 on
`:8006`; Godot on GPU 5 (`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at
`755a89d` on 2026-11-07, 02:52–03:37 UTC (45 minutes for the three rounds together; the lanes carried 7 to 8
runs each), by Claude alone overnight on the operator's instruction (OVERNIGHT_PROMPT.md, 2026-11-06). **30/30
valid**, no attempt beyond the first. Labels: Claude review, not yet confirmed by the operator. Frames stay on
the host.

**Reading.** `a93` on H100 frames is 19 and 20 in two flights (39/60; s02 34/48, s03 5/12), against 24 on
lavapipe: the renderer's cost holds at about 4 to 5 runs and the two H100 flights agree with each other. The
s03 `dynamic` cell is where this agent loses on this renderer (1/3, 0/3): the late latch (seed 1, 33 steps)
and the lobby (seed 2). R56 and R57 are read against this 20.
