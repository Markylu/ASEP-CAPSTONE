# R61 a93, batch 2's reference lane on H100 frames, on the ten contested cells, seeds 1-3: summary

**a93 21/30 (s02 16/24, s03 5/6) on H100 frames, flown beside R59 (`a98`) and R60 (`a96`) at the
same commit in the same minutes. The hypothesis held: within the 16–24 predicted; `a93`'s three H100
flights are 19, 20 and 21 (60/90; s02 50/72, s03 10/18). s03 `dynamic` 2/3 after 0/3 in R58: the cell
swings with the flight. s02vc `dynamic` 0/3, a cell this agent won 2/3 in R58 and 3/3 in R53.**

| cell | `a93` (R58, H100) | `a93` (R54, H100) | `a93` (R61), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 2/3 (—, 30, 23) |
| s02a `dynamic` | 2/3 | 2/3 | 2/3 (—, 39, 40) |
| s02c `final` | 2/3 | 1/3 | 2/3 (28, —, 30) |
| s02c `dynamic` | 1/3 | 3/3 | 2/3 (—, 24, 57) |
| s02va `final` | 2/3 | 3/3 | 3/3 (22, 50, 29) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 (28, 28, 23) |
| s02vc `final` | 3/3 | 1/3 | 2/3 (—, 27, 30) |
| s02vc `dynamic` | 2/3 | 2/3 | 0/3 |
| s03 `final` | 3/3 | 1/3 | 3/3 (38, 38, 27) |
| s03 `dynamic` | 0/3 | 1/3 | 2/3 (59, 51, —) |
| **total** | **20/30** | **19/30** | **21/30** |
| s02 | 17/24 | 17/24 | 16/24 |
| s03 | 3/6 | 2/6 | 5/6 |

What the runs say (scratch `batch_check.py`, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R61_ref_a93`):
- **Renderer and identity:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30); every `run.json` carries
  `a93`, `8cc0bfc63d4e`, git `13456b0`, `:8007`.
- **s03 5/6.** `final` 3/3 by the open tine. `dynamic` seed 1 read the shut door at 32 and never latched, yet
  crossed at 55 and reached the goal at 59; seed 2 (the run that never left the lobby in R58) went down the
  stem this time, read at 20, latched at 26, across at 47, goal at 51; seed 3 read at 30, latched at 36, out,
  not through in time. Latch gaps 6 and 6.
- **s02 16/24.** The survey started in 23 of 24 runs by step 8 (the one without, s02a `final` 3, won). **s02vc
  `dynamic` 0/3**: seed 1 through-phase from 7, two relooks, done at 31 without crossing; seed 2 through from
  4, look 19, done 23, a latch in the hall at 43, crossed at 55, 7 turn-arounds in a row (tagged
  `spin_failure`), out of steps; seed 3 through from 6, `check` at 27, second station looked and done at 43.
  Across the batch the cell went 1 of 9 for three agents whose code there is `a93`'s (R58–R56–R57: 6 of 9).
  Other losses: s02a `dynamic` 1 and s02c `dynamic` 1 (second station done at 27 and 19), s02a `final` 1
  (first station's look to 16, done 20), s02c `final` 2 (first station given up at 8, second looked and done
  at 23), s02vc `final` 1 (through at 2, look, second station, through, look, done at 35).
- **Walls in flight:** missed 21.0% (164/782), phantom 10.4% (575/5523), s03 phantom 12.4% (R58: 20.2 / 10.5 /
  12.7): within 1 point. Longest turn-around streak 7 (s02vc `dynamic` 2).
- **Goal reports:** 234 in 30 runs; 39 with no line of sight (1.3 a run; R58 1.1), 20 dropped (51%); the 20
  kept raised a tag each, taken 20 times.
- **Labels** (`labels.csv`, Claude review): 21 success, 7 replan_failure, 2 timeout; tag spin_failure on s02vc
  `dynamic` 2.

**Manipulation check.** Renderer and identity: held. Walls within 4 points of R58: held. The survey in at least
19 of 24 s02 runs by step 8 (23): held. A route on at least 95% of steps (30 of 30 at 100%): held. Blind reports a
run within a third of R58's 1.1 (1.3): held.

**Not citable.** Host round, three seeds per cell. Host: sctsvr6, lanes 9–12 of twelve (`~/asep-r59-l9..12`) on a
copy of `:8004` on GPU 4 (`:8007`), beside R59 on `:8004` and R60 on `:8006`; Godot on GPU 5 (`GODOT_VK=nvidia`);
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `13456b0` on 2026-11-07, 04:03–04:52 UTC, by Claude
alone overnight (OVERNIGHT_PROMPT.md). **30/30 valid**, no attempt beyond the first. Labels: Claude review, not yet
confirmed by the operator. Frames stay on the host.

**Reading.** 19, 20, 21: `a93` on H100 frames sits at 20 with a spread of 1 on the total and a spread of 2 to 3
on every cell; s03 `dynamic` is 0, 1 and 2 of 3 in three flights of identical code. A candidate has to clear 23 on
this renderer to be more than noise, and no change this night did. The s02vc `dynamic` collapse (1 of 9 in this
batch, with the same code that went 6 of 9 the batch before) is the one thing in this batch that looks like more
than a coin: it is in the navigator's hands at the first station (R59 and R61's traces: "toward your target" on
the sharp turn to the station, straight taken for three steps; the door's carrot flown off to the side), not in
the planner, and the morning report names it.
