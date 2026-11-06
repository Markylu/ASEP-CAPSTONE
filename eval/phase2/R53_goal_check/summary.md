# R53 a93 (a89 with goal reports off the line to the goal dropped) on the ten contested cells, seeds 1-3: summary

**a93 24/30: one above the bar `a85` (R45, 23/30) and `a89` (R49, 23/30), a draw by the rule;
`a66` 15/30 (R32P). The hypothesis held as written: at least 23, s03 3 of 6 or better (4), s02
19 or better (20). s03 `final` 3/3 (`a89` 1/3); every s03 run was in the stem by step 5, where
13 of the 42 s03 runs of R44 to R52 were not by step 6; the two seed-1 s03 runs, lost in 9 of
14 flights before, were both won. s02 is 20/24 (`a89` 21). R54, the same agent on H100 frames
flown beside it, is read in its own summary; the two together are this agent's 60 runs.**

| cell | `a66` (R32P) | `a85` (R45) | `a89` (R49) | `a93` (R53), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 2/3 | 3/3 | 2/3 | 3/3 (42, 18, 35) |
| s02a `dynamic` | 2/3 | 3/3 | 3/3 | 1/3 (47, —, —) |
| s02c `final` | 1/3 | 1/3 | 2/3 | **3/3** (55, 41, 23) |
| s02c `dynamic` | 0/3 | 3/3 | 3/3 | 3/3 (25, 31, 32) |
| s02va `final` | 2/3 | 3/3 | 3/3 | 2/3 (32, —, 26) |
| s02va `dynamic` | 2/3 | 3/3 | 3/3 | 3/3 (33, 32, 31) |
| s02vc `final` | 1/3 | 1/3 | 2/3 | 2/3 (28, 28, —) |
| s02vc `dynamic` | 2/3 | 2/3 | 3/3 | 3/3 (28, 28, 27) |
| s03 `final` | 3/3 | 3/3 | 1/3 | **3/3** (26, 48, 40) |
| s03 `dynamic` | 0/3 | 1/3 | 1/3 | 1/3 (60, —, —) |
| **total** | **15/30** | **23/30** | **23/30** | **24/30** |
| s02 | 12/24 | 19/24 | 21/24 | 20/24 |
| s03 | 3/6 | 4/6 | 2/6 | 4/6 |

Against the predictions (README): 22–27 predicted, 24 landed; s03 `final` 3 (2–3), s03
`dynamic` 1 (1–2), s02 20 (19–22).

What the runs say (`eval/probes/a93_goal_check.py --folders R53_goal_check`,
`eval/probes/a79_check.py`, `eval/probes/a80_check.py`, `eval/r28_flight.py`):
- **The check fired as laid out.** 246 goal reports in 28 runs; 32 made with no line of sight
  (1.1 a run; R44 to R52: 1.2), 14 of them dropped (44%; on the record 43%). Of the 214 made
  with a line of sight, 5 were dropped (2.3%; the limit was 3%, the record 1.0%), all in won
  runs (s02c `dynamic` 1 and 3, s02c `final` 2 twice, s02va `final` 1; 27° to 42° off, the
  goal 4 m or more away). No goal tag stood on a step whose report was dropped; the 18 blind
  reports kept raised a tag each, and the navigator took all 18.
- **s03: the lobby is no longer where runs are lost.** In s03 `dynamic` seed 1 the step-2
  "far right" report was dropped (40° off), the move tagged "toward your target" was taken,
  and the drone was in the stem at step 4; in `final` seed 1 the perceiver made no report
  before step 5 this time, and the drone was in the stem at step 4. All six were in the stem
  by step 5 (R44 to R52: 29 of 42 by step 6) and in a tine (x < 7, 3 ≤ |y| ≤ 7, this summary's
  reading) at 19, 40, 18, 14, 16 and 24: five by step 25 (`a89`: four, with 32 and 33).
  `final` seed 1 reached the goal at 26, `dynamic` seed 1 at 60, the last step; across R44
  to R52 the seed-1 s03 runs were 5 of 14.
- **The two s03 losses are in the tines, not the lobby.** `dynamic` seed 2 was in the stem at
  step 4 but in a tine only at 40, the door shut at 44, the latch fired at 50 and the drone was
  out at 59. `dynamic` seed 3: door shut at 22, latch at 32, out at 35, nine steps in the open
  tine, the goal not reached. Not traced further.
- **s02 20/24.** The survey started in 21 of the 24 runs, all by step 4 (`a89`: 21), and 18 of
  the 21 were won; 13 crossed from their first station, all won. s02c `final` is 3/3 for the
  first time (1/3 for `a66`, `a85`, `a86`, `a87`; 2/3 for `a89`): two surveys crossed from the
  first station (18 and 10) and seed 1 from the second (46). The three losses: s02a `dynamic`
  seeds 2 and 3 took the left (door C's side) first, the door being on the right, went
  through from the second station at 30 and 32 and still never crossed the divider (`a89` won
  this cell 3/3, at 54 to 56); s02va `final` seed 2 ended its survey at 22 without crossing;
  s02vc `final` seed 3 never started one. The sentence was said twice, inside latched
  corridors, and taken twice.
- **Walls in flight:** missed 22.5% (148/657), phantom 10.9% (568/5223), s03 phantom 12.4%
  (R49: 20.6 / 9.2 / 13.5). Longest turn-around streak 3.
- **Labels** (`labels.csv`, Claude review): 24 success, 5 replan_failure, 1 timeout. No tags.

**Manipulation check.** Every `run.json` carries `a93`, `8cc0bfc63d4e`, git `2b77083`.
- A report dropped at step 4 or before in both seed-1 s03 runs: **one of two** (`dynamic`
  seed 1 at step 2; `final` seed 1 made no report to drop); both in the stem by step 6: held.
- The first step in a tine by 25 in at least 5 of 6 s03 runs: held (5 of 6).
- No goal tag on any step whose report was dropped: held (0).
- At most 3% of the reports made with a line of sight dropped: held (2.3%).
- Unbroken: the survey in at least 19 of 24 s02 runs by step 8 (21, by step 4); a route on at
  least 95% of steps (30 of 30 at 100%); walls within 4 points of R49's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, **eight lanes on two vLLM
instances** (`~/asep-r53-l1..8`: lanes 1–4 on `:8004`, lanes 5–8 on a copy on GPU 3, `:8006`,
same image, weights and flags; four lanes to an instance), Godot under lavapipe, `Qwen3-VL-30B-A3B`,
remote profile, temperature 0. R54's four lanes flew beside them on a third instance
(`:8007`, H100 frames). Flown at `2b77083` on 2026-11-06, 18:43–19:04 UTC, by Claude on the
operator's instruction ("do one more cycle of the loop"). **30/30 valid**, no attempt beyond
the first. Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.
The first round flown on more than one instance (operator, 2026-11-06).

**Reading.** 24 against 23 is a draw: `a93` does not replace `a85` as the bar, and stands
beside `a85` and `a89` at the top. What the flight does show is the mechanism: the lobby loss
named on 2026-11-06 was one hallucinated report at step 2, and with it dropped every s03 run
went straight down the stem. s03 `final` came back to 3/3; s03 `dynamic` stays at 1/3, lost
now in the tines (a late door, a slow exit), where the latch's timing is. s02 lost one against
`a89` on s02a `dynamic`, the cell where the survey takes the wrong side first, and gained
s02c `final`: two flights, one run apart on those cells. Pooled over this agent's two flights
(R54 on H100 frames, see its summary), the check's reach is what the rule removes, no more:
a run a game. If one agent is to be built on now it is `a93`: it carries `a89` whole, costs
no call, and the only thing it takes from the navigator is a report the planner knows to be
wrong. Next: the survey's first side on the a sites (s02a `dynamic` has now lost 2 under
`a93` and won 3 under `a89` on the second station), and the latch's exit in s03 `dynamic`.
