# R44 a84 (a66 with the wall survey and the dead-end latch) on the ten contested cells, seeds 1-3: summary

**a84 18/30, a66 15/30 (R32P): +3, at the rule's threshold, so `a84` is carried forward and is
the bar for the rounds after it. The gain is all in s03: 5/6 against 3/6, with s03 `dynamic`
solved twice (47 and 46 steps), the first scored solves of that cell in Phase 2 (0/58 before).
s02 is 13/24 against 12/24, a draw: the survey won the out-of-view sites and lost the in-view
ones.**

| cell | `a66` (R32P) | `a79` (R39) | `a84` (R44), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 2/3 (37, —, 19) |
| s02a `dynamic` | 2/3 | 1/3 | **3/3** (52, 40, 27) |
| s02c `final` | 1/3 | 2/3 | **2/3** (29, 60, —) |
| s02c `dynamic` | 0/3 | 0/3 | **1/3** (—, —, 45) |
| s02va `final` | 2/3 | 2/3 | 2/3 (39, 44, —) |
| s02va `dynamic` | 2/3 | 1/3 | 2/3 (23, —, 37) |
| s02vc `final` | 1/3 | 3/3 | 1/3 (—, 49, —) |
| s02vc `dynamic` | 2/3 | 2/3 | 0/3 |
| s03 `final` | 3/3 | 2/3 | 3/3 (58, 30, 57) |
| s03 `dynamic` | 0/3 | 0/3 | **2/3** (—, 47, 46) |
| **total** | **15/30** | 15/30 | **18/30** |
| s02 | 12/24 | 13/24 | 13/24 |
| s03 | 3/6 | 2/6 | 5/6 |

Against the predictions (README): 17–24 predicted, 18 landed. s02 13/24 (predicted 14–20:
one under), s03 `final` 3/3 (2–3), s03 `dynamic` 2/3 (1–2: at the top).

What the runs say (`eval/probes/a79_check.py`, `eval/probes/a80_check.py`):
- **The latch carried s03.** It fired in 5 of the 6 s03 runs, each time in the shut tine with
  the tine's axis.

  | Run | Door shut | Latch | Out of the tine | Result |
  |---|---|---|---|---|
  | `dynamic` 2 | step 18 | 23 | 27 | solved, 47 |
  | `dynamic` 3 | 17 | 22 | 28 | solved, 46 |
  | `dynamic` 1 | 36 | 47 | never (13 steps left) | lost in the shut tine; 35 steps before the tine |
  | `final` 1 | from load | 34 | 38 | solved, 58 (shut tine first) |
  | `final` 3 | from load | 22 | 32 | solved, 57 (shut tine first) |
  | `final` 2 | from load | none | — | solved, 30 (open tine first) |

  Five steps from the door shutting to the latch in the two `dynamic` wins (R39's `a79`: ten,
  25 and never). Both `final` runs that went down the shut tine first were brought back and
  solved; those are the runs `a66` loses in that cell (Round F seed 1, R35 seed 1).
- **The survey started in 22 of the 24 s02 runs** (step 2–5) and in no s03 run. Where the open
  door is out of view from the way in (s02a, s02c) it scored 8/12 against R32P's 5/12; where it
  is in view (s02va, s02vc), 5/12 against 7/12.
- **s02vc 1/6** is the fault the shakedown showed and the gate row that was waived: the door
  is read from far, flown at, and the reads that would correct the aim lie more than 40° off
  the approach axis and are dropped. Five of the six s02vc runs began a through phase by step
  10; one crossed during it.
- **Six of the 13 s02 wins crossed during the survey or within three steps of it**; the other
  seven crossed 9 to 41 steps after it had ended, on `a66`'s route. In s02c the survey's first
  station was not flyable on the map in four runs of six (`order` one side only) and it ended
  by step 11.
- **A latch in the s02 hall in 6 runs**, 3 of them won. One is plainly harmful: s02va
  `dynamic` 2, the hall in front of the shut door latched at step 15, the drone out at 28, the
  run lost. `a86` (R46) keeps the latch off the direct line.
- **s03 `dynamic` 1** spent 35 steps before the tine (the lobby and the crossbar); the latch
  came 11 steps after the door shut, with 13 left.
- **Walls in flight** (`eval/r28_flight.py`): missed 19.9% (181/910), phantom 11.0%
  (703/6385), s03 phantom 14.0% (Round F 16.7 / 12.4 / 15.9): inside the 4-point window.
  Longest turn-around streak 7 (s02vc `dynamic` 3).
- **Labels** (`labels.csv`, Claude review): 18 success, 11 replan_failure, 1 timeout (s02vc
  `dynamic` 1, through at step 57). `spin_failure` on s02vc `dynamic` 3 (streak 7).

**Manipulation check.** Every `run.json` carries `a84`, `58e76b4b2054`, git `eb80c0f`.
- Survey starts in at least 18 of 24 s02 runs and no s03 run: 22 and 0. Held.
- No survey waypoint more than five steps after a crossing: **failed in 3 runs** (s02va
  `dynamic` 1, `final` 1 and 2: back in the look phase after the drone was through; all three
  solved). `a85` and `a86` change this.
- At least half the s02 wins cross during or within 3 steps of the survey: **6 of 13.** Failed
  by one.
- A latch within 9 steps of the door shutting in every s03 run that stays in the shut tine:
  2 of 3 `dynamic` (5, 5 and 11 steps). Out within 8 steps: 3 of the 4 that got out (4, 6, 4,
  10). Mostly held.
- A route on at least 95% of steps: 29 of 30 runs (s02vc `dynamic` 2: 49/60). Walls within 4
  points. Held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r44-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). A fifth
client flew beside them from 05:39 to 05:58 UTC (R45's shakedown) and from 06:03 (R46's), and
from about 06:19 the lanes that had finished flew R45's first runs beside the last of these.
Flown at `eb80c0f` on 2026-11-06, 05:33–06:22 UTC, by Claude alone on the overnight
instruction; the operator was asleep. **30/30 valid**, no attempt beyond the first. One row of
the shakedown gate was waived before the flight (README, Outcome). Labels: Claude review, not
yet confirmed by the operator. Frames stay on the host.

**Reading.** The hypothesis held in half: the latch takes the drone out of the shut tine in
time (s03 5/6, the cell that was 0/58 at 2/3), and the survey finds the door where it cannot
be seen from the way in, but flies badly at a door it has seen from far. +3 on 30 runs is the
threshold, not a margin (Fisher p about 0.6); the s03 `dynamic` cell is the part that would
be hard to get by chance. By the rule set before the flight `a84` is carried: it is the best
agent on this screen, and R45 (`a85`) and R46 (`a86`) build on it. `a66` is still the only
agent with a 90-run measurement.
