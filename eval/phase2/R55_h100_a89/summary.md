# R55 a89 again, Godot rendered on an H100 (host round), on the ten contested cells, seeds 1-3: summary

**a89 on H100 frames 18/30, against 23/30 for the same agent on lavapipe's frames (R49): a gap
of 5, below the 19 the README set as the line. s02 15/24 against 21; s03 3/6 against 2. With
R54 (`a93`: 19 on H100 frames, 24 on lavapipe's) that is two agents and two flights, each 5
runs lower on H100 frames, both losses on s02. The hypothesis did not hold: the renderer
costs runs, and rounds flown on H100 frames are read against rounds flown on H100 frames
only. Every reading below the score (renderer, walls, survey, route) held.**

| cell | `a89` R49 (lavapipe) | `a93` R54 (H100) | `a89` R55 (H100), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 3/3 (46, 30, 40) |
| s02a `dynamic` | 3/3 | 2/3 | 2/3 (46, 45, —) |
| s02c `final` | 2/3 | 1/3 | **0/3** |
| s02c `dynamic` | 3/3 | 3/3 | 2/3 (29, —, 25) |
| s02va `final` | 3/3 | 3/3 | 3/3 (26, 36, 30) |
| s02va `dynamic` | 3/3 | 3/3 | 2/3 (—, 23, 31) |
| s02vc `final` | 2/3 | 1/3 | 1/3 (36, —, —) |
| s02vc `dynamic` | 3/3 | 2/3 | 2/3 (46, 28, —) |
| s03 `final` | 1/3 | 1/3 | 2/3 (37, 25, —) |
| s03 `dynamic` | 1/3 | 1/3 | 1/3 (—, 55, —) |
| **total** | **23/30** | **19/30** | **18/30** |
| s02 | 21/24 | 17/24 | 15/24 |
| s03 | 2/6 | 2/6 | 3/6 |

Against the predictions (README): 19–27 predicted, 18 landed; s02 15 (18–22 predicted); s03 3
(1–5). The two H100 flights, `a93` and `a89`, are 37/60 (s02 32/48); the two lavapipe flights
of the same agents, R53 and R49, 47/60 (s02 41/48).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R55_h100_a89`):
- **Renderer:** every `godot.log` names `NVIDIA H100 PCIe` (30 of 30). Every `run.json` carries
  `a89`, `85cda76df25b`, git `c329864`, and its lane's instance (`:8004`, `:8006` or `:8007`).
- **Walls in flight:** missed 20.5% (175/853), phantom 10.0% (593/5917), s03 phantom 12.8%
  (R49: 20.6 / 9.2 / 13.5; R54: 19.2 / 11.5 / 15.5): inside 4 points of both. Longest
  turn-around streak 5 (s02c `dynamic` seed 2, tagged spin_failure).
- **Goal reports:** 198 in 30 runs; 38 with no line of sight (1.3 a run), every one raised a
  tag and the navigator took all 38 (`a89` has no check; `a93`'s rule would have dropped 14
  of the 38 and 1 of the 160 made with a line of sight).
- **s02 15/24.** The survey started in 22 of 24 runs (20 by step 4, one at 7; R49: 21), and 15
  of the 22 were won. **s02c `final` 0/3** (R49 2/3; R53 3/3; R54 1/3): seeds 1 and 3 started
  at step 2, seed 2 at 7, none crossed. The other losses: s02a `dynamic` 3, s02c `dynamic` 2
  (the spin), s02va `dynamic` 1 (no survey, tagged failed_goal_identification), s02vc
  `dynamic` 3, s02vc `final` 2 and 3 (seed 3 with no survey). Not traced further.
- **s03 3/6.** `final` seeds 1 and 2 by the open tine at 37 and 25; `dynamic` seed 2 shut at
  17, latched at 24, out at 25, goal at 55. Lost: `dynamic` seed 1 **28 steps in the shut
  tine before a latch at 58** (the zigzag again: R51 s03 `dynamic` 2, R54 s03 `dynamic` 3);
  `dynamic` seed 3 shut at 30, latched at 36, out at 44, not through; `final` seed 3 latched
  at 21, out at 32, crossed at 58, too late.
- **Labels** (`labels.csv`, Claude review): 18 success, 10 replan_failure, 2 timeout; tags
  spin_failure (s02c `dynamic` 2), failed_goal_identification (s02va `dynamic` 1).

**Manipulation check.**
- Every run on the H100, every `run.json` as above: held.
- Walls within 4 points of R49's and R54's: held.
- The survey in at least 19 of 24 s02 runs by step 8 (22); a route on at least 95% of steps
  (30 of 30 at 100%): held.
- Blind goal reports a run within a third of R49's: not read (R49's count was not taken when
  the README was written; 1.3 a run here, 1.2 across R44 to R52).

**Not citable.** Host round, three seeds per cell. Host: sctsvr6, **twelve lanes on three vLLM
instances** (`~/asep-r55-l1..12`: 1–4 on `:8004`, 5–8 on a copy on GPU 3 `:8006`, 9–12 on a
copy on GPU 4 `:8007`; four lanes to an instance), Godot on GPU 5 (`GODOT_VK=nvidia`),
`Qwen3-VL-30B-A3B`, remote profile, temperature 0. Flown at `c329864` on 2026-11-06,
23:40–23:54 UTC (14 minutes), by Claude on the operator's call ("Yes, fly a89"); no shakedown
(nothing new in code; R54 had just flown 30 valid runs on this path). **30/30 valid**, no
attempt beyond the first. Labels: Claude review, not yet confirmed by the operator. Frames
stay on the host. Copies stopped afterwards.

**Reading.** Two agents, two flights, both 5 runs lower on H100 frames than on lavapipe's,
both on s02 (`a93` 20 → 17, `a89` 21 → 15), s03 unmoved (4 → 2, 2 → 3). The probe of
2026-11-06 found no renderer effect in `g05`'s field agreement on matched frames (76–80%
across against 81–82% within), but the frames do differ on thin edges, and the s02 survey
reads a door at the wall's edge; where the reads shift was not traced here. The rule now:
**H100 frames are for probes, trials and rounds read against H100 rounds; R55 (18) and R54
(19) are that bar, a draw with each other. Rounds read against `a85`/`a89` fly on lavapipe,
where two instances carry eight lanes (R53) at the per-instance load every round has had.**
What would settle more: a third pair on both renderers, or a probe of the survey's door
reads on matched frames; both are the operator's to ask for. Twelve lanes at four to an
instance flew the round in 14 minutes.
