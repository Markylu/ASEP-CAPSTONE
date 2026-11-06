# R49 a89 (a88's planner with a85's navigator: no route-behind sentence outside a latched corridor) on the ten contested cells, seeds 1-3: summary

**a89 23/30, level with the bar a85 (R45, 23/30); a91 19/30 (R51), a86 21/30 (R46), a87 12/30
(R47), a66 15/30 (R32P). The hypothesis held as written: at least 23, s02 at 19 or more. s02
is 21/24, the best of the night (a85 19, a91 18, a66 12); s03 is 2/6 (a85 4, a91 1). A draw
with `a85` by the rule: `a89` does not replace it as the bar, and stands beside it.**

| cell | `a66` (R32P) | `a85` (R45) | `a86` (R46) | `a87` (R47) | `a91` (R51) | `a89` (R49), steps to the goal |
|---|---|---|---|---|---|---|
| s02a `final` | 2/3 | 3/3 | 3/3 | 1/3 | 3/3 | 2/3 (—, 22, 28) |
| s02a `dynamic` | 2/3 | 3/3 | 1/3 | 0/3 | 2/3 | 3/3 (55, 56, 54) |
| s02c `final` | 1/3 | 1/3 | 1/3 | 1/3 | 0/3 | **2/3** (31, —, 28) |
| s02c `dynamic` | 0/3 | 3/3 | 2/3 | 2/3 | 2/3 | 3/3 (29, 23, 23) |
| s02va `final` | 2/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 (22, 28, 30) |
| s02va `dynamic` | 2/3 | 3/3 | 2/3 | 3/3 | 3/3 | 3/3 (23, 23, 29) |
| s02vc `final` | 1/3 | 1/3 | 1/3 | 0/3 | 3/3 | 2/3 (26, 37, —) |
| s02vc `dynamic` | 2/3 | 2/3 | 3/3 | 1/3 | 3/3 | 3/3 (33, 31, 30) |
| s03 `final` | 3/3 | 3/3 | 3/3 | 0/3 | 1/3 | 1/3 (—, —, 25) |
| s03 `dynamic` | 0/3 | 1/3 | 2/3 | 1/3 | 0/3 | 1/3 (—, —, 53) |
| **total** | **15/30** | **23/30** | **21/30** | **12/30** | **19/30** | **23/30** |
| s02 | 12/24 | 19/24 | 16/24 | 11/24 | 18/24 | 21/24 |
| s03 | 3/6 | 4/6 | 5/6 | 1/6 | 1/6 | 2/6 |

Against the predictions (README): 22–26 predicted, 23 landed. s02 21/24 (19–22), s03 `final`
1/3 (2–3 predicted: missed), s03 `dynamic` 1/3 (1–2).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- **The survey started in 21 of the 24 s02 runs, all by step 4, and 20 of the 21 were won.**
  16 crossed from their first station (steps 14 to 25), all won. Five went on to the second
  station and four were won: the three s02a `dynamic` runs, which took the left first, the
  door being on the right, took 4 to 15 steps to the second station, got through at 41, 32 and 45
  and reached the goal at 55, 56 and 54; and s02a `final` 3. In R47 the second station won 2
  of 11 and in R51 1 of 4. The one survey lost (s02c `final` 2) gave its first station up
  after six steps, as in R51.
- **With `a85`'s navigator the survey starts again**: 21 of 24 (R46 15, R47 19, R51 19, R45
  23). The sentence was said 7 times, all inside a latched corridor, and taken 7 times.
- **The three s02 losses:** two never started a survey (s02a `final` 1; s02vc `final` 3,
  latched in the hall at 19) and one lost its first station (above).
- **s03 2/6.** The first step in a tine: 32, 33, 14 (`dynamic`) and 22, 19, 14 (`final`).
  Solved: `dynamic` 3 at 53 (door shut at 17, latch at 23, out at 31) and `final` 3 by the
  open tine at 25. Lost: `dynamic` 1 and 2 reached the tine at 32 and 33 and were latched 6
  and 21 steps after the door shut; `final` 1 and 2 went into the shut tine and were latched
  at 31 and 44, 9 and 25 steps after entering it. **The reopening fired in s03 `final` 1**:
  out at 34, back inside at 44, the lane opened again; the run was lost. Whether the
  reopening cost it or the return did is not read from one run.
- **The station guard** kept both stations in all 21 surveys (R51 without it: 15 of 19). One
  of R51's four single-station surveys was lost, so the guard accounts for little of s02's 21
  against 18; three runs' difference between two flights would not show it anyway.
- **Walls in flight** (`eval/r28_flight.py`): missed 20.6% (114/553), phantom 9.2% (482/5242),
  s03 phantom 13.5% (R45 20.9 / 9.2 / 12.2). Longest turn-around streak 3.
- **Labels** (`labels.csv`, Claude review): 23 success, 7 replan_failure. No tags.

**Manipulation check.** Every `run.json` carries `a89`, `85cda76df25b`, git `456209a`.
- The sentence on no step without a latch in force: held (7 of 7 latched).
- The survey starts in at least 20 of the 24 s02 runs by step 8: 21, by step 4. In no s03
  run: held.
- No latch in an s02 run before its survey ended: held (one s02 latch, in a run with no
  survey).
- A reopening only inside the rectangle: two (s02vc `final` 3 at 42, s03 `final` 1 at 44),
  both by the bounded rule.
- A route on at least 95% of steps: 30 of 30. Walls within 4 points of R45's: held.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r49-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). Each
lane started as its R51 lane ended (09:07–09:13 UTC), so the first runs flew beside R51's
last; two extra clients flew beside them from 09:20 to 09:34 UTC (R52's unscored shakedown);
from 09:43 the lanes that had finished flew R52 beside the last of these. Flown at `456209a`
on 2026-11-06, 09:07–09:52 UTC, by Claude alone on the overnight instruction; the operator
was asleep. **30/30 valid**, no attempt beyond the first. Labels: Claude review, not yet
confirmed by the operator. Frames stay on the host.

**Reading.** `a89` and `a91` differ by the station guard and scored 23 and 19 an hour apart;
`a89` and `a85` differ by more and scored the same. One flight does not rank these three.
What the three have in common is the survey with `a85`'s navigator, and together they are
58/72 on s02 (81%) against `a66`'s 32/64 on the same cells and arms (R32P and Round F;
Fisher p = 0.0002, two-sided; the three were picked out after their flights); the whole family, the two sentence rounds included, is 98/144
(68%, p = 0.020). s02 is where the night's gain is, and it is the survey's. s03 is 2, 1 and 4
of 6 for the three, 7 of 18 against `a66`'s 3/6 in R32P: no gain shown. If one agent has to
be named to build on, `a89` has the best s02 and carries every planner fix of the night;
`a85` has the same total. The losses left are the ones R51's summary names, plus the left
going first when the door is on the right (s02a `dynamic`: won here, at 54 to 56 of 60
steps).
