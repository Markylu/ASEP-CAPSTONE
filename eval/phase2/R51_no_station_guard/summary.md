# R51 a91 (a85's navigator on a86's planner: a89 without the station guard) on the ten contested cells, seeds 1-3: summary

**a91 19/30, a85 23/30 (R45, the bar), a86 21/30 (R46), a87 12/30 (R47), a66 15/30 (R32P):
four under the bar, four over `a66`. The hypothesis did not hold. s02 is 18/24, level with
`a85`'s 19/24; the gap is s03, 1/6 against 4/6, lost in the lobby and in the shut tine as
R47's was, this time with no always-on sentence. Not carried; `a85` stays the bar.**

| cell | `a66` (R32P) | `a85` (R45) | `a86` (R46) | `a87` (R47) | `a91` (R51), steps to the goal |
|---|---|---|---|---|---|
| s02a `final` | 2/3 | 3/3 | 3/3 | 1/3 | 3/3 (18, 22, 24) |
| s02a `dynamic` | 2/3 | 3/3 | 1/3 | 0/3 | 2/3 (46, 24, —) |
| s02c `final` | 1/3 | 1/3 | 1/3 | 1/3 | 0/3 |
| s02c `dynamic` | 0/3 | 3/3 | 2/3 | 2/3 | 2/3 (46, —, 32) |
| s02va `final` | 2/3 | 3/3 | 3/3 | 3/3 | 2/3 (—, 26, 23) |
| s02va `dynamic` | 2/3 | 3/3 | 2/3 | 3/3 | 3/3 (31, 31, 24) |
| s02vc `final` | 1/3 | 1/3 | 1/3 | 0/3 | **3/3** (56, 23, 31) |
| s02vc `dynamic` | 2/3 | 2/3 | 3/3 | 1/3 | 3/3 (35, 25, 46) |
| s03 `final` | 3/3 | 3/3 | 3/3 | 0/3 | 1/3 (—, —, 40) |
| s03 `dynamic` | 0/3 | 1/3 | 2/3 | 1/3 | 0/3 |
| **total** | **15/30** | **23/30** | **21/30** | **12/30** | **19/30** |
| s02 | 12/24 | 19/24 | 16/24 | 11/24 | 18/24 |
| s03 | 3/6 | 4/6 | 5/6 | 1/6 | 1/6 |

Against the predictions (README): 23–26 predicted, 19 landed. s02 18/24 (19–22), s03 `final`
1/3 (3), s03 `dynamic` 0/3 (1–2).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- **s02 holds at `a85`'s level, by the same road.** The survey started in 19 of the 24 s02
  runs. 12 crossed from their first station, at steps 13 to 26, and all 12 were won. Four went
  on to the second station and one was won (s02a `dynamic` 1 at 46); the other three got
  through the wall at 48, 53 and 56 and ran out of steps (`timeout`). Two had a single
  station that saw no door (one lost, one won by the route at 46). One flew at a doorway from
  its first station and never got through (s02c `final` 3, lost in R45, R46 and R47 as well).
  Of the five runs with no survey, four found a door on the route.
- **s02vc 6/6** (`a85` 3/6, `a86` 4/6, `a66` 3/6): the door read from far and flown at. Of
  R45's three early-ended surveys, the two s02vc runs were won here (one by the survey, one
  by the route at 56) and s02c `final` 3 was lost again.
- **s02c `final` 0/3**, the one s02 cell under `a66`: in seeds 1 and 2 the first station, on
  the door's side, was given up after six steps without the drone coming nearer to it, and
  the survey went to the far side; both got through late (48, 56). This cell is 1/3 for `a66`, `a85`, `a86` and `a87`.
- **s03 1/6, and not for want of a sentence.** The first step in a tine: 49, 15, 14
  (`dynamic`) and 49, 24, 28 (`final`). Two runs spent 49 steps in the lobby: in s03 `final`
  seed 1 the record is R46's for four steps; at step 4, in the same pose, the perceiver read
  the floor ahead blocked in R46 and open to the right here, the drone slid past the stem's
  mouth and the route was laid through the lobby wall beside it for some 35 steps. Of the
  three that entered the shut tine in time, one was latched at 23 and took 18 steps to get
  out, one at 33 and 23 steps, and **s03 `dynamic` seed 2 was in the shut tine from step 15
  for 38 steps with no latch**: it turned around eight times inside the tine in the 22 steps traced and never held
  the straight run the trigger wants (a closed door read on 11 steps). Not diagnosed further.
- **The sentence** was said 7 times, all inside a latched corridor, and taken 7 times.
- **The reopening fired once**, in s02vc `final` seed 1 at step 50 (hall latch at 19, out at
  28, the wall crossed at 47; solved at 56). Not in s03.
- **Latches in s02: two**, both after or without a survey, neither within 2.5 m of the
  direct line (s02c `final` 1 at 28, two steps after its survey ended; s02vc `final` 1 at 19).
- **Walls in flight** (`eval/r28_flight.py`): missed 22.2% (159/715), phantom 9.4% (529/5600),
  s03 phantom 14.4% (R45 20.9 / 9.2 / 12.2). Longest turn-around streak 5.
- **Labels** (`labels.csv`, Claude review): 19 success, 8 replan_failure, 3 timeout. Tag:
  `failed_goal_identification` on s02c `final` 1.

**Manipulation check.** Every `run.json` carries `a91`, `99b20381ecdc`, git `8b3f291`.
- The sentence on no step without a latch in force: held (7 of 7 latched).
- The survey starts in at least 20 of the 24 s02 runs: **19. Failed by one.** In no s03 run:
  held.
- No survey ends within 3 steps of its first through phase unless the drone has crossed:
  held.
- No latch in an s02 run before its survey ended, none within 2.5 m of the direct line: held.
- A route on at least 95% of steps: 30 of 30 runs. Walls within 4 points of R45's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r51-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). Lanes 2
to 4 started at 08:29 UTC on slots R47 had freed, lane 1 at 08:38 as R47's last lane ended;
from 09:07 the lanes that had finished flew R49 beside the last of these; no fifth client.
Flown at `8b3f291` on 2026-11-06, 08:29–09:13 UTC, by Claude alone on the overnight
instruction; the operator was asleep. **30/30 valid**, no attempt beyond the first. Labels:
Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** On s02, where the night's work went, `a91` is where `a85` was: 18 and 19 of 24
against `a66`'s 12 (Fisher p = 0.14 for 18 against 12, two-sided). `a86`'s planner changes did
not add to that; they did no visible harm either. On s03 the five flights of this family
read 5, 4, 5, 1, 1 of 6 (R44 to R51) on code that barely differs there, so 19 against 23
(p = 0.40) is not evidence that `a91` is the worse agent, and R45's 23 is not evidence that
`a85` is a 23 agent. Pooled over the five flights of the family (R44 to R47 and this one) s02
is 77/120 (64%) against `a66`'s 32/64 on the same cells and arms (R32P 12/24, Round F 20/40):
p = 0.08; without R47, 66/96 (69%), p = 0.02. That is the size of what the night found: the
survey lifts s02 by some 15 to 20 points, s03 has not moved beyond its noise, and which
member of the family is best is not settled by one flight each. What loses now is named: the lobby
wall the route is laid through, a tine the drone zigzags in without latching, the second
station, and s02c `final`.
