# R45 a85 (a84 with the survey lining up on the door) on the ten contested cells, seeds 1-3: summary

**a85 23/30, a84 18/30 (R44), a66 15/30 (R32P): +5 on the bar set an hour before and +8 on
`a66`. The hypothesis held: with the door's later reads kept, the survey gets through the
doors it reaches. s02 is 19/24 (R44 13/24, R32P 12/24), and five of the eight s02 cells are
3/3. `a85` is carried forward and is the bar.**

| cell | `a66` (R32P) | `a84` (R44) | `a85` (R45), steps to the goal |
|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | **3/3** (28, 22, 23) |
| s02a `dynamic` | 2/3 | 3/3 | 3/3 (21, 26, 49) |
| s02c `final` | 1/3 | 2/3 | 1/3 (20, —, —) |
| s02c `dynamic` | 0/3 | 1/3 | **3/3** (24, 26, 25) |
| s02va `final` | 2/3 | 2/3 | **3/3** (27, 26, 26) |
| s02va `dynamic` | 2/3 | 2/3 | **3/3** (26, 23, 34) |
| s02vc `final` | 1/3 | 1/3 | 1/3 (—, 24, —) |
| s02vc `dynamic` | 2/3 | 0/3 | 2/3 (—, 22, 30) |
| s03 `final` | 3/3 | 3/3 | 3/3 (40, 30, 31) |
| s03 `dynamic` | 0/3 | 2/3 | 1/3 (—, —, 51) |
| **total** | **15/30** | **18/30** | **23/30** |
| s02 | 12/24 | 13/24 | 19/24 |
| s03 | 3/6 | 5/6 | 4/6 |

Against the predictions (README): 18–24 predicted, 23 landed. s02 19/24 (predicted 16–20),
s03 `final` 3/3, s03 `dynamic` 1/3 (1–2).

What the runs say (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- **The survey is how s02 was won.** It started in 23 of the 24 s02 runs (steps 2–6) and 21
  flew at a doorway; 17 of the 19 wins crossed during the survey or within three steps of its
  end, at steps 10 to 37 (median 15). Wins took 20–34 steps but for one of 49 (R32P's `a66`
  wins: 25–55).
- **The in-view sites are no longer lost**: s02va 6/6 (R44 4/6), s02vc 3/6 (R44 1/6). The door
  read from far is flown at and the aim follows its later reads. **The line-up is not what won
  them.** A line-up followed a stop in 9 runs. In four the drone was already through the wall
  (stopped in the far room, x from −1.4 to −2.7; all four solved). In five it was stopped at
  the near wall: two then crossed (s02a `dynamic` 2 at step 17, s02va `dynamic` 3 at 25) and
  three never did (s02c `final` 3, s02vc `dynamic` 1, s02vc `final` 1: stopped 0.4 to 1.3 m
  beside the jamb, lined up once or twice, lost).
- **The five s02 losses.** Three were stopped at the wall beside the door, lined up without
  getting through, ended their survey (s02c `final` 3, s02vc `dynamic` 1, s02vc `final` 1, at
  steps 11, 16 and 15), and were latched in the hall on the diagonal they had flown at the
  same step. One never started
  a survey (s02vc `final` 3) and one took both stations and crossed at step 55 (s02c `final`
  2, `timeout`). `a86` (R46, in the air) drops the 5 m rule and holds the latch back while the
  survey runs.
- **s03 4/6.** `final` 3/3, all by the open tine. `dynamic` 1/3: seed 3 solved at 51 (door
  shut at 15, latch at 21, out at 25). Seed 2 reached the tine late (door shut at 39). **Seed
  1 is a new fault in the latch**: door shut at 21, latch at 28, out past the mouth at 36;
  the lane was then shut behind it, the drone flew back in, and inside a corridor shut on
  every side it had no route for 21 steps. A drone back inside its latched corridor needs the
  lane reopened.
- **Walls in flight** (`eval/r28_flight.py`): missed 20.9% (121/579), phantom 9.2% (441/4791),
  s03 phantom 12.2% (Round F 16.7 / 12.4 / 15.9). Missed walls are 4.2 points over Round F's,
  just outside the 4-point window, on a third of Round F's count of near walls: the runs are
  short and meet fewer walls. Longest turn-around streak 3.
- **Labels** (`labels.csv`, Claude review): 23 success, 6 replan_failure, 1 timeout. No tags.

**Manipulation check.** Every `run.json` carries `a85`, `a43435111dff`, git `ca01a4a`.
- Survey starts in at least 18 of 24 s02 runs and no s03 run: 23 and 0. Held.
- At least half the s02 wins cross during or within 3 steps of the survey: 17 of 19. Held.
- No look phase begun after a crossing: one (s02va `final` 1, at step 20, crossed at 14,
  solved at 27). Failed by one run.
- "After a line-up, the drone within 1 m of the door's centre line at the wall in at least
  half": of the five line-ups at the near wall, two crossed. Failed by the letter (2 of 5).
- Latch within 9 steps of the door shutting in the s03 runs that stay in the shut tine: 3 of
  3 (7, 6, 6); out within 8 steps: 3 of 3 (8, 5, 4). Held; seed 1 then went back in.
- A route on at least 95% of steps: 26 of 30 runs (s03 `dynamic` 1 39/60; s02vc `dynamic` 1
  52/60, s02vc `final` 1 53/60, both after a hall latch; s02c `final` 3 58/60). Failed in
  four runs, all with a latch.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, four lanes
(`~/asep-r45-l1..4`) on one vLLM (`Qwen3-VL-30B-A3B`, remote profile, temperature 0). Each
lane started as its R44 lane ended, so the first runs flew beside R44's last; a fifth client
flew beside them until 06:23 UTC and from 06:32 to 06:47 (the unscored shakedowns of R46 and
R47); from about 06:49 the lanes that had finished flew R46 beside the last of these. Flown at
`ca01a4a` on 2026-11-06, 06:17–07:02 UTC, by Claude alone on the overnight instruction; the
operator was asleep. **30/30 valid**, no attempt beyond the first. Labels: Claude review, not
yet confirmed by the operator. Frames stay on the host.

**Reading.** 23/30 against 15/30 is the first gap of the night well clear of the rule's
threshold (Fisher p = 0.06, two-sided; against R44's 18/30, 0.25), and it is where the change
was aimed: the s02 change arms, 19/24. It is one round of 30 on three seeds, under a host
shared with other clients, and the two steps from `a66` to here (R44, R45) were each chosen
after looking at the runs before. What is left is named: a line-up that fails beside the jamb,
a latch that follows the survey's end in the hall, the latched corridor re-entered, and the
s03 runs that reach the tine late. `a86` and `a87` (R46, R47) are in the queue for the second
of these and for s02c.
