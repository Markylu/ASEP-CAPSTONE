# R54 a93 again, Godot rendered on an H100 (host round), on the ten contested cells, seeds 1-3: summary

**a93 on H100 frames 19/30, against 24/30 for the same agent on lavapipe's frames flown
beside it (R53): a gap of 5, outside the 4 the README allowed. s02 17/24 against 20 (inside
its 3), s03 2/6 against 4. The flight-time readings (walls, goal reports, the survey, the
route) are inside their limits, every run rendered on the H100, and every manipulation check
but the score held. The hypothesis as written did not hold. What that means is in the
reading below: one flight, and the spread this agent family shows between two lavapipe
flights is 4.**

| cell | `a93` R53 (lavapipe) | `a93` R54 (H100), steps to the goal |
|---|---|---|
| s02a `final` | 3/3 | 2/3 (—, 56, 31) |
| s02a `dynamic` | 1/3 | 2/3 (—, 47, 41) |
| s02c `final` | 3/3 | 1/3 (24, —, —) |
| s02c `dynamic` | 3/3 | 3/3 (25, 24, 31) |
| s02va `final` | 2/3 | 3/3 (27, 22, 39) |
| s02va `dynamic` | 3/3 | 3/3 (29, 32, 23) |
| s02vc `final` | 2/3 | 1/3 (31, —, —) |
| s02vc `dynamic` | 3/3 | 2/3 (38, —, 47) |
| s03 `final` | 3/3 | 1/3 (—, —, 50) |
| s03 `dynamic` | 1/3 | 1/3 (58, —, —) |
| **total** | **24/30** | **19/30** |
| s02 | 20/24 | 17/24 |
| s03 | 4/6 | 2/6 |

Six cells moved by one run and two by two (s02c `final`, s03 `final`), four each way on the
s02 cells; s03 `final` went from 3 to 1. Together the two flights are 43/60 for `a93` (s02
37/48, s03 6/12); `a85` and `a89`, one lavapipe flight each, are 46/60 (s02 40/48, s03 6/12).

What the runs say (`eval/probes/a93_goal_check.py --folders R54_h100_frames`,
`eval/probes/a79_check.py`, `eval/probes/a80_check.py`, `eval/r28_flight.py`):
- **Renderer:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30; R53: llvmpipe, 30 of
  30). Every `run.json` carries `a93`, `8cc0bfc63d4e`, git `2b77083`, `:8007`.
- **Walls in flight:** missed 19.2% (148/771), phantom 11.5% (681/5904), s03 phantom 15.5%
  (R53: 22.5 / 10.9 / 12.4): inside 4 points. Longest turn-around streak 3.
- **Goal reports:** 211 in 30 runs; 27 with no line of sight (0.9 a run; R53 1.1), 8 dropped
  (30%; R53 44%); 3 of 184 made with a line of sight dropped (1.6%; R53 2.3%). The 19 blind
  reports kept raised a tag each and the navigator took all 19. The step-2 "far right" report
  that R53's `dynamic` seed 1 dropped was not made on H100 frames in either seed-1 s03 run;
  both were in the stem at step 4 all the same, as all six were by step 5 (tine at 13, 34, 14,
  13, 16, 15).
- **s03 2/6.** Won: `dynamic` seed 1 (door shut at 18, latch at 23, out at 25, goal at 58) and
  `final` seed 3 (latch at 24, out at 29, goal at 50). Lost: `final` seeds 1 and 2 latched at
  35 and 25, out at 38 and 38, not through; `dynamic` seed 2 in the stem at 4 and in a tine
  at 34, door shut at 38, latch at 44, out at 51; **`dynamic` seed 3 spent 33 steps in the
  shut tine with no latch** (the zigzag named on 2026-11-06: R51's s03 `dynamic` seed 2 did
  the same).
- **s02 17/24.** The survey started in 23 of 24 runs by step 4 (R53: 21; `a89`: 21) and 17 of
  the 23 were won. Losses: s02a `final` 1 and s02a `dynamic` 1 (through the door line at 21
  and 45 by the survey's own reckoning, never across the divider), s02c `final` 2 and 3
  (first station 20 and 18 steps in transit, no look through), s02vc `dynamic` 2 and `final`
  2 (surveys ended at 28 and 31, not through), s02vc `final` 3 (no survey). R53 lost s02a
  `dynamic` 2 and 3, s02va `final` 2 and s02vc `final` 3: one cell in common.
- **Labels** (`labels.csv`, Claude review): 19 success, 11 replan_failure. No tags.

**Manipulation check.**
- Every run on the H100, every `run.json` as above: held.
- Walls within 4 points of R53's: held.
- Blind reports a run and the share dropped within a third of R53's: held (0.9 against 1.1;
  30% against 44%, at the edge).
- The survey in at least 19 of 24 s02 runs by step 8 (23); a route on at least 95% of steps
  (lowest 98%): held.
- **The score within 4 of R53's: not held (5).** s02 within 3: held (3).

**Not citable.** Host round (changelog 2026-11-02), three seeds per cell. Host: sctsvr6, four
lanes (`~/asep-r54-l9..12`) on a copy of `:8004` on GPU 4 (`:8007`), alone on it; Godot on GPU 5
(`GODOT_VK=nvidia`, `eval/docker/sweep.sh` at `738a6c3`); `Qwen3-VL-30B-A3B`, remote profile,
temperature 0. Flown at `2b77083` on 2026-11-06, 18:43–19:17 UTC, beside R53's eight lavapipe
lanes, by Claude on the operator's instruction ("do one more cycle of the loop"). **30/30
valid**, no attempt beyond the first. The SSH link from the Mac dropped several times while
the runs were copied back; the copy was repeated until all 30 were whole. Labels: Claude
review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** By the README's own rule the renderer is not cleared: a 5-run gap is outside the
4 allowed, so rounds flown on H100 frames are read against rounds flown on H100 frames, and
the bar has no such flight. What the gap is made of: s03 `final` 3 to 1 (the cell that ranged
1 to 5 of 6 across lavapipe flights of code that did not differ), and four s02 cells one run
each way. Everything measured below the score (walls, reports, the survey, the stem entry)
reads the same on both renderers; the one frame-level difference seen is that the s03 step-2
hallucination did not occur on H100 frames (two runs). One flight each cannot say whether 5
is the renderer or the spread a flight has; the lavapipe-only spread between near-identical
agents was 4 on 2026-11-06 (23, 19, 20). What to do with it is the operator's call: either
H100 frames stay for probes and trials only, or the bar flies once on them (one flight of
`a85` or `a89`, 20 minutes on 12 lanes) and later rounds fly 12 to 24 lanes at a time on
them. Until then, R53 is `a93`'s flight of record and this one is its second sample.
