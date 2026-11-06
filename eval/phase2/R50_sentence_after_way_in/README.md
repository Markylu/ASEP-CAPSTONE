# R50: a89 with the route-behind sentence after the first way in, contested cells

**Agent:** `a90` (`5a714edadebd`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17f` · **Planner:** `PATHFINDER_A90` ·
**Navigator notes:** `NAVIGATOR_A90` ·
**Status:** laid out 2026-11-06 (overnight run, Claude alone, operator asleep; every decision
here is Claude's, with its reason) from R46's flight, while R47 was in the air and R49's
shakedown was flying; **not flown** (see Outcome)

Written before flying. Spec: `docs/phase2-test-plan.md`. Design: the ten contested cells, seeds
1–3, 30 runs, read against R45 (`a85`, 23/30, the bar), R46 (`a86`, 21/30) and R49 (`a89`) as
it lands; no control lane.

## Change

One change against `a89`: **the navigator is told its route is behind it outside a latched
corridor too (`a86`'s sentence), except on the drone's first way in.**

- The planner reports `way_in` on every step (`planner.PathPlan.way_in`,
  `PATHFINDER_A90["way_in"]`): true before step 8 while no survey has started, no corridor is
  latched, and the drone has never been more than 2.5 m off the direct line from the spawn to
  the goal (the survey's own `line_m`: while this holds a survey can still start).
- `orchestrator.behind_note` (`NAVIGATOR_A90`, `always = "after_way_in"`): with "toward your
  target" on the turn-around, the sentence is said unless `way_in` is true. Inside a latched
  corridor nothing changes (`a78`'s reason and the sentence).

The route, the survey, the latch and the tags are `a89`'s; the prompt is `p17`.

## Evidence

- **R46 (`a86`, the sentence always):** taken on 98 of the 98 steps it was said. s03 5/6
  (R45 4/6), the drone in a tine at steps 18, 28, 12 (`dynamic`) and 17, 16, 22 (`final`)
  against R45's 19, 37, 12 and 25, 15, 19. s02 16/24 (R45 19/24), the survey started in 15 of
  24 runs (R45: 23).
- **Where R46's sentences fell, by this round's rule** (counted on R46's records): of the 72
  said in s02, 5 were on the way in, all at steps 0 to 2, one in each of 5 of the 9 runs that
  never started a survey (three of those five lost). Of the 26 said in s03, 10 were on the
  direct line with no survey and no latch (the stem lies on it), but only one before step 8
  (s03 `dynamic` seed 1, step 5). The step bound is there to keep s03's: R45's and R46's
  surveys all started at steps 2 to 6, so a drone still on the line at step 8 with none is
  not going to start one.
- **After the way in the sentence did not cost the survey:** R46's 15 runs with a survey won
  12 (80%); R45's 23 won 19.
- **Against it:** R48's shakedown lost s03 `final` seed 1 in the lobby with the navigator
  taking 13 of 13 sentences on a route laid through a wall it had not seen. The sentence makes
  the navigator fly the route, right or wrong.

## Hypothesis

`a90` keeps `a89`'s s02 (the survey starting as often as in R45) and gets R46's s03 (the
tine sooner, `dynamic` 2/3). It scores at least 23/30.

## Predictions

| Cell group | R45 (`a85`) | R46 (`a86`) | Predicted `a90` |
|---|---|---|---|
| s02 ×8 cells | 19/24 | 16/24 | 18–22 |
| s03 `final` | 3/3 | 3/3 | 2–3 |
| s03 `dynamic` | 1/3 | 2/3 | 1–2 |
| **total** | **23/30** | **21/30** | **22–26** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule): 21–25 is a draw with `a85`; the
bar only at 26 or more. Against `a89` (R49) the same rule.

## Manipulation check

From `decisions.jsonl` (`planner.way_in`, `route_behind`; `eval/probes/a80_check.py`,
`eval/probes/a79_check.py`):
- No sentence on a step with `way_in` true; the sentence on every other step with the tag on
  the turn-around, and the turn-around taken on at least 85% of them.
- The survey starts in at least 20 of the 24 s02 runs, by step 8; in none of the 6 s03 runs.
- s03: the first step in a tine at 25 or before in at least 5 of the 6 runs.
- No latch in an s02 run before its survey has ended; a route on at least 95% of steps; walls
  in flight within 4 points of R45's.

## Drop criterion

Not carried below 21/30 or with s02 under 17/24. The bar at 26/30 or more; between, a draw,
and what the morning's reader builds on is whichever of `a85`, `a89` and `a90` holds s02 and
s03 best.

## Probe gate

**No model probe run.** The change touches what the navigator is told on the steps the
sentence is said; the sentence is `a70`'s, and its effect was measured on 98 steps in R46's
flight. The gate for it is the shakedown, on-policy.

**Offline gates:** `python -m pytest server/decider/tests -q` (79 pass; the new one holds the
notes, the planner's `way_in` on and off the line and at step 8, and `a89` unchanged);
`VLM_AGENT=a90 python eval/probes/a63_smoke.py` (627/627); the count on R46's records above.
The planner's routes are `a89`'s (`way_in` is only reported), so `a89`'s closed-loop tables
stand (`eval/phase2/_probes/a89/`). Earlier agents keep their shas (`a89` `85cda76df25b`).

**Shakedown gate** (on-policy, slot 5 as a fifth client): s02a `dynamic` seed 2 and s02c
`dynamic` seed 3 (told at steps 1 and 2 in R46, no survey, lost), s03 `dynamic` seed 1 and s03
`final` seed 1 (the lobby). Passes if no sentence is said on a `way_in` step, the survey
starts by step 8 in both s02 runs, the turn-around is taken on at least 80% of the steps the
sentence is said, and a route is on at least 95% of steps. Wins are not required.

## Builds on

`a89` (R49, queued) and `a86` (R46, 21/30). Branch `phase2/r50-sentence-after-way-in` from
`phase2/r49-no-sentence` (`12c2814`); R49's results are merged in before this round's PR.

## Outcome

**Not flown, no shakedown (decided 2026-11-06, 08:28 UTC, Claude alone).** Laid out at 08:07 UTC on
R46's record. R47 then landed: s03 1/6 for `a87`, which is `a86` in s03 (R46: 5/6), the drone in a
tine at steps 46, 32, 28, 42, 15 and never, the navigator taking every sentence in the lobby and
the stem, nearly all of them after step 8. The s03 gain this round was written to keep was not
there the second time, and the rule here would not have stopped those sentences. The two flights
left went to `a91` (R51) and `a89` (R49). The code (`planner.PathPlan.way_in`, `NAVIGATOR_A90`)
stands, tested, for a round that wants it.
