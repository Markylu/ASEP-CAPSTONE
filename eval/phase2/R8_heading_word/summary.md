# R8 Heading as a compass word: summary

**The mechanism held; the success count did not move, and the pre-registered rule credits no
outcome change to the heading. `a11` is not dropped (1 of 4 drop conditions met).** R8 has 6/18
successes, the same as R7 and as the no-op control R8N:
- `initial`: 5/6 (R7 4/6, R8N 3/6);
- `final`: 1/6 (R7 0/6, R8N 1/6);
- `dynamic`: 0/6 (R7 2/6, R8N 2/6).

What the heading word did:
- Heading arithmetic in reasons: **2** (R7 23, R8N 34). Reasons citing degrees: **0.6%** (R7 94%).
- Turn-arounds with the goal in view: **0** (R7 3, R8N 2). All five in R7 and R8N read a map
  angle as an image direction ("facing 221 degrees, which is toward the left side of the
  scene").
- **s02vc `initial` succeeds (19 steps)**, the step-12 turn-around that failed R6, R7 and R8N.
- R7's blocked-move behaviour kept: same pick after a blocked move 0 of 26, comparison line
  shown 26 of 26. Collisions **41** (R7 60, R8N 55).

Why no success change is credited:
- **The no-op edit (R8N) changed 6 of 18 outcomes against R7; the heading word changed 4.** The
  rule needs more than the noise floor. 4 is not more than 6.
- Three of R8's four flips are shared with R8N (s01 `final` gained, s01 and s02vc `dynamic`
  lost). The fourth, s02vc `initial`, is the targeted cell at the targeted step, and R8N does
  not gain it. One cell.
- See [R8N summary](../R8N_noop_control/summary.md) for the noise floor.

**Not citable.** Agent `a11` (`3859d0345560`), prompts `p12` (`f24e2855bfbe`) and `g02`
(`bf175c973dfb`), `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- Host: sctsvr6 (headless Linux, Xvfb, Mesa lavapipe, Docker), as R7 and R7C.
- Flown at `4c67fc6` on 2026-10-22 (sctsvr6 clock 2026-10-23), right after R8N at the same SHA,
  in tmux (59 minutes). **18 / 18 valid.**
- Probe: gate passed (spin 8/40, `lost` 5/25, `offcentre` 1/25; [probe](probe/probe_r8.md)).
  It predicted the six step-0 divergences exactly.
- Labels reviewed by Claude and confirmed by the operator on 2026-10-23.
- Pre-registration: [README.md](README.md). Reasoning analysis:
  [reasoning_analysis.md](reasoning_analysis.md). Manipulation check:
  [manipulation_check.md](manipulation_check.md).

## Result

| Arm | R0 | R5 | R7 `a10` | R8N `a12` (no-op) | R8 `a11` |
|---|---|---|---|---|---|
| initial | 5/6 | 6/6 | 4/6 | 3/6 | **5/6** |
| final | 0/6 | 2/6 | 0/6 | 1/6 | **1/6** |
| dynamic | 0/6 | 0/6 | 2/6 | 2/6 | **0/6** |

- Of the 12 failures, 9 are `replan_failure`, 2 `timeout` (s02c and s02vc `dynamic`) and 1
  `pre_change_failure` (s03 `dynamic`). No tags.
- Every cell, with first divergences: [reasoning_analysis.md](reasoning_analysis.md) §1.

## Pre-registered predictions

| Prediction | Result |
|---|---|
| initial 4–6/6, s02vc ✓ | held: 5/6, s02vc ✓ 19 |
| final, dynamic within R8N's spread of R7 | held: R8 changes 4 cells against R7, R8N 6 |
| turn-arounds with the goal in view at most 1 | held: 0 |
| heading arithmetic at most 3 | held: 2 |
| reasons citing degrees under 10% | held: 0.6% |
| same pick after a blocked move at most 15% | held: 0% |
| collisions at most 80 | held: 41 |
| progress claimed after a blocked move below 30% | held: 19% |

## Drop criterion

| Condition | R8 |
|---|---|
| goal-in-view turn-arounds not below R7's 3 | no: 0 |
| collisions above 80 | no: 41 |
| `final` + `dynamic` below R8N's | **yes: 1/12 against 3/12** |
| `initial` below R8N's | no: 5/6 against 3/6 |

1 of 4: **carried forward**, on the mechanism. The success counts say nothing either way.

## What the model did

See [reasoning_analysis.md](reasoning_analysis.md). In short:
- It uses the word in every reason and stopped adding degrees.
- The compass word brings its own, rarer frame error: 2 of 7 "facing X, so right is Y"
  sentences are wrong. At s02vc step 12 it writes the wrong compass direction and still picks the
  right-hand marker: it follows the image over its own sentence.
- s03 is 0/3, as in every round since R5.

## For the next round

1. Screen against the noise floor: one no-op sentence moves 6 of 18 outcomes.
2. The step-0 replay predicts every step-0 split: use it before flying.
3. Keep `a11` as the base.
4. Before the final round, spread from seeds or no-op variants, not one 18-run screen.
