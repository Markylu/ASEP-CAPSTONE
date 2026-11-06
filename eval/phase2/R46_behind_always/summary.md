# R46 a86 (a85 with the route-behind sentence always and the latch off the survey's ground) on the ten contested cells, seeds 1-3: summary

**a86 21/30, a85 23/30 (R45), a84 18/30 (R44), a66 15/30 (R32P): a draw with the bar, two
under it. The hypothesis did not hold as written: s03 went to 5/6 (R45 4/6), s02 fell to
16/24 (R45 19/24). The sentence was taken every time it was said, 98 of 98, and that is part
of the trouble in s02: the survey started in 15 of the 24 s02 runs (R45: 23), 5 of the 9 runs
without one were lost, and 5 of the 9 had been told at steps 0 to 2 that their route was
behind them. `a86` is not carried; `a85` stays the bar.**

| cell | `a66` (R32P) | `a84` (R44) | `a85` (R45) | `a86` (R46), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 3/3 | 3/3 (22, 22, 32) |
| s02a `dynamic` | 2/3 | 3/3 | 3/3 | 1/3 (—, —, 46) |
| s02c `final` | 1/3 | 2/3 | 1/3 | 1/3 (26, —, —) |
| s02c `dynamic` | 0/3 | 1/3 | 3/3 | 2/3 (25, 30, —) |
| s02va `final` | 2/3 | 2/3 | 3/3 | 3/3 (22, 29, 28) |
| s02va `dynamic` | 2/3 | 2/3 | 3/3 | 2/3 (23, 25, —) |
| s02vc `final` | 1/3 | 1/3 | 1/3 | 1/3 (—, —, 50) |
| s02vc `dynamic` | 2/3 | 0/3 | 2/3 | **3/3** (26, 31, 32) |
| s03 `final` | 3/3 | 3/3 | 3/3 | 3/3 (28, 31, 33) |
| s03 `dynamic` | 0/3 | 2/3 | 1/3 | 2/3 (57, —, 60) |
| **total** | **15/30** | **18/30** | **23/30** | **21/30** |
| s02 | 12/24 | 13/24 | 19/24 | 16/24 |
| s03 | 3/6 | 5/6 | 4/6 | 5/6 |

Against the predictions (README): 18–24 predicted, 21 landed. s02 `final` 8/12 and s02
`dynamic` 8/12 (8–10 each), s03 `final` 3/3, s03 `dynamic` 2/3 (1–2).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- **The sentence works on the navigator, and too well.** The turn-around was taken on 98 of
  the 98 steps the sentence was said (s03 26 of 26, s02 72 of 72; R39: 66% and 68%). The
  route's turn-arounds are not all sound: in s02a `dynamic` seed 2 the frame at step 1 had
  every strip blocked, the tag sat on the turn-around, the drone turned its back on the wall
  and never read the shut door in the centre strip; s02c `final` seed 3 drifted at heading 160
  the same way. `a85`'s navigator flew on past such tags; `a86`'s was told to take them.
- **Fewer surveys, and the runs without one lose.** The survey started in 15 of the 24 s02
  runs (R45: 23). Of the 9 without one, 5 were lost (s02a `dynamic` 2, s02c `dynamic` 3, s02c
  `final` 3, s02vc `final` 1 and 2) and 4 found a door on the route (s02a `final` 1, s02c
  `dynamic` 2, s02va `final` 1, s02vc `final` 3 at 50). Of the 15 with one, 12 were won, all
  12 crossing while the survey ran, at steps 13 to 37 (median 17).
- **What the sentence accounts for, counted on the record.** A step is on the first way in
  while no survey has started, no corridor is latched and the drone has never been more than
  2.5 m off the direct line (so a survey could still start). 5 of the 72 s02 sentences fell
  there, all at steps 0 to 2, one in each of 5 of the 9 runs without a survey (s02a `dynamic`
  2, s02c `dynamic` 2 and 3, s02vc `final` 2 and 3; three of the five lost). Of the other
  four, two flew straight to an open door and won (s02a `final` 1, s02va `final` 1) and two
  left the line with no sentence said and lost (s02c `final` 3, s02vc `final` 1): the
  sentence does not explain those. In s03, 10 of the 26 sentences fell on the way in (the stem
  lies on the direct line), one of them before step 8.
- **The three lost with a survey.** s02a `dynamic` 1 took both stations and crossed at 54
  (`timeout`). s02c `final` 2 had one station only, ended its survey at 15 and was latched
  along the wall at 25 (the one run with a route on under 95% of steps, 53/60). s02va
  `dynamic` 3 flew at a doorway read from the start, met the wall at step 19 and ended at 23
  without a second station.
- **The survey's second look (`relook_steps`) did what it was for**: no survey ended on the
  5 m rule; 8 of the 12 winning surveys took a second look at the wall they had come through
  and ended there.
- **Latches in s02: three, all in lost runs, none while a survey ran, none on the direct
  line.** s02c `final` 2 (step 25, ten steps after its survey ended), s02vc `final` 1 (step
  13, lane 2.7 m off the line) and s02vc `final` 2 (step 23, 4.8 m off): the last two in runs
  whose survey never started, so the hold-back had nothing to hold.
- **s03 5/6.** `final` 3/3 by the open tine at 28, 31 and 33 (R45: 40, 30, 31). `dynamic`
  2/3: seed 1 solved at 57 (door shut at 20, latch at 27, out at 33, through the other tine's
  door at 54) and seed 3 at 60, on the last step (shut 15, latch 21, out 25). Seed 2 reached
  the tine at step 28 (door shut 31, latch 37, out 42) and ran out of steps. The first step
  in a tine: 18, 28, 12 (`dynamic`), 17, 16, 22 (`final`); R45: 19, 37, 12, 25, 15, 19.
- **Walls in flight** (`eval/r28_flight.py`): missed 20.4% (133/652), phantom 9.3% (507/5438),
  s03 phantom 11.7% (R45 20.9 / 9.2 / 12.2; Round F 16.7 / 12.4 / 15.9).
- **Labels** (`labels.csv`, Claude review): 21 success, 8 replan_failure, 1 timeout. No tags.

**Manipulation check.** Every `run.json` carries `a86`, `cd6b8de756ab`, git `071cc62`.
- The sentence on every step with the tag on the turn-around, and the turn-around taken on at
  least 85% of them: 98 of 98. Held.
- s03: the first step in a tine at 25 or before in at least 5 of the 6 runs: 5 of 6. Held.
- No latch within 2.5 m of the direct line, none while a survey ran: held (three s02 latches,
  2.7 to 7.9 m off, after the survey or in a run without one).
- R45's survey rows: starts in at least 18 of 24 s02 runs: **15. Failed.** No s03 run: held.
  At least half the s02 wins crossing during the survey: 12 of 16. Held.
- A route on at least 95% of steps: 29 of 30 runs. Failed in one (s02c `final` 2).

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r46-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). Each
lane started as its R45 lane ended (06:49–07:03 UTC), so the first runs flew beside R45's
last; a fifth client flew beside them from 07:08 to 07:36 UTC (R48's unscored shakedown);
from about 07:25 the lanes that had finished flew R47 beside the last of these. Flown at
`071cc62` on 2026-11-06, 06:49–07:50 UTC, by Claude alone on the overnight instruction; the
operator was asleep. **30/30 valid**, no attempt beyond the first. Labels: Claude review, not
yet confirmed by the operator. Frames stay on the host.

**Reading.** 21 against 23 is inside the noise of 30 runs on three seeds, and the round is a
bundle (the sentence, the latch guards, the second look), so the score alone does not say
which part did what. The record does: the sentence moved s03 the way it was meant to (the
drone is in a tine sooner, two of three `dynamic` runs solved) and cost s02 its survey in
up to five runs (nine had none; five were told to turn on the way in). The two can be had apart, since inside a latched corridor `a85` already says the
sentence. R49 (`a89`) is that: `a88`'s planner with `a85`'s navigator. R47 (`a87`) and R48
(`a88`), laid out before this round landed, carry `a86`'s sentence and should be read with
that in mind.
