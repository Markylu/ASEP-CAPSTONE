# R30: a49 with a code route planner in place of goal-way and q03

**Agent:** `a70` (`cf82ad60b931`; `a63` `7e6b2f2a6d8c`, `a65` `ec86fb5072ec`, `a66`
`de7f23d07186`, `a67` `c6b3e9877438` and `a68` `1036af9aed35` flew in the shakedown too,
below; `a69` is defined, unflown) · **Prompt:** `p17` (`cb3578251cfe`) · **Perceiver:** `g05`
· **Memory:** `a17f` · **Status:** pre-registered 2026-11-02; offline probe gate failed as
registered; shakedown flown 2026-11-03, its s03 check not met by any planner-side version
(below); operator 2026-11-03: change the navigator (`a70`, shakedown below)

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
- s03, every arm: steps in the lobby ≤ 12 (R25D `final`: 27 by `eval/r30_check.py`'s region
  rule, x > 15; 30 counting the stem mouth).
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
   README. By the rule above the planner is not carried to a round on this probe.

   **Operator's decision (2026-11-02): the on-policy shakedown stands in for this gate.** The
   offline probe is kept as a record; R30 flies only if the shakedown below passes.
2. **On-policy shakedown** (model, a quiet instance, operator's call): one unscored `dynamic` run
   per site, s03 first, for `a63` and for `a64`, outside this folder. Passes only if s03's
   shut-tine check holds, no turn-around streak reaches 10, and `eval/r28_flight.py` shows
   missed and phantom walls within 4 points of R25D's (17.3%, 12.7%). Scored by
   `python eval/r30_check.py <runs dir>` (the manipulation check's readouts per run, with
   these limits) and `python eval/r28_flight.py <runs dir>` (walls). `a64`'s runs are invalid
   by construction (rung `code`): fly them with `--max-attempts 1` so the runner does not
   rerun them, and read them for the ceiling only.

   **Shakedown, first pass (a63, 2026-11-03, sctsvr6 `~/r30_shake`, alone on `:8004`).**
   s03 `dynamic`: 60 steps, 8+ m, not solved. The route was right where it mattered and
   wrong in two ways a63 could not know: (1) s4–s17, beside the stem mouth, the planner put
   "toward your target" on marker 0 for five steps and the navigator flew on along the lobby
   wall to z = −11.5 (the R11 marker-0 pattern, p17 did not cure it); (2) s36–s41 it took tine
   R, met the shut door at s41, then crabbed along the tine for 18 steps, reversing twice,
   never back to the crossbar: the tine's side walls were unknown to the map (the side strips
   read them `bottom` at 2–3 m, which a17d wrote nowhere), so the route hopped to the next
   unsealed cell of the divider; and at s41 a stall block plus a diagonal bump's inflation
   boxed the drone in its new cell, and the soft fallback routed through the shut door.
   **a65** = a63 with memory `a17e` (near walls at 2.5 m from the two side strips, erased by
   seen floor or a visit; on R25D's recorded steps they seal a true route on 0.6% of steps)
   and local mobility (stall cells and inflated stop walls never within a cell of the drone).
   The round moves to a65 before any round flight; the a63 shakedown runs stay on the host
   as `~/r30_shake_a63_runs`, read for the record only. The navigator's marker-0 refusals are
   not addressed by a65 and are what `a64`'s runs measure.

   **a63, all six** (`eval/r30_check.py`, `eval/r28_flight.py`): `dynamic` solved 3/6 (s01 35
   steps, s02a 37, s02va 28); s02c and s02vc ran 60 steps without crossing the divider; s03
   as above. Walls in flight as R25D's: missed 17.7%, phantom 13.2%, s03 phantom 10.8%;
   longest turn-around streak 3; a route on 97–100% of steps. s02c's trace: the drone hugged
   the divider at x ≈ 0.7 for 50 steps between z = −7 and +3 and never reached door C at
   z = +9, because the walls it saw nose-on were popped by the next grazing look along the
   wall (`cells_wall` oscillated 7–12); a64's s03 run (code follows the route) reached the
   shut door at s28, not s41, then bounced at it for 30 steps for the same reason.
   **a66** = a65 with memory `a17f`: a nose-on wall run and a confirmed closed door are firm
   walls, erased only by a visit. Open loop on R25D's steps the shut-tine row moves 43% → 79%
   (probe README). a65's lane was stopped after its s03 run was already lost in the lobby
   (25 steps beside the stem mouth; its runs kept as `~/r30_shake_a65_runs`). The round moves
   to a66.

   **a64, all six** (code follows a63's route, `~/r30_a64_runs`): `dynamic` 2/6 (s01 40
   steps, s02vc 34); s02a, s02c, s02va and s03 ran out. The map, not the navigator, is the
   limit at the divider and the exit wall.

   **a66 s03 `dynamic`** (firm walls): the lobby cost nothing (crossbar at s14), the shut door
   was met at s20, then s21–s34 at the exit wall again. Its cost map at s28: the route ran
   through cells marked seen floor inside the solid beyond the tine's outer wall, written by
   `open_far` rays the perceiver read through that wall (floor seen far along a ray is the
   perceiver's weakest reading, R14), and nothing the drone sees marks the divider; the
   navigator, rightly, will not fly at a wall it can see, so no bump ever writes it either.
   **a67** = a66 with memory `a17g` (floor seen only beyond 2.5 m along a ray is weak: it
   costs 1.6 per metre and a wall beside it seals it; floor within 2.5 m, a visit and a
   confirmed open door's rays are known ground) and `planner.dead_end_seal`: at a `d01`-confirmed
   closed door within 2 m, the corridor the trail came down is sealed three cells either
   side, back to the first trail point where known ground opens past 2.5 m on a side (the
   crossbar; in the s02 hall at door B the first point already opens, so nothing is sealed).
   Sealed cells are recorded in `planner.sealed`, like stall cells. Replaying a66's own s03
   frames under a67 with the seals carried forward: from s25 the route is the 40 m way back
   and round, waypoint 3.5 m toward the crossbar, where a66's was 12–16 m into the divider.
   The round moves to a67; a66's remaining runs finish for the s02 record.

   **a66, all six** (`~/r30_shake_a66_runs`): `dynamic` 4/6 (s01 31 steps, s02c 29, s02va
   28, s02vc 55); s02a ran out (wrong side first, reached door A's position at s33 and
   turned away); s03 as above (lobby 4 steps, shut tine 35). Walls: missed 10.1%, phantom
   10.0%.

   **a67, all six** (`~/r30_shake_a67_runs`): `dynamic` 3/6 (s01 21 steps, s02c 28, s02va
   28); s02a, s02vc and s03 ran out. s03: 18 lobby steps (the navigator's marker-0 refusals
   again), the door read `closed` first at s46 and the drone spun at the exit wall. Its
   reads there: on every nose-on look the door leaf is `no_floor` with no doorway, so no
   door wall was ever written and `dead_end_seal` never fired; the door reads `closed` only
   from 3–8 m out (s40, s46, s51).
   **a68** = a67 with the dead end fired by any closed-door read whose point lies within
   5 m (the memory keeps closed-door points at the strip's range), and the corridor walk
   redone: one axis over the last 8 m of trail; a side is a corridor wall when a seen wall
   lies within four cells of any trail point in the window; a corridor walled on one seen
   side is sealed on both, eight cells deep (a four-deep band was skirted through the solid
   for 24 m against 40); the window ends where known floor reaches four cells sideways (the
   crossbar's own trail from a tine mouth; never inside a 3 m tine). Sealed cells yield to
   known floor seen later (a door looked through reopens). Replaying a66's and a67's own
   s03 frames with the seals carried forward: a66's gives the 40 m way back from s23, a67's
   28–31 m pointing out. The round moves to a68.

   **a68, all six** (`~/r30_shake_a68_runs`): `dynamic` 3/6 (s01 21 steps, s02c 43, s02va
   49). s03: the seal fired at the exit wall (s37–39, route 18 → 29 m), the drone turned
   back and reached the crossbar at s53–55, then with five steps left went back into tine R;
   18 lobby steps at the start had spent the budget. **s02a and s02vc ran out 32–33 m from
   the goal, boxed in the hall**: the both-sides seal fired there too, a route existed on
   53% of s02a's steps, and the fallbacks wandered. Walls: missed 16.9%, phantom 9.2%.

   **Why the corridor rule cannot be grounded (a69, defined, not flown).** a69 seals both
   sides only when each side showed a wall somewhere in the window. Measured on the
   trigger steps of the flown runs (walled trail points over window points, per side):
   a66 s03 s20 1/8 and 0/8; a67 s03 s40 and s46: window empty (known floor already reaches
   four cells sideways at the first point, inside the 3 m tine); a68 s03 s37 1/1 and 0/1;
   a68 s02a s7 1/6 and 1/6, s13 6/8 and 3/8, s25 1/5 and 1/5. The hall shows *more* walls
   beside the trail than the tine, from the far strips' phantom `no_floor` reads (the g05
   side bias, probe C2), and inside the tine the perceiver's far floor through the side walls
   makes the opening test fire at once. Nothing in g05's reads separates a 3 m corridor from
   a hall, so a68's rule has no honest trigger, and a69 was not flown.

   **Shakedown verdict (2026-11-03).** Six unscored `dynamic` runs per version, s03 first, alone
   on `:8004` (a64 on a copy on GPU 3, stopped after):

   | Version | dynamic solved | s03 shut tine after the closed door | s03 lobby | walls missed / phantom |
   |---|---|---|---|---|
   | a63 | 3/6 (s01, s02a, s02va) | 19 (never left) | 18 | 17.7 / 13.2 |
   | a64 (code picks) | 2/6 (s01, s02vc) | 31 | 4 | 18.6 / 13.7 |
   | a66 | **4/6** (s01, s02c, s02va, s02vc) | 35 | 4 | 10.1 / 10.0 |
   | a67 | 3/6 (s01, s02c, s02va) | 11 | 18 | 16.6 / 8.3 |
   | a68 | 3/6 (s01, s02c, s02va) | 10, left the tine, ran out at the crossbar | 18 | 16.9 / 9.2 |

   R25D (`a49`) solved 5/6 `dynamic` on a draw the family repeats at about 3–4 of 6
   (why_14). No turn-around streak above 3 in any version; walls in flight as R25D's or
   better. **The shakedown's pass rule (s03's shut-tine check holds) was not met by any
   version**, so by the rule set on 2026-11-02 R30 does not fly. The round's agent is set
   back to `a66`, the best measured (4/6, no s02 regression, the lobby fixed in its run);
   a67 and a68 are kept as flown experiments. What the s03 cell still needs is either a
   corridor signal this perceiver does not give, or a navigator that takes the planner's
   marker-0 turns (the 18 lobby steps in a63, a67 and a68 are the VLM declining "toward
   your target" on marker 0, the R11 pattern; code following the route left the lobby in
   4 steps every time). Whether to fly R30 on a66 against that rule, change the navigator
   (option B or C of the plan), or stop here, is the operator's call.

   **Operator (2026-11-03): change the navigator.** `a70` = `a66` with two navigator-side
   additions (`agent.NAVIGATOR_A70`, in the sha), both read off the lobby refusals' own
   reasons (a68 s03 `dynamic` s5–s9: "the turn around is only for when the target is behind
   you, but the planner says to head for the goal, so the target is ahead"):
   1. **Route-behind sentence.** While "toward your target" sits on the turn-around, the
      planner line gets a second line: "The next point on your route is behind you: the turn
      around is the move toward it." No distance or direction (`views.check` unchanged);
      recorded as `route_behind` per step.
   2. **Route critic** (`critic: route`, a13's machinery, option B of the plan generalised):
      when the pick carries no "toward your target" while an offered move does and carries no
      blocked, stopped-short or wall note, the navigator is asked once more with "Memory
      note: the planned route goes by [j] (toward your target), not by [i]. Choose again; you
      may keep [i] if the image shows it is right." The second answer stands; the rung is
      the model's (valid). Recorded in `critic` (`changed`). R9's critic changed 0 of 19
      picks, so the sentence is expected to do the work and the critic to measure the rest.
   Smoke (R25D's 627 recorded steps, stub picks): 0 failed; the sentence on 73 steps; the
   critic would have asked on 233 (a49's picks against a63's route, an upper bound).
   Pass rule unchanged: s03's shut-tine check, plus lobby ≤ 12 and "toward" on marker 0
   taken on ≥ 50% of offers. Readouts: `eval/r30_check.py` now prints `behind` and critic
   `changed/asked` per run.

## Builds on

R25D (`a49`). Branch `phase2/r30-pathfinder` from `phase2/r29n-host-noise`.

## Notes for the operator

- **Tests and smoke (no model):** `python -m pytest server/decider/tests -q`;
  `VLM_AGENT=a63 python eval/probes/a63_smoke.py` (and `a64`).
- **Preflight.** `python -m server.decider --profile remote --agent a70`; `/health` should report
  `cf82ad60b931`.
- **a64** is never a round: its rung `code` fails the validity check by construction.

## Outcome

Not flown.
