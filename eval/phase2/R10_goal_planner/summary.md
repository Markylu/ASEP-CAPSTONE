# R10 Goal known to the planner, no double turn: summary

**`final` + `dynamic` 6/12, the most of any round; not credited, by one cell.** R10 has 11/18
successes against its control R10C's 7/18:
- `initial`: 5/6 (R10C 5/6);
- `final`: 3/6 (R10C 1/6);
- `dynamic`: 3/6 (R10C 1/6).

R10 changes **6 of 18** outcomes against R10C (5 gained, 1 lost). The pre-registered rule credits
the bundle only above R8N's noise floor of 6, so **no success change is credited**. `a14` is
**not dropped** (0 of 4 drop conditions) and is carried forward.

What changed:
- **No spins.** No `spin_failure` (R10C 4), and no two turn-arounds in a row anywhere (longest
  run 1; R10C 12). Turn-arounds 8.6% of picks (R10C 14.0%). [0] was left off 65 times and no
  pick ever named it.
- **Collisions 36** (R10C 57, R9 34).
- **s03 solved once** (`final`, 35 steps, 4 collisions): the first s03 success in R6–R10.
- **The strategist steered by the goal more.** The goal was the standing target on 232 steps
  (R10C 206); 59% of its calls chose a target at least 3 m nearer the goal than the drone (R10C
  32%). It was asked less (30% of steps; R10C 40%) and changed target less (median 8 a run; R10C
  13).

**Not citable.** Agent `a14` (`63ad006476b6`): navigator `p14` (`31a9f28eaf94`), perceiver `g03`
(`3531e4d9ade9`), strategist `q02` (`f3a866c9d927`), memory `eceb875a68a3` + a14 wording
`0075a8a0e5c0`; `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R7–R9.
- Flown at `76f8a05` on 2026-10-25, 02:15–03:21 UTC, in tmux (`~/r10_fly.sh`), followed by
  R10C at the same SHA (03:21–04:44). **18 / 18 valid.** Mean step 3.1 s; the longest run took
  5.5 minutes.
- Shakedown before the round: one unscored `dynamic` run per site in a scratch clone, every
  record complete, `hidden` present and never picked, the goal on every strategist list, no goal
  distance or direction in any navigator text, no run over 314 s (3/6 reached the goal; runs kept
  on sctsvr6 in `~/r10_scratch`, not part of the round).
- Probe: gate passed ([probe/probe_r10.md](probe/probe_r10.md)).
- Labels reviewed by Claude and confirmed by the operator on 2026-10-25.
- Pre-registration: [README.md](README.md). Manipulation check:
  [manipulation_check.md](manipulation_check.md).

## Result

| Arm | R5 | R7 `a10` | R8 `a11` | R9 `a13` | R10C `a13` | R10 `a14` |
|---|---|---|---|---|---|---|
| initial | 6/6 | 4/6 | 5/6 | 5/6 | 5/6 | **5/6** |
| final | 2/6 | 0/6 | 1/6 | 0/6 | 1/6 | **3/6** |
| dynamic | 0/6 | 2/6 | 0/6 | 1/6 | 1/6 | **3/6** |

- Of the 7 failures, 5 are `replan_failure`, 1 `timeout` (s01 `dynamic`: round the cube, out of
  steps 6.2 m from the goal) and 1 `pre_change_failure` (s03 `dynamic`). No tags.
- s03 `dynamic` is pick for pick and pose for pose the same run as s03 `initial`: the drone never
  entered a tine, so the switch never fired and the world stayed as `initial`.
- Collisions by site (R10C / R10): s01 2 / 2; s02a 11 / 7; s02c 17 / 2; s02va 6 / 3; s02vc 4 / 6;
  s03 17 / 16.

### Every cell

✓ steps to goal, or ✗ label. First pick that differs from R10C in brackets.

| Site | initial R10C → R10 | final R10C → R10 | dynamic R10C → R10 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 [–] | ✗ replan, spin → ✗ replan [7] | ✓ 48 → **✗ timeout** [7] |
| s02a | ✓ 49 → ✓ 14 [13] | ✓ 58 → ✓ 32 [6] | ✗ replan → **✓ 50** [7] |
| s02c | ✓ 32 → ✓ 19 [14] | ✗ replan → **✓ 47** [2] | ✗ replan → ✗ replan [10] |
| s02va | ✓ 19 → ✓ 19 [–] | ✗ replan, spin → ✗ replan [3] | ✗ ignore → **✓ 48** [7] |
| s02vc | ✓ 19 → ✓ 19 [–] | ✗ replan → ✗ replan [10] | ✗ replan, spin → **✓ 38** [5] |
| s03 | ✗ replan, spin → ✗ replan [7] | ✗ replan → **✓ 35** [5] | ✗ replan → ✗ pre-change [7] |

## Pre-registered predictions

| Prediction | Result |
|---|---|
| initial ≥ 5/6 | held: 5/6 |
| final + dynamic ≥ 4/12, above R10C | held: 6/12 (R10C 2/12) |
| more than 6 of 18 outcomes changed against R10C, more gained than lost | **missed:** 6 changed, 5 gained, 1 lost |
| `spin_failure` runs 0 | held: 0 |
| turn-arounds < 8% of picks | **missed:** 8.6% (R10C 14.0%, R9 12.1%) |
| steps with no target < 10% | **missed:** 16.3% (R10C 15.9%, R9 22.3%) |
| strategist calls choosing a target ≥ 3 m nearer the goal ≥ 60% | **missed:** 58.5% (R10C 31.8%, R9 35.2%) |
| collisions at most R10C's | held: 36 (R10C 57) |

## Drop criterion

`a14` is dropped if two or more hold. None do.

| Condition | R10 |
|---|---|
| `final` + `dynamic` below 3/12 | no: 6/12 |
| `initial` below 4/6 | no: 5/6 |
| any run invalid on the wall clock | no: 18/18 valid, longest 5.5 min |
| `spin_failure` on 2 or more runs | no: 0 |

## What the model did

**The turn rule did what it was built for, and nothing else.** Every turn-around was followed by
a step with [0] left off (65 of 65), and the navigator took a forward move each time. The four
patterns behind R9's spins (wall, turn, open floor, turn again; a target behind) never ran past
one turn. The rule cannot help where the trouble is not turning: s03 `initial`/`dynamic` circled
the lobby (min x 4.92, never into the stem) with only 9 turn-arounds, chasing unexplored ground
(30 of 60 steps on a frontier target).

**Knowing the goal mattered where a wall stood between the drone and it.** The `final` and
`dynamic` gains on s02 and s03 end with the goal as the standing target (s02a `dynamic` 11 of
its last 12 steps, s03 `final` 8 of its last 12); the drone went through the open door or the
open tine and then had a target to follow. Where the strategist did not pick the goal, the run
failed the way R9 did: s02va `final` held the goal for 1 step of 60 and ended at the divider;
s02vc `final` spent 37 steps on doorway targets.

**It still does not always read "the goal is behind the wall" correctly.** s01 `final` (cube in
place from step 0) held the goal on only 8 steps, most of the run on frontiers or no target, and
finished 34.8 m away, behind its start. s01 `dynamic` did get round the cube and then ran out of
steps 6.2 m from the goal with the goal as target.

**The strategist's split trigger was used.** "The doorway you chose is closed or already passed"
30 and "the drone has reached the target you chose" 16, where R10C's single sentence fired 142
times; R10C's strategist was asked on 40% of steps, R10's on 30%.

## R10C as a determinism check

R10C (`a13` at `76f8a05`) repeats R9 (`a13` at `756345b`) in **7 of 18** pick sequences, and in
15 of 18 outcomes (it gains s01 `dynamic` and s02a `final`, and loses s02va `dynamic`). Three
cells part at step 1 or 2. `a11` repeated in 16 of 18 pick sequences and every outcome (R9C
against R8). `a13` makes two to four model calls a step, and one
different perceiver answer changes the map, the notes and every pick after it. **Re-flying the
unchanged `a13` moved 3 of 18 outcomes**; `a11` moved none. R10's 6 changes are twice that, but
the pre-registered floor is R8N's 6 (a no-op prompt edit on a single-call agent), and no floor has
been measured for `a14` itself.
[R10C summary](../R10C_a13_control/summary.md).

## For the next round

1. **Measure the floor for `a14` itself.** Fly `a14` again unchanged (a re-fly control) and count
   how many outcomes move. `a13` moved 3 of 18 between two flights; whether `a14`'s 6 against
   R10C is more than its own run-to-run variation is not known.
2. **Turn rule without the hidden action** (the operator's reservation): `a14` with [0] always
   offered, so the spin fix and the goal-known planner can be told apart.
3. **The strategist still skips the goal when it is not in view** (s02va `final` 1 step of 60,
   s01 `final` 8). An option, in order of how little it changes: make the goal the standing target
   unless the last move toward it was blocked, and ask the strategist only for a detour.
4. **s03 `initial`**: the lobby loop is not a turn problem. The drone never tries the stem at
   y ≈ 0 when a frontier is listed.
