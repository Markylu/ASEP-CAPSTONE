# R6 Ground-truth pose in the memory log: summary

**The hypothesis held for the loop and failed for success; `a08` dropped (screening).** R6 has
5/18 successes:
- `initial`: 3/6 (R5 6/6);
- `final`: 2/6 (R5 2/6);
- `dynamic`: 0/6 (R5 0/6).

`final` + `dynamic` is 2/12, the same as R5.

The pose log did what it was built for. The turn-around loop is gone:
- two turn-arounds in a row: 0% `final`, 2% `dynamic` (R5 26% / 58%);
- turn-around picks: 7% `final`, 10% `dynamic` (R5 41% / 70%);
- `spin_failure` in 1 of 13 failures (R5 9 of 10);
- `dynamic` runs fly 61–84 m (R5 17–41 m).

Two `final` cells that R5 lost to the loop now succeed. Three new failures took their place:
- **It does not compare its position.** It flies into walls (143 collisions, R5 38), and 65% of
  reasons after a blocked move claim progress.
- **It does arithmetic on the heading.** That turned the drone away from a goal 12 m off, in view.
- **It loses a goal it has seen.** With the sighting line removed, three runs saw the goal, lost
  it, and never found it again.

Two of the three drop conditions are met. One seed per cell: a screen, not an effect size
(`docs/phase2-test-plan.md` §3).
- Pre-registration: [README.md](README.md).
- Probe: [probe/probe.md](probe/probe.md).
- Reasoning analysis: [reasoning_analysis.md](reasoning_analysis.md).

**Not citable.** R6 flew agent `a08` (`e8c66be05bd3`), with prompts `p09` (`7642a3e1056d`) and
`g02` (`bf175c973dfb`), on `Qwen3-VL-30B-A3B`, remote profile, temperature 0.
- It was flown at `3e874ce`, after the probe chose `a08` over `a07`.
- Sittings: 2026-10-17 (maps 1–8), then 2026-10-19 (maps 9–12 and 13–18). Each pause was at the
  operator's request.
- **18 / 18 valid.** Every replay was exact, and every `run.json` matches the round lock.
- Labels were reviewed by Claude and confirmed by the operator on 2026-10-19.

## Result

| Arm | R0 | R1 | R5 | R6 |
|---|---|---|---|---|
| initial | 5/6 | 5/6 | 6/6 | **3/6** |
| final | 0/6 | 2/6 | 2/6 | **2/6** |
| dynamic | 0/6 | 1/6 | 0/6 | **0/6** |

- Of the 13 failures, 11 are `replan_failure`.
- s02va `dynamic` is `timeout`: it got through the new door and lost the goal.
- s03 `dynamic` is `pre_change_failure`: it never reached the trigger.
- **Collisions: 143** (R5 38, R4 101). Every failed run has 2–16.
- Latency per step, both calls, pooled: p50 2.94 s, p95 4.25 s.
- The navigator's prompt is 2,168 tokens at the median (max 3,296).

### Every cell

✓ steps to goal, or ✗ label.

| Site | initial R1 → R5 → R6 | final R1 → R5 → R6 | dynamic R1 → R5 → R6 |
|---|---|---|---|
| s01 | ✓ 14 → ✓ 14 → **✓ 14** | ✗ timeout → ✗ replan → ✗ replan | ✗ replan → ✗ replan → ✗ replan (spin) |
| s02a | ✓ 14 → ✓ 14 → **✓ 14** | ✗ timeout → ✗ replan → **✓ 18** | ✓ 60 → ✗ replan → ✗ replan |
| s02c | ✓ 14 → ✓ 14 → **✓ 14** | ✓ 34 → ✗ replan → ✗ replan | ✗ timeout → ✗ replan → ✗ replan |
| s02va | ✓ 55 → ✓ 19 → ✗ replan | ✗ replan → ✓ 35 → ✗ replan | ✗ timeout → ✗ replan → ✗ timeout |
| s02vc | ✓ 55 → ✓ 19 → ✗ replan | ✓ 24 → ✗ replan → **✓ 54** | ✗ timeout → ✗ replan → ✗ replan |
| s03 | ✗ replan → ✓ 41 → ✗ replan | ✗ replan → ✓ 54 → ✗ replan | ✗ replan → ✗ replan → ✗ pre-change |

**Gains:** s02a `final` (18 steps, 0 collisions) and s02vc `final` (54). R5 lost both to the
loop.

**Losses:**
- s02va and s02vc `initial`: one failure, heading arithmetic at step 12 (§ What the model did).
- s03 on all three arms: one failure, pinned at x = 15.2.
- s02va `final`.

**Fewer independent observations than cells:**
- s01, s02a and s02c `initial` fly the same 14 picks.
- s02va and s02vc `initial` fly the same 60.
- s03 flies the same 60 picks and path on all three arms.

The round holds about 13 independent observations. `initial` 3/6 is 3 observations: one
success, two failures.

## Manipulation check

`python eval/agent_evidence.py eval/phase2/R6_pose_log`, saved as
[manipulation_check.md](manipulation_check.md), against R5's
[manipulation check](../R5_goal_identifier/manipulation_check.md):

| Measure | R5 (initial / final / dynamic) | R6 | Pre-registered expectation |
|---|---|---|---|
| delivery: pose in every manifest; `memory_steps` = earlier valid decisions; re-rendered log has one pose line per move, the last equal to the current pose | – | **894 / 894** each | every decision: passed |
| identifier: goal seen when visible | 100% / 100% / 100% | 100% / 100% / 100% | ≥ 90%: passed |
| identifier agrees with ground truth | 95% / 98% / 99% | 96% / 99% / 98% | – |
| reason cites position | 13% / 10% / 12% | **63% / 71% / 76%** | reported |
| **two turn-arounds in a row** | 1% / 26% / 58% | **0% / 0% / 2%** | `final` ≤ 10%, `dynamic` ≤ 20%: **passed** |
| turn-around pick | 7% / 41% / 70% | **5% / 7% / 10%** | reported |
| revisit | 2% / 41% / 57% | 7% / 19% / 25% | reported |
| same pick as the step before | 61% / 46% / 67% | 57% / 45% / 42% | – |
| reason cites memory | 61% / 52% / 87% | 32% / 33% / 42% | reported |
| reason copied word for word | 0% | 0% | – |

The pose reached the model, and it was read: two thirds of reasons quote it. The loop ended as
predicted. The change took effect.

## What the model did

From [reasoning_analysis.md](reasoning_analysis.md), which reran the R5 scripts on R6's 894
decisions.

**It quotes its position, and does not compare it.**
- 123 forward moves went nowhere (moved < 0.85 m); R5 had 36.
- After one, 80 reasons (65%) still say the drone "has been moving forward" or "moving steadily".
  38 (31%) note it did not move.
- s01 `dynamic`, steps 29–37, quotes "(23.5, 11.5)" step after step and calls it progress.
- s03 is the clearest case, on all three arms:
  - At step 8 it used the log as intended: "the last move (Step 7) did not advance the drone,
    indicating a possible wall".
  - From step 14 it pins at x = 15.2 and flies up and down a wall from y −11 to +11.5, for
    16 collisions.
  - Its reason meanwhile says it is "moving in a straight line along a corridor-like path".

The R5 loop was standing still. R6's failure is flying into walls, and the log shows both
without the model checking.

**It does arithmetic on the heading.**
- 96% of reasons cite the heading in degrees.
- Three times it turned around with the goal in view (3 of 112; R5 0 of 114), each time from
  heading arithmetic.
- At step 12 of s02va and s02vc `initial`, the goal was 12.0 m away to the right. The reason:
  "the drone is currently facing 221 degrees, which is toward the left side of the scene …
  turning around (0) … would reorient the drone to face 41 degrees (221 + 180)". It turned around
  and never saw the goal again.
- Compass words are right in 83% of uses. Wrong: "358 degrees, which is nearly due north"; "330
  degrees, which is toward the upper-left of the image".
- The heading is a map angle, while the markers and the identifier are image-relative. The model
  translates between them, badly.

**It loses a goal it has seen.**
- `a08` has no sighting line, so once the goal leaves the frame, the log holds nothing about it.
- s02va `dynamic` got through the new door and saw the goal at steps 22–24, 13 m away
  (identifier: left, right, left). It lost it at step 25 and wandered for 35 steps.
- s02va and s02vc `initial` lost theirs at step 12, as above.
- R5's line caused the "goal is behind, turn around" spin. It is also what these three runs
  needed. The probe tested only the first case.

**`dynamic`: moving, not through.**
- s02a, s02c and s02vc name the closed door by step 4. s02va never does.
- Every s01/s02 run except s02va stays east of the dividing wall (min x 2.3–5.2) while flying
  61–84 m.
- Flying more does not find the open door. R1's only s02a `dynamic` win backed out to x = 20.9;
  R6 reaches 19.7 and does not go round.

## Against the predictions

| Prediction (README) | Outcome |
|---|---|
| `initial` ≥ 5/6 | **Wrong**: 3/6 (heading arithmetic; s03 wall) |
| `final` ≥ 2/6 | **Held**: 2/6, with two new cells |
| `dynamic` ≥ 2/6 | **Wrong**: 0/6 |
| `final` + `dynamic` ≥ 4/12 | **Wrong**: 2/12 |
| Two turn-arounds in a row: `final` ≤ 10%, `dynamic` ≤ 20% | **Held**: 0% / 2% |
| `spin_failure` in ≤ 3 failed runs | **Held**: 1 |
| Collisions ≤ 20 | **Wrong**: 143 |
| s02c `final` gets through door C | **Wrong** (min x 0.7; 7 collisions, R5 23) |
| If `a08`: `initial` may slow, stays ≥ 5/6 | **Wrong**: it failed rather than slowed |

**Drop criterion: met on two of three.**
- `final` + `dynamic` is 2/12 (≤ 3/12).
- `initial` is 3/6 (≤ 4/6).
- Double turn-arounds fell far below half of R5's, so that condition does not fire: the record
  was used.

`a08` is not carried forward as is. Its pose log is, in some form. It is the first change in
Phase 2 to break the loop.

## For the next round

The open problem is now what the model does with the numbers: it quotes them and does not check
them. The analysis (§8) ranks four options:

1. **Fly `a07`.** It is the pose log plus the sighting line, and passed the same probe (loop
   turn-around 17 / 40).
   - It keeps what recovered a lost goal in R5. That is the cheapest test of §4: it exists, and
     its probe is done.
   - Risk: some "goal behind" turn-arounds may return in `dynamic`.
2. **Code writes the comparison.** "Did not move (blocked)", "back where you were at step 14",
   and the position kept.
   - Targets the 80 progress claims, the collisions and the s03 wall.
   - This is R5's option 3, set aside for raw numbers in this round.
3. **Drop the heading degrees.** Keep the position, or give the heading only as the turn since
   the last step. Targets the goal-in-view turn-arounds and compass errors.
4. **2 + 3 on `a07`**, if the operator accepts two changes in one round, as in R5.

Before the next probe, add frames where the goal was seen 1–5 steps ago and is now out of view.
Also add goal-in-view frames off-centre near 12 m. R6's probe had neither, and both are where
`a08` failed.

## Validity notes

- **s01 `final` attempt a01 was stopped by Claude, not the model.** The runner had been asked to
  pause after map 13. The stop command killed map 13's Godot near step 55 instead. The runner
  marked the attempt invalid ("run.json or metrics.json missing") and set it aside in
  `_attempts/s01/final/seed1/a01/`. a02 flew it whole on resume.
- **s02c `dynamic` attempt a01 was interrupted** at the first pause, which came one map late.
  It was set aside as `a01_interrupted` and flown fresh.
- **Tunnel outage.** Before the second resume, the model tunnel (`:8004`) was down. The operator
  restarted it; nothing flew without it. During the probe, an earlier drop cost 192 spin rows,
  which were rerun after `replay()` was fixed to retry failed rows.
- **Acknowledgement corrections** (`labels.csv`):
  - s02a, s02c, s02vc `dynamic`: 3 → 4. Step 3 describes the frame captured before the doors
    switched (R5's step-3 timing artefact).
  - s01 `dynamic`: cleared. The cube is never named.
  - s02va `dynamic`: cleared. The closed door is never named.

  No label changed.
- **Phantom counts of 1** appear on single frames in 8 runs. No run carries the phantom facet.
- **Static-arm `ack_step` values are cleared**, as in R1–R5.
- **The decider was started from this worktree on port 8012**, because 8000 is the operator's
  tunnel. The runner's `/health` preflight matched the lock.
