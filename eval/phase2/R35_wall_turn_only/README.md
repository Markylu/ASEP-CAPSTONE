# R35: a66 with the wall-turn rule alone, contested cells

**Agent:** `a75` (`81d682c1424b`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17j` · **Planner:** `PATHFINDER_A65` (a66's) ·
**Status:** laid out 2026-11-05 on the operator's instruction ("Yes, a75"); shakedown below;
**round not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Analysis:
[docs/research/round-f-analysis.md](../../../docs/research/round-f-analysis.md) §3.1. Design: the
ten contested cells, seeds 1–3, 30 runs, read against R32P (`a66`, 15/30).

## Change

One change against `a66`, code only: **the wall-turn rule** (memory `a17j` = `a17f` +
`SpatialConfig.wall_turn`). The step after a turn-around taken with every strip reading
`blocked_near`, "toward your target" never sits on the turn-around: it goes to the open move
nearest the target's bearing, so the turn rule hides the turn-around; on that step a move onto
ground the drone has stood on carries no wall, blocked or stopped-short note. The planner, the
cost map, the memory's walls and floor, `g05`, `d01` and `p17` are `a66`'s.

## Evidence

- Round F (`a66`, 90 runs): 373 frames read every strip blocked, 332 turn-arounds after them,
  41 repeat turn-arounds on the next step; s03 `dynamic` seed 3 s35–s47 turned in place 13 times
  on an unchanged route (analysis §3.1).
- R33's shakedown of the bundle `a73` (rule + cost map): 10 wall turns, the turn-around hidden
  on all 10 next steps, no repeat turn; s02c `dynamic` seed 1 solved at 30 steps (Round F: lost,
  spin streak 9). Its s03 `dynamic` was lost to the cost map (`seal_diagonal` closed the stem;
  the stem is passable on 60 of 60 of those steps on `a66`'s map with the rule)
  ([R33](../R33_wall_turn_costmap/README.md#outcome)).

## Hypothesis

With the wall-turn rule and nothing else changed, `a75` does not turn in place at walls, loses
no cell `a66` wins, and scores at least 15/30 on the contested cells.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a75` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 6–7 |
| s02 `dynamic` ×4 | 6/12 | 6–8 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 0 (the rule gives steps back; the route out of the shut tine is unchanged) |
| **total** | **15/30** | **15–18** |

**Noise.** A gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

Code only, from `decisions.jsonl`:
- Repeat turn-arounds after a wall turn ≤ 4% of such steps (Round F 12.5%); `hidden` carries the
  turn-around on ≥ 60% of steps after a wall turn where some forward move is open.
- No turn-around streak of 5 or more (Round F: 13, 9, 5, 5).
- `a66`'s checks unchanged: a route on ≥ 95% of steps; walls in flight within 4 points of Round
  F's (missed 16.7%, phantom 12.4%); s03 lobby ≤ 12 steps.

## Drop criterion

Not carried forward below 15/30, or if repeat turn-arounds after a wall turn are not under half
of Round F's rate.

## Probe gate

Offline, no model, Round F's 90 runs (`eval/probes/a74_replay.py --variants a66,a75`,
[replay_a75.txt](../_probes/a74/replay_a75.txt)): the turn-around hidden on 30 of `a66`'s 41
repeat turns; every route readout identical to `a66`'s (the planner is `a66`'s). Gate, written
with R33's shakedown in hand: an on-policy shakedown, alone on `:8004`, seed 1 of s03 `dynamic`,
s03 `final`, s02c `dynamic` and s02a `final`. Passes if there is no repeat turn-around after a
wall turn in any run, a route on ≥ 95% of steps, and the s03 runs enter the stem within 12
steps (the failure `a73` showed).

## Builds on

`a66` (Round F, R32P); the rule from R33 (`a73`). Branch `phase2/r33-deadlock-costmap`.

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (26 pass);
  `VLM_AGENT=a75 python eval/probes/a63_smoke.py` (627/627).
- **Preflight, if flown:** `python -m server.decider --profile remote --agent a75`; `/health`
  should report `81d682c1424b`.

## Outcome

Not flown.
