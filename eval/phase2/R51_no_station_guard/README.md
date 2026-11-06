# R51: a85's navigator on a86's planner (a89 without the station guard), contested cells

**Agent:** `a91` (`99b20381ecdc`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A91` ·
**Navigator notes:** `NAVIGATOR_A78` (`a85`'s) ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) while R47 was landing (22 of 30 flown) and R49's shakedown
was flying; shakedown and flight below

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R45 (`a85`, 23/30, the bar), no control lane. With R46 (`a86`),
R47 (`a87`) and R49 (`a89`) it closes a square over `a86`'s planner:

| | no station guard | `a87`'s station guard |
|---|---|---|
| **sentence only when latched (`a85`'s navigator)** | **`a91` (this round)** | `a89` (R49) |
| **sentence always (`a86`'s navigator)** | `a86` (R46, 21/30) | `a87` (R47) |

## Change

Against `a89`, one setting: **the survey's stations are shut as `a86` shut them** (`a87`'s
`station_guard: hard` off). Against the bar `a85` that leaves `a86`'s two planner changes and
`a88`'s reopening, with no change to what the navigator is told:

- the survey no longer ends 5 m beyond the wall's first estimate (`through_adv_m` off); it
  takes a short second look instead (`relook_steps` 4);
- the dead-end latch does not fire while the survey runs (`after_survey`), nor on a lane
  within 2.5 m of the direct line (`off_line_m`);
- a latched corridor's lane is opened again to a drone back inside it, short of the
  rectangle's far end (`reopen_m`, `reopen_inside`).

## Evidence

- **R45's losses are what `a86`'s planner changes were written for:** three of the five s02
  losses ended their survey early beside the door and were latched in the hall on the same
  step (s02c `final` 3, s02vc `dynamic` 1, s02vc `final` 1); s03 `dynamic` seed 1 flew back
  into its latched corridor and had no route on 21 steps.
- **In R46 those changes did what they were for** (no survey ended on the 5 m rule; no latch
  while a survey ran; 12 of the 15 runs with a survey won), under a navigator that cost the
  survey its start in up to five runs.
- **The station guard is in doubt.** It keeps both stations standing (R44's records: 22 of 22
  surveys, 14 under `a86`'s rule), and the second station is across the hall. R47 (`a87`) was
  at 10 of 22 when this was written, s02 at 10 of 19, with second-station transits of 8 to 20
  steps in the lost s02a and s02c runs. `a89`'s first shakedown run (s02a `dynamic` seed 2)
  took the stale side first, 18 steps to the second station, reached the door at step 36 and
  did not get through; `a85` had one station in that run (the other shut by `a86`'s rule) and
  won it at 26. One run, and R47 carries the sentence as well: the square is how to tell.

## Hypothesis

`a86`'s planner changes win back R45's early-ended surveys without costing anything else:
`a91` scores at least `a85`'s 23/30. If the station guard helps, `a89` beats `a91` in s02; if
it hurts, the reverse.

## Predictions

| Cell group | R45 (`a85`) | R46 (`a86`) | Predicted `a91` |
|---|---|---|---|
| s02 ×8 cells | 19/24 | 16/24 | 19–22 |
| s03 `final` | 3/3 | 3/3 | 3 |
| s03 `dynamic` | 1/3 | 2/3 | 1–2 |
| **total** | **23/30** | **21/30** | **23–26** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule): 21–25 is a draw with `a85`; the
bar only at 26 or more. R46 and R47 flew the same code in s03 and landed 5/6 and (so far) 0/3:
the screen's noise is at least that large.

## Manipulation check

From `decisions.jsonl` (`eval/probes/a80_check.py`, `eval/probes/a79_check.py`):
- The sentence is said on no step without a latch in force.
- The survey starts in at least 20 of the 24 s02 runs, by step 8; in none of the 6 s03 runs.
- No survey ends within 3 steps of its first through phase unless the drone has crossed.
- No latch in an s02 run before its survey has ended, none within 2.5 m of the direct line.
- A route on at least 95% of steps; walls in flight within 4 points of R45's.

## Drop criterion

Not carried below 21/30 or with s02 under 17/24. The bar at 26/30 or more; between, a draw
with `a85`.

## Probe gate

**No model probe.** What the model is asked and told is `a85`'s to the letter, flown on 30
runs in R45; the planner is `a86`'s (R46, 30 runs) but for the reopening (`a88`, shaken down).

**Offline gates:** `python -m pytest server/decider/tests -q` (80 pass; the new one holds
`a91`'s survey to `a86`'s, its latch to `a89`'s, its notes to `a85`'s);
`VLM_AGENT=a91 python eval/probes/a63_smoke.py` (627/627); the closed-loop simulation
(`eval/probes/a80_sim.py --far 20`, `eval/phase2/_probes/a91/`): truthful perceiver 48/48
(change arms 32/32), measured noise with 20% of moves random 115/144 (change arms 69/96;
`a89` 70, `a86` 69). Earlier agents keep
their shas (`a89` `85cda76df25b`, `a90` `5a714edadebd`).

**Shakedown gate** (on-policy, the two lanes R47 had freed, before R49 took them): s02c
`final` seed 3, s02vc `final` seed 1, s02vc `dynamic` seed 1 (R45's three early-ended
surveys) and s03 `dynamic` seed 1 (R45's re-entry). Passes if the survey starts by step 8 in
the three s02 runs, no latch fires before a survey has ended, the sentence is said on no step
without a latch, and a route is on at least 95% of steps. Wins are not required.

## Builds on

`a85` (R45, 23/30) and `a86`'s planner (R46). Branch `phase2/r51-no-station-guard` from
`phase2/r50-sentence-after-way-in` (`a90`, laid out, not flown at this point); R49's results
are merged in before this round's PR.

## Outcome

Not flown. After the round: one line on whether the hypothesis held, and a link to [summary.md](summary.md).
