# R56 a94 (a93 with the latch fired by one square read and from the line's departure) on the ten contested cells, seeds 1-3: summary

**a94 20/30 against the reference lane's 20/30 (R58, `a93`, same batch, same renderer): a draw, not
carried. s03 4/6 against 3/6, with s03 `dynamic` 2/3 (`a93` on H100 frames: 1/3, 0/3; on lavapipe 1/3),
both wins through the latch at 25 and 28; s02 16/24 against 17/24. The hypothesis held as written
(at least as many runs as the reference, the gain on s03 `dynamic`), but the gain is one cell and the
total is level. The latch fired 4 to 6 steps after the first square closed read in every run that
latched (`a93` in the same batch: 5 and 33).**

| cell | `a93` (R58, reference) | `a93` (R54) | `a93` (R53) | `a94` (R56), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 3/3 | **3/3** (27, 25, 26) |
| s02a `dynamic` | 2/3 | 2/3 | 1/3 | 2/3 (—, 44, 51) |
| s02c `final` | 2/3 | 1/3 | 3/3 | 1/3 (24, —, —) |
| s02c `dynamic` | 1/3 | 3/3 | 3/3 | 1/3 (—, 30, —) |
| s02va `final` | 2/3 | 3/3 | 2/3 | 2/3 (28, —, 30) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 | 3/3 (29, 29, 23) |
| s02vc `final` | 3/3 | 1/3 | 2/3 | 2/3 (—, 27, 35) |
| s02vc `dynamic` | 2/3 | 2/3 | 3/3 | 2/3 (—, 32, 31) |
| s03 `final` | 3/3 | 1/3 | 3/3 | 2/3 (22, —, 50) |
| s03 `dynamic` | 0/3 | 1/3 | 1/3 | **2/3** (—, 59, 49) |
| **total** | **20/30** | **19/30** | **24/30** | **20/30** |
| s02 | 17/24 | 17/24 | 20/24 | 16/24 |
| s03 | 3/6 | 2/6 | 4/6 | 4/6 |

Against the predictions (README): reference +0 to +3 predicted, +0 landed; s03 `dynamic` 1–2 of 3 (2);
s03 `final` within 1 of the reference (2 against 3); s02 within 2 (16 against 17).

What the runs say (scratch `batch_check.py`, the step traces, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R56_latch_line`):
- **The latch fired as laid out.** Three s03 runs latched: `dynamic` 2 read the shut door at 22, latched at
  28, was out and across at 56, goal at 59; `dynamic` 3 read at 19, latched at 25, across at 46, goal at 49;
  `dynamic` 1 read at 38, latched at 42, out by 48, no time left (the drone had turned back at step 10 at
  x = 5.9 and flown up the stem to x = 16 and back, steps 10 to 24). Gaps of 4, 6 and 6 steps; every latch
  at the shut door's end of the tine. Two s03 runs read a closed door in the centre strips and did not
  latch: `final` 2 read it once at step 14 from the mouth of the open tine, heading 158, 1.5 m in, and spent
  the run in the crossbar (x 1.5 to 9.8, lost); `final` 3 read it at 48, two steps after crossing at 46
  (won at 50). `final` 1 went by the open tine at 22.
- **s02 16/24.** The survey started in 23 of 24 runs by step 8; the one without (s02vc `final` 3) was won
  at 35. Losses: s02a `dynamic` 1 (first station, through at 14, look again 24, done 28, never across), s02c
  `dynamic` 1 (second station done at 32) and 3 (second station done at 36, latch at 38), s02c `final` 2
  (through at 6, done 28, latch 31, crossed at 53 too late) and 3 (first station given up at 18, second done
  at 28), s02va `final` 2 (look from 18, done 22, latch 25, crossed at 59), s02vc `dynamic` 1 (second station
  done at 24, latch 26), s02vc `final` 1 (survey from step 8 with one station, done at 23, latch 37). **No
  latch before crossing in a won s02 run** (`a93` R58: one). Five lost s02 runs latched in the hall after
  their survey ended (`a93` R58: none of its 7 losses did); whether the latch cost or merely marked those runs
  the record cannot say: all five had ended their survey without crossing.
- **Walls in flight:** missed 19.7% (156/793), phantom 11.1% (615/5562), s03 phantom 13.5% (R58: 20.2 / 10.5
  / 12.7): within 4 points. Longest turn-around streak 3.
- **Goal reports:** 213 in 30 runs; 39 with no line of sight (1.3 a run), 13 dropped (33%); 0 of 174 made
  with a line of sight dropped. The 26 blind reports kept raised a tag each, taken 26 times.
- **Labels** (`labels.csv`, Claude review): 20 success, 7 replan_failure, 3 timeout. No tags.

**Manipulation check.** Every `run.json` carries `a94`, `3ac7eac6e09d`, git `755a89d`, `:8004`; every
`godot.log` names `NVIDIA H100 PCIe`: held.
- Gap from the first square closed read to the latch at most 9 steps in at least 7 s03 runs, longest under
  22: **3 of 3 that latched were within 6 steps, none over 6; but only 5 runs read a door and 2 of those did
  not latch** (a read from the open tine's mouth; a read after the crossing). As written the check assumed 10
  runs with a read; on what flew it held where it applied.
- No latch in the open tine or the stem: held (all three at the shut door).
- A latch before crossing in at most 2 won s02 runs: held (0).
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8 (23); a route on at least 95% of steps (30
  of 30 at 100%); walls within 4 points of R58's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 1–4 of twelve (`~/asep-r56-l1..4`)
on `:8004`, four lanes to the instance, beside R57 on `:8006` and R58 on `:8007`; Godot on GPU 5
(`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `755a89d` on 2026-11-07,
02:52–03:37 UTC, by Claude alone overnight (OVERNIGHT_PROMPT.md). Shakedown: 4 runs at `c403f7b` (the
latch's first form: s03 `final` 1 lost with a latch at 31 after a read at 13, which led to the axis and span
change) and 4 at `755a89d` (3 won; s03 `dynamic` 1 read the door at 54, latched at 59). **30/30 valid**, no
attempt beyond the first. Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** The mechanism did what it was built to do: every latch came within six steps of the first
square read, and two of three s03 `dynamic` runs were won through it, the cell's best on any renderer for
this family. The total is level with the reference because s02 gave one back (16 against 17, inside the
flight-to-flight spread) and s03 `final` lost one to a drone that never entered the shut tine. The latch's
reach is bounded: it needs the drone at the shut door, and two s03 losses this flight (an excursion back
up the stem for 14 steps; a run spent in the crossbar) never got there. By the rule a draw; `a94`'s latch
is carried into the next batch's combination with `a95`'s survey start (R59), since the two changes touch
different sites.
