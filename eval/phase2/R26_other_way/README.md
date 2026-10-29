# R26: R22K with the other way at the fork

**Agent:** `a50` (`122780a7de8a`) · **Prompt:** `p17` (`cb3578251cfe`) · **Strategist:** `q10` ·
**Memory:** `a17b` · **Status:** laid out 2026-10-29, probe gate pending

Written before flying. Spec: `docs/phase2-test-plan.md`. Built overnight without the operator
(operator, 2026-10-28: "mantain a prefrence for subagents over hard coded tasks": code lists one
more way, the strategist decides when to take it). Second agent at the same SHA: **R26N**, `a51`
(`d96785ba4e1c`) = `a42` (R22, no goal confirmer) with the same change.

## Change

One against `a43` (R22K, 12/18, level with the best), three parts:

- **Item (code, `planner.other_way`).** On every detour call, after the other items: the newest
  along-the-wall end offered at an earlier call made 6 m or more from here, that the drone never
  came within 1.5 m of, not left off as a failed detour, with known floor within 4 m of it. Worded
  "the other way along the wall you met at step N (you never went there), D m back over known
  floor". It stands for up to 24 steps (other detours 12).
- **Situation line (`planner.closed_door_line`).** "A closed door was seen ahead at step(s) …"
  when the doorway confirmer called a reported doorway closed in the last 5 steps.
- **Strategist `q10`** = `q08` + rule 5: a closed door seen and at most one along-the-wall item
  listed (or both followed twice) is a dead end; take the "other way" even though it lies behind.

Parameters and wording: `agent.OTHER_WAY_A50`, in the features, so the sha.

## Evidence

- s03 analysis (subagent, read-only):
  [../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md](../R22K_open_near_unwalled_goal_confirmer/s03_tines_analysis.md).
  The goal is in the chamber behind the exit wall, reached through the door at the end of one
  tine. All five failed s03 `final`/`dynamic` runs of R20, R20K, R22 and R22K that reached the
  crossbar spent 34–46 steps in the tine whose door was shut and 0 in the other. A closed door was
  reported there on 9–15 steps per run. A way out was listed on 25 of 33 dead-end calls and taken
  0 times, and none of those ways led to the other tine.
- Items, no model (`eval/r26_other_way_probe.py items` on R21, R21K, R22, R22K; memory rebuilt at
  every recorded call; [probe/items.txt](probe/items.txt)):

  | | calls | item listed | item good | dead-end cue (closed door, ≤ 1 along) | cue and good |
  |---|---|---|---|---|---|
  | s03, in a tine (`final`/`dynamic`) | 22 | 21 | 21 | 10 | 10 |
  | s02, at the divider | 189 | 108 | 56 | 26 | 19 |

  "Good" on s03 means on free floor in the other tine. On s02 it means 0.5 m or more nearer a door
  open at that step. The first version required known floor within 1.5 m of the end and listed
  the item on only 5 of 22 calls: the other tine had never been seen.
- Smoke (`smoke_run`, R22K's 706 manifests): `a50` 0 failed steps.

## Probe gate

Set before the live probe (`eval/r26_other_way_probe.py run`/`score`, `q10` on the recorded calls
with the item and line added, text only):
- s03 calls in a tine with the dead-end cue: "other way" chosen on ≥ 75%;
- s02: "other way" chosen where it is misleading on ≤ 10% of the s02 calls asked;
- s02 divider: along-the-wall picks no more than 10 points below the recorded `q08` picks.

## Hypothesis

At the s03 dead end the drone goes back to the other tine and reaches the chamber: R26 scores
above R22K.

## Predictions

| Arm | Baseline (R22K, `a43`) | Predicted |
|---|---|---|
| initial | 6 | 6 |
| final | 3 | 3 or 4 (s03) |
| dynamic | 3 | 3 or 4 (s03) |

Total ≥ 13/18.

## Manipulation check

In s03 `final`/`dynamic`: an "other way" item chosen at least once, and steps in the open tine > 0.

## Drop criterion

Not carried forward if the total does not beat R22K's 12/18.

## Builds on

R22K (`a43`).

## Outcome

Not flown.
