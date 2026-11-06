# R52: a91 with the survey's stations held for 12 steps, contested cells

**Agent:** `a92` (`8e5bcc8a5c74`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A92` ·
**Navigator notes:** `NAVIGATOR_A78` (`a85`'s) ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R51's flight, while R49 was in the air; the last round
of the night; shakedown flown 2026-11-06 (two of four solved, gate passed, the longer wait not
called on); **flown 2026-11-06, 20/30, not carried**

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R45 (`a85`, 23/30, the bar) and R51 (`a91`, 19/30), no control lane.

## Change

One number against `a91`, code only: **the survey gives a station up after 12 steps without
coming half a metre nearer to it, not 6** (`SURVEY["stall_steps"]`). The navigator, the prompt,
the route, the latch and the rest of the survey are `a91`'s.

## Evidence

- **Counted on the records of R45, R46, R47 and R51** (76 s02 runs with a survey): the first
  station was given up in transit in 9 runs and 3 of those were won; of the 67 that kept it,
  51 were won. 7 of the 9 are s02c `final` (of 12 such runs), where the first station is on
  the open door's side and the survey then goes to the far side; the others are s02vc `final`
  seed 1 (R47) and s02a `dynamic` seed 3 (R45). In 6 of the 9 it was given up exactly 6 steps
  after the survey started.
- **Why the six run out** (R51 s02c `final` seed 2, traced): the survey starts at step 2, 8.7 m
  from the wall, with the station 7 m to the left and "toward your target" on the hard-left
  move. The navigator flies straight on at the shut door for four steps, is stopped by the
  wall at step 6 and turns round; at step 8, one step into the flight back toward the
  station, six steps have passed with the drone no nearer and the station is given up. The
  second station is then given up the same way and the survey is over at step 16.
- **s02c `final` is the one s02 cell the night has not moved:** 1/3 for `a66`, `a85`, `a86`
  and `a87`, 0/3 for `a91`.

## Hypothesis

Held for 12 steps, the first station is reached after the navigator has flown on to the wall
and come back, and the survey looks at the door's side first. s02c `final` goes to 2/3 or
better, the rest of s02 stays where `a91` had it, and `a92` scores at least 20/30.

## Predictions

| Cell group | R45 (`a85`) | R51 (`a91`) | Predicted `a92` |
|---|---|---|---|
| s02c `final` | 1/3 | 0/3 | 2–3 |
| the other seven s02 cells | 18/21 | 18/21 | 16–19 |
| s03 | 4/6 | 1/6 | 1–5 (unchanged code; the screen's noise) |
| **total** | **23/30** | **19/30** | **19–27** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule), and s03 alone has ranged from 1
to 5 of 6 tonight on code that does not differ there. The cell to read is s02c `final`, and
s02 as a whole.

## Manipulation check

From `decisions.jsonl` (`eval/probes/a80_check.py`):
- A first station given up in transit in at most 2 s02 runs (R51: 2 of 19; R47: 4 of 19).
- In the s02c `final` runs with a survey, a look from the first station in at least 2 of 3.
- The survey starts in at least 18 of the 24 s02 runs; a route on at least 95% of steps; the
  sentence on no step without a latch.

## Drop criterion

Not carried with s02 under 17/24. The bar at 26/30 or more; otherwise read on s02 against
`a85`'s 19/24 and `a91`'s 18/24.

## Probe gate

**No model probe.** What the model is asked and told is `a85`'s; the change is one number in
the planner.

**Offline gates:** `python -m pytest server/decider/tests -q` (81 pass);
`VLM_AGENT=a92 python eval/probes/a63_smoke.py` (627/627); the closed-loop simulation
(`eval/probes/a80_sim.py --far 20`, `eval/phase2/_probes/a92/`): truthful perceiver 48/48, measured noise with 20% of moves random 117/144
(`a91` 115). The simulated
navigator takes the tagged move, so a station is seldom stalled there: the tables say the
longer wait breaks nothing, not that it helps. The count on the flown records above is the
evidence.

**Shakedown gate** (on-policy, two extra clients beside R49's lanes on `:8004`, slots 5 and
6): s02c `final` seeds 1, 2 and 3 and s02vc `final` seed 1 (four of the nine runs counted).
Passes if the first station is not given up in transit in at least three of the four, a
route is on at least 95% of steps, and the survey still ends inside its 44 steps. Wins are
not required.

## Builds on

`a91` (R51, 19/30; s02 18/24). Branch `phase2/r52-station-stall` from
`phase2/r51-no-station-guard` (`41f05b9`).

## Outcome

**Flown 2026-11-06: 20/30 against `a91`'s 19/30 (R51) and the bar's 23/30; not carried.** The
hypothesis did not hold: s02c `final` 1/3. The longer wait won the one run that called on it; the
other two runs of the cell never started a survey. s02 17/24, s03 3/6.
[summary.md](summary.md). Labels: Claude review, not yet confirmed by the operator.

**Shakedown (2026-11-06, 09:20–09:34 UTC): four unscored runs as two extra clients beside
R49's four lanes, slot 5 (port 8105, sctsvr6 `~/asep-r33-shake`) and slot 6 (port 8106,
`~/asep-r52-shake-b`) at `64129a9`, logs `~/r52_shake_5.log`, `_6.log`. All valid, two of
four solved. Gate passed.** (`eval/probes/a80_check.py`.)

| Cell (seed) | `a92` | R51 (`a91`), same cell and seed | What happened |
|---|---|---|---|
| s02c `final` (1) | lost | lost (first station given up at 9, through at 48) | a doorway read at step 2 and flown at, look at 11, flown at again at 13, look at 18, survey over at 22; no station, never through; a hall latch at 30 |
| s02c `final` (2) | lost | lost (first station given up at 8, through at 56) | survey from 6; **the first station reached at 12** and looked from for 7 steps (one square look), no doorway flown at; second station looked from at 25; over at 30 |
| s02c `final` (3) | **solved, 23** | lost (flew at a doorway, never through) | survey from 2, the door flown at from 6, through at 10 |
| s02vc `final` (1) | solved, 27 | solved at 56 (no survey) | survey from 2, **the first station reached at 7**, the door flown at from 9, through at 19 |

- **Gate:** the first station not given up in transit in at least three of four: none was
  given up (two runs had a transit to it, both reached it; two flew at a doorway before any
  transit). A route on every step. Surveys over at 22, 30, 16 and 26, inside the 44. Passed.
- **What it shows and does not:** where the station was flown to it was reached, in 6 and 5
  steps, so in neither run did the longer wait come into play: the navigator turned to the
  side sooner than in R51's runs. s02c `final` seed 2 reached the door's side, looked, and
  saw no door. One seed each, unscored, six clients on the host.
