# R34: a73 with only visited ground known to the route, contested cells

**Agent:** `a74` (`5039cd32e383`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Door confirmer:** `d01` · **Memory:** `a17i` · **Planner:** `PATHFINDER_A74` · **Status:**
laid out 2026-11-04 on the operator's instruction ("Build a74"); offline readouts measured
(below); **not flown**

Written before flying. Spec: `docs/phase2-test-plan.md`. Analysis:
[docs/research/round-f-analysis.md](../../../docs/research/round-f-analysis.md) §3.3 and §6.
Design: the ten contested cells, seeds 1–3, 30 runs, read against R32P (`a66`, 15/30) and R33
(`a73`, unflown).

## Change

One change against `a73` (R33), code only, in the cost map the route planner searches
(`spatial.CostMap`, `agent.PATHFINDER_A74`: `ray_floor_known` off, `far_free_cost` 2):

- **Only ground the drone has stood on is known.** Floor the perceiver read along a ray, near
  or far, is a claim: it costs 2 per metre (a visit 1, unknown 4) and an impassable cell beside
  it seals it, as it seals unknown ground. In `a66` every ray cell was known ground (cost 1,
  never sealed); in `a73` the cells within 2.5 m were.
- **A confirmed open doorway's floor is a claim that is never sealed** (`SpatialMemory.door_free`,
  written where `d01` agreed): the gap sits beside its jambs, and the sealing rule would close
  the door the drone was shown.

The memory (`a17i`), the wall-turn rule, the tags, `g05`, `d01` and `p17` are `a73`'s.

## Evidence

- Round F replayed on `a73`'s map: of 1634 s02 near-side route crossings of the divider, 1106
  ran over known floor cells and 1192 crossed six metres or more from the open door; 205 of 223
  s03 shut-tine routes left the tine over known floor in the divider, outer wall or exit wall
  ([_probes/a73](../_probes/a73/README.md)). The floor is `g05`'s `open_near` and `open_far` rays
  through walls 1–4 m away.
- Maps drawn at late steps of failed runs (s02a `final` seed 1 s59, s03 `dynamic` seed 3 s34,
  s50): the s02 divider is on the map as a staggered column of wall cells with one- and two-cell
  holes of ray floor, and the route threads the holes; the tine's inner wall has a three-cell
  hole of ray floor on the route.
- R31 measured weak far floor alone (`a17g`) at 12% against 10% and stopped there; near floor
  (within 2.5 m) stayed known in every variant tried before this one.

## Hypothesis

With ray floor a claim that walls seal, `a74`'s map holds more of the walls the drone has met,
its route leaves the s03 shut tine and reaches the s02 door more often than `a73`'s, and it
scores at least 15/30 on the contested cells.

## Predictions

| Cell group | R32P (`a66`) | Predicted `a74` |
|---|---|---|
| s02 `final` ×4 | 6/12 | 5–8 |
| s02 `dynamic` ×4 | 6/12 | 5–8 |
| s03 `final` | 3/3 | 2–3 |
| s03 `dynamic` | 0/3 | 0–1 |
| **total** | **15/30** | **14–19** |

Wider than R33's range on purpose: the map is stricter, and the replay shows both more wall
(below) and more steps with no route. **Noise:** a gap under 3 on 30 runs is a draw (R32's rule).

## Manipulation check

Code only, from `decisions.jsonl`:
- R33's checks (repeat turn-arounds after a wall turn ≤ 4%; a route on ≥ 95% of steps...) with
  one changed: `planner.fallback` is `none` on ≥ 90% of steps (the replay: 95%), and on ≥ 95% in
  s01 and every `initial`-type stretch before a wall is met.
- s02 runs that do not cross: the divider's truly walled rows impassable on the map at the last
  step ≥ 70% (`eval/probes/a74_replay.py`, readout 6; Round F under `a66` 58%).
- s03 `final`/`dynamic`: steps in the shut tine after the first closed read ≤ 15 (Round F
  30–41); steps in the open tine > 0.

## Drop criterion

Not carried forward below 15/30; or if any s01 or settled cell flown in the shakedown is lost;
or if `planner.fallback` is not `none` on more than 15% of steps (the map boxed the drone).

## Probe gate

Offline, no model, on Round F's 90 recorded runs (`eval/probes/a74_replay.py`,
[_probes/a74/replay.txt](../_probes/a74/replay.txt)). **Measured while the agent was being
built, before this section was written: a record, not a pre-registration.** Open loop.

| Readout | `a66` | `a73` | `a74` |
|---|---|---|---|
| Repeat turn-arounds after a wall turn hidden | 0/41 | 30/41 | 30/41 |
| s02 near-side routes crossing inside the open door's gap | 85/1638 (5%) | 134 (8%) | 149 (9%) |
| s03 shut-tine routes leaving by the crossbar | 0/223 | 4 (2%) | 23 (10%) |
| Failed s02 runs: divider's walled rows impassable at the last step | 58% | 65% | **73%** |
| The same rows re-opened per step | 0.13 | 0.16 | 0.13 |
| s02 near-side steps with the true gap impassable | 54/1638 (3%) | 106 (6%) | **174 (11%)** |
| s03 shut-tine steps with the open tine's door impassable | 0/223 | 0 | 0 |
| Steps with no route (soft or frontier fallback), all 90 runs | 3/3304 | 6 | **156 (5%)** |
| The same in the runs `a66` solved | 0/1744 | 1 | **78 (4%)** |

Against the gates the analysis doc set for a cost-map change (s02 ≥ 50%, s03 ≥ 80%): **failed**,
as `a73`'s did. What `a74` buys on these steps is a map that keeps 73% of the divider it has
met against 58%, and a route out of the shut tine on 10% of steps against none. What it costs:
the true door's gap is sealed on 11% of near-side steps (ray floor in the gap beside jamb walls,
on steps where `d01` had not confirmed the opening), and the search falls back on 5% of steps,
4% in runs `a66` solved. Smoke on R25D's 627 steps: fallbacks none 604, soft 10, frontier 13
(`a73`: 624 / 0 / 3).

Tried on the same steps and not carried: ray floor at 3 per metre (s02 8%, s03 8%); closing
holes of one to three cells between wall cells on a line (no change to any readout with or
without the visits-only map: sealing already closes what the holes' neighbours allow).

Open loop cannot say whether the stricter map converges on the door in flight: each probe at a
wall now stays on the map, which is what a search needs, and the replay cannot fly the search.
By the test plan's rule this probe does not carry `a74` to a round. Whether to fly it against
that rule, as R30 was, is the operator's call. If flown: shakedown first, alone on `:8004`, s01
`dynamic` (the settled-cell check), s03 `dynamic`, s02c `dynamic` and s02a `final`, scored by
the manipulation check.

## Builds on

R33 (`a73`). Branch `phase2/r33-deadlock-costmap` (R33 and R34 share it: neither is flown).

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q` (25 pass);
  `VLM_AGENT=a74 python eval/probes/a63_smoke.py`.
- **Replay:** `python eval/probes/a74_replay.py` (a66, a73, a74 and the ray-3 variant on Round
  F, about 3 min).
- **Preflight, if flown:** `python -m server.decider --profile remote --agent a74`; `/health`
  should report `5039cd32e383`. `a66` `de7f23d07186`, `a73` `7ce95fcbea92` unchanged.

## Outcome

Not flown.
