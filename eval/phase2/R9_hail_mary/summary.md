# R9 Orchestrated agent with a spatial memory: summary

**The map worked; the agent spun. `a13` is dropped (2 of 4 drop conditions), and the
pre-registered rule credits no outcome change to the bundle.** R9 has 6/18 successes, the same as
its control R9C:
- `initial`: 5/6 (R9C 5/6);
- `final`: 0/6 (R9C 1/6);
- `dynamic`: 1/6 (R9C 0/6).

What the memory did:
- **No pick went into a heading known to be blocked:** 0 of 871 decisions carried "blocked here
  before". On the probe's 255 recorded trap steps, earlier agents did it 36% of the time.
- Collisions **34** (R9C 42, R8 41, R7 60). Revisit rate 15% (R7 ~19%).
- **s03 got further than any round since R5.** `initial` and `final` reached the crossbar
  (min x 5.2; R9C 14.3 and 14.8, R7 pinned at 15.2). `dynamic` flew a tine to its exit (min x
  −5.8) and triggered the switch at step 29; R9C and R8 ended there as `pre_change_failure`.
- The perceiver named the goal's strip within one on 112 of 113 in-view frames.

Why it is dropped:
- **`spin_failure` on 4 runs** (R9C 0): s01 `final` (7 turn-arounds in a row), s02va `final` (6),
  s02vc `dynamic` (5), s03 `dynamic` (5). Turn-arounds are 12% of picks (R9C 9%).
- **`final` + `dynamic` 1/12** (drop below 3/12).

Why no success change is credited:
- R9 changes **2 of 18** outcomes against R9C: it gains s02va `dynamic` (29 steps) and loses
  s01 `final` (a spin from step 6; R9C and R8 reach the goal there). The rule needs more than 6
  (R8N's noise floor) with more gained than lost.

**Not citable.** Agent `a13` (`3de550e110e7`): navigator `p14` (`31a9f28eaf94`), perceiver `g03`
(`3531e4d9ade9`), strategist `q01` (`40fb0fbc3285`), memory `eceb875a68a3`; `Qwen3-VL-30B-A3B`,
remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R7 and R8.
- Flown at `756345b` on 2026-10-23, 16:18–17:36 UTC, in tmux, followed by R9C at the same SHA.
  **18 / 18 valid.** Mean step 3.2 s (perceiver about 2 s); the longest run took under 6 minutes.
- Shakedown before the round: one unscored `dynamic` run per site, all records complete, no run
  over 317 s (runs kept on sctsvr6 in `~/r9_shakedown/`, not part of the round).
- Probe: gate passed ([probe/probe_r9.md](probe/probe_r9.md)).
- Labels reviewed by Claude on 2026-10-23 and confirmed by the operator on 2026-10-24.
- Pre-registration: [README.md](README.md). Manipulation check:
  [manipulation_check.md](manipulation_check.md).

## Result

| Arm | R5 | R7 `a10` | R8 `a11` | R9C `a11` | R9 `a13` |
|---|---|---|---|---|---|
| initial | 6/6 | 4/6 | 5/6 | 5/6 | **5/6** |
| final | 2/6 | 0/6 | 1/6 | 1/6 | **0/6** |
| dynamic | 0/6 | 2/6 | 0/6 | 0/6 | **1/6** |

- Of the 12 failures, 10 are `replan_failure` and 2 `timeout` (s02a and s02c `final`, both got
  through the divider and ran out of steps 8.4 and 12.7 m from the goal). Tags: `spin_failure` ×4.
- Collisions by site (R9C / R9): s01 9 / 2; s02a 11 / 2; s02c 8 / 9; s02va 6 / 8; s02vc 2 / 3;
  s03 6 / 10.

### Every cell

✓ steps to goal, or ✗ label. First pick that differs from R9C in brackets.

| Site | initial R9C → R9 | final R9C → R9 | dynamic R9C → R9 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 [11] | ✓ 42 → **✗ replan, spin** [0] | ✗ replan → ✗ replan [4] |
| s02a | ✓ 14 → ✓ 14 [12] | ✗ replan → ✗ timeout [0] | ✗ replan → ✗ replan [5] |
| s02c | ✓ 14 → ✓ 56 [12] | ✗ replan → ✗ timeout [0] | ✗ timeout → ✗ replan [5] |
| s02va | ✓ 19 → ✓ 19 [11] | ✗ replan → ✗ replan, spin [1] | ✗ replan → **✓ 29** [6] |
| s02vc | ✓ 19 → ✓ 19 [11] | ✗ replan → ✗ replan [0] | ✗ timeout → ✗ replan, spin [4] |
| s03 | ✗ replan → ✗ replan [0] | ✗ replan → ✗ replan [0] | ✗ pre-change → ✗ replan, spin [0] |

## Pre-registered predictions

| Prediction | Result |
|---|---|
| initial ≥ 5/6 | held: 5/6 |
| final + dynamic ≥ 5/12, above R9C | **missed:** 1/12 (R9C 1/12) |
| more than 6 of 18 outcomes changed against R9C, more gained than lost | **missed:** 2 changed, 1 gained, 1 lost |
| s03 ≥ 1/3 | **missed:** 0/3 (but deepest progress since R5) |
| collisions below R7's 60 | held: 34 |
| `spin_failure` runs 0 | **missed: 4** |
| picks carrying "blocked here before" < 5% | held: 0% |
| revisit rate below R7's ~19% | held: 15% |

## Drop criterion

`a13` is dropped if two or more hold. Two do.

| Condition | R9 |
|---|---|
| `final` + `dynamic` below 3/12 | **yes: 1/12** |
| `initial` below 4/6 | no: 5/6 |
| any run invalid on the wall clock | no: 18/18 valid, longest under 6 min |
| `spin_failure` on 2 or more runs | **yes: 4** |

## What the model did

**It obeyed the map's block notes completely, and it spun at turn-around.** Every one of the four
spins is a run of turn-arounds where the critic objected ("third turn-around in four steps") on
nearly every step and the model kept its pick every time (critic: 19 objections, 0 picks changed
across the round). Two patterns:

- **Wall, turn, open floor, turn again** (s01 `final`, s02vc `dynamic`, s03 `dynamic`). Facing the
  wall, all five strips read "wall close (seen now)" and turning is right. After the turn, every
  move reads "new ground", and the model turns again: "the drone is currently facing a wall, as
  indicated by … the fact that it stopped short in the previous step". It argues from the
  recent-moves line, not the notes or the image, and cannot tell which way it now faces.
- **A target behind** (s02va `final`, target `back_to_step_1`). "Toward your target" moves between
  turn-around and [2] on alternate steps; the model reasons each time that the target "is behind
  the current heading" and turns.

**Targets churned.** The strategist was asked on 321 of 871 steps (37%), most often because the
target had been reached or was no longer open (115) or a new doorway was in view (98). The median
run changed target 15.5 times. The perceiver reports a doorway on about a third of frames, so the
plan rarely held for long.

**The goal estimate is good only before a change.** Median error 1.6 m on `initial` runs, 18.6 m
on `final` and 18.0 m on `dynamic`. With the goal out of view for most of those runs, the few
phantom sightings (22 of 758 out-of-view frames, 2.9%) carry the least-squares estimate.

## R9C as a determinism check

R9C (`a11` at `756345b`) made the same picks as R8 (`a11` at `4c67fc6`) in 16 of 18 cells, and every
outcome is the same. The two that differ are both s03 (`initial` from step 2, `dynamic` from
step 0). This branch's decider changes did not touch `a11`. [R9C summary](../R9C_a11_control/summary.md).

## For the next round

1. **Turn-around is where the bundle fails.** Options, in order of how little they change:
   tell the navigator after a turn which way it now faces in the notes ("you just turned around:
   the wall you saw is behind you"); keep the target's direction words fresh in the critic's
   note; or a hard rule against a third turn-around in four steps, which needs the operator's
   ruling (R9 kept the model's pick final).
2. **Reject phantom sightings** before they enter the goal estimate (a ray that disagrees with the
   others by more than a strip, or one sighting not repeated on the next frame).
3. **Damp the strategist:** do not re-ask for a doorway already on the list; keep a target until it
   is reached or closed.
4. The block notes and the map are worth keeping: zero repeats at known blocks, the fewest
   collisions since R1 (31), deepest s03 progress since R5.
