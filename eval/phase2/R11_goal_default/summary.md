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
  short (R11C's unexplored ground 2%).
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
  [manipulation_check.md](manipulation_check.md).

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
| s01 | ✓ 14 → ✓ 14 [–] | ✓ 16 → ✓ 29 [4] | ✗ timeout → **✓ 29** [8] |
| s02a | ✓ 19 → ✓ 19 [–] | ✓ 32 → ✓ 26 [10] | ✗ replan → ✗ replan [8] |
| s02c | ✓ 14 → ✓ 19 [14] | ✓ 47 → **✗ replan** [4] | ✗ replan → ✗ replan [8] |
| s02va | ✓ 19 → ✓ 19 [–] | ✗ replan → **✓ 34** [2] | ✓ 48 → **✗ replan** [6] |
| s02vc | ✓ 19 → ✓ 19 [–] | ✗ replan → ✗ replan [3] | ✓ 38 → **✗ replan** [13] |
| s03 | ✗ replan → **✓ 39** [6] | ✓ 35 → ✓ 39 [15] | ✗ pre-change → ✗ replan [6] |

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
`a16` offers unexplored ground at the edge's cell nearest the goal; when the way is walled, that
cell lies against the wall in question. 37 of 38 detours were such points, and they stood about
10 steps each. s02c `final` (lost): 43 of 60 steps on detours, 9 collisions, revisit rate 0.40.
s02va and s02vc `dynamic` (lost): 45 and 32 steps on detours. A doorway was chosen once; R11C's
strategist chose doorways 78 times, and standing on a doorway gained 0.87 m a step.

**Where the drone did get round, the goal took it the rest of the way.** s02va `final` (gained)
stood on the goal for 29 of 34 steps around two short detours; s01 `dynamic` (gained) went round
the cube and closed in under the goal.

**The block note did not change the repeats.** With the narrow window, "blocked here before" was
offered on 25 moves and "stopped short here before" on 154; the navigator picked one of them
once, and 15 of 16 near-repeat collisions carried no note at all.

## R11C as a determinism check

R11C (`a14` at `caa209a`) repeats R10 (`a14` at `76f8a05`) in **11 of 18** pick sequences and 16
of 18 outcomes (it gains s01 `final`, loses s02a `dynamic`). [R11C summary](../R11C_a14_control/summary.md).

## For the next round

1. **Detour targets that lead round the wall, not into it.** Offer doorways first when the way is
   walled, and unexplored ground at a point the drone can reach with the goal off to one side,
   not the edge cell nearest the goal.
2. **Shorter detours.** Hand back to the goal once the drone has moved a few metres sideways of
   the wall, not after 12 steps.
3. **The block note is not the lever.** Two windows (45°, 15°/25°) both left the repeat
   collisions unwarned or warned everything. A note for "this move continues into the wall you
   just hit" may need the perceiver's view, not the map.
4. **Keep the parts that held:** goal by default where the way is open (`initial` 6/6), wall-aware
   "toward", the role-view leak check.
