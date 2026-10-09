# R1 No goal hint: summary

**Hypothesis held (screening).** With no goal distance or bearing in the prompt, `final` and
`dynamic` went from 0/12 to 3/12. `initial` held at 5/6, and the manipulation check passed on every
measure. This is one seed per cell, so it is a screen, not an effect size
(`docs/phase2-test-plan.md` §3). Pre-registration: [README.md](README.md).

**Not citable.** Flown at `32ef803` on 2026-10-08, 15:39–16:10 UTC. The runs used
`Qwen3-VL-30B-A3B` on the remote profile, at temperature 0, with agent `a01` (`48f6b3973760`) and
prompt `p03` (`e476e566cea2`). The decider ran on :8010 because the operator's tunnel holds :8000.
Labels were reviewed by Claude and confirmed by the operator on 2026-10-09.

- **18 / 18 runs valid on the first attempt.** Every replay was exact, every `run.json` has
  `git_dirty: false`, and the agent sha matches the round lock.
- Spawn jitter for seed 1 is the same as in R0: dz −0.170 m, dyaw −2.23°.

## Result

R0 is Phase 1's seed-1 runs under `a00` (`eval/phase2/results/results.md`).

| Arm | R0 | R1 | success | ignore | replan | collision | timeout | latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|
| initial | 5/6 | **5/6** | 5 | – | 1 | 0 | 0 | 1.30 / 1.71 s |
| final | 0/6 | **2/6** | 2 | – | 2 | 0 | 2 | 1.44 / 1.75 s |
| dynamic | 0/6 | **1/6** | 1 | 0 | 2 | 0 | 3 | 1.42 / 1.84 s |

Collisions over all 18 runs: **31** (R0: 675), at about the same total number of steps (870 vs 860).

### Every cell

✓ steps to goal, or ✗ label, with the R0 result alongside.

| Site | initial R0 → R1 | final R0 → R1 | dynamic R0 → R1 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 | ✗ replan → ✗ timeout | ✗ ignore → ✗ replan |
| s02a | ✓ 14 → ✓ 14 | ✗ replan → ✗ timeout | ✗ ignore → **✓ 60** |
| s02c | ✓ 14 → ✓ 14 | ✗ replan → **✓ 34** | ✗ ignore → ✗ timeout |
| s02va | ✓ 19 → ✓ 55 | ✗ replan → ✗ replan | ✗ ignore → ✗ timeout |
| s02vc | ✓ 19 → ✓ 55 | ✗ replan → **✓ 24** | ✗ ignore → ✗ timeout |
| s03 | ✗ replan → ✗ replan | ✗ replan → ✗ replan | ✗ pre-change → ✗ replan |

Four of R0's five `ignore_change` cells became `timeout` or `success`: the agent got through the new
route. The fifth, s01, became `replan_failure`: the agent saw the cube and turned away, but never
got round it. Nothing is labelled `ignore_change` in R1.

## Manipulation check

`python eval/agent_evidence.py eval/phase2/R1_no_goal_hint`, saved as
[manipulation_check.md](manipulation_check.md), against Phase 1's [evidence.md](evidence.md):

| Arm | reason cites bearing | reason cites distance | nearest-bearing pick (chance 20%) | turn-around pick |
|---|---|---|---|---|
| initial | 100% → **0%** | 100% → **0%** | 74% → 58% | 0% → 8% |
| final | 100% → **0%** | 98% → **0%** | 81% → **12%** | 1% → 8% |
| dynamic | 100% → **0%** | 99% → **0%** | 81% → **14%** | 0% → 12% |

The model never invented a bearing or a distance. In `final` and `dynamic` the pick nearest the
goal's true bearing fell below chance. The agent routes around obstacles instead of pointing at a
goal it cannot see. `initial` stays well above chance because the goal is in view at spawn, so
flying at it and following the bearing are the same action.

## What the model did

**It sees the change and says so.** On all five s01/s02 `dynamic` runs, the first reason after
the change (step 4) refers to it. In R0 none did. Two reasons read the door switch correctly and
act on it:

- s02va, step 4: "The middle door (marker 3) is closed. The rightmost door (marker 5) is open". It
  picks 5, and door A is on the agent's right.
- s02vc, step 4: it picks marker 1, "an open doorway on the left", because the other markers
  "point toward closed doors". That is door C.
- s01, step 4: "facing a wall directly ahead, as indicated by the 'WALL' label", and it turns
  around. R0 flew into the cube on all 10 Phase 1 cube runs and never turned around.

**It no longer pins.** Collisions fell from 675 to 31. Only s03 `dynamic` keeps the Phase 1 pattern:
11 of its 16 collisions follow a reason calling the path clear (`path_hallucination`).

**New failure: it finds the route, then loses the goal.** All five `timeout` runs got through
(s01 `final` round the cube; s02a `final`, s02c/va/vc `dynamic` through the new door) and came
within 8–13 m of the goal. Then they flew back out the way they came. Two ended further from the
goal than the 24 m they started at: s02va `dynamic` 26.4 m and s02vc `dynamic` 33.2 m. s01
`final` sees the beam again at steps 52–56, from about 20 m out, and never closes on it. Without
the bearing there is nothing to keep the agent heading toward a goal once the beam leaves the
frame. s02c `dynamic` was closing (9.1 m, goal in view at steps 55–59) when the step limit hit,
and s02a `dynamic` reached the goal on step 60, so the step limit binds now where it never did
in R0.

**s03.** `dynamic` reached its trigger, at step 44. That is the first s03 `dynamic` run in the
project to fire the change (Phase 1: 5/5 `pre_change_failure`). It acknowledged the closed door at
step 45 but never entered the other tine. `initial` and `final` never reached the divider (min x
7.4, against R0 pinned at 5.2) and drifted back toward spawn, ending 30–35 m out. The goal is never
in line of sight on s03.

**Cost on `initial`.** s02va and s02vc took 55 steps against 19 in R0. Both succeed with 0
collisions, but with 5 steps to spare.

## Against the predictions

| Prediction (README) | Outcome |
|---|---|
| `initial` 4–5/6, s03 stays failed | **Held**: 5/6, s03 failed. s02va/vc nearly 3× slower |
| `final` ≥1/6, from s01 or s02va/vc | **Held**: 2/6, from s02vc (predicted) and s02c (not predicted). s01 got round the cube but timed out |
| `dynamic` ≥1/6, from the same sites | **Held in count, wrong site**: 1/6 from s02a, which I called least likely |
| Fewer `ignore_change` than R0's 5 | **Held**: 0 |
| s02a/s02c least likely to improve | **Wrong**: 2 of their 4 `final`/`dynamic` cells succeeded, the most of any family |
| Manipulation check | **Passed** on all three measures |

**Drop criterion: not met.** `final` + `dynamic` is 3/12 (the criterion was 0/12), and `initial` is
5/6 (the criterion was ≤ 3/6). `a01` carries forward.

**The rival explanation (README Evidence 4) is weakened.** Phase 1's "the model does not see
the walls" reading predicted no change here. Instead, the same model with the same image names
closed doors and the cube, and picks the open door. At least for s01 and s02, the Phase 1
`path_hallucination` came with following the bearing, not with perception. s03 is the exception
and still hallucinates a clear path.

## For the next round

The operator picks the change. This round points at one gap: once the goal leaves the frame, the
agent has no way to hold on to where it was going, so it doubles back through the door it just
used. Candidates that stay inside "change the agent, not the model": memory of the last frame
where the goal was seen, or of the route taken so far.

## Validity notes

- The §9 auto-acknowledgement detector fires on all 18 runs, static arms included. `p03` makes
  the model restate "the goal is ... not visible" and describe walls every step, which hits the
  keyword list. No label depends on it: `ignore_change` also needs ≥ 3 of 5 actions toward the
  bearing, and no R1 `dynamic` run exceeds 2/5. Manual review cleared `ack_step` on every static
  arm and set it to the first genuine reference on each `dynamic` arm (`labels.csv` notes). The
  rubric and thresholds are unchanged. If later rounds rely on the detector, it needs a
  p03-aware keyword list as a new rubric version.
- The R0 column in `results.md` uses Phase 1's manual labels; R1 uses these.
