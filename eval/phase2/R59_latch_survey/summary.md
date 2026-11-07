# R59 a98 (a94's latch and a95's survey start together on a93) on the ten contested cells, seeds 1-3: summary

**a98 20/30 against the reference lane's 21/30 (R61, `a93`, same batch, same renderer): one below, a
draw, not carried. s02 17/24 against 16/24; s03 3/6 against 5/6. The hypothesis (the two changes add:
s03 `dynamic` above `a93`'s, s02 not below) did not hold: s03 `dynamic` 1/3 against 2/3, and the latch,
firing 5 steps after the read in both runs that reached the shut door, could not make up for a run that
never left the lobby and a run that read the door from the lobby at step 5 and latched 34 steps later.
The survey rule started a survey in the s03 stem once (won anyway) and in no s02 run that the old rule
would have refused.**

| cell | `a93` (R61, reference) | `a93` (R58) | `a94` (R56) | `a95` (R57) | `a98` (R59), steps to the goal |
|---|---|---|---|---|---|
| s02a `final` | 2/3 | 2/3 | 3/3 | 3/3 | 2/3 (40, 18, —) |
| s02a `dynamic` | 2/3 | 2/3 | 2/3 | 3/3 | **3/3** (41, 41, 43) |
| s02c `final` | 2/3 | 2/3 | 1/3 | 2/3 | 2/3 (54, —, 34) |
| s02c `dynamic` | 2/3 | 1/3 | 1/3 | 2/3 | 2/3 (—, 29, 40) |
| s02va `final` | 3/3 | 2/3 | 2/3 | 2/3 | 3/3 (29, 32, 27) |
| s02va `dynamic` | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 (25, 29, 23) |
| s02vc `final` | 2/3 | 3/3 | 2/3 | 3/3 | 1/3 (—, —, 31) |
| s02vc `dynamic` | 0/3 | 2/3 | 2/3 | 2/3 | 1/3 (26, —, —) |
| s03 `final` | 3/3 | 3/3 | 2/3 | 2/3 | 2/3 (45, 32, —) |
| s03 `dynamic` | 2/3 | 0/3 | 2/3 | 1/3 | 1/3 (—, —, 58) |
| **total** | **21/30** | **20/30** | **20/30** | **22/30** | **20/30** |
| s02 | 16/24 | 17/24 | 16/24 | 19/24 | 17/24 |
| s03 | 5/6 | 3/6 | 4/6 | 3/6 | 3/6 |

Against the predictions (README): reference +0 to +3 predicted, −1 landed; s03 `dynamic` 1–2 (1); s03 `final`
within 1 (2 against 3); s02 within 2 (17 against 16).

What the runs say (scratch `batch_check.py`, the step traces, the survey timelines, `eval/r28_flight.py`,
`eval/probes/a93_goal_check.py --folders R59_latch_survey`):
- **The latch:** `dynamic` 1 read the shut door at 16, latched at 21, out, crossed at 58, two steps short;
  `dynamic` 3 read at 16, latched at 21, across at 54, goal at 58 (won); `dynamic` 2 **never left the lobby**
  (the same seed, the same stall as R58's `a93`: stopped at x = 16 at step 3, 57 steps in the lobby, min x 15.2);
  `final` 3 read a closed door at step 5 from the lobby (x = 16, the far wall), went down the stem, into the
  shut tine at 30 and latched at 39 (the from-line mouth found; the earlier read at step 5 did not count: the
  drone was still advancing), out, not through in time. `final` 1 and 2 by the open tine (45, 32). Gaps where
  the door was read from the tine: 5, 5.
- **The survey rule:** one s03 run started a survey, `final` 1 at step 5 at (13.6, 0.8) in the stem's mouth,
  on a closed read down the stem; it ran 40 steps (stations to either side, into the walls, given up) and the run
  was won at 45 all the same. The old rule would have started it too (the trail was on the line); `a93` has
  simply never read a closed door square there in 7 flights. In s02 no run had been off the line before its
  survey started; the four runs with no survey (s02a `final` 1 and 2, s02va `final` 2 won; s02c `final` 2 lost
  with a latch at 15) never read the door square on the line.
- **s02 17/24.** Surveys in 20 of 24 runs. Losses: s02a `final` 3 (second station, through from 20, done 46), s02c
  `dynamic` 1 (second station done 28, crossed at 56), s02c `final` 2 (no survey), s02vc `dynamic` 2 and 3
  (**both stations given up in transit, 6 steps each, no look at all**: the navigator flew straight at the wall
  for three steps with "toward your target" on the sharp turn), s02vc `final` 1 and 2 (crossed at 56 and 57, out
  of steps). One won run latched before crossing (s02va `final` 2, latch 12, crossed 23).
- **Walls in flight:** missed 16.4% (106/648), phantom 11.4% (668/5837), s03 phantom 14.7% (R61: 21.0 / 10.4 /
  12.4): within 4.6 on missed (outside the 4 allowed, on the low side), within 2.3 on the others. Longest streak 3.
- **Goal reports:** 243 in 30 runs; 35 with no line of sight (1.2 a run), 20 dropped; the 20 kept were taken.
- **Labels** (`labels.csv`, Claude review): 20 success, 5 replan_failure, 4 timeout, 1 pre_change_failure.

**Manipulation check.** Identity and renderer (`a98`, `6905821be0ab`, H100 in 30 of 30): held. The latch within 9
steps of a square read in the shut tine: held (5, 5) in the two runs that read it there; the `final` 3 read at step
5 was from the lobby, 20 m off. No latch in the open tine or the stem: held. The survey in at least 22 of 24 s02 runs
by step 8: **not held (20)**; in every s02 run back on the line with a square read: held (none arose). No survey in
any s03 run: **not held (1, won)**. A latch before crossing in at most 3 won s02 runs (1): held. A route on at
least 95% of steps (30 of 30): held. Walls within 4 points: not held on missed (16.4 against 21.0), held otherwise.

**Not citable.** Screening, three seeds per cell. Host: sctsvr6, lanes 1–4 of twelve (`~/asep-r59-l1..4`) on
`:8004`, beside R60 on `:8006` and R61 on `:8007`; Godot on GPU 5 (`GODOT_VK=nvidia`); `Qwen3-VL-30B-A3B`, remote
profile, temperature 0. Flown at `13456b0` on 2026-11-07, 04:03–04:52 UTC, by Claude alone overnight. Shakedown 4/4
won at `13456b0` (s03 `dynamic` 1 latched on the read at 25, goal at 58). **30/30 valid**, no attempt beyond the first.
Labels: Claude review, not yet confirmed by the operator. Frames stay on the host.

**Reading.** The two changes did not add: s02 +1, s03 −2, inside the spread. Across R56 and R59 the latch has
fired within 6 steps of a square read in every run that reached the shut door (5 of 5) and won 3 of those 5 runs
through it; what it cannot do is get the drone to the door, and the s03 `dynamic` losses of this batch are a lobby
stall (seed 2, twice in two flights of two agents) and a run spent back up the stem. The survey rule's one s03
start shows the risk the README named (a survey holds the latch off), though the run was won. Not carried. `a93`
stays the parent.
