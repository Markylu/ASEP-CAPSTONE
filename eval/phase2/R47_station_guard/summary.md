# R47 a87 (a86 with the survey's stations shut only by walls the drone has met) on the ten contested cells, seeds 1-3: summary

**a87 12/30, a86 21/30 (R46), a85 23/30 (R45, the bar), a66 15/30 (R32P): nine under the
agent it differs from by one setting, eleven under the bar, three under `a66`. Dropped. The
record does not put the loss on the station guard: s03, where `a87` is `a86` line for line,
fell from 5/6 to 1/6, and in s02 the surveys that did not get through from their first
station lost at the second. What the round shows is how far one agent's score
moves between two flights of this screen, and what the always-on sentence does in a run that
has gone wrong.**

| cell | `a66` (R32P) | `a85` (R45) | `a86` (R46) | `a87` (R47), steps to the goal |
|---|---|---|---|---|
| s02a `final` | 2/3 | 3/3 | 3/3 | 1/3 (—, 32, —) |
| s02a `dynamic` | 2/3 | 3/3 | 1/3 | 0/3 |
| s02c `final` | 1/3 | 1/3 | 1/3 | 1/3 (—, 35, —) |
| s02c `dynamic` | 0/3 | 3/3 | 2/3 | 2/3 (43, 30, —) |
| s02va `final` | 2/3 | 3/3 | 3/3 | 3/3 (32, 34, 22) |
| s02va `dynamic` | 2/3 | 3/3 | 2/3 | 3/3 (33, 43, 23) |
| s02vc `final` | 1/3 | 1/3 | 1/3 | 0/3 |
| s02vc `dynamic` | 2/3 | 2/3 | 3/3 | 1/3 (—, —, 30) |
| s03 `final` | 3/3 | 3/3 | 3/3 | **0/3** |
| s03 `dynamic` | 0/3 | 1/3 | 2/3 | 1/3 (—, —, 60) |
| **total** | **15/30** | **23/30** | **21/30** | **12/30** |
| s02 | 12/24 | 19/24 | 16/24 | 11/24 |
| s03 | 3/6 | 4/6 | 5/6 | 1/6 |

Against the predictions (README): 19–25 predicted, 12 landed. s02 `final` 5/12 and s02
`dynamic` 6/12 (8–10 each), s03 `final` 0/3 (2–3), s03 `dynamic` 1/3 (1–3).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- **s03 is `a86`'s code and lost four more runs than `a86` did.** No survey starts in s03 and
  the station guard is read nowhere else. The first step in a tine: 46, 32, 28 (`dynamic`)
  and 42, 15, never (`final`); R46: 18, 28, 12 and 17, 16, 22. The drone spent the run in the
  lobby and the stem with the navigator taking every sentence it was given (54 of 54 in s03;
  14 and 13 in the two runs that reached a tine after step 40). s03 `final` had been
  3/3 for `a66`, `a84`, `a85` and `a86`. R48's shakedown lost s03 `final` seed 1 the same way.
- **s02: the first station wins, the second does not.** The survey started in 19 of the 24
  s02 runs. 7 crossed from their first station and all 7 were won. 11 went on to the second
  station (two of them after flying at a doorway from the first and not getting through) and
  2 were won (s02c `dynamic` 1 through the door at 31; s02c `final` 2 by the route at 27, its
  survey over). One had a single station and lost (s02c `final` 1). R46: 11 of 15 surveys
  crossed from the first station.
- **Why fewer first stations found the door.** With no open doorway remembered to the side
  when the survey starts, the left goes first. In the s02a cells that was the order in 5 of 6
  runs and all five lost (R46: 2 of 4 surveys, one lost; R45: 1 of 6, won): the door was on
  the other side, the crossing to the second station took 8 to 11 steps (given up in two),
  and of the three that then flew at the door one got through, at step 30, and was not
  solved. The order is
  decided by what the perceiver had read by steps 2 to 6; the station guard has no part in it.
- **The station guard itself.** Both stations stood in 18 of the 19 surveys. In R46 they
  stood in 14 of 15 under `a86`'s rule, so in flight the setting changed little (on R44's
  records it had been 14 of 22).
- **The sentence in a run gone wrong.** Taken on 162 of the 162 steps it was said (R46: 98 of
  98). s02a `final` seed 3 turned around 14 times in a row from step to step, the route
  behind it after each turn, told so each time (`spin_failure`): the longest streak of the
  night (R45: 3). Lost runs were told 4 to 16 times, won runs 0 to 5.
- **Latches in s02: three**, at steps 38 (s02c `final` 1, 26 steps after its survey ended),
  47 (s02c `dynamic` 3, no survey) and 40 (s02va `dynamic` 2, in the far room, solved at 43).
- **Walls in flight** (`eval/r28_flight.py`): missed 20.0% (202/1008), phantom 10.8%
  (697/6477), s03 phantom 13.7% (R46 20.4 / 9.3 / 11.7; Round F 16.7 / 12.4 / 15.9).
- **No sign of the host in it.** Steps answered on the first attempt: 1477 of 1497 (R46 1198
  of 1218, R45 1058 of 1074); median step 4.4 s (R46 4.7, R45 4.5).
- **Labels** (`labels.csv`, Claude review): 12 success, 17 replan_failure, 1 timeout (s03
  `final` 2, through the exit wall at 58). Tag: `spin_failure` on s02a `final` 3.

**Manipulation check.** Every `run.json` carries `a87`, `aaf90e0ca54d`, git `e68a3c2`.
- The survey starts with both stations in at least 20 of the s02 runs it starts in: 18 of
  19. Failed on the count (19 surveys), held as a share.
- R46's rows: the sentence taken on at least 85% of the steps it is said: 162 of 162. s03 in
  a tine by step 25 in at least 5 of 6 runs: **1 of 6. Failed.** No latch within 2.5 m of the
  direct line or while a survey ran: held. Survey starts in at least 18 of 24 s02 runs: 19.
  A route on at least 95% of steps: 29 of 30 runs (s03 `final` 2, 55/60).

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r47-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). Each
lane started as its R46 lane ended (07:25–07:50 UTC), so the first runs flew beside R46's
last; a fifth client flew beside them until 07:36 (R48's unscored shakedown) and from 07:59
to 08:27 UTC (R49's); lanes 3 and 4, done by 08:13, flew R51's unscored shakedown (08:14–
08:27) and from 08:29 R51 itself beside lane 1's last runs. Flown at `e68a3c2` on 2026-11-06,
07:25–08:38 UTC, by Claude alone on the overnight instruction; the operator was asleep.
**30/30 valid**, no attempt beyond the first. Labels: Claude review, not yet confirmed by the
operator. Frames stay on the host.

**Reading.** Two things, both about how to read the night rather than about the station
guard. First, `a86` and `a87` are the same agent in s03 and scored 5/6 and 1/6 an hour apart
(Fisher p = 0.08, two-sided, on six runs each); over the whole screen they differ by one
setting, under which the stations stood much as they had under `a86`'s rule, and scored 21
and 12 (p = 0.04). Either the
always-on sentence makes this agent's runs unusually sensitive to small differences in what
the model returns, or a 3-run rule on 30 runs understates the noise of this screen for every
round flown on it, R45's 23 included. The record favours the first without ruling out the
second: with the sentence taken every time, a wrong route is flown instead of ignored, and
the losses are long runs of obeyed turn-arounds. Second, the survey wins from its first
station and seldom from its second, so which side goes first matters more than whether both
stand. R49 (`a89`) and R51 (`a91`) drop the always-on sentence; R51 also drops the guard.
Neither touches the order of the stations.

**Added after R51 landed (2026-11-06, 09:15 UTC).** The first reading above does not stand for
s03. `a91` (R51) never says the sentence outside a latched corridor and scored 1/6 in s03 in
the next flight, the same way: s03 `final` seed 1 never reached a tine in 60 steps. Its record
against R46's on that cell and seed is identical for four steps; at step 4, in the same pose,
the perceiver read the floor ahead blocked in R46 and open to the right in R51, the drone
slid past the stem's mouth, and the route was laid through the lobby wall beside it for the
next 35 steps. That is the planner not learning a wall it is stopped by, set off by one
frame read two ways, with or without the sentence. What stands: the 14-turn spin and the
162 of 162 are the sentence's; s03's 1/6 is the screen's noise, and it is that large.
