# R52 a92 (a91 with the survey's stations held for 12 steps) on the ten contested cells, seeds 1-3: summary

**a92 20/30; a85 23/30 (R45, the bar), a89 23/30 (R49), a91 19/30 (R51), a66 15/30 (R32P). The
hypothesis did not hold: s02c `final`, the cell the change was aimed at, is 1/3 (predicted
2–3), and s02 is 17/24 against `a91`'s 18. s03 3/6. Not carried. The longer wait did what it
was written to do in the one run that called on it; the cell was lost elsewhere, in two runs
that never started a survey.**

| cell | `a66` (R32P) | `a85` (R45) | `a91` (R51) | `a89` (R49) | `a92` (R52), steps to the goal |
|---|---|---|---|---|---|
| s02a `final` | 2/3 | 3/3 | 3/3 | 2/3 | 3/3 (38, 18, 41) |
| s02a `dynamic` | 2/3 | 3/3 | 2/3 | 3/3 | 3/3 (42, 25, 37) |
| s02c `final` | 1/3 | 1/3 | 0/3 | 2/3 | 1/3 (—, 31, —) |
| s02c `dynamic` | 0/3 | 3/3 | 2/3 | 3/3 | 1/3 (43, —, —) |
| s02va `final` | 2/3 | 3/3 | 2/3 | 3/3 | 3/3 (28, 42, 23) |
| s02va `dynamic` | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 (30, 30, 39) |
| s02vc `final` | 1/3 | 1/3 | 3/3 | 2/3 | 2/3 (23, 32, —) |
| s02vc `dynamic` | 2/3 | 2/3 | 3/3 | 3/3 | 1/3 (59, —, —) |
| s03 `final` | 3/3 | 3/3 | 1/3 | 1/3 | 2/3 (48, —, 33) |
| s03 `dynamic` | 0/3 | 1/3 | 0/3 | 1/3 | 1/3 (—, 60, —) |
| **total** | **15/30** | **23/30** | **19/30** | **23/30** | **20/30** |
| s02 | 12/24 | 19/24 | 18/24 | 21/24 | 17/24 |
| s03 | 3/6 | 4/6 | 1/6 | 2/6 | 3/6 |

Against the predictions (README): 19–27 predicted, 20 landed. s02c `final` 1/3 (2–3: missed),
the other seven s02 cells 16/21 (16–19), s03 3/6 (1–5).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- **The change, where it was called on.** s02c `final` seed 2: survey from step 2, the first
  station reached at step 14, twelve steps later (under `a91`'s rule it would have been given
  up at 8, as it was in R51), a look, the door flown at from 18, through at 23, solved at 31.
  One other station was held past six steps and then given up at twelve (s02vc `dynamic` 1,
  solved at 59). A first station was given up in transit in 1 of 19 surveys (R51: 2 of 19;
  R47: 4 of 19).
- **Where s02c `final` was lost.** Seeds 1 and 3 never started a survey and were latched in
  the hall at steps 17 and 15. R51 and R49 started one in all three runs of this cell. The
  start is decided by what the perceiver reads in the centre strip in the first few steps;
  this round did not touch it.
- **The survey started in 19 of the 24 s02 runs and 15 of the 19 were won** (R49: 20 of 21;
  R51: 14 of 19). All four lost were c-site `dynamic` runs (s02c 2 and 3, s02vc 2 and 3), and
  three of the four had a single station, on the right: the left station, the open door's
  side on these sites, had been shut by `a86`'s rule before the survey began.
- **That is evidence for `a87`'s station guard, which `a91` and `a92` leave out.** With the
  guard (`a89`, R49) every survey had both stations and the c-site `dynamic` runs were 6/6;
  without it, R51 and R52 had a single station in 10 of 38 surveys and were 5/6 and 2/6 on
  those cells. Five single-station surveys were on c sites and four of them were lost. R51's
  and R49's summaries did not see this: R51 alone had one such loss.
- **Six latches in s02**, five of them in lost runs, all after a survey had ended or in a run
  with none (steps 15 to 28); the sixth in the far room of a run that was solved. The
  reopening fired twice, in one lost s02 run.
- **s03 3/6.** The first step in a tine: 53, 20, 17 (`dynamic`) and 37, 19, 22 (`final`).
  Solved: `final` 1 and 3 by the open tine (48, 33) and `dynamic` 2 on the last step (door
  shut at 22, latch at 28, out at 35). Lost: `dynamic` 1 (53 steps in the lobby), `dynamic` 3
  and `final` 2 (latched 6 and 9 steps after the door shut or the tine was entered, out 10
  and 4 steps later, not through the other tine in time).
- **The sentence** was said 4 times, all inside a latched corridor, and taken 4 times.
- **Walls in flight** (`eval/r28_flight.py`): missed 14.7% (91/617), phantom 8.8% (530/5993),
  s03 phantom 10.6% (R45 20.9 / 9.2 / 12.2): missed walls 6 points under R45's, the lowest
  of the night. Longest turn-around streak 3.
- **Labels** (`labels.csv`, Claude review): 20 success, 9 replan_failure, 1 timeout (s02vc
  `final` 3, through at 55). No tags.

**Manipulation check.** Every `run.json` carries `a92`, `8e5bcc8a5c74`, git `c16d989`.
- A first station given up in transit in at most 2 s02 runs: 1. Held.
- In the s02c `final` runs with a survey, a look from the first station in at least 2 of 3:
  one run had a survey, and it looked from its first station. Not met as written.
- The survey starts in at least 18 of the 24 s02 runs: 19. A route on at least 95% of steps:
  30 of 30. The sentence on no step without a latch: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r52-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). Each
lane started as its R49 lane ended (09:43–09:52 UTC), so the first runs flew beside R49's
last; no other client after that. Flown at `c16d989` on 2026-11-06, 09:43–10:30 UTC, by
Claude alone on the overnight instruction; the operator was asleep; the last flight of the
night. **30/30 valid**, no attempt beyond the first. Labels: Claude review, not yet confirmed
by the operator. Frames stay on the host.

**Reading.** 20 against `a91`'s 19 is no difference, and the cell aimed at did not move. The
round's use is what it adds to R51 and R49 taken together: the survey agents without the
station guard lose c-site `dynamic` runs to a single station on the wrong side (four of five
such surveys), and the one with the guard did not have any. That is three flights, one seed
set, and a pattern found after the fact; it is the best-supported pointer the night leaves
for s02, and it says the agent to build on is `a89`, with `a92`'s longer wait added if a
round wants it (it cost nothing visible here: one station held to twelve steps and given up).
