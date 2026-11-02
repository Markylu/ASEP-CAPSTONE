# R30: a49 with a code route planner in place of goal-way and q03

**Agent:** `a63` (`7e6b2f2a6d8c`) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05` ·
**Memory:** `a17d` · **Status:** pre-registered 2026-11-02; offline probe gate failed as
registered (below); not flown

Written before flying. Spec: `docs/phase2-test-plan.md`. Design and evidence:
[docs/research/pathfinder-plan.md](../../../docs/research/pathfinder-plan.md). Operator's
decisions (2026-11-02): the VLM navigator picks the action (option A); `a64` (code picks) is a
shakedown diagnostic only.

## Change

One change against `a49` (R25D, 14/18, the best round so far): how the target is set.

- **Route planner (code, `planner.pathfind`).** Every step, A* over a cost map built from the
  memory (`spatial.CostMap`): visited and seen floor cost 1, unknown ground 2, suspect cells 4;
  perceiver walls, stop walls (one cell wider each side), walls at confirmed closed doors and
  stall cells are impassable, and so is any unknown cell touching one of them (a wall seen in
  part is a wall, not a gap). A seen-free or visited cell is never sealed. The target is the
  farthest route point within 4 m that a straight flight reaches over passable cells. Boxed in
  by perceiver walls, the search repeats with those walls soft; still boxed in, the nearest
  unsearched edge is the target.
- **Stall rule.** The route not 1 m shorter after 5 decisions, the last move forward and not
  blocked: the two cells ahead of that move, one each side, become stall cells. Recorded in
  `planner.stall`, so the memory rebuilt from `decisions.jsonl` carries them.
- **Memory `a17d`** = `a17b` plus what the planner reads: a `d01`-confirmed closed door whose
  floor ends within 2.5 m is a wall across its strip and neighbours; a floor end `lower` or
  `middle` is a suspect cell at 4.5 m or 8 m; three or more adjacent strips read `no_floor` are
  one flat wall, written across the span and one cell beyond each end. Parameters
  `spatial.PARAMS_A17D`, in the sha.
- **Removed:** the goal-way test, the q03 detour strategist and its menus, `detour_stall`. No
  strategist call: the step is perceiver, `d01` when an open doorway is reported, map, planner,
  tags, navigator.
- **Unchanged:** `g05`, `d01`, `p17` and its tags (`spatial.project`), the turn rule, goal truth
  on the planner side only (the navigator's plan line stays "head for the goal (approach)";
  `views.check` refuses anything more).

Parameters: `agent.PATHFINDER_A63`, in the features, so the sha.

## Evidence

- **The map was right; the choice of target was wrong.** s03 `final`/`dynamic`: all five
  failed a17b-line runs that reached the crossbar spent 34–46 steps in the shut tine and 0 in
  the other; the closed door was reported on 9–15 steps per run and the map wrote the wall
  ([s03_tines_analysis.md](../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md) §2).
  `planner.way` read `open` on 376 of 485 shut-tine decisions, because a goal behind the drone
  counts as open ([probe B0](../_probes/b0/README.md)). R25D s03 `final`: exit wall reached at
  s43, s43–59 at x ∈ [−6, −5], 12 turn-arounds (`runs/s03/final/seed1/decisions.jsonl`).
- **A way back fit the budget.** Four of the five runs had 30–40 steps left at the exit wall; the
  route back and round is about 42 m, 26–28 steps (tines analysis §1). R26 offered it as one
  target 11 m behind and the stall hand-back ended it after 4 steps; its Outcome asks for
  "waypoints back along the trail" ([R26](../R26_other_way/README.md)).
- **Lobby waste.** R25D s03 `final` spent s2–31 in the lobby (out to z = −11.5 at s10) before
  entering the stem; `initial` took 50 steps. The stem mouth lies on the goal line.
- **s02 crossing.** From the inner side the goal line clips the jamb on 197 of 202 steps; the
  wrong side is a coin flip
  ([s02_failure_analysis.md](../R19_searched_defined/s02_failure_analysis.md) §2). R25D's two
  s02 failures (s02c, s02va `final`) ran 60 steps with 22 and 24 `d01` calls and never crossed.
- **Perceiver unchanged on purpose.** Seven attempts at its wall reading failed their gates or
  flew worse (R27, R28, LD); the host rounds R29N/R29S test the remaining lever, and this round
  flies on whatever host setting they decide.
- **Smoke** (`eval/probes/a63_smoke.py`, no model, R25D's 627 recorded manifests, stub replies
  equal to the recorded ones): 0 failed steps, a route on 627/627, fallback `none` on 624
  (`soft` 3), stall cells added on 51 steps (open loop: a49 did not follow a63's route), door
  walls written on 302 steps, suspects on 622. a64: 627/627 code picks.

## Hypothesis

With a route search over the memory in place of the local goal-way test and the detour
strategist, `a63` leaves the s03 dead end and crosses the s02 open door more often than `a49`,
and scores at least 14/18.

## Predictions

| Arm | Baseline (R25D, `a49`) | Predicted |
|---|---|---|
| initial | 6 | 6 (s03 in fewer steps: 50 → about 30) |
| final | 3 | 4 or 5 (s03 tine recovery, the first tine a coin flip; s02c/s02va door crossing) |
| dynamic | 5 | 4 to 6 (s03 recovery needs about 44 of 60 steps; R25D's s02 draw may not repeat, why_14) |

Total ≥ 14/18.

**Noise.** The `a17b` family expects 11.3 ± 1.4 per 18 (why_14 §4); one seed-1 round cannot
resolve ±1 run. R30 is read on its s03 and s02 cells and the manipulation check as much as on
the total.

## Manipulation check

Code only, from `decisions.jsonl` and the site geometry (`eval/probes/pathfinder.py`'s readouts
on the flown runs, plus `eval/r28_flight.py` for the walls):
- s03 `final`/`dynamic`: steps in the shut tine after the first confirmed closed door ≤ 8 (R25D
  `final` 17; R22K 34–46); steps in the open tine > 0 (R20–R25D: 0).
- s03, every arm: steps in the lobby ≤ 12 (R25D `final` 30).
- The navigator takes the "toward your target" action on ≥ 70% of steps where it is on a forward
  move, and on ≥ 50% where it is on marker 0.
- A route exists (`fallback: none`) on ≥ 95% of steps.
- No turn-around streak of 10 or more (R27: 36).

## Drop criterion

Not carried forward below 14/18, or if the s03 shut-tine check fails in both `final` and
`dynamic` (the planner did not do the one thing it was built for, whatever the total).

## Probe gate

Two gates, both before the 18 runs.

1. **Offline, no model** ([_probes/pathfinder](../_probes/pathfinder/README.md), thresholds
   committed before the run): on R20–R26's recorded steps, the route leads out of the shut tine
   on ≥ 80%, through the stem mouth from the lobby on ≥ 70%, through the open door's gap on
   ≥ 60% of near-door steps, seals a true route on ≤ 5% of steps outside the s03 tines, and
   tags a49's own pick on R25D's solved runs at least as often as a49's tag did (minus 5 points).
   Re-scored on R27 (and R29 when flown) as the held-out set after any tuning.

   **Outcome (2026-11-02): failed as registered.** Tuning set R20–R26: shut tine 28.0%, lobby
   75.4% (pass), door gap 44.9%, sealing harm 28.5%, initial safety 68.5% against a49's 83.9%.
   Held out R27: shut tine 2/2, lobby 12/12, door gap 46.9%, sealing harm 25.0%. Two readouts
   added after the first run pass on both sets: no true route left on a63's map 0.8% / 0.0%
   (the question the registered "sealing harm" was meant to ask). Three of the four failing
   rows measure a closed-loop behaviour on open-loop data: from where a49 stood the divider
   and the door wall are unknown to the map (73% of routes rely on unknown ground that is
   wall), and the route points out of the tine or through the gap only once bumps have
   written stop walls. Four map bugs were found and fixed along the way (door walls across
   the drone's front, `bottom` closed doors 14 m out, a17b's ray end popping the floor
   straight ahead, near walls from `bottom` reads); the run-by-run record is in the probe
   README. By the rule above the planner is not carried to a round on this probe; whether
   the shakedown may stand in for it is the operator's call.
2. **On-policy shakedown** (model, a quiet instance, operator's call): one unscored `dynamic` run
   per site, s03 first, for `a63` and for `a64`, outside this folder. Passes only if s03's
   shut-tine check holds, no turn-around streak reaches 10, and `eval/r28_flight.py` shows
   missed and phantom walls within 4 points of R25D's (17.3%, 12.7%).

## Builds on

R25D (`a49`). Branch `phase2/r30-pathfinder` from `phase2/r29n-host-noise`.

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q`;
  `VLM_AGENT=a63 python eval/probes/a63_smoke.py` (and `a64`).
- **Preflight.** `python -m server.decider --profile remote --agent a63`; `/health` should report
  `7e6b2f2a6d8c`.
- **a64** is never a round: its rung `code` fails the validity check by construction.

## Outcome

Not flown.
