# R11 Goal by default, detours on demand: summary

**11/18, the same as its control; `final` + `dynamic` 5/12 against R11C's 6/12. Not credited,
not dropped.** R11 (`a16`) against R11C (`a14` re-flown):
- `initial`: **6/6** (R11C 5/6);
- `final`: 4/6 (R11C 4/6);
- `dynamic`: **1/6** (R11C 2/6).

R11 changes **6 of 18** outcomes against R11C (3 gained, 3 lost). The floor is
F = max(6, R11C against R10) = max(6, 2) = 6, and the bundle is credited only above F with more
gained than lost: **no success change is credited**. `a16` is **not dropped** (0 of 4 drop
conditions).

What changed:
- **The parts ran as built.** The goal stood on 47% of steps (R11C 33%), the strategist was
  asked on 5% (R11C 31%), "toward your target" never sat on a walled move (R11C 40 times), and no
  navigator text worded the goal's position.
- **Collisions 58** (R11C 24, R10 36): the most since R10C's 57.
- **The detours did not get nearer the goal.** 376 steps stood on goal-side unexplored ground,
  gaining 0.01 m a step toward the goal, and 13% of the forward moves made under them stopped
  short (R11C's unexplored ground 2%). The targets could not be reached: on 34 of 37 frontier picks
  the straight line to the target crosses a wall, and only 1 of 33 detours ended "reached"
  ([failure_analysis.md](failure_analysis.md)).
- **`a14` re-flown moved 2 of 18 outcomes** (R11C against R10) and repeated 11 of 18 pick
  sequences: its run-to-run floor is lower than `a13`'s (3 of 18 outcomes, 7 of 18 sequences
  repeated).

**Not citable.** Agent `a16` (`6d614e3c4450`): navigator `p14` (`31a9f28eaf94`), perceiver `g03`
(`3531e4d9ade9`), strategist `q03` (`1ec0f511a6e0`), memory `eceb875a68a3` + a14 wording
`0075a8a0e5c0` + a16 `1af123e381c0`; route planner and progress monitor in code
(`server/decider/planner.py`); `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R7–R10.
- Flown at `caa209a` on 2026-10-27, 17:44–18:43 UTC, in tmux (`~/r11_fly.sh`, checkout
  `~/asep-r11`), followed by R11C at the same SHA (18:43–19:46). **18 / 18 valid.** Mean step
  2.9 s.
- Shakedown before the round: one unscored `dynamic` run per site in a scratch clone
  (`~/r11_shake`), every record complete, `a16`'s sha on every record, no errors, no goal
  position in any navigator text, [0] hidden 59 times and never picked, longest run 5.5 minutes
  (1/6 reached the goal; not part of the round).
- Probe: `a15` failed ([probe/probe_a15.md](probe/probe_a15.md)); `a16` passed the gate as
  re-set by the operator on 2026-10-27 ([probe/probe_a16.md](probe/probe_a16.md), README "Gate
  change").
- Labels reviewed by Claude and confirmed by the operator on 2026-10-28. No overrides.
- Pre-registration: [README.md](README.md). Manipulation check:
  [manipulation_check.md](manipulation_check.md). Failure analysis (after labelling, read-only):
  [failure_analysis.md](failure_analysis.md).

## Result

| Arm | R9 `a13` | R10C `a13` | R10 `a14` | R11C `a14` | R11 `a16` |
|---|---|---|---|---|---|
| initial | 5/6 | 5/6 | 5/6 | 5/6 | **6/6** |
| final | 0/6 | 1/6 | 3/6 | 4/6 | **4/6** |
| dynamic | 1/6 | 1/6 | 3/6 | 2/6 | **1/6** |

- Of the 7 failures, all 7 are `replan_failure`. No tags (no spin, no goal-identifier tag).
- **s03 `initial` solved** (39 steps), the first since R5. s03 `final` also solved (39 steps;
  `initial` and `final` flew the same run), s03 `dynamic` not.
- Collisions by site (R11C / R11): s01 1 / 2; s02a 3 / 5; s02c 1 / 16; s02va 2 / 8; s02vc 6 / 8;
  s03 11 / 19.

### Every cell

✓ steps to goal, or ✗ label. First pick that differs from R11C in brackets.

| Site | initial R11C → R11 | final R11C → R11 | dynamic R11C → R11 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 [–] | ✓ 16 → ✓ 29 [3] | ✗ timeout → **✓ 29** [7] |
| s02a | ✓ 19 → ✓ 19 [–] | ✓ 32 → ✓ 26 [9] | ✗ replan → ✗ replan [7] |
| s02c | ✓ 14 → ✓ 19 [13] | ✓ 47 → **✗ replan** [3] | ✗ replan → ✗ replan [7] |
| s02va | ✓ 19 → ✓ 19 [–] | ✗ replan → **✓ 34** [1] | ✓ 48 → **✗ replan** [5] |
| s02vc | ✓ 19 → ✓ 19 [–] | ✗ replan → ✗ replan [2] | ✓ 38 → **✗ replan** [12] |
| s03 | ✗ replan → **✓ 39** [5] | ✓ 35 → ✓ 39 [14] | ✗ pre-change → ✗ replan [5] |

Steps are 0-based, as in the R10 and R11C summaries (corrected 2026-10-28; first written 1-based).
4 of 18 cells have the same pick sequence as R11C from step 0 to the end.

## Pre-registered predictions

| Prediction | Result |
|---|---|
| `initial` ≥ 5/6 | held: 6/6 |
| `final` + `dynamic` above R11C | **missed:** 5/12 (R11C 6/12) |
| more than F of 18 outcomes changed against R11C, more gained than lost | **missed:** 6 changed (F = 6), 3 gained, 3 lost |
| steps with the goal as standing target ≥ 50% | **missed:** 47% (329/706; R11C 33%) |
| steps on unexplored ground, backtrack or none ≤ 25% | **missed:** 53% (376; R11C 43%) |
| strategist calls ≤ 15% of steps | held: 5% (38; R11C 31%) |
| "toward your target" on an action with a not-open note: 0 | held: 0 (R11C 40) |
| picked moves with a block note that stopped short ≥ 65% | held, on 1 pick: 1/1 |
| steps with a block note on every forward move: 0 | **missed:** 1 |
| collisions at most R11C's | **missed:** 58 (R11C 24) |
| `spin_failure` runs 0 | held: 0 |

## Drop criterion

`a16` is dropped if two or more hold. None do.

| Condition | R11 |
|---|---|
| `final` + `dynamic` below 3/12 | no: 5/12 |
| `initial` below 4/6 | no: 6/6 |
| any run invalid on the wall clock | no: 18/18 valid |
| `spin_failure` on 2 or more runs | no: 0 |

## What the model did

**Where the way to the goal was open, the goal by default worked.** Every `initial` run reached
the goal, five of them in 14–19 steps with the goal standing the whole way, and s03 `initial`
went through after two detours. The strategist was not asked at all on five of the six `initial`
runs.

**Where a wall stood between the drone and the goal, the detours sent it back into the wall.**
`a16` offers unexplored ground at the edge's cell nearest the goal. The memory marks floor free 6 m
along every perceiver ray, collisions never write wall cells, and a newer look erases older wall
marks, so that cell lies beyond the wall or inside it, not in front of it: 25 of 27 s02 frontier
picks were on the goal side of the divider, 5 picks were inside a solid object, and with a perfect
perceiver the top frontier would still be beyond or inside a wall at 37 of 38 strategist calls.
37 of 38 detours were such points, and they stood about 10 steps each; `q03` re-picked the same
point 7 times. s02c `final` (lost): 43 of 60 steps on detours, 9 collisions, revisit rate 0.40.
s02va and s02vc `dynamic` (lost): 45 and 32 steps on detours. A doorway was chosen once; R11C's
strategist chose doorways 78 times, and standing on a doorway gained 0.87 m a step. Doorways were on
the menu at 19 of 38 calls but worded "as far" or "farther" (placed on the near side of the wall,
against frontiers beyond it, under a prompt that says to prefer nearer), and the real open door was
in memory at 14 of the s02 calls but listed at 4: it was struck as "passed" once the drone came
within 1.5 m, without going through. Menu order was not the cause: doorways are listed first.

**Where the drone did get round, the goal took it the rest of the way.** s02va `final` (gained)
stood on the goal for 29 of 34 steps around two short detours; s01 `dynamic` (gained) went round
the cube and closed in under the goal.

**The block note did not change the repeats.** With the narrow window, "blocked here before" was
offered on 25 moves and "stopped short here before" on 154; the navigator picked one of them
once, and 15 of 16 near-repeat collisions carried no note at all. The perceiver had said open far
on the picked strip for 48 of the 57 stopped-short moves, so the missing piece is the map (no wall
written on a collision), not the perceiver's view.

**Two things the round's numbers hide.** 10 of the 14 "goal in view" hand-backs were goal
sightings without line of sight, 7 of them in failed runs; a 20° check against the true bearing
rejects all 10 and keeps the 4 real ones. And on byte-identical frames 50 of 178 perceiver outputs
differ between R11 and R11C at temperature 0; in s02a and s02c `dynamic` one such read of the closed
door B seeded the first unreachable target. Of the gains, s01 `dynamic` and s03 `initial` went
through on an unreachable target and a false sighting respectively (inferred: luck).

**The navigator is not what changed.** It follows a forward "toward your target" 71% of the time
and a goal note every time in both rounds, and its stated reason contradicts the notes or the
outcome on 24% of steps in both. `a16` left the target behind the drone, with no forward action
carrying "toward", on 185 steps (R11C 113), over which the drone moved 158 m away from the goal
(R11C 47 m).

## R11C as a determinism check

R11C (`a14` at `caa209a`) repeats R10 (`a14` at `76f8a05`) in **11 of 18** pick sequences and 16
of 18 outcomes (it gains s01 `final`, loses s02a `dynamic`). [R11C summary](../R11C_a14_control/summary.md).

## For the next round

Ranked in [failure_analysis.md](failure_analysis.md), Q6, each with an offline test.

1. **Reachable detour targets (code).** A collision or stopped-short move writes wall cells that a
   later look cannot erase; `open_far` rays stop at about 4 m; a frontier is offered only if a path
   over known free cells reaches it; a failed detour's target is dropped. Shortening detours alone
   would only ask `q03` again, and it re-picked the same unreachable point 7 times.
2. **"toward" when the target is behind (code).** Put it on the sharpest forward move on the
   target's side when nothing in the fan is within 55°, and never hide [0] while it alone carries
   "toward".
3. **Doorways (code and `q03` wording).** Mark a doorway passed only on crossing the wall; when
   walled, list doorways first and drop "prefer nearer" for them.
4. **Goal sightings checked against the true bearing (code)** before they hand a detour back.
5. **The block note is not the lever.** Two windows (45°, 15°/25°) both left the repeat
   collisions unwarned or warned everything; with walls written on collision (1), the map can
   warn without the perceiver.
4. **Keep the parts that held:** goal by default where the way is open (`initial` 6/6), wall-aware
   "toward", the role-view leak check.
