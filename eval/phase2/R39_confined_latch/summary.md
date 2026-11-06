# R39 a79 (a66 with the dead-end latch fired by the trail) on the ten contested cells, seeds 1-3: summary

**a79 15/30, a66 15/30 (R32P): a draw, and s03 `dynamic` 0/3, so the hypothesis did not hold
and `a79` is not carried forward as it is. The latch itself did what it was built for once: in
s03 `dynamic` seed 1 the drone left the shut tine, flew the other one, and was through its
open door into the goal chamber at step 57, the first run of that cell to get there in Phase 2
(0/55), 2.8 m from the goal when the steps ran out. In the other two the trigger came too
late or not at all.**

| cell | `a66` (R32P) | `a66` (F, 5 seeds) | `a79` (R39), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 1/5 | 2/3 (—, 42, 18) |
| s02a `dynamic` | 2/3 | 3/5 | 1/3 (—, 34, —) |
| s02c `final` | 1/3 | 2/5 | **2/3** (49, 45, —) |
| s02c `dynamic` | 0/3 | 1/5 | 0/3 |
| s02va `final` | 2/3 | 4/5 | 2/3 (—, 57, 22) |
| s02va `dynamic` | 2/3 | 4/5 | 1/3 (—, 37, —) |
| s02vc `final` | 1/3 | 1/5 | **3/3** (28, 52, 44) |
| s02vc `dynamic` | 2/3 | 4/5 | 2/3 (38, —, 60) |
| s03 `final` | 3/3 | 4/5 | 2/3 (—, 31, 25) |
| s03 `dynamic` | 0/3 | 0/5 | 0/3 |
| **total** | **15/30** | 24/50 | **15/30** |
| s02 | 12/24 | 20/40 | 13/24 |
| s03 | 3/6 | 4/10 | 2/6 |

Against the predictions (README): 15–18 predicted, 15 landed, at the bottom. s02 13/24
(predicted 10–14), s03 `final` 2/3 (2–3), s03 `dynamic` 0/3 (1–2: missed).

What the runs say (`eval/probes/a79_check.py`):
- **s03 `dynamic`, the cell the round was for: one run through, none solved.**

  | Seed | Door shut | First closed read | Latch | Out of the tine | After |
  |---|---|---|---|---|---|
  | 1 | step 25 | 26 | **35**, axis 180°, mouth x = 2.0 | 40 | crossbar 41–47, other tine 48–56, through its door at 57, 2.8 m from the goal at 60 (`timeout`) |
  | 2 | 20 | 21 | 45 | 54 | 6 steps left; lost in the crossbar |
  | 3 | 25 | 26 | none | — | 35 steps in the shut tine |

  Seed 1 needed two more steps. Seeds 2 and 3 are the trigger's: with a dwell of five steps
  the drone had drifted 1.5 m off the run's axis (seed 3, flying down one wall of a 3 m tine)
  or flown out of the tine and back (seed 2) before the fifth step came. A dwell of three
  would have fired at steps 31 and 26 in those two runs (offline, on their records).
- **The way out is fast when it is taken**: 5 steps from the latch to the mouth in seed 1, 9
  in seed 2. The sentence was said on 3 steps in the round and the turn-around taken on all 3.
- **The latch fired in 7 of the 24 s02 runs, and 5 of them then crossed** (4 solved: s02c
  `final` 1, s02vc `final` 2 and 3, s02vc `dynamic` 3; one through at step 53 and out of
  steps, s02c `final` 3; two never through, s02a `final` 1, s02va `dynamic` 1). The record had
  said it would fire in runs already stuck (13 of 45 lost ones, none of 53 won before a
  crossing); in flight a stuck run with the lane it was stuck in shut went somewhere else,
  and that was the other side of the divider more often than not. s02vc `final` is 3/3
  (R32P 1/3, Round F 1/5), two of the three after a latch. Seven runs: a lead, not a result.
- **s03 `final` 2/3.** Seed 1 never passed the crossbar (min x 5.8): it met the divider's face
  at step 9, the navigator declined the turn-around the route asked for and flew back up the
  stem into the lobby. No latch, no closed door: `a66`'s own loss, and the one this round
  cannot touch.
- **Walls in flight** (`eval/r28_flight.py`): missed 17.5% (195/1116), phantom 9.4%
  (592/6294), s03 phantom 13.1% (Round F 16.7 / 12.4 / 15.9; R32P 21.2 / 11.2 / 15.0): inside
  the window. Longest turn-around streak 3.
- **Labels** (`labels.csv`, Claude review): 15 success, 13 replan_failure, 2 timeout (s03
  `dynamic` 1, s02c `final` 3). No spin tag. The labeller's `failed_goal_identification` on
  s03 `dynamic` 1 (closest approach 2.8 m) was not applied: the run was flying at the goal
  when the steps ran out.

**Manipulation check.** Every `run.json` carries `a79`, `4ef945298c6d`, git `095d9c9`.
- "A latch by step 40 in every s03 run that spends 10 steps in the shut tine": **1 of 3**
  (35; 45; none). Failed.
- "Out past the mouth within 12 steps of the latch": 2 of 2 (5 and 9 steps). Held.
- "The sentence taken on at least 70% of the steps it is said": 3 of 3. Held.
- "No latch before the crossing in an s02 run that is won": **4 such runs.** Failed as
  written; the runs were won after it.
- "A route on at least 95% of steps": 29 of 30 runs (s02vc `final` 3: 41/44). Walls within 4
  points. Held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r39-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). From
04:28 to 04:57 UTC a fifth client flew beside them (the unscored shakedowns of R40 and R42),
and from 05:02 the lanes that had finished flew R43's shakedown beside the last runs; R32P
flew as four lanes of eight. Flown at `095d9c9` on 2026-11-06, 04:15–05:09 UTC, by Claude
alone on the overnight instruction; the operator was asleep. **30/30 valid**, no attempt
beyond the first. Labels: Claude review, not yet confirmed by the operator. Frames stay on
the host.

**Reading.** A draw on the total, and the cell it was aimed at is still 0/3, so by the rule
set before the flight `a79` is dropped. What it leaves: the shut tine can be left, in five
steps, on a trigger that needs no model; the trigger as tuned on the record was two steps
too slow in the one run it caught and missed two it should have had; and a latch in the s02
hall did no harm in seven runs. `a83` (R43) carries the latch with a dwell of three steps
and a steadier way out, beside the wall survey. The best agent is still `a66` (F 64/90).
